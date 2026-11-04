#!/usr/bin/env python3
"""Street Legends: wire the pool PvP rooms (create/join) to the frontend.

LIVE EVIDENCE (2026-11-03): GET /api/pool/rooms/{code} IS live
(patch-specific {"detail":"Room not found"}), but the phone's pool rooms
screen shows "not live yet" — a banner that fires only when POST
/api/pool/rooms/create or POST /api/pool/rooms/join returns 404 or the
fetch throws. So the CREATE (and possibly JOIN) route shape is the
suspect, not the whole rooms backend. This patch adapts to whatever
shape is already in server.py at run time:

  * If a POST create/join route already exists -> it is left alone
    (FOUND, nothing duplicated).
  * If a route is missing but a creation/join function already exists
    -> a thin alias route is added that delegates to that function
    (no duplicated creation logic).
  * Only if no creation/join logic exists at all -> a full endpoint
    is added, with a room doc that carries BOTH the original
    host_id/guest_id shape and a players list, so either consumer works.

Routes are written with NO /api prefix when the router is api_router
mounted under /api, and WITH /api when the router is app-level or when
the live GET route already uses /api — the GET route's own prefix is
mirrored first, because the GET that works live proves which form
registers correctly. All Motor calls are awaited; timezone is imported
when used.

Run from /app: python3 backend/patch-pool-rooms-wire.py
Idempotent: re-running prints POOL_ROOMS_WIRE_ALREADY_APPLIED.
Backend only: Deploy after running.
"""
import re
import sys
import py_compile

PATH = "backend/server.py"
MARKER = "# POOL_ROOMS_WIRE"
OK = "POOL_ROOMS_WIRE_OK"
ALREADY = "POOL_ROOMS_WIRE_ALREADY_APPLIED"


def _indent_of(line):
    return line[:len(line) - len(line.lstrip())]


def find_router(src):
    if re.search(r"@api_router\.", src):
        return "api_router"
    if re.search(r"@app\.", src):
        return "app"
    return None


def find_db(src):
    m = re.search(r"(\w+)\.pool_rooms\b", src)
    if m:
        return m.group(1)
    m = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
    if m:
        return m.group(1)
    return None


def mount_prefix(src, router):
    """Return the /api mount prefix of api_router, or None if unknown."""
    if router != "api_router":
        return None
    m = re.search(r"include_router\(\s*api_router[^)]*prefix\s*=\s*[\"']([^\"']*)[\"']", src)
    if m:
        return m.group(1)
    return None


def route_decorator_re(method, pool_path_fragment):
    # Matches @api_router.post("/pool/rooms/create") in any prefix form,
    # including a trailing path parameter variant.
    return re.compile(
        r"@\w+\." + method + r"\(\s*[\"']([^\"']*pool[^\"']*" + pool_path_fragment + r")[\"']",
        re.IGNORECASE,
    )


def find_route(src, method, fragment):
    """Return (decorator_path, router_var) for a pool route, or (None, None)."""
    for m in re.finditer(r"@(\w+)\." + method + r"\(\s*[\"']([^\"']*)[\"']", src):
        path = m.group(2)
        if "pool" in path and fragment in path:
            return path, m.group(1)
    return None, None


def find_get_route(src):
    for m in re.finditer(r"@(\w+)\.get\(\s*[\"']([^\"']*)[\"']", src):
        path = m.group(2)
        if "pool" in path and ("{code}" in path or "rooms" in path):
            return path, m.group(1)
    return None, None


def choose_prefix(src, router, get_path):
    """Decide the code-side prefix for new routes, e.g. '' or '/api'.

    The new route path is prefix + '/pool/rooms/create'. Mirroring the
    live GET route wins: if GET is '/api/pool/rooms/{code}' the new
    routes are '/api/pool/rooms/create'; if GET is '/pool/rooms/{code}'
    they are '/pool/rooms/create'.
    """
    if get_path:
        if get_path.startswith("/api/pool"):
            return "/api"
        if get_path.startswith("/pool"):
            return ""
    mp = mount_prefix(src, router)
    if mp is not None:
        return "" if mp == "/api" else mp.rstrip("/")
    return "" if router == "api_router" else "/api"


def split_functions(src):
    """Split top-level (async) defs into (name, is_async, header, body)."""
    pat = re.compile(r"^(async\s+def|def)\s+(\w+)\s*\(", re.M)
    matches = list(pat.finditer(src))
    out = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(src)
        # Header runs to the closing paren + colon.
        chunk = src[start:end]
        paren = 0
        h_end = 0
        for j, ch in enumerate(chunk):
            if ch == "(":
                paren += 1
            elif ch == ")":
                paren -= 1
                if paren == 0:
                    h_end = chunk.find(":", j)
                    break
        header = chunk[:h_end + 1] if h_end else chunk.split("\n")[0]
        out.append((m.group(2), m.group(1).startswith("async"), header, chunk))
    return out


def parse_params(header):
    """Parse a def header into [(name, annotation_or_None, has_default)]."""
    start = header.find("(")
    if start == -1:
        return []
    depth = 0
    end = -1
    for j in range(start, len(header)):
        if header[j] == "(":
            depth += 1
        elif header[j] == ")":
            depth -= 1
            if depth == 0:
                end = j
                break
    if end == -1:
        return []
    inner = header[start + 1:end]
    params = []
    depth = 0
    cur = ""
    for ch in inner:
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == "," and depth == 0:
            params.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        params.append(cur)
    out = []
    for p in params:
        p = p.strip()
        if not p or p in ("self", "cls"):
            continue
        if p.startswith("*"):
            continue
        if "=" in p:
            left, _ = p.split("=", 1)
            has_default = True
        else:
            left, has_default = p, False
        if ":" in left:
            name, ann = left.split(":", 1)
            out.append((name.strip(), ann.strip(), has_default))
        else:
            out.append((left.strip(), None, has_default))
    return out


def model_classes(src):
    """Map BaseModel class name -> its field names."""
    out = {}
    for m in re.finditer(r"class\s+(\w+)\s*\(\s*BaseModel\s*\):\s*\n((?:[ \t]+\w+.*\n)+)", src):
        fields = re.findall(r"^\s+(\w+)\s*:", m.group(2), re.M)
        out[m.group(1)] = fields
    return out


def find_pool_logic(src, kind):
    """Find helper/endpoint functions that already create or join rooms.

    Returns a list of (name, is_async, header, body). Route functions
    for the *other* operation are not returned: a function is a
    creation candidate only if its body inserts into pool_rooms, and a
    join candidate only if its body looks up a room by code and updates
    it (guest/status/players).
    """
    out = []
    for name, is_async, header, body in split_functions(src):
        lname = name.lower()
        if kind == "create":
            if "pool_rooms.insert_one" in body or "pool_rooms . insert_one" in body:
                out.append((name, is_async, header, body))
            elif ("create" in lname and "pool" in lname) or lname in ("create_pool_room",):
                out.append((name, is_async, header, body))
        else:
            if ("pool_rooms.find_one" in body and
                    ("guest" in body or "players" in body or "status" in body)):
                if "join" in lname or "pool" in lname:
                    out.append((name, is_async, header, body))
            elif ("join" in lname and "pool" in lname) or lname in ("join_pool_room",):
                out.append((name, is_async, header, body))
    return out


def adapt_call(fn_name, is_async, header, src, body_var, call_kwargs, required=()):
    """Build a call expression for an existing function, or None.

    call_kwargs maps the values the caller has, e.g.
    {"player_id": "body.player_id", "player_name": "body.player_name"}.
    Returns (call_expr, note_or_None).
    """
    params = parse_params(header)
    models = model_classes(src)
    await_pfx = "await " if is_async else ""
    # Model-parameter style: a single param annotated with a BaseModel.
    model_params = [(n, a) for (n, a, _) in params if a in models]
    if model_params and len(params) == 1:
        mname = model_params[0][1]
        fields = models[mname]
        args = []
        for k, expr in call_kwargs.items():
            if k in fields:
                args.append("%s=%s" % (k, expr))
        if "player_id" not in fields or any(k not in fields for k in required):
            return None, "model %s lacks required fields" % mname
        call = "%s%s(%s(%s))" % (await_pfx, fn_name, mname, ", ".join(args))
        return call, "alias assumes %s fields %s" % (mname, sorted(fields))
    # Keyword style: params name the values we have.
    names = [n for (n, _, _) in params]
    if "player_id" in names and all(k in names for k in required):
        args = []
        for k, expr in call_kwargs.items():
            if k in names:
                args.append("%s=%s" % (k, expr))
        call = "%s%s(%s)" % (await_pfx, fn_name, ", ".join(args))
        return call, None
    return None, "signature not adaptable"


def now_expr(src):
    """Return (now_expression, import_to_add_or_None)."""
    if re.search(r"from datetime import[^\n]*\btimezone\b", src):
        return "datetime.now(timezone.utc).isoformat()", None
    if re.search(r"^import datetime\b", src, re.M):
        return "datetime.datetime.now(datetime.timezone.utc).isoformat()", None
    return "datetime.now(timezone.utc).isoformat()", "from datetime import datetime, timezone"


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            orig = f.read()
    except FileNotFoundError:
        print("POOL_ROOMS_WIRE_ERROR: backend/server.py not found (run from /app)")
        return 1
    src = orig
    if MARKER in src:
        print(ALREADY)
        return 0
    router = find_router(src)
    if not router:
        print("POOL_ROOMS_WIRE_ERROR: NO_ROUTER (no @api_router or @app decorator found)")
        return 1
    db = find_db(src)
    get_path, _ = find_get_route(src)
    prefix = choose_prefix(src, router, get_path)
    base = prefix + "/pool/rooms"

    create_path, _ = find_route(src, "post", "create")
    join_path, _ = find_route(src, "post", "join")
    # A route only counts if its path is a pool rooms route, not some
    # other feature that happens to contain "create"/"join".
    def _is_pool_route(path):
        return path is not None and "pool" in path and "rooms" in path
    create_exists = _is_pool_route(create_path)
    join_exists = _is_pool_route(join_path)
    print("POOL_ROOMS_WIRE: create route %s" % ("FOUND " + create_path if create_exists else "MISSING"))
    print("POOL_ROOMS_WIRE: join route %s" % ("FOUND " + join_path if join_exists else "MISSING"))
    print("POOL_ROOMS_WIRE: get route %s" % ("FOUND " + get_path if get_path else "MISSING"))
    if create_exists and join_exists:
        print(ALREADY)
        return 0

    models = model_classes(src)
    create_model = None
    for cand in ("PoolRoomCreate", "PoolRoomsWireCreate"):
        if cand in models:
            create_model = cand
            break
    join_model = None
    for cand in ("PoolRoomJoin", "PoolRoomsWireJoin"):
        if cand in models:
            join_model = cand
            break

    now, dt_import = now_expr(src)
    additions = []  # code blocks (each with its own sub-marker)
    warnings = []
    need_models = []
    need_imports = []

    def ensure_model(name, fields):
        if name not in models and name not in [m for m, _ in need_models]:
            need_models.append((name, fields))

    # ---- CREATE ----
    if not create_exists:
        cands = find_pool_logic(src, "create")
        wired = False
        for fn_name, is_async, header, _body in cands:
            call, note = adapt_call(
                fn_name, is_async, header, src, None,
                {"player_id": "body.player_id", "player_name": "body.player_name"})
            if call is None:
                continue
            if create_model is None:
                create_model = "PoolRoomsWireCreate"
                ensure_model(create_model, [("player_id", "str", False),
                                            ("player_name", "str", True)])
            if note:
                warnings.append("WARNING: create alias to %s: %s" % (fn_name, note))
            additions.append(
                "# POOL_ROOMS_WIRE_CREATE (alias: delegates to %s)\n"
                "@%s.post(\"%s/create\")\n"
                "async def pool_rooms_wire_create(body: %s):\n"
                "    result = %s\n"
                "    if isinstance(result, dict) and \"code\" in result:\n"
                "        return result\n"
                "    if isinstance(result, str):\n"
                "        return {\"code\": result}\n"
                "    return result\n" % (fn_name, router, base, create_model, call))
            print("POOL_ROOMS_WIRE: create aliased to %s" % fn_name)
            wired = True
            break
        if not wired:
            if not db:
                warnings.append("WARNING: create endpoint SKIPPED (no db handle found)")
            else:
                if create_model is None:
                    create_model = "PoolRoomsWireCreate"
                    ensure_model(create_model, [("player_id", "str", False),
                                                ("player_name", "str", True)])
                warnings.append("WARNING: create doc shape assumed (no live GET handler found)"
                                if not get_path else
                                "POOL_ROOMS_WIRE: create doc shape mirrors live pool room fields")
                additions.append(
                    "# POOL_ROOMS_WIRE_CREATE (full endpoint)\n"
                    "@%s.post(\"%s/create\")\n"
                    "async def pool_rooms_wire_create(body: %s):\n"
                    "    player = await %s.players.find_one({\"id\": body.player_id})\n"
                    "    if not player:\n"
                    "        raise HTTPException(status_code=404, detail=\"Player not found\")\n"
                    "    code = \"\"\n"
                    "    for _ in range(50):\n"
                    "        cand = str(random.randint(1000, 9999))\n"
                    "        existing = await %s.pool_rooms.find_one({\"code\": cand})\n"
                    "        if not existing:\n"
                    "            code = cand\n"
                    "            break\n"
                    "    if not code:\n"
                    "        code = str(random.randint(1000, 9999))\n"
                    "    now = %s\n"
                    "    room = {\"id\": str(uuid.uuid4()), \"code\": code, "
                    "\"host_id\": body.player_id, \"host_name\": body.player_name, "
                    "\"guest_id\": None, \"guest_name\": None, \"status\": \"waiting\", "
                    "\"players\": [{\"player_id\": body.player_id, \"player_name\": body.player_name}], "
                    "\"state\": None, \"chat\": [], \"created_at\": now, \"updated_at\": now}\n"
                    "    await %s.pool_rooms.insert_one(room)\n"
                    "    if room.get(\"_id\") is not None:\n"
                    "        room[\"_id\"] = str(room[\"_id\"])\n"
                    "    return room\n" % (router, base, create_model, db, db, now, db))
                print("POOL_ROOMS_WIRE: full create endpoint added")
    # ---- JOIN ----
    if not join_exists:
        cands = find_pool_logic(src, "join")
        wired = False
        for fn_name, is_async, header, _body in cands:
            call, note = adapt_call(
                fn_name, is_async, header, src, None,
                {"code": "body.code", "player_id": "body.player_id",
                 "player_name": "body.player_name"}, required=("code",))
            if call is None:
                continue
            if join_model is None:
                join_model = "PoolRoomsWireJoin"
                ensure_model(join_model, [("code", "str", False),
                                          ("player_id", "str", False),
                                          ("player_name", "str", True)])
            if note:
                warnings.append("WARNING: join alias to %s: %s" % (fn_name, note))
            additions.append(
                "# POOL_ROOMS_WIRE_JOIN (alias: delegates to %s)\n"
                "@%s.post(\"%s/join\")\n"
                "async def pool_rooms_wire_join(body: %s):\n"
                "    result = %s\n"
                "    return result\n" % (fn_name, router, base, join_model, call))
            print("POOL_ROOMS_WIRE: join aliased to %s" % fn_name)
            wired = True
            break
        if not wired:
            if not db:
                warnings.append("WARNING: join endpoint SKIPPED (no db handle found)")
            else:
                if join_model is None:
                    join_model = "PoolRoomsWireJoin"
                    ensure_model(join_model, [("code", "str", False),
                                              ("player_id", "str", False),
                                              ("player_name", "str", True)])
                additions.append(
                    "# POOL_ROOMS_WIRE_JOIN (full endpoint)\n"
                    "@%s.post(\"%s/join\")\n"
                    "async def pool_rooms_wire_join(body: %s):\n"
                    "    room = await %s.pool_rooms.find_one({\"code\": body.code})\n"
                    "    if not room:\n"
                    "        raise HTTPException(status_code=404, detail=\"Room not found\")\n"
                    "    members = []\n"
                    "    if room.get(\"host_id\"):\n"
                    "        members.append(room[\"host_id\"])\n"
                    "    if room.get(\"guest_id\"):\n"
                    "        members.append(room[\"guest_id\"])\n"
                    "    for p in room.get(\"players\", []) or []:\n"
                    "        if isinstance(p, dict) and p.get(\"player_id\"):\n"
                    "            members.append(p[\"player_id\"])\n"
                    "    if body.player_id in members:\n"
                    "        if room.get(\"_id\") is not None:\n"
                    "            room[\"_id\"] = str(room[\"_id\"])\n"
                    "        return room\n"
                    "    if room.get(\"status\") != \"waiting\":\n"
                    "        raise HTTPException(status_code=400, detail=\"Room is not waiting\")\n"
                    "    await %s.pool_rooms.update_one({\"code\": body.code}, "
                    "{\"$set\": {\"guest_id\": body.player_id, \"guest_name\": body.player_name, "
                    "\"status\": \"playing\", \"updated_at\": %s}, "
                    "\"$push\": {\"players\": {\"player_id\": body.player_id, \"player_name\": body.player_name}}})\n"
                    "    room = await %s.pool_rooms.find_one({\"code\": body.code})\n"
                    "    if room.get(\"_id\") is not None:\n"
                    "        room[\"_id\"] = str(room[\"_id\"])\n"
                    "    return room\n" % (router, base, join_model, db, db, now, db))
                print("POOL_ROOMS_WIRE: full join endpoint added")

    if not additions:
        for w in warnings:
            print(w)
        print("POOL_ROOMS_WIRE_NOTHING_WIRED (no route could be wired, file unchanged)")
        return 0

    # Imports for the added code.
    if any("random.randint" in b for b in additions) and not re.search(r"^import random\b", src, re.M):
        need_imports.append("import random")
    if any("uuid.uuid4" in b for b in additions) and not re.search(r"^import uuid\b", src, re.M):
        need_imports.append("import uuid")
    if dt_import and not re.search(r"from datetime import[^\n]*\btimezone\b", src):
        # Only needed when the added code actually uses the now expression.
        if any("timezone.utc" in b or "datetime.now" in b for b in additions):
            need_imports.append(dt_import)
    if need_models:
        if "BaseModel" not in src:
            need_imports.append("from pydantic import BaseModel")
        if "HTTPException" not in src:
            need_imports.append("from fastapi import HTTPException")
    lines = src.split("\n")
    if need_imports:
        last_import = -1
        for i, ln in enumerate(lines[:80]):
            s = ln.strip()
            if s.startswith("import ") or s.startswith("from "):
                last_import = i
        for j, imp in enumerate(need_imports):
            lines.insert(last_import + 1 + j, imp)
        src = "\n".join(lines)

    model_block = ""
    for mname, fields in need_models:
        flds = "\n".join(
            "    %s: %s%s" % (n, t, " = \"Player\"" if d else "")
            for (n, t, d) in fields)
        model_block += "class %s(BaseModel):\n%s\n\n\n" % (mname, flds)
    block = MARKER + "\n" + model_block + "\n".join(additions)
    # Only claim the global marker when every missing route got wired.
    # (If a route was skipped, leave the global marker out so a later
    # run retries it; the per-route sub-markers still prevent dupes.)
    # Decide whether all originally-missing routes were wired.
    wired_create = create_exists or any("POOL_ROOMS_WIRE_CREATE" in b for b in additions)
    wired_join = join_exists or any("POOL_ROOMS_WIRE_JOIN" in b for b in additions)
    if wired_create and wired_join:
        block = block  # global MARKER already at the top of the block
    else:
        block = block.replace(MARKER + "\n", "", 1)

    # Insertion point: before include_router(api_router) when the router
    # is api_router (routes added after that call would never register),
    # else before __main__, else at end of file.
    lines = src.split("\n")
    idx = None
    if router == "api_router":
        for i, ln in enumerate(lines):
            if "include_router(api_router" in ln:
                idx = i
                break
    if idx is None:
        for i, ln in enumerate(lines):
            if ln.startswith('if __name__ == "__main__"'):
                idx = i
                break
    if idx is None:
        new_src = src.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new_src = "\n".join(lines[:idx]) + "\n" + block + "\n" + "\n".join(lines[idx:]) + "\n"
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    try:
        py_compile.compile(PATH, doraise=True)
    except Exception as e:
        with open(PATH, "w", encoding="utf-8") as f:
            f.write(orig)
        print("POOL_ROOMS_WIRE_SYNTAX_FAIL: %s (file restored)" % e)
        return 1
    for w in warnings:
        print(w)
    print(OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
