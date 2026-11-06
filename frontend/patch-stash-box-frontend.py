#!/usr/bin/env python3
"""Street Legends frontend: Stash Box (house Utilities) — Expo Go.

User spec (2026-11-06, preview approved, "Wire it to the house
inventory"): the wooden chest goes in the house inventory under
Utilities, $5,000 buy / $2,500 sell. Tap it and it opens 20 slots,
3 free, $5,000 PER slot to unlock the other 17. Each slot holds a
stack of ONE of the 5 fiend items (Grass/Pills/Rock Candy/Flake/
Brown Sugar). STORE buttons on the 5 item rows in the player
inventory ask HOW MANY first, then show the slot picker.

HOUSE FULL: the Mansion is 6/6 full. The Stash Box is a UTILITY —
it never counts toward the 6-item limit and buying it is never
blocked by a full house. The Utilities dropdown tap is intercepted
in handleHouseItemToggle and goes to the dedicated /stash-box/buy
endpoint, NEVER to the generic items/add path (which would 400
"House is full"). The box is never added to interiorHouse.items.

What this patch does (frontend only: reload Expo Go after running,
no build, no Deploy for this patch itself — the backend patch needs
Publish separately):
  1. services/api.ts: getStashBox / buyStashBox / sellStashBox /
     unlockStashSlot / depositStashItem / withdrawStashItem.
  2. app/(tabs)/index.tsx:
     - Stash Box entry in the HOUSE_ITEMS utilities array (chest art
       embedded as a 400px JPEG data URI, ~17KB).
     - Stash state + handlers (load/buy/unlock/deposit/withdraw/sell)
       after the selectedMarker state; box state loads when the house
       interior opens.
     - Dropdown row: stash-box shows OWNED / BUY $5,000 instead of
       PLACED / TAP TO PLACE; tap is intercepted in
       handleHouseItemToggle (buy -> dedicated endpoint, owned ->
       open the stash modal).
     - Stash modal (before {/* Popup */}): 20-slot grid (5x4),
       locked slots show 🔒 + $5,000, tap to unlock (cash-checked);
       tap an open empty slot -> deposit picker (5 items with held
       oz) -> qty prompt (ask how many FIRST) -> STORE; tap a filled
       slot -> withdraw (qty prompt + TAKE ALL) and STORE MORE.
       SELL $2,500 button with the confirm text (items return to
       inventory first).
  3. app/(tabs)/character.tsx (ItemsTab):
     - STORE button on each of the 5 item rows, right after the USE
       button. USE / ACTIVE states are NOT touched; SELL stays
       removed. STORE -> if no box owned, "Buy the Stash Box first
       - $5,000 in House > Utilities"; else ask HOW MANY first,
       then the slot picker (open slots that are empty or hold the
       same item), then deposit. Inventory + box state refresh after.
Emoji are literal characters, never unicode escapes. Every
"already present" check is scoped to the component being wired.

Run from /app: python3 frontend/patch-stash-box-frontend.py
Idempotent: rerun prints ALREADY_APPLIED per part, files unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"
API = ROOT / "frontend/services/api.ts"

MARKER = "STASH_BOX_FRONTEND_OK"
PRICE = 5000
SELL_PRICE = 2500
SLOT_PRICE = 5000

STASH_CHEST_B64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAGQAZADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5UooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKVVLdAT9BU8dncyfct5W+iGi9gsV6K0Y9E1GT7tpKB7jH86sJ4b1JjzEi/VxWbqwW7RapzeyMaiumt/BmpznCqp/3VZv5Cta1+GesTf8ALC6P+7bt/Ws5YujHeSNFhqr2icHRXqVp8IdXlxm3uR/vbE/ma1rb4LXpx5kYH+/cD+grGWY4dfaNFgaz6Hi9Fe9Q/BV8Df8AZB9ZXP8ASkvPgqRATAbZ39FkZT+vFZ/2rh72uX/Z9Y8Gorv9b+Gmq6eWJhnRR3dMr/30uRXKXehahagl7dnUfxR/MK7KeIpVPhkc86FSHxIy6KVlKnDAg+hpK2MQooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoro9C8Jahq5Tykb5xlVVC7EeuBXd6b8GtSmAM8Mij/prIqfoMmuWrjKNLSUjop4WrU1SPIaK+grL4Lxrjz5LRfX78n+FdBZfCfSoAPMnYn/pnCq/zzXJLOKC21OmOWVXufMUdvNJ/q4pG+ik1bi0bUZPu2kuPcY/nX1LJ4Q8LaUiNqDlQeAZ7jbn6AYqI3HgWx6LZyEekbS/41i84v8ABBmiyy3xSPmqHwzqUhx5aL9XH9K1rP4f6vc42RyN/wBc4Xb+le/r438N2nFnaSEjp5Vuq/4Up+IDzcWWh30w7E8fyBrGWaYh7QsarAUVvK54zafC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Garp+nPqwnuYoLdrjMKk9Rz0H0xXTDkqxbgnoUqjTtI70GiuZuvG+jQH5ZZZv9yM4/XFYt98UdMgyI4Rx3lmVf0GauOGqz+GLHKtTjuz0CivHL74wYJ8j7Mv+6jOf6Cufv8A4s6hNkRz3AB7Iqxj/GumGV4iXQwlj6Mep9BngZPSq1xf2dv/AK+7t4/96QCvmO88fapc5DM7A/8APSVmrIm8S6lIeJET/dQf1rqhktV/E7HPLNKa2R9QXPivRbfO6+Rz6RqW/kKybv4h6RACVSd8f3tqD9TXzRNql9NnzLqY+27FVGdnOWYsfc5rqhkkF8UjCWaS+yj6Dvvi1aR58mK2X/elLn8gK52++L1w2RFKF9PKh/q1eOUV1QyrDx6XOeWY1n1PQdQ+JuqXIIEt0R7zbR+S1gXXi3UZyTmNSe5BY/rXO0V1QwlGG0UYSxNWW8jRn1nUJs77qQD0U7f5VRkkeQ5kdmPqxzTKK3UVHZGLk3uwooopiCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAs2V7cWMu+1laM98dD9RXW6d4zL24t9Q8xUU7hs5XPrjtXE0VjVoQq/EjWnWnT+Fns938adQZQsMxUAYHlwKP55rCvvizrNwCPtN4Qe3mhP8A0EV5rRXNHLMLHaCNXjKz6nV3njjVLokudxPeR2f+ZrIn1/Upid1yyg9kAWsuiuqNCnD4YoxlWnLdk0t1PMcyzSP/ALzE1DRRWuxmFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQB//9k="

STASH_API = '''
// STASH_BOX_API: house Stash Box - 20 slots, 3 free, $5,000 per extra slot.
export const getStashBox = async (playerId: string) => {
  const response = await api.get(`/stash-box?player_id=${playerId}`);
  return response.data;
};

export const buyStashBox = async (playerId: string) => {
  const response = await api.post(`/stash-box/buy?player_id=${playerId}`);
  return response.data;
};

export const sellStashBox = async (playerId: string) => {
  const response = await api.post(`/stash-box/sell?player_id=${playerId}`);
  return response.data;
};

export const unlockStashSlot = async (playerId: string, slot: number) => {
  const response = await api.post(`/stash-box/unlock?player_id=${playerId}&slot=${slot}`);
  return response.data;
};

export const depositStashItem = async (playerId: string, slot: number, itemId: string, qty: number) => {
  const response = await api.post(`/stash-box/deposit?player_id=${playerId}&slot=${slot}&item=${itemId}&qty=${qty}`);
  return response.data;
};

export const withdrawStashItem = async (playerId: string, slot: number, qty: number) => {
  const response = await api.post(`/stash-box/withdraw?player_id=${playerId}&slot=${slot}&qty=${qty}`);
  return response.data;
};
'''

STASH_IMG_CONST = (
    '// STASH_BOX: chest art for the Utilities tab + stash modal (400px JPEG, embedded).\n'
    'const STASH_BOX_IMG = "data:image/jpeg;base64,' + STASH_CHEST_B64 + '";'
)

STASH_STATE = '''
  // STASH_BOX: 20 slots, 3 free, $5,000 per extra slot. A UTILITY: never
  // counts toward the house 6-item limit; buying it never hits the generic
  // items/add path (see handleHouseItemToggle intercept below).
  const [stashBox, setStashBox] = useState<any>(null);
  const [stashModalOpen, setStashModalOpen] = useState(false);
  const [stashDepositSlot, setStashDepositSlot] = useState<number | null>(null);
  const [stashDepositItem, setStashDepositItem] = useState<string | null>(null);
  const [stashQty, setStashQty] = useState('');
  const [stashWithdrawSlot, setStashWithdrawSlot] = useState<number | null>(null);
  const [stashBusy, setStashBusy] = useState<string | null>(null);
  const STASH_ITEMS = [
    { id: 'grass', name: 'Grass', price: 100 },
    { id: 'pills', name: 'Pills', price: 200 },
    { id: 'rock_candy', name: 'Rock Candy', price: 300 },
    { id: 'flake', name: 'Flake', price: 400 },
    { id: 'brown_sugar', name: 'Brown Sugar', price: 500 },
  ];
  // STASH_BOX: oz held for one item id (player.inventory: string ids or {item_id|id, qty|quantity|count}).
  const stashOzHeld = (itemId: string) => {
    const inv: any[] = (player as any)?.inventory || [];
    let held = 0;
    for (const it of inv) {
      if (typeof it === 'string') { if (it === itemId) held += 1; }
      else if (it && (it.item_id === itemId || it.id === itemId)) { held += (it.qty ?? it.quantity ?? it.count ?? 1); }
    }
    return held;
  };
  const loadStashBox = async () => {
    if (!playerId) return;
    try { const res: any = await getStashBox(playerId); setStashBox(res); } catch (_) {}
  };
  useEffect(() => { if (interiorHouse && playerId) { loadStashBox(); } }, [interiorHouse, playerId]);
  // STASH_BOX: buy via the dedicated endpoint (never the generic items/add
  // path - that one enforces the 6-item limit and would 400 on a full house).
  const handleStashBoxToggle = async () => {
    if (!playerId) return;
    if (!stashBox?.owned) {
      if ((player?.cash || 0) < 5000) { Alert.alert('Stash Box', 'You need $5,000 to buy the Stash Box.'); return; }
      try {
        const res: any = await buyStashBox(playerId);
        setStashBox(res?.box || res);
        if (typeof res?.cash === 'number' && player) setPlayer({ ...player, cash: res.cash });
        try { await refetchPlayer(); } catch (_) {}
        Alert.alert('Stash Box', (res && res.message) || 'Stash Box bought! Tap it again to open it.');
      } catch (e: any) { Alert.alert('Stash Box', e?.response?.data?.detail || 'Could not buy the Stash Box.'); }
      return;
    }
    setStashModalOpen(true);
  };
  const handleStashUnlock = async (slot: number) => {
    if (!playerId || stashBusy) return;
    setStashBusy('unlock:' + slot);
    try {
      const res: any = await unlockStashSlot(playerId, slot);
      setStashBox(res?.box || res);
      if (typeof res?.cash === 'number' && player) setPlayer({ ...player, cash: res.cash });
      try { await refetchPlayer(); } catch (_) {}
    } catch (e: any) { Alert.alert('Stash Box', e?.response?.data?.detail || 'Could not unlock that slot.'); }
    finally { setStashBusy(null); }
  };
  const handleStashDeposit = async () => {
    if (!playerId || stashDepositSlot === null || !stashDepositItem) return;
    const qty = parseInt(stashQty, 10);
    if (!qty || qty < 1) { Alert.alert('Stash Box', 'Enter how many oz to store.'); return; }
    if (stashBusy) return;
    setStashBusy('deposit');
    try {
      const res: any = await depositStashItem(playerId, stashDepositSlot, stashDepositItem, qty);
      setStashBox(res?.box || res);
      setStashDepositSlot(null); setStashDepositItem(null); setStashQty('');
      try { await refetchPlayer(); } catch (_) {}
    } catch (e: any) { Alert.alert('Stash Box', e?.response?.data?.detail || 'Could not store that.'); }
    finally { setStashBusy(null); }
  };
  const handleStashWithdraw = async (takeAll: boolean) => {
    if (!playerId || stashWithdrawSlot === null) return;
    const slotEntry = stashBox?.slots?.[String(stashWithdrawSlot)];
    if (!slotEntry) return;
    const qty = takeAll ? slotEntry.qty : parseInt(stashQty, 10);
    if (!qty || qty < 1 || qty > slotEntry.qty) { Alert.alert('Stash Box', 'Enter 1 to ' + slotEntry.qty + ' oz.'); return; }
    if (stashBusy) return;
    setStashBusy('withdraw');
    try {
      const res: any = await withdrawStashItem(playerId, stashWithdrawSlot, qty);
      setStashBox(res?.box || res);
      setStashWithdrawSlot(null); setStashQty('');
      try { await refetchPlayer(); } catch (_) {}
    } catch (e: any) { Alert.alert('Stash Box', e?.response?.data?.detail || 'Could not take that out.'); }
    finally { setStashBusy(null); }
  };
  const handleSellStashBox = async () => {
    if (!playerId) return;
    Alert.alert('Sell Stash Box?', 'Selling returns every stashed item to your inventory first, then pays $2,500.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'SELL $2,500', onPress: async () => {
        try {
          const res: any = await sellStashBox(playerId);
          setStashBox(res?.box || { owned: false });
          if (typeof res?.cash === 'number' && player) setPlayer({ ...player, cash: res.cash });
          setStashModalOpen(false);
          try { await refetchPlayer(); } catch (_) {}
          Alert.alert('Sold!', (res && res.message) || 'Stash Box sold for $2,500.');
        } catch (e: any) { Alert.alert('Stash Box', e?.response?.data?.detail || 'Could not sell the Stash Box.'); }
      } },
    ]);
  };'''

STASH_MODAL = '''      {/* STASH_BOX modal - 20 slots, 3 free, $5,000 per extra slot. */}
      <Modal visible={stashModalOpen} animationType="slide" onRequestClose={() => setStashModalOpen(false)}>
        <View style={{ flex: 1, backgroundColor: '#111', padding: 16 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Image source={{ uri: STASH_BOX_IMG }} style={{ width: 56, height: 56, borderRadius: 10 }} resizeMode="cover" />
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 22, fontWeight: 'bold', color: '#FFD700' }}>STASH BOX</Text>
              <Text style={{ color: '#aaa', fontSize: 13 }}>Your cash: ${player?.cash || 0} · Slots open: {stashBox?.unlocked_count || 3}/20</Text>
            </View>
            <TouchableOpacity onPress={() => setStashModalOpen(false)} style={{ padding: 8 }}>
              <Text style={{ color: '#fff', fontSize: 18 }}>✕</Text>
            </TouchableOpacity>
          </View>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 }}>
            {Array.from({ length: 20 }, (_, i) => {
              const open = (stashBox?.unlocked || [0, 1, 2]).includes(i);
              const entry = stashBox?.slots?.[String(i)];
              const item = entry ? STASH_ITEMS.find((x: any) => x.id === entry.item) : null;
              if (!open) {
                return (
                  <TouchableOpacity key={i} onPress={() => handleStashUnlock(i)} disabled={!!stashBusy} style={{ width: '18%', aspectRatio: 1, borderRadius: 10, borderWidth: 1, borderColor: '#444', backgroundColor: '#181818', alignItems: 'center', justifyContent: 'center' }}>
                    <Text style={{ fontSize: 18 }}>🔒</Text>
                    <Text style={{ color: '#888', fontSize: 11, fontWeight: '700' }}>$5,000</Text>
                  </TouchableOpacity>
                );
              }
              if (!entry) {
                return (
                  <TouchableOpacity key={i} onPress={() => { setStashDepositSlot(i); setStashDepositItem(null); setStashQty(''); }} style={{ width: '18%', aspectRatio: 1, borderRadius: 10, borderWidth: 2, borderColor: '#555', borderStyle: 'dashed', backgroundColor: '#1c1c1c', alignItems: 'center', justifyContent: 'center' }}>
                    <Text style={{ color: '#888', fontSize: 11 }}>EMPTY</Text>
                  </TouchableOpacity>
                );
              }
              return (
                <TouchableOpacity key={i} onPress={() => { setStashWithdrawSlot(i); setStashQty(String(entry.qty)); }} style={{ width: '18%', aspectRatio: 1, borderRadius: 10, borderWidth: 2, borderColor: '#FFD700', backgroundColor: '#241f0a', alignItems: 'center', justifyContent: 'center' }}>
                  <Text style={{ color: '#FFD700', fontWeight: '800', fontSize: 12 }}>{item ? item.name : entry.item}</Text>
                  <Text style={{ color: '#FFD700', fontWeight: '700', fontSize: 12 }}>{entry.qty} oz</Text>
                </TouchableOpacity>
              );
            })}
          </View>
          {stashDepositSlot !== null && !stashDepositItem ? (
            <View style={{ marginTop: 16 }}>
              <Text style={{ color: '#FFD700', fontWeight: '800', fontSize: 15 }}>Store in slot {stashDepositSlot + 1} — pick an item:</Text>
              {STASH_ITEMS.map((it: any) => (
                <TouchableOpacity key={it.id} onPress={() => { if (stashOzHeld(it.id) <= 0) { Alert.alert('Stash Box', 'You have no ' + it.name + ' to store.'); return; } setStashDepositItem(it.id); }} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#222' }}>
                  <Text style={{ color: '#fff', fontWeight: '700' }}>{it.name} · ${it.price}/oz</Text>
                  <Text style={{ color: '#aaa' }}>{stashOzHeld(it.id)} oz held</Text>
                </TouchableOpacity>
              ))}
              <TouchableOpacity onPress={() => setStashDepositSlot(null)} style={{ marginTop: 8 }}><Text style={{ color: '#888' }}>Cancel</Text></TouchableOpacity>
            </View>
          ) : null}
          {stashDepositSlot !== null && stashDepositItem ? (
            <View style={{ marginTop: 16 }}>
              <Text style={{ color: '#FFD700', fontWeight: '800', fontSize: 15 }}>How many oz of {STASH_ITEMS.find((x: any) => x.id === stashDepositItem)?.name}? You hold {stashOzHeld(stashDepositItem)} oz.</Text>
              <TextInput value={stashQty} onChangeText={setStashQty} keyboardType="numeric" placeholder="oz" placeholderTextColor="#666" style={{ backgroundColor: '#1a1a1a', color: '#fff', borderRadius: 8, padding: 10, marginTop: 8 }} />
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 8 }}>
                <TouchableOpacity onPress={handleStashDeposit} disabled={!!stashBusy} style={{ backgroundColor: '#FFD700', borderRadius: 8, paddingVertical: 10, paddingHorizontal: 16 }}><Text style={{ fontWeight: '800', color: '#000' }}>STORE</Text></TouchableOpacity>
                <TouchableOpacity onPress={() => { setStashDepositItem(null); }}><Text style={{ color: '#888', paddingVertical: 10 }}>Back</Text></TouchableOpacity>
              </View>
            </View>
          ) : null}
          {stashWithdrawSlot !== null ? (
            <View style={{ marginTop: 16 }}>
              <Text style={{ color: '#FFD700', fontWeight: '800', fontSize: 15 }}>Take out of slot {stashWithdrawSlot + 1} ({stashBox?.slots?.[String(stashWithdrawSlot)]?.qty || 0} oz in slot):</Text>
              <TextInput value={stashQty} onChangeText={setStashQty} keyboardType="numeric" placeholder="oz" placeholderTextColor="#666" style={{ backgroundColor: '#1a1a1a', color: '#fff', borderRadius: 8, padding: 10, marginTop: 8 }} />
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 8 }}>
                <TouchableOpacity onPress={() => handleStashWithdraw(false)} disabled={!!stashBusy} style={{ backgroundColor: '#FFD700', borderRadius: 8, paddingVertical: 10, paddingHorizontal: 16 }}><Text style={{ fontWeight: '800', color: '#000' }}>TAKE OUT</Text></TouchableOpacity>
                <TouchableOpacity onPress={() => handleStashWithdraw(true)} disabled={!!stashBusy} style={{ backgroundColor: '#333', borderRadius: 8, paddingVertical: 10, paddingHorizontal: 16 }}><Text style={{ fontWeight: '800', color: '#fff' }}>TAKE ALL</Text></TouchableOpacity>
                <TouchableOpacity onPress={() => { const e = stashBox?.slots?.[String(stashWithdrawSlot)]; setStashWithdrawSlot(null); if (e) { setStashDepositSlot(stashWithdrawSlot); setStashDepositItem(e.item); setStashQty(''); } }}><Text style={{ color: '#3498db', paddingVertical: 10 }}>STORE MORE</Text></TouchableOpacity>
                <TouchableOpacity onPress={() => setStashWithdrawSlot(null)}><Text style={{ color: '#888', paddingVertical: 10 }}>Cancel</Text></TouchableOpacity>
              </View>
            </View>
          ) : null}
          <TouchableOpacity onPress={handleSellStashBox} style={{ marginTop: 20, backgroundColor: '#333', borderRadius: 8, paddingVertical: 12, alignItems: 'center' }}>
            <Text style={{ color: '#f39c12', fontWeight: '800' }}>SELL STASH BOX — $2,500 (items return to inventory first)</Text>
          </TouchableOpacity>
        </View>
      </Modal>
'''

CHAR_HANDLERS = '''
  // STASH_BOX: STORE from the item screen. Asks HOW MANY first, then shows the slot picker.
  const [stashBox, setStashBox] = useState<any>(null);
  const [storeItem, setStoreItem] = useState<any>(null);
  const [storeQty, setStoreQty] = useState('');
  const [storeStep, setStoreStep] = useState<'qty' | 'slots' | null>(null);
  const [storeBusy, setStoreBusy] = useState(false);
  const loadStashBox = async () => {
    if (!playerId) return null;
    try { const res: any = await getStashBox(playerId); setStashBox(res); return res; } catch (_) { return null; }
  };
  const stashOzHeld = (itemId: string) => {
    const inv: any[] = (player as any)?.inventory || [];
    let held = 0;
    for (const it of inv) {
      if (typeof it === 'string') { if (it === itemId) held += 1; }
      else if (it && (it.item_id === itemId || it.id === itemId)) { held += (it.qty ?? it.quantity ?? it.count ?? 1); }
    }
    return held;
  };
  const handleStoreItem = async (item: EquipmentItem) => {
    if (!playerId) return;
    const itemId = (item as any).id || (item as any).item_id;
    if (!['grass', 'pills', 'rock_candy', 'flake', 'brown_sugar'].includes(itemId)) return;
    const box = stashBox || (await loadStashBox());
    if (!box?.owned) {
      Alert.alert('Stash Box', 'Buy the Stash Box first — $5,000 in House > Utilities.');
      return;
    }
    setStoreItem(item);
    setStoreQty(String(stashOzHeld(itemId) || ''));
    setStoreStep('qty');
  };
  const confirmStoreQty = () => {
    if (!storeItem) return;
    const itemId = (storeItem as any).id || (storeItem as any).item_id;
    const qty = parseInt(storeQty, 10);
    if (!qty || qty < 1 || qty > stashOzHeld(itemId)) { Alert.alert('Stash Box', 'Enter 1 to ' + stashOzHeld(itemId) + ' oz.'); return; }
    setStoreStep('slots');
  };
  const pickStoreSlot = async (slot: number) => {
    if (!playerId || !storeItem || storeBusy) return;
    const itemId = (storeItem as any).id || (storeItem as any).item_id;
    const qty = parseInt(storeQty, 10);
    setStoreBusy(true);
    try {
      const res: any = await depositStashItem(playerId, slot, itemId, qty);
      setStashBox(res?.box || res);
      setStoreItem(null); setStoreStep(null); setStoreQty('');
      await loadAllData();
      Alert.alert('Stored!', qty + ' oz ' + storeItem.name + ' stored in slot ' + (slot + 1) + '.');
    } catch (e: any) { Alert.alert('Stash Box', e?.response?.data?.detail || 'Could not store that.'); }
    finally { setStoreBusy(false); }
  };'''

STORE_BUTTON = '''                <TouchableOpacity
                  style={[styles.itemActionBtn, styles.equipActionBtn]}
                  onPress={() => onStore(item)}
                >
                  <Ionicons name="archive" size={14} color="#3498db" />
                  <Text style={[styles.itemActionText, { color: '#3498db' }]}>STORE</Text>
                </TouchableOpacity>'''

CHAR_STORE_MODAL = '''      {/* STASH_BOX store modal — ask HOW MANY first, then pick a slot. */}
      <Modal visible={storeStep !== null} animationType="slide" onRequestClose={() => { setStoreStep(null); setStoreItem(null); }}>
        <View style={{ flex: 1, backgroundColor: '#111', padding: 16 }}>
          <Text style={{ fontSize: 22, fontWeight: 'bold', color: '#FFD700' }}>STORE {storeItem?.name || ''}</Text>
          {storeStep === 'qty' && storeItem ? (
            <View style={{ marginTop: 16 }}>
              <Text style={{ color: '#fff' }}>You hold {stashOzHeld((storeItem as any).id || (storeItem as any).item_id)} oz. How many?</Text>
              <TextInput value={storeQty} onChangeText={setStoreQty} keyboardType="numeric" placeholder="oz" placeholderTextColor="#666" style={{ backgroundColor: '#1a1a1a', color: '#fff', borderRadius: 8, padding: 10, marginTop: 8 }} />
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
                <TouchableOpacity onPress={confirmStoreQty} style={{ backgroundColor: '#FFD700', borderRadius: 8, paddingVertical: 10, paddingHorizontal: 16 }}><Text style={{ fontWeight: '800', color: '#000' }}>NEXT</Text></TouchableOpacity>
                <TouchableOpacity onPress={() => { setStoreStep(null); setStoreItem(null); }}><Text style={{ color: '#888', paddingVertical: 10 }}>Cancel</Text></TouchableOpacity>
              </View>
            </View>
          ) : null}
          {storeStep === 'slots' && storeItem ? (
            <View style={{ marginTop: 16 }}>
              <Text style={{ color: '#FFD700', fontWeight: '800', fontSize: 15 }}>Store {storeQty} oz {storeItem.name} — pick a slot:</Text>
              {Array.from({ length: 20 }, (_, i) => {
                const open = (stashBox?.unlocked || [0, 1, 2]).includes(i);
                if (!open) return null;
                const entry = stashBox?.slots?.[String(i)];
                const itemId = (storeItem as any).id || (storeItem as any).item_id;
                if (entry && entry.item !== itemId) return null;
                return (
                  <TouchableOpacity key={i} onPress={() => pickStoreSlot(i)} disabled={storeBusy} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#222' }}>
                    <Text style={{ color: '#fff', fontWeight: '700' }}>Slot {i + 1}{entry ? ' — ' + entry.qty + ' oz already in here' : ' — EMPTY'}</Text>
                    <Text style={{ color: '#FFD700' }}>STORE</Text>
                  </TouchableOpacity>
                );
              })}
              <TouchableOpacity onPress={() => setStoreStep('qty')} style={{ marginTop: 8 }}><Text style={{ color: '#888' }}>Back</Text></TouchableOpacity>
            </View>
          ) : null}
        </View>
      </Modal>
'''

# (display name, USE handler) for the five item rows.
STORE_ROWS = [
    ("Grass", "onUseGrass"),
    ("Pills", "onUsePills"),
    ("RockCandy", "onUseRockCandy"),
    ("Flake", "onUseFlake"),
    ("BrownSugar", "onUseBrownSugar"),
]

SELL_ITEM_ANCHOR = """export const sellItem = async (playerId: string, itemId: string) => {
  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);
  return response.data;
};"""


def delta(s):
    """Balance deltas only (raw counts grow with every insert)."""
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"), s.count("[") - s.count("]"))


def add_to_import(src, module, names):
    """Add names to a single-line `import {...} from 'module'`. Returns (src, ok)."""
    m = re.search(r"import\s+(?:\w+\s*,\s*)?\{([^}]*)\}\s*from\s*['\"]" + re.escape(module) + r"['\"]", src)
    if not m:
        return src, False
    have = [x.strip() for x in m.group(1).split(",") if x.strip()]
    missing = [n for n in names if n not in have]
    if not missing:
        return src, True
    new_inner = ", ".join(have + missing)
    src = src[:m.start(1)] + " " + new_inner + " " + src[m.end(1):]
    return src, True


def main():
    landed = []
    warned = []

    # ================= Part 1: services/api.ts =================
    if not API.exists():
        print("WARNING: services/api.ts not found - Stash Box api functions NOT added")
        warned.append("api")
    else:
        asrc = API.read_text(errors="ignore")
        if "getStashBox" in asrc and "buyStashBox" in asrc and "depositStashItem" in asrc:
            print("STASH_BOX_FRONTEND_API_ALREADY_APPLIED")
            landed.append("api")
        elif SELL_ITEM_ANCHOR in asrc:
            asrc = asrc.replace(SELL_ITEM_ANCHOR, SELL_ITEM_ANCHOR + STASH_API, 1)
            API.write_text(asrc)
            print("STASH_BOX_FRONTEND_API_OK")
            landed.append("api")
        else:
            asrc = asrc + STASH_API
            API.write_text(asrc)
            print("STASH_BOX_FRONTEND_API_OK (appended at end of file - sellItem anchor not found)")
            landed.append("api")

    # ================= Part 2: app/(tabs)/index.tsx =================
    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - Stash Box wiring NOT added")
        warned.append("index")
    else:
        src = INDEX.read_text(errors="ignore")
        iorig = src
        i0 = delta(src)

        # 2a. api imports (scoped to the services/api import block only).
        m = re.search(r"\} from '\.\./\.\./services/api';", src)
        if not m:
            print("WARNING: services/api import not found in index.tsx - Stash Box imports NOT added")
            warned.append("index-import")
        else:
            block = src[:m.start()]
            add = ""
            for n in ("getStashBox", "buyStashBox", "sellStashBox", "unlockStashSlot", "depositStashItem", "withdrawStashItem"):
                if n not in block:
                    add += "  " + n + ",\n"
            if not add:
                print("STASH_BOX_FRONTEND_INDEX_IMPORT_ALREADY_APPLIED")
            else:
                src = src[:m.start()] + add + src[m.start():]
                print("STASH_BOX_FRONTEND_INDEX_IMPORT_OK")

        # 2b. react + react-native imports (useState/useEffect/Alert/Image/Modal/TextInput).
        work, ok = add_to_import(src, "react", ["useState", "useEffect"])
        if ok:
            src = work
        else:
            print("WARNING: react import not extended (useState/useEffect) - stash state may fail")
            warned.append("index-react-import")
        work, ok = add_to_import(src, "react-native", ["Alert", "Image", "Modal", "TextInput"])
        if ok:
            src = work
        else:
            print("WARNING: react-native import not extended (Alert/Image/Modal/TextInput) - stash UI may fail")
            warned.append("index-rn-import")

        # 2c. Chest art const, right before HOUSE_ITEMS (must precede it: the entry references it).
        if "STASH_BOX_IMG" in src:
            print("STASH_BOX_FRONTEND_INDEX_IMG_ALREADY_APPLIED")
        elif src.count("const HOUSE_ITEMS") == 1:
            src = src.replace("const HOUSE_ITEMS", STASH_IMG_CONST + "\n\nconst HOUSE_ITEMS", 1)
            print("STASH_BOX_FRONTEND_INDEX_IMG_OK")
        else:
            print("WARNING: HOUSE_ITEMS anchor not found - chest art const NOT added")
            warned.append("index-img")

        # 2d. Utilities entry (brace-scan, same approach as the Radio patch).
        if "'stash-box'" in src and "Stash Box" in src:
            print("STASH_BOX_FRONTEND_INDEX_ENTRY_ALREADY_APPLIED")
        else:
            hpos = src.find("HOUSE_ITEMS")
            ok = False
            if hpos >= 0:
                upos = src.find("utilities:", hpos)
                if upos >= 0:
                    bstart = src.find("[", upos)
                    if bstart >= 0:
                        depth = 0
                        bend = -1
                        for i in range(bstart, min(len(src), bstart + 8000)):
                            c = src[i]
                            if c == "[":
                                depth += 1
                            elif c == "]":
                                depth -= 1
                                if depth == 0:
                                    bend = i
                                    break
                        if bend > bstart:
                            inner = src[bstart + 1:bend]
                            entry = "{ id: 'stash-box', name: 'Stash Box', image: { uri: STASH_BOX_IMG }, price: 5000 }"
                            if inner.strip() == "":
                                src = src[:bend] + entry + src[bend:]
                            else:
                                src = src[:bend] + ", " + entry + src[bend:]
                            print("STASH_BOX_FRONTEND_INDEX_ENTRY_OK")
                            ok = True
            if not ok:
                print("WARNING: HOUSE_ITEMS utilities array anchor not matched - Stash Box not added to menu")
                warned.append("index-entry")

        # 2e. Stash state + handlers (after the selectedMarker state; fallback: after MapScreen anchor).
        if "handleStashBoxToggle" in src and "loadStashBox" in src:
            print("STASH_BOX_FRONTEND_INDEX_STATE_ALREADY_APPLIED")
        else:
            sm = re.search(r"const \[selectedMarker, setSelectedMarker\] = useState<\{.*?\} \| null>\(null\);", src, re.S)
            if sm:
                src = src[:sm.end()] + "\n" + STASH_STATE.strip("\n") + src[sm.end():]
                print("STASH_BOX_FRONTEND_INDEX_STATE_OK")
            elif "export default function MapScreen() {" in src:
                src = src.replace("export default function MapScreen() {",
                                  "export default function MapScreen() {" + "\n" + STASH_STATE.strip("\n"), 1)
                print("STASH_BOX_FRONTEND_INDEX_STATE_OK (after MapScreen anchor)")
            else:
                print("WARNING: selectedMarker/MapScreen anchor not found - stash state NOT added")
                warned.append("index-state")

        # 2f. Dropdown row: stash-box shows OWNED / BUY $5,000 (not PLACED / TAP TO PLACE).
        placed_old = "const placed = (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);"
        placed_new = "const placed = item.id === 'stash-box' ? !!(stashBox && stashBox.owned) : (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);"
        if placed_new in src:
            print("STASH_BOX_FRONTEND_INDEX_ROW_PLACED_ALREADY_APPLIED")
        elif src.count(placed_old) == 1:
            src = src.replace(placed_old, placed_new, 1)
            print("STASH_BOX_FRONTEND_INDEX_ROW_PLACED_OK")
        else:
            print(f"WARNING: dropdown placed anchor matched {src.count(placed_old)}x - stash-box row state NOT wired")
            warned.append("index-row-placed")
        label_old = "{placed ? '✓ PLACED' : 'TAP TO PLACE'}"
        label_new = "{item.id === 'stash-box' ? (placed ? '✓ OWNED — TAP TO OPEN' : 'BUY $5,000') : (placed ? '✓ PLACED' : 'TAP TO PLACE')}"
        if label_new in src:
            print("STASH_BOX_FRONTEND_INDEX_ROW_LABEL_ALREADY_APPLIED")
        elif src.count(label_old) == 1:
            src = src.replace(label_old, label_new, 1)
            print("STASH_BOX_FRONTEND_INDEX_ROW_LABEL_OK")
        else:
            print(f"WARNING: dropdown label anchor matched {src.count(label_old)}x - stash-box row label NOT wired")
            warned.append("index-row-label")

        # 2g. Toggle intercept: stash-box never goes down the generic items/add path.
        intercept = "    if (item.id === 'stash-box') { await handleStashBoxToggle(); return; }"
        handler_anchor = "  const handleHouseItemToggle = async (item: any) => {\n    if (!interiorHouse || !playerId) return;"
        if intercept in src:
            print("STASH_BOX_FRONTEND_INDEX_TOGGLE_ALREADY_APPLIED")
        elif src.count(handler_anchor) == 1:
            src = src.replace(handler_anchor, handler_anchor + "\n" + intercept, 1)
            print("STASH_BOX_FRONTEND_INDEX_TOGGLE_OK")
        else:
            print(f"WARNING: toggle handler anchor matched {src.count(handler_anchor)}x - stash-box tap NOT intercepted (generic add would 400 'House is full')")
            warned.append("index-toggle")

        # 2h. Stash modal, before the Popup section (same anchor as the Pharmacy modal).
        if "STASH_BOX modal" in src:
            print("STASH_BOX_FRONTEND_INDEX_MODAL_ALREADY_APPLIED")
        elif src.count("      {/* Popup */}") == 1:
            src = src.replace("      {/* Popup */}", STASH_MODAL.rstrip("\n") + "\n      {/* Popup */}", 1)
            print("STASH_BOX_FRONTEND_INDEX_MODAL_OK")
        else:
            print("WARNING: popup section anchor not found - Stash modal NOT added")
            warned.append("index-modal")

        if delta(src) != i0:
            print("WARNING: balance changed - index.tsx NOT written")
            warned.append("index-balance")
        elif src != iorig:
            INDEX.write_text(src)
            landed.append("index")
        elif "handleStashBoxToggle" in src:
            landed.append("index")

    # ================= Part 3: app/(tabs)/character.tsx =================
    if not CHAR.exists():
        print("WARNING: frontend/app/(tabs)/character.tsx not found - STORE buttons NOT added")
        warned.append("character")
    else:
        csrc = CHAR.read_text(errors="ignore")
        corig = csrc
        c0 = delta(csrc)

        # 3a. api imports.
        if "getStashBox" in csrc and "depositStashItem" in csrc:
            print("STASH_BOX_FRONTEND_CHAR_IMPORTS_ALREADY_APPLIED")
        elif "  sellItem,\n" in csrc:
            csrc = csrc.replace("  sellItem,\n", "  sellItem,\n  getStashBox,\n  depositStashItem,\n", 1)
            print("STASH_BOX_FRONTEND_CHAR_IMPORTS_OK")
        else:
            print("WARNING: api import anchor not found in character.tsx - Stash Box imports NOT added")
            warned.append("character-imports")

        # 3b. Stash state + STORE handlers (before handleRepairItem).
        if "handleStoreItem" in csrc and "loadStashBox" in csrc:
            print("STASH_BOX_FRONTEND_CHAR_HANDLERS_ALREADY_APPLIED")
        elif "  const handleRepairItem = async" in csrc:
            csrc = csrc.replace("  const handleRepairItem = async", CHAR_HANDLERS.strip() + "\n\n  const handleRepairItem = async", 1)
            print("STASH_BOX_FRONTEND_CHAR_HANDLERS_OK")
        else:
            print("WARNING: handleRepairItem anchor not found - STORE handlers NOT added")
            warned.append("character-handlers")

        # 3c. ItemsTab props (type + destructure + render) - mirrors the Brown Sugar patch.
        _prop_markers = ("onStore: (item: EquipmentItem) => void;", "onStore={handleStoreItem}")
        if all(x in csrc for x in _prop_markers):
            print("STASH_BOX_FRONTEND_CHAR_PROPS_ALREADY_APPLIED")
        elif any(x in csrc for x in _prop_markers):
            print("WARNING: ItemsTab onStore props partially present - NOT added (hand-fix needed)")
            warned.append("character-props")
        else:
            tline = "  onRepair: (item: EquipmentItem) => void;"
            if tline in csrc:
                ti = csrc.find(tline)
                di = csrc.rfind("  onRepair,\n", 0, ti)
                if di != -1 and ti - di < 8000:
                    csrc = csrc[:di] + "  onRepair,\n  onStore,\n" + csrc[di + len("  onRepair,\n"):]
                    ti = csrc.find(tline)
                    csrc = csrc[:ti + len(tline)] + "\n  onStore: (item: EquipmentItem) => void;" + csrc[ti + len(tline):]
                    print("STASH_BOX_FRONTEND_CHAR_PROPS_OK")
                else:
                    print("WARNING: ItemsTab destructure anchor not found - onStore props NOT added")
                    warned.append("character-props")
            else:
                print("WARNING: ItemsTab props type anchor not found - onStore props NOT added")
                warned.append("character-props")
            ri = csrc.find("onRepair={handleRepairItem}")
            if ri == -1:
                print("WARNING: ItemsTab render anchor not found - onStore NOT wired to the item screen")
                warned.append("character-render")
            else:
                line_start = csrc.rfind("\n", 0, ri) + 1
                line_end = csrc.find("\n", ri)
                indent = csrc[line_start:ri]
                if indent.strip() != "":
                    print("WARNING: ItemsTab render line has unexpected content - onStore NOT wired")
                    warned.append("character-render")
                else:
                    csrc = csrc[:line_end + 1] + indent + "onStore={handleStoreItem}\n" + csrc[line_end + 1:]
                    print("STASH_BOX_FRONTEND_CHAR_RENDER_OK")

        # 3d. STORE button on each of the five item rows, right after the USE button.
        # USE / ACTIVE are never touched: the insert lands after the USE button's
        # closing tag and adds one new button.
        _store_done = []
        for _name, _handler in STORE_ROWS:
            press = "onPress={() => %s()}" % _handler
            if csrc.count("onPress={() => onStore(item)}") >= 5:
                break
            if csrc.count(press) != 1:
                print(f"WARNING: {_name} USE button not found exactly once (x{csrc.count(press)}) - STORE NOT added for {_name}")
                warned.append(f"character-store-{_name.lower()}")
                continue
            pi = csrc.find(press)
            close = csrc.find("</TouchableOpacity>", pi)
            if close == -1:
                print(f"WARNING: {_name} USE button close tag not found - STORE NOT added for {_name}")
                warned.append(f"character-store-{_name.lower()}")
                continue
            end = close + len("</TouchableOpacity>")
            csrc = csrc[:end] + "\n" + STORE_BUTTON + csrc[end:]
            print(f"STASH_BOX_FRONTEND_CHAR_STORE_{_name.upper()}_OK")
            _store_done.append(_name)
        if len(_store_done) == 5:
            landed.append("character-store")
        elif _store_done:
            print("STASH_BOX_FRONTEND_CHAR_STORE_PARTIAL: " + ",".join(_store_done))

        # 3e. Store modal (qty first, then slot picker) before the Profile Picture Menu Modal.
        if "STASH_BOX store modal" in csrc:
            print("STASH_BOX_FRONTEND_CHAR_MODAL_ALREADY_APPLIED")
        elif csrc.count("      {/* Profile Picture Menu Modal */}") == 1:
            csrc = csrc.replace("      {/* Profile Picture Menu Modal */}",
                                CHAR_STORE_MODAL.rstrip("\n") + "\n      {/* Profile Picture Menu Modal */}", 1)
            print("STASH_BOX_FRONTEND_CHAR_MODAL_OK")
        else:
            print("WARNING: profile picture modal anchor not found - store modal NOT added")
            warned.append("character-modal")

        if delta(csrc) != c0:
            print("WARNING: balance changed - character.tsx NOT written")
            warned.append("character-balance")
        elif csrc != corig:
            CHAR.write_text(csrc)
            landed.append("character")
        elif "handleStoreItem" in csrc:
            landed.append("character")

    if warned:
        print("STASH_BOX_FRONTEND_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warned) + ")")
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
