"""Street Legends frontend: ask "Are you sure?" before buying or selling house items.
Run from repo root: python3 frontend/patch-house-item-confirm.py
Idempotent - safe to re-run.

WHY (user 2026-10-31): tapping an item in the house menu buys or sells it
immediately, with no chance to back out of a $10k / $50k tap. This patch
puts a confirmation dialog in front of every house-item buy and sell:

1. The house-menu item tap (handleHouseItemToggle) - buys when the item is
   not placed, sells when it is. Wrapped so it asks first, naming the item
   and the price (buy) or the half-price refund (sell).
2. The room-menu SELL buttons (sellPoolTable, sellDartboard) - wrapped so
   they ask first, naming the refund.

HOW: each worker is renamed (handleHouseItemToggle -> handleHouseItemToggleDo,
etc.) and a same-named wrapper takes its place. Buttons and props already
call the original name, so they now hit the wrapper (confirm) first and the
worker only runs when the user taps Buy / Sell. Cancel does nothing.
No button, prop, or worker body is touched, so a missed anchor is a safe
WARNING, never a broken file. Alert is added to the react-native import
only if it is not already there.

FRONTEND change: reload Expo Go to check (no build needed for the check).
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")

TOGGLE_DECL = "  const handleHouseItemToggle = async (item: any) => {"
TOGGLE_WRAPPER = """  const handleHouseItemToggle = (item: any) => {
    const placed = (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);
    const knownPrice: any = { 'pool-table': 50000, 'dartboard': 10000 };
    const price = item.price ?? knownPrice[item.id];
    const title = placed ? 'Sell ' + item.name + '?' : 'Buy ' + item.name + '?';
    const msg = placed
      ? (price ? 'Sell ' + item.name + ' for $' + Math.floor(price / 2).toLocaleString() + ' back?' : 'Remove ' + item.name + ' from your house?')
      : (price ? 'Buy ' + item.name + ' for $' + price.toLocaleString() + '?' : 'Place ' + item.name + ' in your house?');
    Alert.alert(title, msg, [
      { text: 'Cancel', style: 'cancel' },
      { text: placed ? 'Sell' : 'Buy', onPress: () => handleHouseItemToggleDo(item) },
    ]);
  };
"""

POOL_DECL_ASYNC = "  const sellPoolTable = async () => {"
POOL_DECL_PLAIN = "  const sellPoolTable = () => {"
POOL_WRAPPER = """  const sellPoolTable = () => {
    Alert.alert('Sell Pool Table?', 'Sell the Pool Table for $25,000 back?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sell', onPress: () => sellPoolTableDo() },
    ]);
  };
"""

DART_DECL = "  const sellDartboard = async () => {"
DART_WRAPPER = """  const sellDartboard = () => {
    Alert.alert('Sell Dartboard?', 'Sell the Dartboard for $5,000 back?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sell', onPress: () => sellDartboardDo() },
    ]);
  };
"""


def ensure_alert_import(src):
    """Add Alert to the react-native import block if it is not already there."""
    m = re.search(r"import\s*\{([\s\S]*?)\}\s*from\s*['\"]react-native['\"]", src)
    if not m:
        print("WARNING: react-native import not found, Alert import not added")
        return src, False
    if re.search(r"\bAlert\b", m.group(1)):
        print("SKIP: Alert already in the react-native import")
        return src, True
    inner = m.group(1)
    stripped = inner.rstrip()
    sep = "" if stripped.endswith(",") or not stripped.strip() else ","
    new_inner = stripped + sep + "\n  Alert,"
    src = src[:m.start(1)] + new_inner + src[m.end(1):]
    print("OK: Alert added to the react-native import")
    return src, True


def wrap(src, worker, decls, wrapper, label):
    """Rename one worker declaration to <worker>Do and insert the wrapper before it.
    Returns (src, status) where status is 'ok', 'skip', or 'warn'."""
    if worker + "Do" in src:
        print("SKIP: %s already wrapped" % label)
        return src, "skip"
    for decl in decls:
        if src.count(decl) == 1:
            renamed = decl.replace(worker, worker + "Do", 1)
            src = src.replace(decl, wrapper.rstrip("\n") + "\n" + renamed, 1)
            print("OK: %s now asks first" % label)
            return src, "ok"
    print("WARNING: %s declaration not found, not wrapped" % label)
    return src, "warn"


def main():
    if not INDEX.exists():
        print("ERROR: %s not found. Run from repo root." % INDEX)
        sys.exit(1)
    src = INDEX.read_text()

    src, _ = ensure_alert_import(src)

    results = []
    src, st = wrap(src, "handleHouseItemToggle", [TOGGLE_DECL], TOGGLE_WRAPPER, "house-menu buy/sell")
    results.append(st)
    src, st = wrap(src, "sellPoolTable", [POOL_DECL_ASYNC, POOL_DECL_PLAIN], POOL_WRAPPER, "pool table sell")
    results.append(st)
    src, st = wrap(src, "sellDartboard", [DART_DECL], DART_WRAPPER, "dartboard sell")
    results.append(st)

    INDEX.write_text(src)
    if "warn" in results and "ok" not in results and "skip" not in results:
        print("WARNING: no confirm wrappers added")
    else:
        print("HOUSE_ITEM_CONFIRM_OK")


if __name__ == "__main__":
    main()
