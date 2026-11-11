#!/usr/bin/env python3
"""Pharmacy: item descriptions + BUY 10 oz (frontend only).

User (2026-11-07, live in the pharmacy): "the pharmacy needs description
on items and allow to buy 1 or 10 items at a time". Screenshot ground truth:
Rite Aid, cash $1,827,304, Grass 3 oz / Pills 2 oz / Rock Candy 0 oz /
Flake 2 oz / Brown Sugar 0 oz, BUY 1 OZ / SELL 1 OZ buttons, NO STOCK on
Rock Candy sell. The backend + api.ts ALREADY take qty (default 1) --
probe diag-pharmacy-buy10.py confirms live before this runs -- so this patch
touches index.tsx only:
  1. desc on each of the 5 items (the USE buff, 60s) + a desc line under
     the item name in the shop row
  2. BUY 10 OZ button (second row, full width, total price, NEED $X when
     cash is short) calling handlePharmacyTrade(item, 'buy', 10)
  3. handlePharmacyTrade takes qty (default 1) and passes it through;
     the alert names the qty bought/sold
SELL stays 1 oz per tap (user asked buy only). Run from /app. Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
MARKER = 'PHARMACY_BUY10'

DESCS = {
    'grass': '+50% max health for 60s when used.',
    'pills': '+50% max energy for 60s when used.',
    'rock_candy': '+50% attack for 60s when used.',
    'flake': 'Defense x1.5 for 60s when used.',
    'brown_sugar': '+50% Luck for 60s when used.',
}

ITEM_LINES = {
    'grass': ("{ id: 'grass', name: 'Grass', buy: 100, sell: 50 },",
              "{ id: 'grass', name: 'Grass', buy: 100, sell: 50, desc: '+50% max health for 60s when used.' },"),
    'pills': ("{ id: 'pills', name: 'Pills', buy: 200, sell: 100 },",
              "{ id: 'pills', name: 'Pills', buy: 200, sell: 100, desc: '+50% max energy for 60s when used.' },"),
    'rock_candy': ("{ id: 'rock_candy', name: 'Rock Candy', buy: 300, sell: 150 },",
                   "{ id: 'rock_candy', name: 'Rock Candy', buy: 300, sell: 150, desc: '+50% attack for 60s when used.' },"),
    'flake': ("{ id: 'flake', name: 'Flake', buy: 400, sell: 200 },",
              "{ id: 'flake', name: 'Flake', buy: 400, sell: 200, desc: 'Defense x1.5 for 60s when used.' },"),
    'brown_sugar': ("{ id: 'brown_sugar', name: 'Brown Sugar', buy: 500, sell: 250 },",
                    "{ id: 'brown_sugar', name: 'Brown Sugar', buy: 500, sell: 250, desc: '+50% Luck for 60s when used.' },"),
}

HANDLER_SIG_OLD = "const handlePharmacyTrade = async (item: any, kind: 'buy' | 'sell') => {"
HANDLER_SIG_NEW = "const handlePharmacyTrade = async (item: any, kind: 'buy' | 'sell', qty: number = 1) => {"
BUY_CALL_OLD = "const result: any = kind === 'buy' ? await pharmacyBuy(playerId, item.id, 1) : await pharmacySell(playerId, item.id, 1);"
BUY_CALL_NEW = "const result: any = kind === 'buy' ? await pharmacyBuy(playerId, item.id, qty) : await pharmacySell(playerId, item.id, qty);"
ALERT_OLD = "Alert.alert(kind === 'buy' ? 'Bought!' : 'Sold!', (result && result.message) || (kind === 'buy' ? 'Bought 1 oz ' + item.name + '.' : 'Sold 1 oz ' + item.name + '.'));"
ALERT_NEW = "Alert.alert(kind === 'buy' ? 'Bought!' : 'Sold!', (result && result.message) || (kind === 'buy' ? 'Bought ' + qty + ' oz ' + item.name + '.' : 'Sold ' + qty + ' oz ' + item.name + '.'));"
COMMENT_OLD = "  // PHARMACY: buy/sell 1 oz. The tapped button is disabled while the"
COMMENT_NEW = "  // PHARMACY: buy/sell 1 or 10 oz. The tapped button is disabled while the"

HELD_LINE = "<Text style={{ fontSize: 14, color: '#e0e0e0', marginTop: 2 }}>Held: {held} oz</Text>"
DESC_LINE = "<Text style={{ fontSize: 13, color: '#b2dfdb', marginTop: 2 }}>{item.desc}</Text>"

CANBUY_OLD = "const canBuy = cash >= item.buy;"
CANBUY_NEW = "const canBuy = cash >= item.buy;\n                const canBuy10 = cash >= item.buy * 10;"

SELL_TEXT = "'SELL 1 OZ ($' + item.sell + ')' : 'NO STOCK'"

BUY10_ROW = """                    <View style={{ flexDirection: 'row', marginTop: 8 }}>
                      <TouchableOpacity
                        style={{ flex: 1, backgroundColor: canBuy10 ? '#009688' : '#555', opacity: (canBuy10 && !busyKey) ? 1 : 0.6, padding: 12, borderRadius: 8, alignItems: 'center' }}
                        disabled={!canBuy10 || !!busyKey}
                        onPress={() => handlePharmacyTrade(item, 'buy', 10)}
                      >
                        <Text style={{ color: '#fff', fontWeight: 'bold' }}>{busyKey ? '...' : (canBuy10 ? 'BUY 10 OZ ($' + (item.buy * 10) + ')' : 'NEED $' + (item.buy * 10))}</Text>
                      </TouchableOpacity>
                    </View>"""


def _delta(s):
    return (s.count('{'), s.count('}'), s.count('('), s.count(')'),
            s.count('['), s.count(']'))


def _imbalances_ok(before, after):
    b, a = _delta(before), _delta(after)
    return ((a[0] - a[1]) == (b[0] - b[1]) and (a[2] - a[3]) == (b[2] - b[3])
            and (a[4] - a[5]) == (b[4] - b[5]))


def replace_once(src, old, new, label):
    n = src.count(old)
    if n == 1:
        return src.replace(old, new, 1), None
    if n == 0 and new in src:
        return src, None  # already applied (new text present)
    return src, '%s anchor count=%d (want 1)' % (label, n)


def insert_buy10_row(src):
    """Insert the BUY 10 row after the button row that holds the SELL button.

    Anchor: the SELL button text (unique) -> the first </View> after it
    closes the button row. Returns (src, err).
    """
    lines = src.split('\n')
    sell = [i for i, ln in enumerate(lines) if SELL_TEXT in ln]
    if len(sell) != 1:
        return src, 'SELL button anchor count=%d (want 1)' % len(sell)
    closes = [i for i in range(sell[0], len(lines)) if lines[i].strip() == '</View>']
    if not closes:
        return src, 'button-row closing </View> not found'
    c = closes[0]
    new_lines = lines[:c + 1] + BUY10_ROW.split('\n') + lines[c + 1:]
    return '\n'.join(new_lines), None


def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - pharmacy buy-10 NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if MARKER in src and 'BUY 10 OZ' in src and 'item.desc' in src:
        print('PHARMACY_BUY10_ALREADY_APPLIED')
        return 0
    # Preconditions (print only).
    if 'Held: {held} oz' not in src:
        print('WARNING: pharmacy Held line not found - is the pharmacy live?')
    if 'pharmacyBuy(playerId, item.id, 1)' not in src:
        print('WARNING: pharmacy buy call not in expected form - check the handler')
    ok = {}
    # 1. desc on each item in the array
    desc_ok = True
    for item_id, (old, new) in ITEM_LINES.items():
        src, err = replace_once(src, old, new, 'item ' + item_id)
        if err:
            print('WARNING: ' + err)
            desc_ok = False
        else:
            print('OK: desc added to %s' % item_id)
    ok['desc'] = desc_ok
    # 2. desc line under the item name (anchor: the Held line, unique).
    # Idempotent: skip if the desc line is already directly above Held.
    if DESC_LINE + '\n                    ' + HELD_LINE in src:
        print('SKIP: desc line already present')
        ok['descline'] = True
    else:
        src, err = replace_once(src, HELD_LINE, DESC_LINE + '\n                    ' + HELD_LINE, 'Held line')
        ok['descline'] = err is None
        print('OK: desc line added under item name' if err is None else 'WARNING: ' + err)
    # 3. handler takes qty
    src, err = replace_once(src, HANDLER_SIG_OLD, HANDLER_SIG_NEW, 'handler signature')
    ok['sig'] = err is None
    print('OK: handler takes qty' if err is None else 'WARNING: ' + err)
    src, err = replace_once(src, BUY_CALL_OLD, BUY_CALL_NEW, 'buy/sell call')
    ok['call'] = err is None
    print('OK: buy/sell call passes qty' if err is None else 'WARNING: ' + err)
    src, err = replace_once(src, ALERT_OLD, ALERT_NEW, 'alert message')
    ok['alert'] = err is None
    print('OK: alert names qty' if err is None else 'WARNING: ' + err)
    if COMMENT_OLD in src:
        src = src.replace(COMMENT_OLD, COMMENT_NEW, 1)
        print('OK: handler comment updated')
    # 4. canBuy10 + BUY 10 row. Idempotent: skip if canBuy10 already there.
    if 'const canBuy10 = cash >= item.buy * 10;' in src:
        print('SKIP: canBuy10 already present')
        ok['canbuy10'] = True
    else:
        src, err = replace_once(src, CANBUY_OLD, CANBUY_NEW, 'canBuy')
        ok['canbuy10'] = err is None
        print('OK: canBuy10 added' if err is None else 'WARNING: ' + err)
    if 'BUY 10 OZ' in src:
        print('SKIP: BUY 10 row already present')
        ok['row'] = True
    else:
        src, err = insert_buy10_row(src)
        ok['row'] = err is None
        print('OK: BUY 10 OZ row added' if err is None else 'WARNING: ' + err)
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if all(ok.values()):
        print('PHARMACY_BUY10_OK')
        return 0
    print('PHARMACY_BUY10_PARTIAL ' + ' '.join('%s=%s' % (k, v) for k, v in ok.items()))
    return 1


if __name__ == '__main__':
    main()
