"""Locks down Street Legends account deletion - requires password.
Run from repo root: python3 patch-delete-auth.py
Aborts on mismatch. Safe to re-run.
"""
import sys

PATCHES = []
PATCHES.append(("delete endpoint password check", "@api_router.delete(\"/players/{player_id}/account\")\nasync def delete_player_account(player_id: str):\n    \"\"\"\n    Permanently delete a player's account and all associated data.\n    This is for logged-in users who want to delete their own account.\n    \"\"\"\n    # Find the player\n    player = await db.players.find_one({\"id\": player_id})\n    if not player:\n        raise HTTPException(status_code=404, detail=\"Player not found\")", "class DeleteAccountConfirm(BaseModel):\n    password: str\n\n\n@api_router.delete(\"/players/{player_id}/account\")\nasync def delete_player_account(player_id: str, data: DeleteAccountConfirm):\n    \"\"\"\n    Permanently delete a player's account and all associated data.\n    Requires the account password to confirm ownership.\n    \"\"\"\n    # Find the player\n    player = await db.players.find_one({\"id\": player_id})\n    if not player:\n        raise HTTPException(status_code=404, detail=\"Player not found\")\n\n    # Verify password to confirm account ownership\n    if not pwd_context.verify(data.password, player.get(\"password_hash\", \"\")):\n        raise HTTPException(status_code=401, detail=\"Incorrect password. Account deletion cancelled.\")"))
PATCHES.append(("delete-request model", "class DeleteAccountRequest(BaseModel):\n    username: str", "class DeleteAccountRequest(BaseModel):\n    username: str\n    password: str"))
PATCHES.append(("delete-request password check", "    if player:\n        player_id = player.get(\"id\")\n        \n        # Store deletion request for processing", "    if player:\n        player_id = player.get(\"id\")\n\n        # Verify password to confirm account ownership (don't reveal failures)\n        if not pwd_context.verify(data.password, player.get(\"password_hash\", \"\")):\n            return {\"status\": \"success\", \"message\": \"If an account exists with this username, it will be deleted within 30 days.\"}\n        \n        # Store deletion request for processing"))

def main():
    path = "backend/server.py"
    try:
        with open(path) as f: src = f.read()
    except FileNotFoundError:
        print(f"ERROR: {path} not found. Run from repo root."); sys.exit(1)
    changed = 0
    for name, old, new in PATCHES:
        if new in src and old not in src:
            print(f"SKIP (already applied): {name}"); continue
        if src.count(old) != 1:
            print(f"ERROR: anchor for '{name}' matched {src.count(old)}x. Aborting."); sys.exit(1)
        src = src.replace(old, new, 1); changed += 1
        print(f"OK: {name}")
    if changed:
        with open(path, "w") as f: f.write(src)
        print(f"\nDone. {changed} patch(es) applied.")
        # syntax check
        import py_compile
        try: py_compile.compile(path, doraise=True); print("Python syntax OK.")
        except Exception as e: print(f"SYNTAX WARNING: {e}")
    else:
        print("\nNothing to do - all patches already applied.")

if __name__ == "__main__": main()
