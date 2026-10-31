"""Street Legends backend: add the Dartboard to HOUSE_ITEM_CATALOG (Games, $10,000).
Run from repo root: python3 backend/patch-house-dartboard.py
Idempotent - safe to re-run. BACKEND ONLY - Deploy to go live.
The generic items/add|remove|move endpoints already handle any catalog item:
buy deducts price, remove refunds half ($5,000 back), move saves x/y.
"""
import re
from pathlib import Path

SERVER = Path("backend/server.py")
ENTRY = '    "dartboard": {"name": "Dartboard", "category": "games", "price": 10000},'


def main():
    if not SERVER.exists():
        print("HOUSE_DARTBOARD_ERROR: backend/server.py not found (run from /app)")
        return
    src = SERVER.read_text()
    if '"dartboard"' in src and "HOUSE_ITEM_CATALOG" in src:
        # Already in the catalog (check it is inside the catalog block, not just mentioned).
        m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
        if m and '"dartboard"' in m.group(1):
            print("SKIP: Dartboard already in HOUSE_ITEM_CATALOG")
            print("HOUSE_DARTBOARD_BACKEND_OK")
            return
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
    if not m:
        print("HOUSE_DARTBOARD_ERROR: HOUSE_ITEM_CATALOG not found")
        return
    pool_line = re.search(r'\n(\s*)"pool-table":\s*\{[^}]*\},', src[m.end():])
    if pool_line:
        indent = pool_line.group(1)
        ins_at = m.end() + pool_line.end()
        src = src[:ins_at] + "\n" + indent + ENTRY.strip() + src[ins_at:]
        print("OK: Dartboard added after Pool Table in HOUSE_ITEM_CATALOG")
    else:
        ins_at = m.end()
        src = src[:ins_at] + "\n" + ENTRY + src[ins_at:]
        print("OK: Dartboard added to HOUSE_ITEM_CATALOG")
    SERVER.write_text(src)
    import py_compile
    try:
        py_compile.compile(str(SERVER), doraise=True)
    except Exception as e:
        print("HOUSE_DARTBOARD_SYNTAX_FAIL: %s" % e)
        return
    print("HOUSE_DARTBOARD_BACKEND_OK")


if __name__ == "__main__":
    main()
