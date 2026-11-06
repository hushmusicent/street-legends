#!/usr/bin/env python3
"""Street Legends backend: send a whitelisted User-Agent on every Overpass
httpx call (activity centers, pharmacies, parks, billboards).

Run from repo root: python3 backend/patch-osm-user-agent.py
Backend only. Idempotent - safe to re-run.

ROOT CAUSE (2026-11-06, proven live by minigame-diag/diag-osm-backend-fetch-v2.py):
  - From the SAME python on /app: httpx direct to
    https://overpass.openstreetmap.fr/api/interpreter -> 403 in 0.4s,
    0 elements; urllib direct to the same URL -> 200 in 0.8s, 2 elements
    (Davis College + The University of Toledo). No proxy env set.
  - The four OSM fetch functions call Overpass with httpx.AsyncClient
    and NO headers, so httpx sends its default User-Agent
    (python-httpx/x.y.z). openstreetmap.fr answers that with 403 and the
    body "This service is only available to white-listed usages".
  - The same mirror answers 200 with the 2 centers for a descriptive
    application User-Agent: "StreetLegends/1.0 (+https://www.hushmusicent.com)".
  - So every backend Overpass call 403s, the mirror loop falls through
    to osm.ch (Swiss-only, empty) -> .de (refused) -> kumi (timeout),
    and the endpoint returns [] after burning the ~10s budget.
  - The older place fetchers (banks, restaurants, nightclubs, gas
    stations) already send their own User-Agent headers and are NOT
    touched by this patch.

FIX: add headers={"User-Agent": "StreetLegends/1.0 (+https://www.hushmusicent.com)"}
to the httpx.AsyncClient call in each of the four OSM fetch functions.
The UA is written as a plain string literal, never a unicode escape.
Timeouts, budgets, mirrors, cache epoch, queries, and the no-fallback
rule are untouched.

IN-RUN CHECK: after editing, if /opt/plugins-venv/bin/python exists on
this host, a subprocess runs an httpx POST of the centers query for his
cell to .fr with the new UA and prints UA_CHECK with the status and
element count. A 200 + 2 elements proves the exact client + UA the
backend uses is accepted from /app. The live endpoint test after
Publish is the final proof.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "OSM_USER_AGENT_OK"
UA = "StreetLegends/1.0 (+https://www.hushmusicent.com)"
UA_CHECK_PYTHON = "/opt/plugins-venv/bin/python"
UA_CHECK_URL = "https://overpass.openstreetmap.fr/api/interpreter"
# His cell bbox (s, w, n, e) -- the same query the centers handler uses.
UA_CHECK_QUERY = (
    "[out:json][timeout:25];\n"
    "(\n"
    '  nwr["amenity"="university"](41.65,-83.65,41.7,-83.6);\n'
    '  nwr["amenity"="college"](41.65,-83.65,41.7,-83.6);\n'
    ");\n"
    "out center;\n"
)

ENDPOINTS = [
    {"name": "activity-centers", "fetch_fn": "_activity_center_fetch_cell"},
    {"name": "pharmacies", "fetch_fn": "_pharmacy_fetch_cell"},
    {"name": "parks", "fetch_fn": "_park_fetch_cell"},
    {"name": "billboards", "fetch_fn": "_billboard_fetch_cell"},
]

# The httpx client shapes the live fetch functions can have (fast-patched
# mirror loop first, then the original v2 single-URL shape). The generic
# fallback below covers any other plain timeout=... form.
CLIENT_FORMS = [
    "httpx.AsyncClient(timeout=OSM_CELL_TIMEOUT)",
    "httpx.AsyncClient(timeout=30.0)",
]


def _fn_span(src, fn_name):
    """(start, end) char offsets of one fetch function, or (None, None).

    Ends at the next top-level def/decorator or 6000 chars in, whichever
    comes first -- never a file-wide search.
    """
    start = src.find("async def %s(" % fn_name)
    if start == -1:
        return None, None
    nxt = src.find("\nasync def ", start + 1)
    dec = src.find("\n@api_router", start + 1)
    ends = [e for e in (nxt, dec) if e != -1]
    end = min(ends) if ends else start + 6000
    return start, min(end, start + 6000)


def _ua_check():
    """POST the centers query to .fr with the new UA, using the
    plugins-venv python if it exists. Prints one UA_CHECK line."""
    if not Path(UA_CHECK_PYTHON).exists():
        print("UA_CHECK_SKIPPED: plugins-venv python not found (%s)" % UA_CHECK_PYTHON)
        return
    lines = [
        "import json",
        "import httpx",
        "q = %r" % UA_CHECK_QUERY,
        "try:",
        "    with httpx.Client(headers={'User-Agent': %r}, timeout=20) as c:" % UA,
        "        r = c.post(%r, data={'data': q})" % UA_CHECK_URL,
        "    els = r.json().get('elements', []) if r.status_code == 200 else []",
        "    names = [e.get('tags', {}).get('name') for e in els]",
        "    print(json.dumps({'status': r.status_code, 'elements': len(els), 'names': names}))",
        "except Exception as e:",
        "    print(json.dumps({'status': None, 'error': str(e), 'elements': 0, 'names': []}))",
    ]
    script = "\n".join(lines) + "\n"
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            tf.write(script)
            tmp = tf.name
        out = subprocess.run(
            [UA_CHECK_PYTHON, tmp], capture_output=True, text=True, timeout=40
        )
        line = (out.stdout or "").strip().splitlines()
        data = json.loads(line[-1]) if line else {}
    except Exception as e:
        print("UA_CHECK_FAILED: could not run check (%s)" % e)
        return
    status = data.get("status")
    if status == 200:
        print("UA_CHECK: status=200 elements=%s names=%s"
              % (data.get("elements"), data.get("names")))
    elif status is not None:
        print("UA_CHECK_FAILED: status=%s elements=%s"
              % (status, data.get("elements")))
    else:
        print("UA_CHECK_FAILED: %s" % data.get("error"))


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - OSM User-Agent NOT added")
        return 1
    src = SERVER.read_text()
    orig = src
    warnings = []
    landed = []

    for ep in ENDPOINTS:
        name = ep["name"]
        fn = ep["fetch_fn"]
        start, end = _fn_span(src, fn)
        if start is None:
            print("WARNING: %s fetch function not found - User-Agent NOT added "
                  "(looked for 'async def %s(')" % (name, fn))
            warnings.append("%s-fetch-fn" % name)
            continue
        span = src[start:end]
        if UA in span:
            print("ALREADY_APPLIED: %s fetch already sends the User-Agent" % name)
            landed.append(name)
            continue
        new_span = None
        for form in CLIENT_FORMS:
            if form in span:
                new_span = span.replace(
                    form,
                    form[:-1] + ', headers={"User-Agent": "%s"}' % UA + ")",
                    1,
                )
                print("OK: %s fetch sends User-Agent (client %s)"
                      % (name, form.split("(")[1].split(")")[0]))
                break
        if new_span is None:
            # Generic fallback: exactly one bare AsyncClient(timeout=...) in
            # this function -- add the header to it, whatever its timeout.
            bare = re.findall(r"httpx\.AsyncClient\(timeout=[^)]+\)", span)
            if len(bare) == 1 and "headers=" not in bare[0]:
                new_span = span.replace(
                    bare[0],
                    bare[0][:-1] + ', headers={"User-Agent": "%s"}' % UA + ")",
                    1,
                )
                print("OK: %s fetch sends User-Agent (client %s)"
                      % (name, bare[0]))
            elif len(bare) == 0:
                print("WARNING: %s AsyncClient anchor not found - User-Agent NOT added "
                      "(looked for 'httpx.AsyncClient(timeout=' in %s)" % (name, fn))
                warnings.append("%s-client-anchor" % name)
                continue
            else:
                print("WARNING: %s AsyncClient anchor matched %dx - User-Agent NOT added "
                      "(expected exactly 1 bare client in %s)" % (name, len(bare), fn))
                warnings.append("%s-client-ambiguous" % name)
                continue
        src = src[:start] + new_span + src[end:]
        landed.append(name)

    # Safety net: no Overpass httpx call left bare. Every AsyncClient in
    # the file must have a User-Agent nearby -- either on the client (the
    # four OSM fetchers) or on the post call (the older place fetchers,
    # which already send their own UA and are NOT touched here). Only
    # Overpass calls are flagged: a bare client counts only if an
    # Overpass marker (_osm_url, overpass_url, OVERPASS_URLS,
    # OSM_OVERPASS_MIRRORS, or the Overpass data= post) follows it.
    # Non-Overpass httpx calls (TV schedule, webhooks, ...) are out of
    # scope and are never flagged.
    bare_sites = []
    for m in re.finditer(r"httpx\.AsyncClient\(", src):
        window = src[m.start():m.start() + 900]
        if "User-Agent" not in window and (
            "_osm_url" in window
            or "overpass_url" in window
            or "OVERPASS_URLS" in window
            or "OSM_OVERPASS_MIRRORS" in window
            or 'data={"data": query}' in window
        ):
            line_no = src[:m.start()].count("\n") + 1
            bare_sites.append(line_no)
    if bare_sites:
        print("WARNING: %d httpx.AsyncClient call(s) left without a nearby "
              "User-Agent (lines %s) - check them, the four OSM fetchers "
              "are covered above" % (len(bare_sites), bare_sites))
        warnings.append("bare-clients")

    if src == orig:
        if len(landed) == 4 and not warnings:
            print("OSM_USER_AGENT_ALREADY_APPLIED")
        else:
            print("OSM_USER_AGENT_PARTIAL: already-applied "
                  "(warnings: %s)" % ", ".join(warnings))
        _ua_check()
        return 0

    # Syntax check before writing; restore on failure.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    try:
        tmp.write(src)
        tmp.close()
        import py_compile
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("WARNING: patched server.py failed syntax check - NOT written (%s)" % e)
        return 1
    SERVER.write_text(src)
    _ua_check()
    if warnings:
        print("OSM_USER_AGENT_PARTIAL: " + ", ".join(landed) +
              " (warnings: " + ", ".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
