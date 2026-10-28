"""Street Legends backend: stop the LLM call that stalls monster spawning.
Run from repo root: python3 backend/patch-fast-monsters.py
Idempotent - safe to re-run.

ROOT CAUSE: every new monster spawn awaited a live GPT-4o call
(generate_ai_content("monster")) for a 1-2 sentence flavor description, one at
a time, in sequence. Entering a new territory cell spawns 5 monsters = 5
sequential LLM calls (15-50s), and the map query waits for ALL entity calls,
so the territory grid + bad guys + everything else froze until ChatGPT
answered.

FIX: canned street descriptions (name + level filled in) instead of the LLM
call. Same flavor, zero wait. The description is only shown when you tap an
enemy — it never needed to be AI-written live.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

DESCRIPTIONS = '''
# Canned monster descriptions (replaces the live GPT-4o call during spawn)
MONSTER_DESCRIPTIONS = [
    "A level {level} {name} holding down this block. Don't let the look fool you.",
    "A level {level} {name} with a reputation on these streets. Approach with caution.",
    "Word on the street is this level {level} {name} runs with a rough crew.",
    "A level {level} {name} posted up here, watching everyone who passes.",
    "This level {level} {name} has been causing trouble in the neighborhood.",
    "A hardened level {level} {name}. The streets made them this way.",
    "A level {level} {name} looking for their next score. Could be you.",
    "Nobody walks past this level {level} {name} without paying attention.",
]

'''

OLD_CALL = '''            description = await generate_ai_content("monster", {
                "name": template["name"],
                "level": monster_level,
                "type": enemy_type
            })'''
NEW_CALL = '''            description = random.choice(MONSTER_DESCRIPTIONS).format(name=template["name"], level=monster_level)'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. Add the descriptions list before the monster spawn endpoint
    if "MONSTER_DESCRIPTIONS" not in src:
        marker = '@api_router.get("/monsters/spawn")'
        if src.count(marker) != 1:
            print("ERROR: monsters spawn marker not found. Aborting.")
            sys.exit(1)
        src = src.replace(marker, DESCRIPTIONS.strip("\n") + "\n\n" + marker, 1)
        print("OK: added canned monster descriptions")
    else:
        print("SKIP: canned descriptions already present")

    # 2. Swap the LLM call for a canned description
    if "random.choice(MONSTER_DESCRIPTIONS)" in src:
        print("SKIP: monster spawn already uses canned descriptions")
    else:
        if src.count(OLD_CALL) != 1:
            print(f"ERROR: LLM call anchor matched {src.count(OLD_CALL)}x. Aborting.")
            sys.exit(1)
        src = src.replace(OLD_CALL, NEW_CALL, 1)
        print("OK: monster spawn no longer calls GPT-4o (instant)")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("FAST_MONSTERS_OK")


if __name__ == "__main__":
    main()
