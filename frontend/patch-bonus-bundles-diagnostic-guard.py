#!/usr/bin/env python3
"""Bonus Bundles diagnostic + guard.

Two small, safe changes to frontend/components/BonusBundles.tsx:

1. GUARD in buy(): if Play has not returned this SKU in fetchProducts,
   do NOT call requestPurchase(). On an unknown SKU requestPurchase()
   hangs forever and never fires either listener, leaving the BUY button
   spinning until a full app restart. Instead show a clear message.
2. DIAGNOSTIC line under the BONUS BUNDLES header showing exactly how
   many products Play returned and which IDs, so we can tell whether
   Play has the products on this device at all.

Does NOT touch the listeners, the billing connection lifecycle, or the
Shop structure. Idempotent.
"""
import sys

PATH = "frontend/components/BonusBundles.tsx"
MARKER = "BONUS_BUNDLES_DIAG_GUARD_OK"

BUY_OLD = """  const buy = async (sku: string) => {
    if (!playerIdRef.current) {
      Alert.alert('Login Required', 'Log in before buying a bundle.');
      return;
    }
    try {"""

BUY_NEW = """  const buy = async (sku: string) => {
    if (!playerIdRef.current) {
      Alert.alert('Login Required', 'Log in before buying a bundle.');
      return;
    }
    // DIAG-GUARD: do not start a purchase Play has not sent us yet.
    // requestPurchase() hangs forever on an unknown SKU and never fires
    // either listener, leaving the BUY button spinning. If Play has not
    // returned this product, tell the user instead of hanging.
    const known = products.some((x: any) => (x.id ?? x.productId) === sku);
    if (!known) {
      Alert.alert(
        'Not Ready Yet',
        'Play Store has not sent this product to your phone yet. Close the app fully and reopen it, or clear the Play Store cache and try again.'
      );
      return;
    }
    try {"""

HEADER_OLD = """      <View style={styles.sectionHeader}>
        <Ionicons name="gift" size={18} color="#f39c12" />
        <Text style={styles.sectionTitle}>BONUS BUNDLES</Text>
        <View style={styles.realMoneyBadge}>
          <Text style={styles.realMoneyText}>REAL MONEY</Text>
        </View>
      </View>"""

HEADER_NEW = """      <View style={styles.sectionHeader}>
        <Ionicons name="gift" size={18} color="#f39c12" />
        <Text style={styles.sectionTitle}>BONUS BUNDLES</Text>
        <View style={styles.realMoneyBadge}>
          <Text style={styles.realMoneyText}>REAL MONEY</Text>
        </View>
      </View>
      <Text style={{ color: '#f39c12', fontSize: 12, marginBottom: 8 }}>
        Play sent {products.length}/4 products{products.length > 0 ? `: ${products.map((x: any) => x.id ?? x.productId).join(', ')}` : ' - none yet'}
      </Text>"""


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print(f"ERROR: {PATH} not found. Run from /app.")
        sys.exit(1)

    if "DIAG-GUARD" in src:
        print("BONUS_BUNDLES_DIAG_GUARD_ALREADY_APPLIED")
        print(MARKER)
        return

    if BUY_OLD not in src:
        print("ERROR: buy() anchor not found. File has drifted; stopping without writing.")
        sys.exit(1)
    if HEADER_OLD not in src:
        print("ERROR: sectionHeader anchor not found. File has drifted; stopping without writing.")
        sys.exit(1)

    src = src.replace(BUY_OLD, BUY_NEW, 1)
    src = src.replace(HEADER_OLD, HEADER_NEW, 1)

    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)

    # sanity: balanced braces after edit
    if src.count("{") != src.count("}"):
        print("WARNING: brace count changed; review the file.")
    print(MARKER)


if __name__ == "__main__":
    main()
