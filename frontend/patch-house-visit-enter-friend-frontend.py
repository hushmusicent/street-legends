#!/usr/bin/env python3
"""Street Legends frontend: add ENTER HOUSE to the FRIEND house popup.

LIVE GAP (2026-11-03, screenshot from a friend's phone): a friend
(account AppSolutGroup) taps Mayor Veno's Luxury Mansion and the popup
shows ONLY "Luxury Mansion / Owned by Mayor Veno / This house belongs
to another player." -- there is NO Enter button at all. The earlier
visit patch (HOUSE_VISIT_FRONTEND_OK) only wrapped the OWNER popup's
SELL / HIDE / MOVE buttons in an owner check, assuming Enter was
shared. It was not: the friend popup is a SEPARATE info-only branch
with no Enter to expose. This patch adds the Enter button to that
friend branch itself.

What it does (and nothing else):
- Finds the friend-house popup branch in frontend/app/(tabs)/index.tsx
  by TEXT, never by line number (the live file is ~4500+ lines and
  older snapshots lack this popup entirely). Anchor priority:
  1. a line containing "belongs to another player"
  2. a line containing "Owned by" (never "Owned by YOU") whose
     NEAREST player_id comparison within +/-30 lines is a
     friend check (player_id !== playerId), not an owner check
- Inserts ONE ENTER HOUSE button after that text's closing </Text>,
  inside the same popup card, styled like the existing house Enter
  button (styles.actionButton / styles.actionButtonText when those
  exist in the file, else an inline-styled TouchableOpacity).
  Its onPress is exactly the owner Enter:
      () => setInteriorHouse(selectedMarker.data)
  so the guest-mode, presence-enter, and interior-guest-gate logic
  from the earlier visit patch (which keys off
  interiorHouse.player_id !== playerId) all engage when the friend
  enters. No second interior state, no owner-branch change, no
  SELL/HIDE/MOVE change, no presence/TV/radio change.
- The button lives inside the friend branch only, so it can never
  duplicate the owner's own Enter button.

Idempotency: if the inserted button's marker comment
({/* HOUSE_VISIT_ENTER_FRIEND */}) is already in the file, the script
prints HOUSE_VISIT_ENTER_FRIEND_ALREADY_APPLIED, exit 0, and changes
nothing.

Anchor failure: if no friend-branch anchor is found, the script
prints the anchor WARNING below, changes NOTHING, prints no OK
marker, and exits 0. Send the live popup snippet to the assistant
if that happens; do NOT hand-edit around it.

Balance guard: if the edit would change the brace or paren balance
of the file, the write is aborted with a WARNING and nothing changes.

Run from /app: python3 frontend/patch-house-visit-enter-friend-frontend.py
Frontend only: reload Expo Go after running, no build, no Deploy.
An optional first argument is a root directory (used by sim tests);
it defaults to the current directory.
"""

import re
import sys
from pathlib import Path

MARKER = "HOUSE_VISIT_ENTER_FRIEND_OK"
# NOTE: the inserted button's marker is a JSX comment
# ({/* HOUSE_VISIT_ENTER_FRIEND */}), so idempotency must match the
# bare string, not a // comment (which cannot appear inside JSX).
CODE_MARKER = "HOUSE_VISIT_ENTER_FRIEND"
ALREADY = "HOUSE_VISIT_ENTER_FRIEND_ALREADY_APPLIED"
ANCHOR_WARNING = (
    "WARNING: friend house popup anchor not matched - ENTER button "
    "NOT added (send the live popup snippet)"
)
BALANCE_WARNING = "WARNING: brace balance changed - index.tsx NOT written"

ENTER_ONPRESS = "() => setInteriorHouse(selectedMarker.data)"


def _indent_of(line):
    m = re.match(r"[ \t]*", line)
    return m.group(0) if m else ""


def _button_lines(indent, use_styles):
    """The inserted ENTER HOUSE button (braces/parens balanced)."""
    if use_styles:
        return [
            indent + "{/* HOUSE_VISIT_ENTER_FRIEND */}",
            indent
            + "<TouchableOpacity style={styles.actionButton} onPress={() => setInteriorHouse(selectedMarker.data)}>",
            indent + "  <Text style={styles.actionButtonText}>ENTER HOUSE</Text>",
            indent + "</TouchableOpacity>",
        ]
    return [
        indent + "{/* HOUSE_VISIT_ENTER_FRIEND */}",
        indent
        + "<TouchableOpacity style={{ backgroundColor: '#EA4335', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, borderRadius: 8 }} onPress={() => setInteriorHouse(selectedMarker.data)}>",
        indent
        + "  <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>ENTER HOUSE</Text>",
        indent + "</TouchableOpacity>",
    ]


def _nearest_comparison_is_friend(lines, idx, window=30):
    """True if the nearest player_id comparison near idx is a friend
    check (!== playerId), False if it is an owner check (===) or none
    is found. Scans outward from idx so the closest comparison wins."""
    lo = max(0, idx - window)
    hi = min(len(lines), idx + window + 1)
    for dist in range(0, window + 1):
        for j in (idx - dist, idx + dist):
            if lo <= j < hi and j != idx:
                ln = lines[j]
                if "player_id" in ln and "playerId" in ln:
                    if "!==" in ln or "!=" in ln:
                        return True
                    if "===" in ln or "==" in ln:
                        return False
    return False


def _find_anchor(lines):
    """Return (anchor_line_index, anchor_kind) or (None, None)."""
    # 1. Primary: the friend-only text seen live.
    for i, ln in enumerate(lines):
        if "belongs to another player" in ln:
            return i, "belongs-to-another-player"
    # 2. Fallback: an "Owned by" owner line whose nearest player_id
    #    comparison is a friend check, never an owner check.
    for i, ln in enumerate(lines):
        if "Owned by" in ln and "Owned by YOU" not in ln and "Owned by you" not in ln:
            if _nearest_comparison_is_friend(lines, i):
                return i, "owned-by-near-friend-check"
    return None, None


def _insert_after_text_close(lines, anchor_idx):
    """Line index just after the anchor Text element's closing tag.
    If the closing tag is not within the next few lines, insert right
    after the anchor line itself."""
    for j in range(anchor_idx, min(len(lines), anchor_idx + 6)):
        if "</Text>" in lines[j]:
            return j + 1
    return anchor_idx + 1


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    index_path = root / "frontend/app/(tabs)/index.tsx"
    if not index_path.exists():
        print(
            "HOUSE_VISIT_ENTER_FRIEND_ERROR: frontend/app/(tabs)/index.tsx "
            "not found (run from /app)"
        )
        return 1
    src = index_path.read_text(encoding="utf-8")
    orig = src
    if CODE_MARKER in src:
        print(ALREADY)
        return 0

    lines = src.split("\n")
    anchor_idx, kind = _find_anchor(lines)
    if anchor_idx is None:
        print(ANCHOR_WARNING)
        return 0

    insert_at = _insert_after_text_close(lines, anchor_idx)
    # Do not duplicate an Enter that is already in this branch (from
    # some other edit): buttons follow the text within a few lines.
    following = "\n".join(lines[insert_at:insert_at + 12])
    if "ENTER HOUSE" in following:
        print("NOTE: friend branch already has an ENTER HOUSE button - nothing added")
        return 0

    indent = _indent_of(lines[anchor_idx])
    use_styles = "styles.actionButton" in src and "styles.actionButtonText" in src
    if not use_styles:
        print("NOTE: styles.actionButton / styles.actionButtonText not found - using inline button style")
    new_lines = (
        lines[:insert_at] + _button_lines(indent, use_styles) + lines[insert_at:]
    )
    new_src = "\n".join(new_lines)

    # Balance guard: the inserted button is balanced by construction,
    # so both deltas must be exactly zero, or the write is aborted.
    if (new_src.count("{") - new_src.count("}")) != (
        orig.count("{") - orig.count("}")
    ) or (new_src.count("(") - new_src.count(")")) != (
        orig.count("(") - orig.count(")")
    ):
        print(BALANCE_WARNING)
        return 1

    index_path.write_text(new_src, encoding="utf-8")
    print("OK: ENTER HOUSE button added to friend house popup (anchor: %s)" % kind)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
