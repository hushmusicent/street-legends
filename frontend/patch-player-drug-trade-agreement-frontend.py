#!/usr/bin/env python3
"""Two-step drug trade UI: BOTH players must agree before a trade completes.

User (2026-11-12): "both players have to agree with the trade before it's
complete."

The v1 trade modal executed the trade the moment SELL / BUY was tapped.
Now SELL / BUY SENDS AN OFFER and nothing moves until the other player
accepts it:

  - SELL / BUY buttons become "SEND SELL OFFER" / "SEND BUY OFFER". After a
    proposal is sent, the modal shows "Waiting for {name} to accept your
    offer: {qty} oz {item} for ${total}" with a CANCEL OFFER button.
  - When the trade modal opens, it also fetches the pending offers between
    the two players. An INCOMING offer shows at the TOP of the modal as a
    card — "{name} wants to sell you / buy from you {qty} oz {item} for
    ${total}" — with green ACCEPT and red DECLINE buttons. Accepting
    executes the trade (toast + player + both sides refresh); declining
    just removes it.
  - While the map screen is open, pending offers are polled every 15s. When
    a NEW incoming offer appears, a toast fires once: "Trade offer from
    {name} — tap them on the map to accept or decline." No auto-open.
  - While the trade modal is open, the pending offers with that player
    refresh every 15s so an incoming offer appears without reopening.

Adds to frontend/services/api.ts:
  - proposeTradeDrug / getPendingTradeOffers / respondTradeDrug /
    cancelTradeDrug (the v1 tradeDrugs direct helper stays exported).

Keeps the v2 availability behaviour (only qty > 0 rows, qty picker caps at
min(10, oz held)) and the Follow / Add Friend / CHALLENGE TO BATTLE buttons
untouched. The v1 direct tradeDrugs call is no longer made from the modal.

Requires the v1 trade frontend patch (patch-player-drug-trade-frontend.py)
to have run first. Works whether or not the v2 availability patch ran.

This is a FRONTEND patch: run in /app, check in Expo Go first, then Deploy.
Marker: TRADE_AGREEMENT_FRONTEND_OK
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
API = Path("frontend/services/api.ts")

# ---------------------------------------------------------------- api.ts
API_ANCHOR = """export const tradeDrugs = async (sellerId: string, buyerId: string, itemId: string, qty: number): Promise<{ ok: boolean; item_id: string; name: string; qty: number; total: number; seller_cash: number; buyer_cash: number; message: string }> => {
  const response = await api.post('/trade/drugs', { seller_id: sellerId, buyer_id: buyerId, item_id: itemId, qty });
  return response.data;
};"""

API_BLOCK = API_ANCHOR + """

// TRADE_AGREEMENT: two-step drug trade — propose, then the other player accepts.
export interface TradeOffer {
  offer_id: string;
  seller_id: string;
  buyer_id: string;
  proposer_id: string;
  other_id: string;
  other_name: string;
  item_id: string;
  item_name: string;
  qty: number;
  unit_price: number;
  total: number;
  viewer_role: 'buyer' | 'seller';
  summary: string;
  status: string;
  created_at: string;
}

export const proposeTradeDrug = async (proposerId: string, otherId: string, itemId: string, qty: number, direction: 'sell' | 'buy'): Promise<any> => {
  const response = await api.post('/trade/drugs/propose', { proposer_id: proposerId, other_id: otherId, item_id: itemId, qty, direction });
  return response.data;
};

export const getPendingTradeOffers = async (playerId: string): Promise<{ incoming: TradeOffer[]; outgoing: TradeOffer[] }> => {
  const response = await api.get(`/trade/drugs/pending/${playerId}`);
  return response.data;
};

export const respondTradeDrug = async (offerId: string, playerId: string, accept: boolean): Promise<any> => {
  const response = await api.post('/trade/drugs/respond', { offer_id: offerId, player_id: playerId, accept });
  return response.data;
};

export const cancelTradeDrug = async (offerId: string, playerId: string): Promise<any> => {
  const response = await api.post('/trade/drugs/cancel', { offer_id: offerId, player_id: playerId });
  return response.data;
};"""

# ---------------------------------------------------------------- index.tsx
IMPORT_ANCHOR = """  getPlayerDrugs,
  tradeDrugs,
} from '../../services/api';"""

IMPORT_BLOCK = """  getPlayerDrugs,
  tradeDrugs,
  proposeTradeDrug,
  getPendingTradeOffers,
  respondTradeDrug,
  cancelTradeDrug,
} from '../../services/api';"""

STATE_ANCHOR = """  const [tradeBuyItem, setTradeBuyItem] = useState<string | null>(null);
  const [tradeBuyQty, setTradeBuyQty] = useState(1);"""

STATE_BLOCK = STATE_ANCHOR + """
  // TRADE_AGREEMENT: pending offers between me and the trade target.
  const [tradePending, setTradePending] = useState<{ incoming: any[]; outgoing: any[] }>({ incoming: [], outgoing: [] });
  const tradeSeenOfferIdsRef = useRef<Set<string>>(new Set());"""

# Helpers that openTradeModal needs — inserted before its comment line.
HELPERS_ANCHOR = """  // PLAYER_DRUG_TRADE: open the trade modal for the tapped player."""

HELPERS_BLOCK = """  // TRADE_AGREEMENT: keep only the pending offers with this player.
  const filterTradePendingFor = (pending: any, targetId: string) => {
    const incoming = (pending?.incoming || []).filter((o: any) => o.other_id === targetId);
    const outgoing = (pending?.outgoing || []).filter((o: any) => o.other_id === targetId);
    return { incoming, outgoing };
  };

  // TRADE_AGREEMENT: reload the pending offers between me and this player.
  const refreshTradePending = useCallback(async (targetId: string) => {
    if (!playerId) return;
    try {
      const pending: any = await getPendingTradeOffers(playerId);
      setTradePending(filterTradePendingFor(pending, targetId));
    } catch (_) {}
  }, [playerId]);

""" + HELPERS_ANCHOR

# openTradeModal: reset pending + fetch pending offers alongside the drugs.
OPEN_FETCH_ANCHOR = """      const [mine, theirs] = await Promise.all([
        getPlayerDrugs(playerId),
        getPlayerDrugs(targetPlayer.id),
      ]);
      setTradeMyDrugs(mine?.drugs || []);
      setTradeTheirDrugs(theirs?.drugs || []);
      setTradeTheirCash(theirs?.cash || 0);"""

OPEN_FETCH_BLOCK = """      const [mine, theirs] = await Promise.all([
        getPlayerDrugs(playerId),
        getPlayerDrugs(targetPlayer.id),
      ]);
      setTradeMyDrugs(mine?.drugs || []);
      setTradeTheirDrugs(theirs?.drugs || []);
      setTradeTheirCash(theirs?.cash || 0);
      await refreshTradePending(targetPlayer.id);"""

OPEN_RESET_ANCHOR = "    setTradeTheirCash(0);"
OPEN_RESET_BLOCK = """    setTradeTheirCash(0);
    setTradePending({ incoming: [], outgoing: [] });"""

# The whole v1 handleTradeConfirm function is replaced (regex, see below)
# by propose / respond / cancel handlers + the two 15s polls.
HANDLE_CONFIRM_RE = re.compile(
    r"  // PLAYER_DRUG_TRADE: one direction per confirm[^\n]*\n"
    r"  const handleTradeConfirm = useCallback\(async \(direction: 'sell' \| 'buy'\) => \{.*?"
    r"\n  \}, \[playerId, tradeTarget, tradeBusy, tradeSellItem, tradeSellQty, tradeBuyItem, tradeBuyQty\]\);",
    re.DOTALL,
)

HANDLE_BLOCK = """  // TRADE_AGREEMENT: SELL / BUY now SENDS AN OFFER — nothing moves until
  // the other player accepts it. The direct trade call is no longer used.
  const handleTradePropose = useCallback(async (direction: 'sell' | 'buy') => {
    if (!playerId || !tradeTarget || tradeBusy) return;
    const itemId = direction === 'sell' ? tradeSellItem : tradeBuyItem;
    const qty = direction === 'sell' ? tradeSellQty : tradeBuyQty;
    if (!itemId) return;
    setTradeBusy(true);
    try {
      await proposeTradeDrug(playerId, tradeTarget.id, itemId, qty, direction);
      showGameToast({ type: 'success', title: 'Offer sent', message: 'Waiting for ' + tradeTarget.name + ' to accept', duration: 3000 });
      setTradeSellItem(null); setTradeSellQty(1);
      setTradeBuyItem(null); setTradeBuyQty(1);
      await refreshTradePending(tradeTarget.id);
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Offer failed', message: e?.response?.data?.detail || 'Could not send offer', duration: 3000 });
    } finally {
      setTradeBusy(false);
    }
  }, [playerId, tradeTarget, tradeBusy, tradeSellItem, tradeSellQty, tradeBuyItem, tradeBuyQty, refreshTradePending]);

  // TRADE_AGREEMENT: accept or decline an incoming offer from the modal.
  const handleTradeRespond = useCallback(async (offer: any, accept: boolean) => {
    if (!playerId || !tradeTarget || tradeBusy) return;
    setTradeBusy(true);
    try {
      const res: any = await respondTradeDrug(offer.offer_id, playerId, accept);
      if (accept) {
        showGameToast({ type: 'success', title: 'Trade done', message: res?.message || ('Traded ' + offer.qty + ' oz for $' + (offer.total || 0)), duration: 3000 });
        try { await refetchPlayer(); } catch (_) {}
        try {
          const [mine, theirs] = await Promise.all([getPlayerDrugs(playerId), getPlayerDrugs(tradeTarget.id)]);
          setTradeMyDrugs(mine?.drugs || []);
          setTradeTheirDrugs(theirs?.drugs || []);
          setTradeTheirCash(theirs?.cash || 0);
        } catch (_) {}
      } else {
        showGameToast({ type: 'info', title: 'Offer declined', message: 'You declined the trade offer', duration: 3000 });
      }
      await refreshTradePending(tradeTarget.id);
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Trade failed', message: e?.response?.data?.detail || 'Could not respond to offer', duration: 3000 });
      await refreshTradePending(tradeTarget.id);
    } finally {
      setTradeBusy(false);
    }
  }, [playerId, tradeTarget, tradeBusy, refreshTradePending]);

  // TRADE_AGREEMENT: cancel my own outgoing offer.
  const handleTradeCancel = useCallback(async (offer: any) => {
    if (!playerId || !tradeTarget || tradeBusy) return;
    setTradeBusy(true);
    try {
      await cancelTradeDrug(offer.offer_id, playerId);
      showGameToast({ type: 'info', title: 'Offer cancelled', message: 'Your trade offer was cancelled', duration: 3000 });
      await refreshTradePending(tradeTarget.id);
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Cancel failed', message: e?.response?.data?.detail || 'Could not cancel offer', duration: 3000 });
    } finally {
      setTradeBusy(false);
    }
  }, [playerId, tradeTarget, tradeBusy, refreshTradePending]);

  // TRADE_AGREEMENT: while the map is open, poll for incoming trade offers
  // every 15s and toast once per new offer so the target knows to tap the
  // proposer on the map. No auto-open.
  useEffect(() => {
    if (!playerId) return;
    let stopped = false;
    const checkOffers = async () => {
      try {
        const pending: any = await getPendingTradeOffers(playerId);
        if (stopped) return;
        for (const offer of (pending?.incoming || [])) {
          const id = offer.offer_id;
          if (id && !tradeSeenOfferIdsRef.current.has(id)) {
            tradeSeenOfferIdsRef.current.add(id);
            showGameToast({ type: 'info', title: 'Trade offer', message: 'Trade offer from ' + (offer.other_name || 'a player') + ' — tap them on the map to accept or decline', duration: 5000 });
          }
        }
      } catch (_) {}
    };
    checkOffers();
    const t = setInterval(checkOffers, 15000);
    return () => { stopped = true; clearInterval(t); };
  }, [playerId]);

  // TRADE_AGREEMENT: while the trade modal is open, refresh the pending
  // offers with this player every 15s so an incoming offer appears.
  useEffect(() => {
    if (!tradeTarget || !playerId) return;
    const t = setInterval(() => { refreshTradePending(tradeTarget.id); }, 15000);
    return () => clearInterval(t);
  }, [tradeTarget, playerId, refreshTradePending]);"""

# Modal: SELL / BUY now send offers.
SELL_PRESS_ANCHOR = "onPress={() => handleTradeConfirm('sell')}"
SELL_PRESS_BLOCK = "onPress={() => handleTradePropose('sell')}"
BUY_PRESS_ANCHOR = "onPress={() => handleTradeConfirm('buy')}"
BUY_PRESS_BLOCK = "onPress={() => handleTradePropose('buy')}"
SELL_LABEL_ANCHOR = "<Text style={styles.terrBtnText}>SELL {tradeSellQty} OZ TO {tradeTarget.name.toUpperCase()}</Text>"
SELL_LABEL_BLOCK = "<Text style={styles.terrBtnText}>SEND SELL OFFER — {tradeSellQty} OZ</Text>"
BUY_LABEL_ANCHOR = "<Text style={styles.terrBtnText}>BUY {tradeBuyQty} OZ</Text>"
BUY_LABEL_BLOCK = "<Text style={styles.terrBtnText}>SEND BUY OFFER — {tradeBuyQty} OZ</Text>"

# Modal: incoming + outgoing offer cards at the top of the trade modal.
CARDS_ANCHOR = """                    <Text style={styles.tradeSectionTitle}>YOUR DRUGS — sell to {tradeTarget.name}</Text>"""

CARDS_BLOCK = """                    {tradePending.incoming.map((o: any) => (
                      <View key={o.offer_id} style={styles.tradeOfferCard}>
                        <Text style={styles.tradeOfferText}>{o.summary}</Text>
                        <View style={styles.tradeOfferBtns}>
                          <TouchableOpacity style={[styles.tradeOfferBtn, { backgroundColor: '#27ae60' }]} disabled={tradeBusy} onPress={() => handleTradeRespond(o, true)}>
                            <Text style={styles.tradeOfferBtnText}>ACCEPT</Text>
                          </TouchableOpacity>
                          <TouchableOpacity style={[styles.tradeOfferBtn, { backgroundColor: '#e74c3c' }]} disabled={tradeBusy} onPress={() => handleTradeRespond(o, false)}>
                            <Text style={styles.tradeOfferBtnText}>DECLINE</Text>
                          </TouchableOpacity>
                        </View>
                      </View>
                    ))}
                    {tradePending.outgoing.map((o: any) => (
                      <View key={o.offer_id} style={styles.tradeOfferCard}>
                        <Text style={styles.tradeOfferText}>Waiting for {tradeTarget.name} to accept your offer: {o.qty} oz {o.item_name} for ${o.total.toLocaleString()}</Text>
                        <View style={styles.tradeOfferBtns}>
                          <TouchableOpacity style={[styles.tradeOfferBtn, { backgroundColor: '#555' }]} disabled={tradeBusy} onPress={() => handleTradeCancel(o)}>
                            <Text style={styles.tradeOfferBtnText}>CANCEL OFFER</Text>
                          </TouchableOpacity>
                        </View>
                      </View>
                    ))}
""" + CARDS_ANCHOR

STYLE_ANCHOR = """  tradeError: { color: '#e74c3c', fontSize: 12, marginTop: 8, textAlign: 'center' },
});"""

STYLE_BLOCK = """  tradeError: { color: '#e74c3c', fontSize: 12, marginTop: 8, textAlign: 'center' },

  // TRADE_AGREEMENT offer cards
  tradeOfferCard: { backgroundColor: '#2a2118', borderWidth: 2, borderColor: '#f39c12', borderRadius: 10, padding: 12, marginBottom: 10 },
  tradeOfferText: { color: '#fff', fontSize: 14, fontWeight: '700', marginBottom: 10 },
  tradeOfferBtns: { flexDirection: 'row', gap: 10 },
  tradeOfferBtn: { flex: 1, borderRadius: 8, paddingVertical: 10, alignItems: 'center' },
  tradeOfferBtnText: { color: '#fff', fontSize: 13, fontWeight: '800' },
});"""


def _replace_once(src, anchor, block, name, failures):
    if src.count(anchor) != 1:
        failures.append("%s: anchor count %d (want 1)" % (name, src.count(anchor)))
        return src
    return src.replace(anchor, block, 1)


def _replace_regex_once(src, pattern, block, name, failures):
    new, n = pattern.subn(lambda _m: block, src, count=1)
    if n != 1:
        failures.append("%s: regex matched %d (want 1)" % (name, n))
        return src
    return new


def main():
    failures = []
    if not INDEX.exists() or not API.exists():
        print("TRADE_AGREEMENT_FRONTEND_FAIL index.tsx or api.ts not found")
        return 1

    api_src = API.read_text(encoding="utf-8")
    if "export const proposeTradeDrug" in api_src and "export const getPendingTradeOffers" in api_src and "export const respondTradeDrug" in api_src and "export const cancelTradeDrug" in api_src:
        print("TRADE_AGREEMENT_FRONTEND_API_ALREADY_APPLIED")
    else:
        if "export const tradeDrugs" not in api_src:
            print("TRADE_AGREEMENT_FRONTEND_FAIL v1 trade api helpers not present — run patch-player-drug-trade-frontend.py first")
            return 1
        api_src = _replace_once(api_src, API_ANCHOR, API_BLOCK, "api.ts tradeDrugs", failures)
        API.write_text(api_src, encoding="utf-8")

    src = INDEX.read_text(encoding="utf-8")
    if "handleTradePropose" in src and "handleTradeRespond" in src and "handleTradeCancel" in src and "tradePending" in src:
        print("TRADE_AGREEMENT_FRONTEND_INDEX_ALREADY_APPLIED")
    else:
        if "handleTradeConfirm" not in src or "TRADE DRUGS" not in src:
            print("TRADE_AGREEMENT_FRONTEND_FAIL trade modal not present — run patch-player-drug-trade-frontend.py first")
            return 1
        src = _replace_once(src, IMPORT_ANCHOR, IMPORT_BLOCK, "index.tsx import", failures)
        src = _replace_once(src, STATE_ANCHOR, STATE_BLOCK, "index.tsx trade state", failures)
        src = _replace_once(src, HELPERS_ANCHOR, HELPERS_BLOCK, "index.tsx trade helpers", failures)
        src = _replace_once(src, OPEN_RESET_ANCHOR, OPEN_RESET_BLOCK, "index.tsx openTradeModal reset", failures)
        src = _replace_once(src, OPEN_FETCH_ANCHOR, OPEN_FETCH_BLOCK, "index.tsx openTradeModal fetch", failures)
        src = _replace_regex_once(src, HANDLE_CONFIRM_RE, HANDLE_BLOCK, "index.tsx handleTradeConfirm", failures)
        src = _replace_once(src, SELL_PRESS_ANCHOR, SELL_PRESS_BLOCK, "index.tsx sell onPress", failures)
        src = _replace_once(src, BUY_PRESS_ANCHOR, BUY_PRESS_BLOCK, "index.tsx buy onPress", failures)
        src = _replace_once(src, SELL_LABEL_ANCHOR, SELL_LABEL_BLOCK, "index.tsx sell label", failures)
        src = _replace_once(src, BUY_LABEL_ANCHOR, BUY_LABEL_BLOCK, "index.tsx buy label", failures)
        src = _replace_once(src, CARDS_ANCHOR, CARDS_BLOCK, "index.tsx offer cards", failures)
        src = _replace_once(src, STYLE_ANCHOR, STYLE_BLOCK, "index.tsx trade styles", failures)
        INDEX.write_text(src, encoding="utf-8")

    # Verify the landed behaviours, not just the marker.
    api_src = API.read_text(encoding="utf-8")
    src = INDEX.read_text(encoding="utf-8")
    for needle in (
        "export const proposeTradeDrug",
        "export const getPendingTradeOffers",
        "export const respondTradeDrug",
        "export const cancelTradeDrug",
        "/trade/drugs/propose",
        "/trade/drugs/pending/${playerId}",
        "/trade/drugs/respond",
        "/trade/drugs/cancel",
    ):
        if needle not in api_src:
            failures.append("api.ts missing: %s" % needle)
    for needle in (
        "proposeTradeDrug,",
        "getPendingTradeOffers,",
        "respondTradeDrug,",
        "cancelTradeDrug,",
        "handleTradePropose",
        "handleTradeRespond",
        "handleTradeCancel",
        "refreshTradePending",
        "tradePending.incoming.map",
        "tradePending.outgoing.map",
        "SEND SELL OFFER",
        "SEND BUY OFFER",
        "Waiting for {tradeTarget.name} to accept your offer",
        "Trade offer from",
        "tradeOfferCard",
        "setInterval(checkOffers, 15000)",
    ):
        if needle not in src:
            failures.append("index.tsx missing: %s" % needle)
    for gone in (
        "handleTradeConfirm",
        "tradeDrugs(sellerId, buyerId, itemId, qty)",
    ):
        if gone in src:
            failures.append("index.tsx still has direct-trade code: %s" % gone)

    if failures:
        print("TRADE_AGREEMENT_FRONTEND_FAIL " + " | ".join(failures))
        return 1
    print("TRADE_AGREEMENT_FRONTEND_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
