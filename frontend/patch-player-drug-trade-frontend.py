#!/usr/bin/env python3
"""Player-to-player drug trading UI (map player popup).

Adds to frontend/app/(tabs)/index.tsx:
  - a TRADE DRUGS button in the player popup (next to Follow / Add Friend /
    CHALLENGE TO BATTLE),
  - a trade modal with TWO sides: YOUR DRUGS (your 5 items, oz held, regular
    price) and THEIR DRUGS (the tapped player's 5 items). Tap an item, pick
    1-10 oz with -/+, see the live total, then SELL (yours to them) or BUY
    (theirs to you) at the regular price. Confirm is disabled when the
    seller lacks the oz or the buyer lacks the cash. On success a toast
    shows and the player + both sides refresh.

Adds to frontend/services/api.ts:
  - getPlayerDrugs(playerId) -> GET /players/{id}/drugs
  - tradeDrugs(sellerId, buyerId, itemId, qty) -> POST /trade/drugs

Styling follows the existing dark bottom-sheet modal (terrModal) and the
existing toast (showGameToast) + player refresh (refetchPlayer).

This is a FRONTEND patch: run in /app, check in Expo Go first, then Deploy.
Marker: TRADE_DRUGS_FRONTEND_OK
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
API = Path("frontend/services/api.ts")

# ---------------------------------------------------------------- api.ts
API_ANCHOR = """export const pharmacySell = async (playerId: string, itemId: string, qty: number = 1, requestId?: string): Promise<any> => {
  const response = await api.post('/pharmacies/sell', { player_id: playerId, item_id: itemId, qty, request_id: requestId || pharmacyRequestId() });
  return response.data;
};"""

API_BLOCK = API_ANCHOR + """

// Player-to-player drug trade (regular price, map player popup).
export interface PlayerDrugRow {
  item_id: string;
  name: string;
  qty: number;
  price: number;
}

export const getPlayerDrugs = async (playerId: string): Promise<{ player_id: string; name: string; cash: number; drugs: PlayerDrugRow[] }> => {
  const response = await api.get(`/players/${playerId}/drugs`);
  return response.data;
};

export const tradeDrugs = async (sellerId: string, buyerId: string, itemId: string, qty: number): Promise<{ ok: boolean; item_id: string; name: string; qty: number; total: number; seller_cash: number; buyer_cash: number; message: string }> => {
  const response = await api.post('/trade/drugs', { seller_id: sellerId, buyer_id: buyerId, item_id: itemId, qty });
  return response.data;
};"""

# ---------------------------------------------------------------- index.tsx
IMPORT_ANCHOR = """  getAllItems,
} from '../../services/api';"""

IMPORT_BLOCK = """  getAllItems,
  getPlayerDrugs,
  tradeDrugs,
} from '../../services/api';"""

STATE_ANCHOR = """  const [selectedMarker, setSelectedMarker] = useState<{
    type: 'monster' | 'mission' | 'bounty' | 'player' | 'shop' | 'restaurant' | 'nightclub' | 'activityCenter' | 'fiend' | 'pharmacy' | 'park' | 'billboard';
    data: any;
  } | null>(null);"""

STATE_BLOCK = STATE_ANCHOR + """
  // PLAYER_DRUG_TRADE: trade modal state (map player popup -> TRADE DRUGS).
  const [tradeTarget, setTradeTarget] = useState<any | null>(null);
  const [tradeMyDrugs, setTradeMyDrugs] = useState<any[]>([]);
  const [tradeTheirDrugs, setTradeTheirDrugs] = useState<any[]>([]);
  const [tradeTheirCash, setTradeTheirCash] = useState(0);
  const [tradeLoading, setTradeLoading] = useState(false);
  const [tradeBusy, setTradeBusy] = useState(false);
  const [tradeSellItem, setTradeSellItem] = useState<string | null>(null);
  const [tradeSellQty, setTradeSellQty] = useState(1);
  const [tradeBuyItem, setTradeBuyItem] = useState<string | null>(null);
  const [tradeBuyQty, setTradeBuyQty] = useState(1);"""

HANDLER_ANCHOR = """  }, [playerId]);

  // Load relationship status when player popup opens"""

HANDLER_BLOCK = """  }, [playerId]);

  // PLAYER_DRUG_TRADE: open the trade modal for the tapped player.
  const openTradeModal = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId) return;
    setTradeTarget(targetPlayer);
    setTradeSellItem(null);
    setTradeSellQty(1);
    setTradeBuyItem(null);
    setTradeBuyQty(1);
    setTradeTheirCash(0);
    setTradeLoading(true);
    try {
      const [mine, theirs] = await Promise.all([
        getPlayerDrugs(playerId),
        getPlayerDrugs(targetPlayer.id),
      ]);
      setTradeMyDrugs(mine?.drugs || []);
      setTradeTheirDrugs(theirs?.drugs || []);
      setTradeTheirCash(theirs?.cash || 0);
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Trade', message: e?.response?.data?.detail || 'Could not load drugs', duration: 3000 });
      setTradeTarget(null);
    } finally {
      setTradeLoading(false);
    }
  }, [playerId]);

  // PLAYER_DRUG_TRADE: one direction per confirm - sell mine to them, or buy theirs.
  const handleTradeConfirm = useCallback(async (direction: 'sell' | 'buy') => {
    if (!playerId || !tradeTarget || tradeBusy) return;
    const itemId = direction === 'sell' ? tradeSellItem : tradeBuyItem;
    const qty = direction === 'sell' ? tradeSellQty : tradeBuyQty;
    if (!itemId) return;
    const sellerId = direction === 'sell' ? playerId : tradeTarget.id;
    const buyerId = direction === 'sell' ? tradeTarget.id : playerId;
    setTradeBusy(true);
    try {
      const res: any = await tradeDrugs(sellerId, buyerId, itemId, qty);
      showGameToast({ type: 'success', title: 'Trade done', message: res?.message || ('Traded ' + qty + ' oz for $' + (res?.total || 0)), duration: 3000 });
      try { await refetchPlayer(); } catch (_) {}
      try {
        const [mine, theirs] = await Promise.all([getPlayerDrugs(playerId), getPlayerDrugs(tradeTarget.id)]);
        setTradeMyDrugs(mine?.drugs || []);
        setTradeTheirDrugs(theirs?.drugs || []);
        setTradeTheirCash(theirs?.cash || 0);
      } catch (_) {}
      setTradeSellItem(null); setTradeSellQty(1);
      setTradeBuyItem(null); setTradeBuyQty(1);
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Trade failed', message: e?.response?.data?.detail || 'Trade failed', duration: 3000 });
    } finally {
      setTradeBusy(false);
    }
  }, [playerId, tradeTarget, tradeBusy, tradeSellItem, tradeSellQty, tradeBuyItem, tradeBuyQty]);

  // Load relationship status when player popup opens"""

BUTTON_ANCHOR = """              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#e74c3c'}]} onPress={() => handlePvPChallenge(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>CHALLENGE TO BATTLE</Text>
              </TouchableOpacity>"""

BUTTON_BLOCK = BUTTON_ANCHOR + """
              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#27ae60', marginTop: 8}]} onPress={() => openTradeModal(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>TRADE DRUGS</Text>
              </TouchableOpacity>"""

MODAL_ANCHOR = """      {/* Bank Robbery Modal */}"""

MODAL_BLOCK = """      {/* PLAYER_DRUG_TRADE: trade drugs with the tapped player at regular price */}
      <Modal
        visible={!!tradeTarget}
        transparent
        animationType="fade"
        onRequestClose={() => setTradeTarget(null)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setTradeTarget(null)}>
          <Pressable style={[styles.terrModal, { maxHeight: '88%' }]} onPress={(e) => e.stopPropagation()}>
            <TouchableOpacity style={styles.terrClose} onPress={() => setTradeTarget(null)}>
              <Ionicons name="close" size={22} color="#666" />
            </TouchableOpacity>

            {tradeTarget && (
              <>
                <View style={styles.terrHeader}>
                  <Text style={styles.bankIcon}>💊</Text>
                  <View style={styles.terrHeaderText}>
                    <Text style={styles.terrName}>TRADE DRUGS</Text>
                    <Text style={styles.terrSubtitle}>with {tradeTarget.name} • Regular price • 1-10 oz per trade</Text>
                  </View>
                </View>

                {tradeLoading ? (
                  <ActivityIndicator size="large" color="#f39c12" style={{ marginVertical: 24 }} />
                ) : (
                  <ScrollView showsVerticalScrollIndicator={false}>
                    <Text style={styles.tradeSectionTitle}>YOUR DRUGS — sell to {tradeTarget.name}</Text>
                    <Text style={styles.tradeCash}>Your cash: ${(player?.cash || 0).toLocaleString()}</Text>
                    {tradeMyDrugs.map((d: any) => (
                      <TouchableOpacity
                        key={d.item_id}
                        style={[styles.tradeRow, tradeSellItem === d.item_id && styles.tradeRowSelected]}
                        onPress={() => { setTradeSellItem(d.item_id); setTradeSellQty(1); }}
                      >
                        <Text style={styles.tradeRowName}>{d.name}</Text>
                        <Text style={styles.tradeRowQty}>{d.qty} oz</Text>
                        <Text style={styles.tradeRowPrice}>${d.price}/oz</Text>
                      </TouchableOpacity>
                    ))}
                    {tradeSellItem && (
                      <View style={styles.tradeConfirmBox}>
                        <View style={styles.tradeQtyRow}>
                          <TouchableOpacity style={styles.tradeQtyBtn} onPress={() => setTradeSellQty((q: number) => Math.max(1, q - 1))}>
                            <Text style={styles.tradeQtyBtnText}>-</Text>
                          </TouchableOpacity>
                          <Text style={styles.tradeQtyText}>{tradeSellQty} oz</Text>
                          <TouchableOpacity style={styles.tradeQtyBtn} onPress={() => setTradeSellQty((q: number) => Math.min(10, q + 1))}>
                            <Text style={styles.tradeQtyBtnText}>+</Text>
                          </TouchableOpacity>
                          <Text style={styles.tradeTotal}>Total: ${((tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.price || 0) * tradeSellQty).toLocaleString()}</Text>
                        </View>
                        <TouchableOpacity
                          style={[styles.terrBtn, { backgroundColor: '#27ae60' }, (tradeBusy || tradeSellQty > (tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.qty || 0) || ((tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.price || 0) * tradeSellQty) > tradeTheirCash) && { opacity: 0.5 }]}
                          disabled={tradeBusy || tradeSellQty > (tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.qty || 0) || ((tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.price || 0) * tradeSellQty) > tradeTheirCash}
                          onPress={() => handleTradeConfirm('sell')}
                        >
                          {tradeBusy ? (
                            <ActivityIndicator size="small" color="#fff" />
                          ) : (
                            <Text style={styles.terrBtnText}>SELL {tradeSellQty} OZ TO {tradeTarget.name.toUpperCase()}</Text>
                          )}
                        </TouchableOpacity>
                        {tradeSellQty > (tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.qty || 0) && (
                          <Text style={styles.tradeError}>You only hold {(tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.qty || 0)} oz of this.</Text>
                        )}
                        {((tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.price || 0) * tradeSellQty) > tradeTheirCash && (
                          <Text style={styles.tradeError}>{tradeTarget.name} only has ${tradeTheirCash.toLocaleString()} cash.</Text>
                        )}
                      </View>
                    )}

                    <Text style={[styles.tradeSectionTitle, { marginTop: 18 }]}>{tradeTarget.name.toUpperCase()}'S DRUGS — buy from them</Text>
                    <Text style={styles.tradeCash}>{tradeTarget.name}'s cash: ${tradeTheirCash.toLocaleString()}</Text>
                    {tradeTheirDrugs.map((d: any) => (
                      <TouchableOpacity
                        key={d.item_id}
                        style={[styles.tradeRow, tradeBuyItem === d.item_id && styles.tradeRowSelected]}
                        onPress={() => { setTradeBuyItem(d.item_id); setTradeBuyQty(1); }}
                      >
                        <Text style={styles.tradeRowName}>{d.name}</Text>
                        <Text style={styles.tradeRowQty}>{d.qty} oz</Text>
                        <Text style={styles.tradeRowPrice}>${d.price}/oz</Text>
                      </TouchableOpacity>
                    ))}
                    {tradeBuyItem && (
                      <View style={styles.tradeConfirmBox}>
                        <View style={styles.tradeQtyRow}>
                          <TouchableOpacity style={styles.tradeQtyBtn} onPress={() => setTradeBuyQty((q: number) => Math.max(1, q - 1))}>
                            <Text style={styles.tradeQtyBtnText}>-</Text>
                          </TouchableOpacity>
                          <Text style={styles.tradeQtyText}>{tradeBuyQty} oz</Text>
                          <TouchableOpacity style={styles.tradeQtyBtn} onPress={() => setTradeBuyQty((q: number) => Math.min(10, q + 1))}>
                            <Text style={styles.tradeQtyBtnText}>+</Text>
                          </TouchableOpacity>
                          <Text style={styles.tradeTotal}>Total: ${((tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.price || 0) * tradeBuyQty).toLocaleString()}</Text>
                        </View>
                        <TouchableOpacity
                          style={[styles.terrBtn, { backgroundColor: '#e67e22' }, (tradeBusy || tradeBuyQty > (tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.qty || 0) || ((tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.price || 0) * tradeBuyQty) > (player?.cash || 0)) && { opacity: 0.5 }]}
                          disabled={tradeBusy || tradeBuyQty > (tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.qty || 0) || ((tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.price || 0) * tradeBuyQty) > (player?.cash || 0)}
                          onPress={() => handleTradeConfirm('buy')}
                        >
                          {tradeBusy ? (
                            <ActivityIndicator size="small" color="#fff" />
                          ) : (
                            <Text style={styles.terrBtnText}>BUY {tradeBuyQty} OZ</Text>
                          )}
                        </TouchableOpacity>
                        {tradeBuyQty > (tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.qty || 0) && (
                          <Text style={styles.tradeError}>{tradeTarget.name} only holds {(tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.qty || 0)} oz of this.</Text>
                        )}
                        {((tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.price || 0) * tradeBuyQty) > (player?.cash || 0) && (
                          <Text style={styles.tradeError}>You need ${((tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.price || 0) * tradeBuyQty).toLocaleString()} — you have ${(player?.cash || 0).toLocaleString()}.</Text>
                        )}
                      </View>
                    )}
                  </ScrollView>
                )}
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>

""" + MODAL_ANCHOR

STYLE_ANCHOR = """  socialButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },
});"""

STYLE_BLOCK = """  socialButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },

  // PLAYER_DRUG_TRADE
  tradeSectionTitle: { color: '#f39c12', fontSize: 13, fontWeight: '800', letterSpacing: 1, marginBottom: 8 },
  tradeCash: { color: '#888', fontSize: 12, marginBottom: 8 },
  tradeRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#222', borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 2, borderColor: 'transparent' },
  tradeRowSelected: { borderColor: '#f39c12', backgroundColor: '#2a2118' },
  tradeRowName: { color: '#fff', fontSize: 14, fontWeight: '700', flex: 1 },
  tradeRowQty: { color: '#aaa', fontSize: 13, marginRight: 12 },
  tradeRowPrice: { color: '#2ecc71', fontSize: 13, fontWeight: '700' },
  tradeConfirmBox: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, marginBottom: 8 },
  tradeQtyRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  tradeQtyBtn: { backgroundColor: '#333', width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  tradeQtyBtnText: { color: '#fff', fontSize: 18, fontWeight: '800' },
  tradeQtyText: { color: '#fff', fontSize: 15, fontWeight: '700', minWidth: 44, textAlign: 'center' },
  tradeTotal: { color: '#ffd23f', fontSize: 14, fontWeight: '800', marginLeft: 'auto' },
  tradeError: { color: '#e74c3c', fontSize: 12, marginTop: 8, textAlign: 'center' },
});"""


def _replace_once(src, anchor, block, name, failures):
    if src.count(anchor) != 1:
        failures.append("%s: anchor count %d (want 1)" % (name, src.count(anchor)))
        return src
    return src.replace(anchor, block, 1)


def main():
    failures = []
    if not INDEX.exists() or not API.exists():
        print("TRADE_DRUGS_FRONTEND_FAIL index.tsx or api.ts not found")
        return 1

    api_src = API.read_text(encoding="utf-8")
    if "export const tradeDrugs" in api_src and "export const getPlayerDrugs" in api_src:
        print("TRADE_DRUGS_FRONTEND_API_ALREADY_APPLIED")
    else:
        api_src = _replace_once(api_src, API_ANCHOR, API_BLOCK, "api.ts pharmacySell", failures)
        API.write_text(api_src, encoding="utf-8")

    src = INDEX.read_text(encoding="utf-8")
    if "openTradeModal" in src and "TRADE DRUGS" in src and "tradeSectionTitle" in src:
        print("TRADE_DRUGS_FRONTEND_INDEX_ALREADY_APPLIED")
    else:
        src = _replace_once(src, IMPORT_ANCHOR, IMPORT_BLOCK, "index.tsx import", failures)
        src = _replace_once(src, STATE_ANCHOR, STATE_BLOCK, "index.tsx trade state", failures)
        src = _replace_once(src, HANDLER_ANCHOR, HANDLER_BLOCK, "index.tsx trade handlers", failures)
        src = _replace_once(src, BUTTON_ANCHOR, BUTTON_BLOCK, "index.tsx TRADE button", failures)
        src = _replace_once(src, MODAL_ANCHOR, MODAL_BLOCK, "index.tsx trade modal", failures)
        src = _replace_once(src, STYLE_ANCHOR, STYLE_BLOCK, "index.tsx trade styles", failures)
        INDEX.write_text(src, encoding="utf-8")

    # Verify the landed behaviours, not just the marker.
    api_src = API.read_text(encoding="utf-8")
    src = INDEX.read_text(encoding="utf-8")
    for needle in (
        "export const getPlayerDrugs",
        "export const tradeDrugs",
        "/players/${playerId}/drugs",
        "api.post('/trade/drugs'",
    ):
        if needle not in api_src:
            failures.append("api.ts missing: %s" % needle)
    for needle in (
        "getPlayerDrugs,",
        "tradeDrugs,",
        "openTradeModal",
        "handleTradeConfirm",
        "TRADE DRUGS",
        "tradeSectionTitle",
        "YOUR DRUGS",
        "SELL {tradeSellQty} OZ",
        "BUY {tradeBuyQty} OZ",
    ):
        if needle not in src:
            failures.append("index.tsx missing: %s" % needle)

    if failures:
        print("TRADE_DRUGS_FRONTEND_FAIL " + " | ".join(failures))
        return 1
    print("TRADE_DRUGS_FRONTEND_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
