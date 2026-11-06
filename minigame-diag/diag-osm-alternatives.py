#!/usr/bin/env python3
"""Street Legends diag: find a real-world map data source the server CAN
reach with REAL data.

ROOT CAUSE (established 2026-11-06 ~02:58 EST, verified from two networks):
  - overpass.osm.ch is a SWISS-REGIONAL Overpass instance: 19 universities
    for a Zurich bbox, ZERO for Toledo (zero universities/colleges in a
    wide Toledo bbox, zero restaurants, zero for a by-name query for
    "University of Toledo", zero pharmacies). It has no data outside
    Switzerland. That is why ALL FOUR OSM endpoints (centers, pharmacies,
    parks, billboards) return [] fast.
  - The data EXISTS: overpass-api.de returns 7 centers for the wide
    Toledo bbox including 'The University of Toledo', 'Davis College',
    'Mercy College', 'University of Toledo at SeaGate Campus' -- but
    /app gets Errno 111 Connection refused from .de, and
    overpass.kumi.systems times out from /app (11.9s).
  - minigame-diag/diag-osm-mirrors.py (2026-11-05) tested 6 mirrors
    from /app and found ONLY osm.ch reachable. It already proved these
    UNREACHABLE from /app, so this probe SKIPS them (unless the env
    override below forces a retest):
      overpass-api.de, overpass.kumi.systems, overpass.private.coffee,
      overpass.nchc.org.tw, overpass.openstreetmap.ru
    (osm.ch is the reachable one -- but Swiss-regional, no US data.)

This probe tests, in order, from /app:
  1. overpass.private.coffee -- SKIPPED (proven unreachable) unless
     OSM_ALT_DIAG_SKIP_PROVEN=0.
  2. overpass.nchc.org.tw -- SKIPPED (proven unreachable) unless forced.
  3. Other full-planet Overpass mirrors NOT tested by the mirrors diag,
     verified to exist (OSM wiki Overpass_API page + DNS, 2026-11-06):
       overpass.atownsend.org, overpass.geofabrik.de,
       overpass.maprva.org, overpass.openplaceguide.org,
       overpass.osm.jp (DNS-verified), overpass.openstreetmap.fr
       (DNS + HTTP 403 -- a server answers there).
     Each gets the REAL centers query for his cell bbox.
  4. Main OSM API (api.openstreetmap.org) -- GET /api/0.6/map?bbox=
     (raw OSM XML). Counts per category: university/college,
     pharmacy, park, highway motorway/trunk/primary/secondary.
     Leading Plan B if no mirror works. Falls back to the smaller
     cell bbox if the wide bbox hits the 50k-node limit (HTTP 400).
  5. Nominatim (nominatim.openstreetmap.org) -- q=pharmacy and
     q=University, viewbox-bounded to Toledo. Fair-use limit 1 req/s
     (the probe waits 1.1s between the two calls).
  6. overpass-api.de over plain HTTP (http://...) -- one shot; TCP
     refused on https, but test it once to close the .de question.

Verdict, exactly one of:
  (a) a named full-planet mirror IS reachable from /app AND returns
      Toledo data -- URL + counts (becomes the new first mirror);
  (b) no mirror works, but the main OSM API returns usable data --
      per-category counts (Plan B: rewrite the four fetchers to
      filter raw map data);
  (c) no mirror works, but Nominatim returns usable data -- counts +
      the fair-use caveat (Plan C);
  (d) NOTHING reachable returns Toledo data -- every candidate with
      its failure (fallback is seeding real data another way).

Read-only: never edits a file, never restarts anything, never calls a
state-changing endpoint. Only network calls are Overpass POSTs and
read-only GETs. Every network call is capped at 15s; a global
~85s deadline skips late candidates with a note instead of hanging.

Run from /app:  python3 minigame-diag/diag-osm-alternatives.py
Test hooks (env): OSM_ALT_DIAG_SKIP_PROVEN (default 1; set 0 to
retest private.coffee / nchc), OSM_ALT_DIAG_EXTRA_MIRRORS
(comma-separated URLs replacing the candidate-3 list),
OSM_ALT_DIAG_DEADLINE_SECS (default 85).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# Reference point: the player, by the University of Toledo.
LAT, LNG = 41.66308, -83.61536
# His grid cell bbox (from diag-osm-empty-fast.py).
CELL_S, CELL_W, CELL_N, CELL_E = 41.65, -83.65, 41.70, -83.60
# Wide Toledo bbox used by the sanity queries: (s, w, n, e).
WIDE_S, WIDE_W, WIDE_N, WIDE_E = 41.60, -83.70, 41.70, -83.50
VIEWBOX = "-83.70,41.60,-83.50,41.70"  # nominatim: minlon,minlat,maxlon,maxlat

MIRROR_BUDGET = 10.0   # seconds per mirror POST
API_BUDGET = 15.0      # seconds per OSM API / Nominatim GET
DEADLINE_SECS = float(os.environ.get("OSM_ALT_DIAG_DEADLINE_SECS", "85"))
SKIP_PROVEN = os.environ.get("OSM_ALT_DIAG_SKIP_PROVEN", "1") != "0"

UA = "StreetLegends-diag/1.0"
MARKER = "OSM_ALTERNATIVES_DIAG_OK"
PARTIAL = "OSM_ALTERNATIVES_DIAG_PARTIAL"

# Candidates 1-2: already proven unreachable from /app by
# diag-osm-mirrors.py (2026-11-05; only osm.ch reachable of 6).
PROVEN_UNREACHABLE = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]
# Candidate 3: verified to exist (OSM wiki Overpass_API page, 2026-11-06)
# but NOT tested by the mirrors diag. Coverage unknown -- that is what
# the real Toledo query below determines.
EXTRA_MIRRORS = os.environ.get("OSM_ALT_DIAG_EXTRA_MIRRORS", "").split(",") \
    if os.environ.get("OSM_ALT_DIAG_EXTRA_MIRRORS") else [
        "https://overpass.atownsend.org/api/interpreter",
        "https://overpass.geofabrik.de/api/interpreter",
        "https://overpass.maprva.org/api/interpreter",
        "https://overpass.openplaceguide.org/api/interpreter",
        "https://overpass.osm.jp/api/interpreter",
        "https://overpass.openstreetmap.fr/api/interpreter",
    ]
EXTRA_MIRRORS = [m.strip() for m in EXTRA_MIRRORS if m.strip()]

CENTERS_QUERY = (
    "[out:json][timeout:25];\n"
    "(\n"
    '  nwr["amenity"="university"](%s,%s,%s,%s);\n'
    '  nwr["amenity"="college"](%s,%s,%s,%s);\n'
    ");\n"
    "out center;\n"
) % (CELL_S, CELL_W, CELL_N, CELL_E, CELL_S, CELL_W, CELL_N, CELL_E)


def _deadline_left(t0):
    return DEADLINE_SECS - (time.time() - t0)


def _post(url, data, budget):
    """POST form-encoded data. Returns (status, elapsed, raw_bytes, err).
    Never raises."""
    body = urllib.parse.urlencode({"data": data}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=budget) as r:
            raw = r.read()
        return r.status, time.time() - t0, raw, None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read()
        except Exception:
            raw = b""
        return e.code, time.time() - t0, raw, "HTTPError: HTTP %s" % e.code
    except Exception as e:  # noqa: BLE001
        return None, time.time() - t0, None, "%s: %s" % (type(e).__name__, e)


def _get(url, budget):
    """GET. Returns (status, elapsed, raw_bytes, err). Never raises."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, application/xml, text/xml",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=budget) as r:
            raw = r.read()
        return r.status, time.time() - t0, raw, None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read()
        except Exception:
            raw = b""
        return e.code, time.time() - t0, raw, "HTTPError: HTTP %s" % e.code
    except Exception as e:  # noqa: BLE001
        return None, time.time() - t0, None, "%s: %s" % (type(e).__name__, e)


def count_centers(payload):
    """Usable centers from an Overpass JSON payload: amenity university /
    college with a real lat/lon (node lat/lon or center). Returns
    (usable_count, [first 3 names]). Never raises."""
    try:
        elements = payload.get("elements", []) or []
    except Exception:
        return 0, []
    names = []
    usable = 0
    for el in elements:
        try:
            tags = el.get("tags") or {}
            if tags.get("amenity") not in ("university", "college"):
                continue
            if el.get("type") == "node":
                lat, lng = el.get("lat"), el.get("lon")
            else:
                c = el.get("center") or {}
                lat, lng = c.get("lat"), c.get("lon")
            if lat is None or lng is None:
                continue
            usable += 1
            if len(names) < 3:
                names.append(tags.get("name") or tags["amenity"])
        except Exception:
            continue
    return usable, names


def parse_osm_map_xml(raw):
    """Count usable categories in raw OSM map XML (api.openstreetmap.org).
    Returns (counts_dict, names_dict, error_or_None). Never raises."""
    counts = {"university_college": 0, "pharmacy": 0, "park": 0,
              "highway_major": 0}
    names = {"university_college": [], "pharmacy": [], "park": [],
             "highway_major": []}
    try:
        root = ET.fromstring(raw)
    except Exception as e:  # noqa: BLE001
        return counts, names, "XML parse failed: %s" % e
    try:
        for el in root:
            if el.tag not in ("node", "way", "relation"):
                continue
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            amenity = tags.get("amenity")
            if amenity in ("university", "college"):
                counts["university_college"] += 1
                if len(names["university_college"]) < 3:
                    names["university_college"].append(
                        tags.get("name") or amenity)
            elif amenity == "pharmacy":
                counts["pharmacy"] += 1
                if len(names["pharmacy"]) < 3:
                    names["pharmacy"].append(tags.get("name") or "pharmacy")
            if tags.get("leisure") == "park":
                counts["park"] += 1
                if len(names["park"]) < 3:
                    names["park"].append(tags.get("name") or "park")
            if tags.get("highway") in ("motorway", "trunk", "primary",
                                       "secondary"):
                counts["highway_major"] += 1
                if len(names["highway_major"]) < 3:
                    names["highway_major"].append(
                        tags.get("name") or tags["highway"])
    except Exception as e:  # noqa: BLE001
        return counts, names, "XML walk failed: %s" % e
    return counts, names, None


def nominatim_search(query, viewbox):
    """One Nominatim search. Returns (status, elapsed, count, [names], err).
    Never raises. Caller must respect the 1 req/s fair-use limit."""
    url = ("https://nominatim.openstreetmap.org/search?q=%s"
           "&viewbox=%s&bounded=1&format=json&limit=10"
           % (urllib.parse.quote(query), urllib.parse.quote(viewbox)))
    status, el, raw, err = _get(url, API_BUDGET)
    if err is not None or raw is None:
        return status, el, 0, [], err
    try:
        items = json.loads(raw.decode("utf-8", "ignore"))
    except Exception as e:  # noqa: BLE001
        return status, el, 0, [], "JSON parse failed: %s" % e
    if not isinstance(items, list):
        return status, el, 0, [], "unexpected payload: %r" % (items,)[:120]
    names = [(it.get("display_name") or "?").split(",")[0]
             for it in items[:3] if isinstance(it, dict)]
    return status, el, len(items), names, None


def main():
    t0 = time.time()
    skipped = []
    mirror_winners = []   # (url, usable, names)
    mirror_failures = []  # (url, reason)
    osm_api_counts = None
    osm_api_names = None
    osm_api_note = ""
    nominatim_results = {}  # query -> (count, names)
    nominatim_failures = []

    print("=== OSM alternatives diag (find a data source /app can reach) ===")
    print("reference point: lat=%s lng=%s (University of Toledo); "
          "cell bbox s=%s w=%s n=%s e=%s"
          % (LAT, LNG, CELL_S, CELL_W, CELL_N, CELL_E))
    print("proven unreachable by diag-osm-mirrors.py (only osm.ch of 6 "
          "reachable): overpass-api.de, overpass.kumi.systems, "
          "overpass.private.coffee, overpass.nchc.org.tw, "
          "overpass.openstreetmap.ru")
    print("osm.ch is reachable BUT Swiss-regional: 0 Toledo elements "
          "(root cause). This probe tests what the mirrors diag did NOT.")

    # ---------- 1-2: private.coffee / nchc (skip unless forced) ----------
    print("=== 1-2. private.coffee / nchc (proven unreachable) ===")
    for url in PROVEN_UNREACHABLE:
        if SKIP_PROVEN:
            print("mirror %s: SKIPPED (already proven unreachable from /app "
                  "by diag-osm-mirrors.py; set OSM_ALT_DIAG_SKIP_PROVEN=0 "
                  "to retest)" % url)
            skipped.append(url)
            continue
        if _deadline_left(t0) < MIRROR_BUDGET + 2:
            print("mirror %s: SKIPPED (global deadline)" % url)
            skipped.append(url)
            continue
        status, el, raw, err = _post(url, CENTERS_QUERY, MIRROR_BUDGET)
        _report_mirror(url, status, el, raw, err, mirror_winners,
                       mirror_failures)

    # ---------- 3: other verified mirrors ----------
    print("=== 3. other Overpass mirrors (verified to exist, NOT tested "
          "by the mirrors diag) ===")
    for url in EXTRA_MIRRORS:
        if _deadline_left(t0) < MIRROR_BUDGET + 2:
            print("mirror %s: SKIPPED (global deadline)" % url)
            skipped.append(url)
            continue
        status, el, raw, err = _post(url, CENTERS_QUERY, MIRROR_BUDGET)
        _report_mirror(url, status, el, raw, err, mirror_winners,
                       mirror_failures)

    # ---------- 4: main OSM API (raw map data) ----------
    print("=== 4. main OSM API api.openstreetmap.org (raw map XML) ===")
    if _deadline_left(t0) < API_BUDGET + 2:
        print("OSM API: SKIPPED (global deadline)")
        skipped.append("osm-api")
    else:
        wide_bbox = "%s,%s,%s,%s" % (WIDE_W, WIDE_S, WIDE_E, WIDE_N)
        url = ("https://api.openstreetmap.org/api/0.6/map?bbox=%s"
               % wide_bbox)
        status, el, raw, err = _get(url, API_BUDGET)
        used_bbox = "wide"
        if status == 400 and raw and b"too many nodes" in raw.lower():
            print("OSM API wide bbox: HTTP 400 too many nodes in %.1fs -- "
                  "retrying the smaller cell bbox" % el)
            cell_bbox = "%s,%s,%s,%s" % (CELL_W, CELL_S, CELL_E, CELL_N)
            url2 = ("https://api.openstreetmap.org/api/0.6/map?bbox=%s"
                    % cell_bbox)
            status, el, raw, err = _get(url2, API_BUDGET)
            used_bbox = "cell"
        if status == 400 and raw and b"too many nodes" in raw.lower():
            # Even a 0.05-degree cell is too node-dense (urban area).
            # One last try: a 0.02-degree box around the player point.
            print("OSM API cell bbox: HTTP 400 too many nodes in %.1fs -- "
                  "retrying a 0.02-degree box around the player" % el)
            tiny_bbox = "%.5f,%.5f,%.5f,%.5f" % (LNG - 0.01, LAT - 0.01,
                                                  LNG + 0.01, LAT + 0.01)
            url3 = ("https://api.openstreetmap.org/api/0.6/map?bbox=%s"
                    % tiny_bbox)
            status, el, raw, err = _get(url3, API_BUDGET)
            used_bbox = "tiny(0.02deg)"
        if err is not None or raw is None or status != 200:
            body = ""
            if raw:
                try:
                    body = " body=%r" % raw.decode("utf-8", "ignore")[:160]
                except Exception:
                    body = ""
            print("OSM API (%s bbox): FAILED status=%s in %.1fs err=%s%s"
                  % (used_bbox, status, el, err, body))
            osm_api_note = ("FAILED status=%s err=%s%s"
                            % (status, err, body))
        else:
            counts, names, perr = parse_osm_map_xml(raw)
            if perr:
                print("OSM API (%s bbox): 200 in %.1fs but %s"
                      % (used_bbox, el, perr))
                osm_api_note = perr
            else:
                osm_api_counts, osm_api_names = counts, names
                print("OSM API (%s bbox): 200 in %.1fs bytes=%d "
                      "university/college=%d %s pharmacy=%d %s park=%d %s "
                      "highway(motorway/trunk/primary/secondary)=%d %s"
                      % (used_bbox, el, len(raw),
                         counts["university_college"],
                         names["university_college"],
                         counts["pharmacy"], names["pharmacy"],
                         counts["park"], names["park"],
                         counts["highway_major"],
                         names["highway_major"]))

    # ---------- 5: Nominatim ----------
    print("=== 5. Nominatim (fair use: max 1 req/s) ===")
    for q in ("pharmacy", "University"):
        if _deadline_left(t0) < API_BUDGET + 2:
            print("Nominatim q=%r: SKIPPED (global deadline)" % q)
            skipped.append("nominatim:%s" % q)
            continue
        status, el, count, names, err = nominatim_search(q, VIEWBOX)
        if err is not None:
            print("Nominatim q=%r: FAILED status=%s in %.1fs err=%s"
                  % (q, status, el, err))
            nominatim_failures.append((q, err))
        else:
            nominatim_results[q] = (count, names)
            print("Nominatim q=%r: 200 in %.1fs count=%d sample=%s"
                  % (q, el, count, names))
        time.sleep(1.1)  # Nominatim fair-use limit: 1 request per second

    # ---------- 6: .de over plain HTTP ----------
    print("=== 6. overpass-api.de over plain HTTP (long shot) ===")
    if _deadline_left(t0) < MIRROR_BUDGET + 2:
        print("http://overpass-api.de: SKIPPED (global deadline)")
        skipped.append("http-overpass-api.de")
    else:
        status, el, raw, err = _post(
            "http://overpass-api.de/api/interpreter", CENTERS_QUERY,
            MIRROR_BUDGET)
        if status == 200 and raw:
            try:
                payload = json.loads(raw.decode("utf-8", "ignore"))
                usable, names = count_centers(payload)
            except Exception:
                usable, names = 0, []
            print("http://overpass-api.de: 200 in %.1fs bytes=%d "
                  "usable centers=%d %s" % (el, len(raw), usable, names))
            if usable > 0:
                mirror_winners.append(
                    ("http://overpass-api.de/api/interpreter", usable,
                     names))
            else:
                mirror_failures.append(
                    ("http://overpass-api.de", "200 but 0 usable centers"))
        else:
            print("http://overpass-api.de: FAILED status=%s in %.1fs "
                  "err=%s" % (status, el, err))
            mirror_failures.append(
                ("http://overpass-api.de",
                 "status=%s err=%s" % (status, err)))

    # ---------- verdict ----------
    print("=== VERDICT ===")
    for url, usable, names in mirror_winners:
        print("mirror WINNER: %s usable centers=%d %s"
              % (url, usable, names))
    for url, reason in mirror_failures:
        print("mirror failure: %s -- %s" % (url, reason))
    if osm_api_counts is not None:
        print("OSM API counts: %s names: %s"
              % (osm_api_counts, osm_api_names))
    else:
        print("OSM API: no usable data (%s)" % (osm_api_note or "skipped"))
    print("Nominatim: %s failures: %s"
          % ({q: v[0] for q, v in nominatim_results.items()},
             nominatim_failures))
    verdict = None
    detail = ""
    if mirror_winners:
        url, usable, names = mirror_winners[0]
        verdict = "(a)"
        detail = ("full-planet mirror %s IS reachable from /app and "
                  "returns Toledo data: %d usable centers %s -- use it "
                  "as the new FIRST entry of OSM_OVERPASS_MIRRORS"
                  % (url, usable, names))
    elif osm_api_counts is not None and any(
            v > 0 for v in osm_api_counts.values()):
        verdict = "(b)"
        detail = ("no mirror works, but the main OSM API returns usable "
                  "Toledo data: %s (sample names %s) -- Plan B: rewrite "
                  "the four fetchers to filter raw map data from "
                  "api.openstreetmap.org" % (osm_api_counts, osm_api_names))
    elif any(c > 0 for c, _ in nominatim_results.values()):
        verdict = "(c)"
        detail = ("no mirror works and no OSM API data, but Nominatim "
                  "returns usable data: %s -- Plan C: use Nominatim, "
                  "respecting the 1 req/s fair-use limit (one query per "
                  "second, cached per grid cell)"
                  % ({q: v[0] for q, v in nominatim_results.items()},))
    else:
        verdict = "(d)"
        fails = "; ".join("%s: %s" % (u, r)
                          for u, r in mirror_failures)
        detail = ("NOTHING reachable returns Toledo data. Mirror "
                  "failures: %s. OSM API: %s. Nominatim failures: %s. "
                  "Fallback: seed real data another way (e.g. a data "
                  "dump fetched from this VM and loaded into the DB)."
                  % (fails or "none recorded",
                     osm_api_note or "no data",
                     nominatim_failures or "none"))
    print("VERDICT: %s %s" % (verdict, detail))
    if skipped:
        print("skipped checks: %s" % ", ".join(skipped))
    partial = (verdict == "(d)" and not mirror_failures
               and osm_api_counts is None and not nominatim_results
               and not nominatim_failures)
    print((PARTIAL if partial else MARKER) + " verdict=%s" % verdict)
    return 0


def _report_mirror(url, status, el, raw, err, winners, failures):
    """Print one mirror result; record winner/failure. Never raises."""
    if err is not None or raw is None or status != 200:
        print("mirror %s: FAILED status=%s in %.1fs err=%s"
              % (url, status, el, err))
        failures.append((url, "status=%s err=%s" % (status, err)))
        return
    try:
        payload = json.loads(raw.decode("utf-8", "ignore"))
        usable, names = count_centers(payload)
    except Exception as e:  # noqa: BLE001
        print("mirror %s: 200 in %.1fs but payload unparsable: %s"
              % (url, el, e))
        failures.append((url, "unparsable payload"))
        return
    print("mirror %s: 200 in %.1fs bytes=%d elements=%d usable centers=%d "
          "%s" % (url, el, len(raw),
                  len(payload.get("elements", []) or []), usable, names))
    if usable > 0:
        winners.append((url, usable, names))
    else:
        failures.append((url, "200 but 0 usable centers"))


if __name__ == "__main__":
    sys.exit(main())
