#!/usr/bin/env python3
"""Street Legends frontend: add the missing PanResponder import (v2 follow-up).

LIVE FACT (user terminal screenshot, 2026-11-06 11:03 EST, from running
frontend/patch-activity-center-pool-table-v2-frontend.py):
  POOL_V2_ART=require('../../assets/houses/items/pool-table.png') via
  house-items-entry, and API / IMPORT / STATE / LOAD / CARD_REMOVED /
  ROOM_OPEN / SCENE / CLOSE / LEAVE / HIDEMANAGE all landed — but ONE
  WARNING: "react-native import anchor not found - PanResponder NOT
  imported (hold-drag will fail to compile)", final marker
  ACTIVITY_CENTER_POOL_V2_PARTIAL (warnings: panresponder).
The v2 responder code now references PanResponder in index.tsx, but
nothing imports it. If it stays missing, the bundle fails / the center
modal throws when rendered. This patch adds ONLY that import.

WHY v2's anchor missed: v2 keyed on the LAST member of the react-native
brace list — "  Dimensions,\n} from 'react-native';" or
"  Image,\n} from 'react-native';". The live file has grown far past the
Oct-12 snapshot (5712 lines vs 2137) and later patches added more
react-native members, so the block no longer ends with Dimensions or
Image. This patch never anchors on the last member: for a multi-line
block it inserts right after the opening brace, using the block's own
member indent; for a single-line block it inserts inside the braces.
The house's own PanResponder import does not help index.tsx — the
house drag patch used the same two last-member anchors, and v2's
"  PanResponder,\n" check was false live, so no PanResponder import
landed in the live file from any earlier patch.

Run from /app: python3 frontend/patch-activity-center-panresponder-import-frontend.py
Frontend / Expo Go only. Idempotent: a re-run prints
ACTIVITY_CENTER_PANRESPONDER_IMPORT_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "ACTIVITY_CENTER_PANRESPONDER_IMPORT_OK"

# A named react-native import: import { ... } from 'react-native' (either quote).
# The brace content is [^}]* (never [\s\S]*?) so the match can never span
# across an earlier import's closing brace to reach this one.
RN_BRACE_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]react-native['\"]\s*;?")
# Any react-native import statement (named, default, namespace).
RN_ANY_RE = re.compile(r"import[^\n]*from\s*['\"]react-native['\"]\s*;?")
# Any top-of-file import statement (for the no-react-native fallback).
TOP_IMPORT_RE = re.compile(r"^import[^\n]*;\s*$", re.M)


def _rn_import_block(src):
    """The react-native import statement text, or None. First ~12 lines
    are printed by the diagnosis; the repr is what the next fix reads.
    The brace regex is tried first because it spans newlines — the
    single-line RN_ANY_RE cannot see a multi-line import's `from` line."""
    m = RN_BRACE_RE.search(src)
    if m:
        return m.group(0)
    m = RN_ANY_RE.search(src)
    return m.group(0) if m else None


def _already_imported(src):
    """True iff PanResponder is imported FROM react-native (brace list or
    standalone line). A bare PanResponder.create usage is NOT an import."""
    m = RN_BRACE_RE.search(src)
    if m and re.search(r"\bPanResponder\b", m.group(1)):
        return True
    return False


def _verify(src):
    """PanResponder is imported from react-native AND at least one
    PanResponder. usage (the v2 responder code) exists."""
    m = RN_BRACE_RE.search(src)
    if not m or not re.search(r"\bPanResponder\b", m.group(1)):
        return False
    return src.count("PanResponder.") >= 1


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - PanResponder import NOT added")
        print("ACTIVITY_CENTER_PANRESPONDER_IMPORT_PARTIAL: index-missing")
        return 1
    src = IDX.read_text(errors="ignore")

    # ---- Step 1: diagnose (always printed). ----
    block = _rn_import_block(src)
    if block is not None:
        lines = block.split("\n")
        # First ~12 lines, but always keep the closing `} from ...` line
        # so the repr proves WHICH module the block imports from.
        shown = lines if len(lines) <= 12 else lines[:11] + ["..."] + [lines[-1]]
        print("RN_IMPORT_BLOCK_REPR=%r" % "\n".join(shown))
    else:
        print("RN_IMPORT_BLOCK_REPR=None (no react-native import found)")
    print("PANRESPONDER_OCCURRENCES_BEFORE=%d" % src.count("PanResponder"))

    # ---- Step 2e: already imported. ----
    if _already_imported(src):
        print("ACTIVITY_CENTER_PANRESPONDER_IMPORT_ALREADY_APPLIED")
        return 0

    strategy = None
    new = None

    # ---- Step 2a/2b: named brace-list import (multi-line or single-line). ----
    m = RN_BRACE_RE.search(src)
    if m:
        inner = m.group(1)
        if "\n" in inner:
            # (a) multi-line: insert right after the opening brace, using
            # the block's own member indent (never the last member).
            ind = re.search(r"\n(\s*)\S", inner)
            indent = ind.group(1) if ind else "  "
            new = src[:m.start(1)] + "\n" + indent + "PanResponder," + inner + src[m.end(1):]
            strategy = "a-multi-line-brace-insert"
        else:
            # (b) single-line: insert inside the braces.
            new = src[:m.start(1)] + " PanResponder," + inner + src[m.end(1):]
            strategy = "b-single-line-brace-insert"
    else:
        # ---- Step 2c: a react-native import exists but no brace list to edit. ----
        m2 = RN_ANY_RE.search(src)
        if m2:
            quote = "'" if "'" in m2.group(0) else '"'
            line = "import { PanResponder } from %sreact-native%s;" % (quote, quote)
            new = src[:m2.end()] + "\n" + line + src[m2.end():]
            strategy = "c-standalone-line-after-rn-import"
        else:
            # ---- Step 2d: no react-native import at all. ----
            head = src[:4000]
            imports = list(TOP_IMPORT_RE.finditer(head))
            if imports:
                last = imports[-1]
                new = src[:last.end()] + "\nimport { PanResponder } from 'react-native';" + src[last.end():]
                strategy = "d-standalone-line-after-last-import"
            else:
                print("WARNING: no import statements found - PanResponder import NOT added")
                print("ACTIVITY_CENTER_PANRESPONDER_IMPORT_PARTIAL: no-imports")
                return 1

    # ---- Verify in-run BEFORE writing; on failure, write nothing. ----
    if new is None or not _verify(new):
        print("WARNING: post-edit verification failed (PanResponder import + usage not both present) - index.tsx NOT written")
        print("ACTIVITY_CENTER_PANRESPONDER_IMPORT_PARTIAL: verify-failed")
        return 1

    IDX.write_text(new)
    print("PANRESPONDER_IMPORT_STRATEGY=%s" % strategy)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
