#!/usr/bin/env python3
"""Street Legends Bonus tab (frontend).

Adds a BONUS tab to the Shop, next to House, with four real-money
bundles (Play Billing, same pattern as God Potions) and the Street
Legends banner picture over the options.

What it does:
  1. Downloads frontend/components/BonusBundles.tsx from GitHub.
  2. Downloads frontend/assets/bonus-banner.b64.txt from GitHub and
     decodes it to frontend/assets/bonus-banner.jpg (the push tool
     cannot carry binary files, so the banner travels as base64 text).
  3. Patches frontend/app/(tabs)/shop.tsx:
       - adds 'bonus' to FilterKey
       - adds a Bonus tab (gift icon) after the House tab
       - imports BonusBundles
       - renders <BonusBundles> when the Bonus tab is active
  4. The backend (grant-bonus / use-mk1) is a separate patch:
     backend/patch-bonus-bundles.py -> Deploy.

Bundles (product IDs must be created in Play Console first, same as
the God Potions, before they can be bought):
  bonus_cash_100k ($10)  - $100,000 cash
  bonus_cash_250k ($25)  - $250,000 cash
  bonus_pack_500k ($50)  - $500,000 cash + 5 Health MK1 + 5 Energy MK1
  bonus_pack_1m   ($100) - $1,000,000 cash + 5 Health MK1 + 5 Energy MK1
                          + 1h Infinite Health + 1h Infinite Energy

Run from /app: python3 frontend/patch-bonus-tab.py
Idempotent: a full re-run prints BONUS_TAB_ALREADY_APPLIED.
"""
import re
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
SHOP = Path("frontend/app/(tabs)/shop.tsx")
COMP = Path("frontend/components/BonusBundles.tsx")
BANNER = Path("frontend/assets/bonus-banner.jpg")
MARKER = "BONUS_TAB_OK"

FILTERKEY_RE = re.compile(
    r"(type FilterKey = 'all' \| 'health_recharge' \| 'energy_recharge' \| 'combo' \| 'consumable' \| 'house';)",
    re.DOTALL,
)
FILTERKEY_NEW = "type FilterKey = 'all' | 'health_recharge' | 'energy_recharge' | 'combo' | 'consumable' | 'house' | 'bonus';"

FILTERS_RE = re.compile(
    r"(\{ key: 'house', label: 'House', icon: 'home' \},)",
    re.DOTALL,
)
FILTERS_NEW = (
    "\\1\n"
    "    { key: 'bonus', label: 'Bonus', icon: 'gift' },"
)

IMPORT_RE = re.compile(
    r"(import \{ GodPotions \} from '\.\./\.\./components/GodPotions';)",
    re.DOTALL,
)
IMPORT_NEW = (
    "\\1\n"
    "import { BonusBundles } from '../../components/BonusBundles';"
)

# NOTE: the render anchor captures the "{filter === 'house' ? (" opener,
# but the replacement must NOT carry that leading "{" into the else
# branch -- ") : {filter ..." parses as an object literal and breaks
# the build (shop.tsx 409). The chained ternary is ") : filter ...".
RENDER_RE = re.compile(
    r"\{filter === 'house' \? \(",
    re.DOTALL,
)
RENDER_NEW = (
    "{filter === 'bonus' ? (\n"
    "        <ScrollView style={styles.itemsScroll} contentContainerStyle={styles.scrollContent}>\n"
    "          <BonusBundles playerId={playerId} />\n"
    "        </ScrollView>\n"
    "      ) : filter === 'house' ? ("
)

def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["curl", "-sL", url, "-o", str(dest)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
        print(f"ERROR: download failed: {url}")
        sys.exit(1)

def _download_b64(url: str, dest: Path) -> None:
    """Download a base64 text file and decode it to a binary image.
    (The push tool cannot carry binary files, so the banner travels as
    base64 text and is decoded here.)"""
    import base64
    tmp = dest.with_suffix(".b64.txt")
    _download(url, tmp)
    raw = tmp.read_text().replace("\n", "").replace(" ", "").strip()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(raw))
    try:
        tmp.unlink()
    except OSError:
        pass

def main():
    if not SHOP.exists():
        print("ERROR: shop.tsx not found (run from /app)")
        sys.exit(1)
    src = SHOP.read_text()
    if "BONUS_TAB" in src or "'bonus'" in src and "BonusBundles" in src:
        print("BONUS_TAB_ALREADY_APPLIED")
        return
    _download(f"{RAW}/frontend/components/BonusBundles.tsx?v=1", COMP)
    _download_b64(f"{RAW}/frontend/assets/bonus-banner.b64.txt?v=1", BANNER)
    if "BonusBundles" not in COMP.read_text():
        print("ERROR: BonusBundles.tsx download looks wrong")
        sys.exit(1)
    if BANNER.stat().st_size < 10000:
        print("ERROR: bonus-banner.jpg download looks wrong")
        sys.exit(1)
    for name, rx, new in (
        ("FilterKey", FILTERKEY_RE, FILTERKEY_NEW),
        ("filters array", FILTERS_RE, FILTERS_NEW),
        ("import", IMPORT_RE, IMPORT_NEW),
        ("render", RENDER_RE, RENDER_NEW),
    ):
        m = rx.search(src)
        if not m:
            print(f"ERROR: shop.tsx {name} anchor not found (file changed in an unexpected way)")
            sys.exit(1)
        # RENDER_NEW has no group refs; the others use \1.
        repl = new if name == "render" else m.expand(new)
        src = src[:m.start()] + repl + src[m.end():]
    SHOP.write_text(src)
    cur = SHOP.read_text()
    if "'bonus'" not in cur or "BonusBundles" not in cur:
        print("ERROR: Bonus tab patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
