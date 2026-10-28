"""Street Legends backend: TEST-ONLY cash grant endpoint.
Run from repo root: python3 backend/patch-grant-endpoint.py
Idempotent - safe to re-run.

WHY: the terminal grant script kept failing because the Emergent
terminal's MONGO_URL/DB_NAME env does not point at the live game
database (it found no players). An endpoint runs INSIDE the backend,
so it always uses the backend's own (correct) database connection.

SAFETY: the endpoint is hardcoded to ONE player ID (Mayor Veno, the
test account) and a max of $10M per call, so it cannot be used to
enrich any other player. Remove it after testing is done.

ENDPOINT:
  POST /api/admin/grant-test-cash  {player_id, amount}
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ENDPOINT = '''# ============== TEST-ONLY CASH GRANT (remove after mansion test) ==============
@api_router.post("/admin/grant-test-cash")
async def grant_test_cash(data: dict):
    """TEST ONLY: grant in-game cash to the test player (Mayor Veno).
    Hardcoded to one player ID so it cannot enrich anyone else."""
    player_id = data.get("player_id")
    amount = data.get("amount", 1000000)
    if player_id != "3872dca3-bf7d-4807-8fc5-47c22ba67620":
        raise HTTPException(status_code=403, detail="Test grants only for the test player")
    try:
        amount = int(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount")
    if amount <= 0 or amount > 10000000:
        raise HTTPException(status_code=400, detail="Amount out of range")
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    await db.players.update_one({"id": player_id}, {"$inc": {"cash": amount}})
    updated = await db.players.find_one({"id": player_id})
    return {"player": player.get("name"), "cash": updated.get("cash", 0), "granted": amount}


'''

ANCHOR = "# ============== MISSION ENDPOINTS =============="


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "/admin/grant-test-cash" in src:
        print("SKIP: grant endpoint already present")
    elif ANCHOR in src:
        src = src.replace(ANCHOR, ENDPOINT + ANCHOR, 1)
        print("OK: grant endpoint added")
    else:
        print("ERROR: MISSION ENDPOINTS anchor not found.")
        sys.exit(1)
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("GRANT_ENDPOINT_OK")


if __name__ == "__main__":
    main()
