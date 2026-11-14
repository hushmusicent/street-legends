import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  Image,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../services/api';

// IAP only works on native platforms, not web
let initConnection: any = () => Promise.resolve();
let endConnection: any = () => Promise.resolve();
let fetchProducts: any = () => Promise.resolve([]);
let requestPurchase: any = () => Promise.resolve();
let finishTransaction: any = () => Promise.resolve();
let purchaseUpdatedListener: any = () => ({ remove: () => {} });
let purchaseErrorListener: any = () => ({ remove: () => {} });

if (Platform.OS !== 'web') {
  try {
    const iap = require('react-native-iap');
    initConnection = iap.initConnection;
    endConnection = iap.endConnection;
    fetchProducts = iap.fetchProducts;
    requestPurchase = iap.requestPurchase;
    finishTransaction = iap.finishTransaction;
    purchaseUpdatedListener = iap.purchaseUpdatedListener;
    purchaseErrorListener = iap.purchaseErrorListener;
  } catch (e) {
    console.log('IAP not available:', e);
  }
}

// Bonus bundles - real money via Google Play Billing.
// These product IDs must be created in Play Console (same as the God
// Potions) before they can be bought. Prices below are the fallback
// shown until Play returns the live product price.
const SKUS = ['bonus_cash_100k', 'bonus_cash_250k', 'bonus_pack_500k', 'bonus_pack_1m'];

const BUNDLE_META: Record<string, { name: string; contents: string[]; fallbackPrice: string; icon: keyof typeof Ionicons.glyphMap; color: string }> = {
  bonus_cash_100k: {
    name: '$100,000 Cash',
    contents: ['$100,000 in-game cash'],
    fallbackPrice: '$10.00',
    icon: 'cash',
    color: '#2ecc71',
  },
  bonus_cash_250k: {
    name: '$250,000 Cash',
    contents: ['$250,000 in-game cash'],
    fallbackPrice: '$25.00',
    icon: 'cash',
    color: '#27ae60',
  },
  bonus_pack_500k: {
    name: '$500,000 Pack',
    contents: ['$500,000 in-game cash', '5x Health MK1 (full HP restore)', '5x Energy MK1 (full Energy restore)'],
    fallbackPrice: '$50.00',
    icon: 'gift',
    color: '#f39c12',
  },
  bonus_pack_1m: {
    name: '$1,000,000 Pack',
    contents: ['$1,000,000 in-game cash', '5x Health MK1 (full HP restore)', '5x Energy MK1 (full Energy restore)', '1x Infinite Health (1 hour)', '1x Infinite Energy (1 hour)'],
    fallbackPrice: '$100.00',
    icon: 'diamond',
    color: '#9b59b6',
  },
};

export function BonusBundles({ playerId }: { playerId: string | null }) {
  const [connecting, setConnecting] = useState(true);
  const [products, setProducts] = useState<any[]>([]);
  const [buying, setBuying] = useState<string | null>(null);
  const [mk1, setMk1] = useState<{ health_mk1: number; energy_mk1: number }>({ health_mk1: 0, energy_mk1: 0 });
  const [using, setUsing] = useState<string | null>(null);
  const playerIdRef = useRef(playerId);
  playerIdRef.current = playerId;
  const buyTimeoutRef = useRef<any>(null);
  const clearBuyTimeout = () => { if (buyTimeoutRef.current) { clearTimeout(buyTimeoutRef.current); buyTimeoutRef.current = null; } };

  const refreshMk1 = async () => {
    const pid = playerIdRef.current;
    if (!pid) return;
    try {
      const res = await api.get(`/players/${pid}/bonus-items`);
      const b = res.data || {};
      setMk1({
        health_mk1: b.health_mk1 || 0,
        energy_mk1: b.energy_mk1 || 0,
      });
    } catch (_) {
      // Backend may predate the bonus endpoints; ignore.
    }
  };

  useEffect(() => {
    if (Platform.OS !== 'android') {
      setConnecting(false);
      return;
    }
    let purchaseSub: any = null;
    let errorSub: any = null;
    let mounted = true;

    (async () => {
      try {
        const ok = await initConnection();
        if (!ok) throw new Error('Billing unavailable');
        const prods = await fetchProducts({ skus: SKUS });
        if (mounted) setProducts(prods || []);
        await refreshMk1();
      } catch (e) {
        console.warn('BonusBundles billing init failed:', e);
      } finally {
        if (mounted) setConnecting(false);
      }
    })();

    purchaseSub = purchaseUpdatedListener(async (purchase: any) => {
      // Ignore purchases for other products (e.g. God Potions). Without
      // this, a God Potion buy would pop a 'Grant Failed' alert here.
      if (!SKUS.includes(purchase.productId)) return;
      const pid = playerIdRef.current;
      try {
        if (!pid) throw new Error('Not logged in');
        const res = await api.post('/iap/grant-bonus', {
          player_id: pid,
          product_id: purchase.productId,
          purchase_token: purchase.purchaseToken,
        });
        await finishTransaction({ purchase, isConsumable: true });
        await refreshMk1();
        const meta = BUNDLE_META[purchase.productId];
        Alert.alert(
          'Bonus Granted!',
          res.data?.message || `${meta?.name || 'Bundle'} is yours.`
        );
      } catch (err: any) {
        Alert.alert(
          'Grant Failed',
          err?.response?.data?.detail || err?.message || 'Could not grant your bundle.'
        );
      } finally {
        clearBuyTimeout();
        setBuying(null);
      }
    });

    errorSub = purchaseErrorListener((error: any) => {
      clearBuyTimeout();
      setBuying(null);
      if (error?.code === 'E_USER_CANCELLED') return;
      Alert.alert('Purchase Failed', error?.message || 'The purchase did not complete.');
    });

    return () => {
      mounted = false;
      try { purchaseSub?.remove(); } catch (_) {}
      try { errorSub?.remove(); } catch (_) {}
      clearBuyTimeout();
      // Do NOT call endConnection() here: GodPotions is also mounted in
      // the shop and shares this billing connection. Disconnecting when
      // the Bonus tab unmounts kills GodPotions purchases (stuck spinner
      // / frozen shop). GodPotions owns the connection lifecycle.
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (Platform.OS !== 'android') return null;

  const buy = async (sku: string) => {
    if (!playerIdRef.current) {
      Alert.alert('Login Required', 'Log in before buying a bundle.');
      return;
    }
    // Safety net: if Play Billing never answers and neither listener
    // fires, unstick the button after 30s instead of spinning forever.
    clearBuyTimeout();
    buyTimeoutRef.current = setTimeout(() => {
      setBuying((cur: string | null) => (cur === sku ? null : cur));
      buyTimeoutRef.current = null;
    }, 30000);
    try {
      setBuying(sku);
      await requestPurchase({ request: { google: { skus: [sku] } }, type: 'in-app' });
      // Result arrives via purchaseUpdatedListener.
    } catch (e: any) {
      clearBuyTimeout();
      setBuying(null);
      if (e?.code === 'E_USER_CANCELLED') return;
      Alert.alert('Purchase Failed', e?.message || 'Could not start the purchase.');
    }
  };

  const useMk1 = async (item: 'health_mk1' | 'energy_mk1') => {
    const pid = playerIdRef.current;
    if (!pid) return;
    try {
      setUsing(item);
      const res = await api.post('/iap/use-mk1', { player_id: pid, item });
      await refreshMk1();
      Alert.alert('Used!', res.data?.message || 'Restored.');
    } catch (err: any) {
      Alert.alert('Could Not Use', err?.response?.data?.detail || err?.message || 'Try again.');
    } finally {
      setUsing(null);
    }
  };

  const priceFor = (sku: string) => {
    const p = products.find((x: any) => (x.id ?? x.productId) === sku);
    return p?.displayPrice || p?.localizedPrice || BUNDLE_META[sku]?.fallbackPrice || '';
  };

  return (
    <View style={styles.section}>
      <Image source={require('../assets/bonus-banner.jpg')} style={styles.banner} resizeMode="cover" />

      <View style={styles.sectionHeader}>
        <Ionicons name="gift" size={18} color="#f39c12" />
        <Text style={styles.sectionTitle}>BONUS BUNDLES</Text>
        <View style={styles.realMoneyBadge}>
          <Text style={styles.realMoneyText}>REAL MONEY</Text>
        </View>
      </View>

      {(mk1.health_mk1 > 0 || mk1.energy_mk1 > 0) && (
        <View style={styles.mk1Row}>
          <View style={styles.mk1Chip}>
            <Ionicons name="medkit" size={16} color="#e74c3c" />
            <Text style={styles.mk1Text}>Health MK1 x{mk1.health_mk1}</Text>
            <TouchableOpacity
              style={styles.useBtn}
              onPress={() => useMk1('health_mk1')}
              disabled={using === 'health_mk1' || mk1.health_mk1 <= 0}
            >
              <Text style={styles.useText}>{using === 'health_mk1' ? '...' : 'USE'}</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.mk1Chip}>
            <Ionicons name="flash" size={16} color="#3498db" />
            <Text style={styles.mk1Text}>Energy MK1 x{mk1.energy_mk1}</Text>
            <TouchableOpacity
              style={styles.useBtn}
              onPress={() => useMk1('energy_mk1')}
              disabled={using === 'energy_mk1' || mk1.energy_mk1 <= 0}
            >
              <Text style={styles.useText}>{using === 'energy_mk1' ? '...' : 'USE'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {connecting ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator size="small" color="#f39c12" />
          <Text style={styles.loadingText}>Connecting to Play Store...</Text>
        </View>
      ) : (
        SKUS.map((sku) => {
          const meta = BUNDLE_META[sku];
          const isBuying = buying === sku;
          return (
            <View key={sku} style={[styles.card, { borderLeftColor: meta.color, borderLeftWidth: 3 }]}>
              <View style={[styles.iconWrap, { backgroundColor: `${meta.color}18` }]}>
                <Ionicons name={meta.icon} size={26} color={meta.color} />
              </View>
              <View style={styles.info}>
                <Text style={styles.name}>{meta.name}</Text>
                {meta.contents.map((c) => (
                  <Text key={c} style={styles.desc}>• {c}</Text>
                ))}
                <Text style={styles.price}>{priceFor(sku)}</Text>
              </View>
              <TouchableOpacity
                style={[styles.buyBtn, { backgroundColor: meta.color }, isBuying && styles.buyBtnDisabled]}
                onPress={() => buy(sku)}
                disabled={isBuying}
              >
                {isBuying ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.buyText}>BUY</Text>
                )}
              </TouchableOpacity>
            </View>
          );
        })
      )}

      {!connecting && products.length === 0 && (
        <Text style={styles.note}>
          Store products are syncing — if buying fails, the products aren't live in Play Console yet.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    backgroundColor: '#141414',
    borderRadius: 12,
    padding: 12,
    marginHorizontal: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  banner: {
    width: '100%',
    height: 170,
    borderRadius: 10,
    marginBottom: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  sectionTitle: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: 1,
    flex: 1,
  },
  realMoneyBadge: {
    backgroundColor: '#f39c12',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  realMoneyText: {
    color: '#000',
    fontSize: 10,
    fontWeight: '800',
  },
  mk1Row: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  mk1Chip: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#1e1e1e',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  mk1Text: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
    flex: 1,
  },
  useBtn: {
    backgroundColor: '#f39c12',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  useText: {
    color: '#000',
    fontSize: 11,
    fontWeight: '800',
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  loadingText: {
    color: '#888',
    fontSize: 13,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e1e1e',
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    gap: 10,
  },
  iconWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: {
    flex: 1,
  },
  name: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  desc: {
    color: '#999',
    fontSize: 12,
    marginTop: 2,
  },
  price: {
    color: '#f39c12',
    fontSize: 14,
    fontWeight: '800',
    marginTop: 4,
  },
  buyBtn: {
    borderRadius: 10,
    paddingHorizontal: 18,
    paddingVertical: 10,
    minWidth: 78,
    alignItems: 'center',
  },
  buyBtnDisabled: {
    opacity: 0.6,
  },
  buyText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '800',
  },
  note: {
    color: '#666',
    fontSize: 11,
    marginTop: 4,
    fontStyle: 'italic',
  },
});
