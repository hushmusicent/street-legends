import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import {
  initConnection,
  endConnection,
  fetchProducts,
  requestPurchase,
  finishTransaction,
  purchaseUpdatedListener,
  purchaseErrorListener,
} from 'react-native-iap';
import api from '../services/api';

const SKUS = ['god_potion_health_1h', 'god_potion_energy_1h'];

const POTION_META: Record<string, { name: string; desc: string; icon: keyof typeof Ionicons.glyphMap; color: string }> = {
  god_potion_health_1h: {
    name: 'Infinite Health Potion',
    desc: 'Take no damage for 1 hour',
    icon: 'heart',
    color: '#e74c3c',
  },
  god_potion_energy_1h: {
    name: 'Infinite Energy Potion',
    desc: 'Skills cost no energy for 1 hour',
    icon: 'flash',
    color: '#3498db',
  },
};

const REMAINING_KEY: Record<string, string> = {
  god_potion_health_1h: 'infinite_health',
  god_potion_energy_1h: 'infinite_energy',
};

function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function GodPotions({ playerId }: { playerId: string | null }) {
  const [connecting, setConnecting] = useState(true);
  const [products, setProducts] = useState<any[]>([]);
  const [remaining, setRemaining] = useState<Record<string, number>>({ infinite_health: 0, infinite_energy: 0 });
  const [buying, setBuying] = useState<string | null>(null);
  const playerIdRef = useRef(playerId);
  playerIdRef.current = playerId;

  const refreshGodmode = async () => {
    const pid = playerIdRef.current;
    if (!pid) return;
    try {
      const res = await api.get(`/players/${pid}/godmode`);
      const r = res.data?.remaining_seconds || {};
      setRemaining({
        infinite_health: r.infinite_health || 0,
        infinite_energy: r.infinite_energy || 0,
      });
    } catch (_) {
      // Backend may predate the godmode endpoints; ignore.
    }
  };

  useEffect(() => {
    if (Platform.OS !== 'android') {
      setConnecting(false);
      return;
    }
    let purchaseSub: any = null;
    let errorSub: any = null;
    let timer: any = null;
    let mounted = true;

    (async () => {
      try {
        const ok = await initConnection();
        if (!ok) throw new Error('Billing unavailable');
        const prods = await fetchProducts({ skus: SKUS });
        if (mounted) setProducts(prods || []);
        await refreshGodmode();
      } catch (e) {
        console.warn('GodPotions billing init failed:', e);
      } finally {
        if (mounted) setConnecting(false);
      }
    })();

    purchaseSub = purchaseUpdatedListener(async (purchase: any) => {
      const pid = playerIdRef.current;
      try {
        if (!pid) throw new Error('Not logged in');
        await api.post('/iap/grant-godmode', {
          player_id: pid,
          product_id: purchase.productId,
          purchase_token: purchase.purchaseToken,
        });
        await finishTransaction({ purchase, isConsumable: true });
        await refreshGodmode();
        const meta = POTION_META[purchase.productId];
        Alert.alert(
          'Potion Activated!',
          `${meta?.name || 'Potion'} is live for 1 hour. Go wild.`
        );
      } catch (err: any) {
        Alert.alert(
          'Activation Failed',
          err?.response?.data?.detail || err?.message || 'Could not activate your potion.'
        );
      } finally {
        setBuying(null);
      }
    });

    errorSub = purchaseErrorListener((error: any) => {
      setBuying(null);
      if (error?.code === 'E_USER_CANCELLED') return;
      Alert.alert('Purchase Failed', error?.message || 'The purchase did not complete.');
    });

    timer = setInterval(refreshGodmode, 30000);

    return () => {
      mounted = false;
      try { purchaseSub?.remove(); } catch (_) {}
      try { errorSub?.remove(); } catch (_) {}
      if (timer) clearInterval(timer);
      endConnection().catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (Platform.OS !== 'android') return null;

  const buy = async (sku: string) => {
    if (!playerIdRef.current) {
      Alert.alert('Login Required', 'Log in before buying a potion.');
      return;
    }
    try {
      setBuying(sku);
      await requestPurchase({ sku });
      // Result arrives via purchaseUpdatedListener.
    } catch (e: any) {
      setBuying(null);
      if (e?.code === 'E_USER_CANCELLED') return;
      Alert.alert('Purchase Failed', e?.message || 'Could not start the purchase.');
    }
  };

  const priceFor = (sku: string) => {
    const p = products.find((x: any) => (x.id ?? x.productId) === sku);
    return p?.displayPrice || p?.localizedPrice || '$1.00';
  };

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Ionicons name="flask" size={18} color="#f39c12" />
        <Text style={styles.sectionTitle}>GOD POTIONS</Text>
        <View style={styles.realMoneyBadge}>
          <Text style={styles.realMoneyText}>REAL MONEY</Text>
        </View>
      </View>

      {connecting ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator size="small" color="#f39c12" />
          <Text style={styles.loadingText}>Connecting to Play Store...</Text>
        </View>
      ) : (
        SKUS.map((sku) => {
          const meta = POTION_META[sku];
          const secs = remaining[REMAINING_KEY[sku]] || 0;
          const active = secs > 0;
          const isBuying = buying === sku;
          return (
            <View key={sku} style={[styles.card, { borderLeftColor: meta.color, borderLeftWidth: 3 }]}>
              <View style={[styles.iconWrap, { backgroundColor: `${meta.color}18` }]}>
                <Ionicons name={meta.icon} size={26} color={meta.color} />
              </View>
              <View style={styles.info}>
                <Text style={styles.name}>{meta.name}</Text>
                <Text style={styles.desc}>{meta.desc}</Text>
                {active ? (
                  <View style={styles.activeRow}>
                    <Ionicons name="timer" size={13} color="#2ecc71" />
                    <Text style={styles.activeText}>ACTIVE — {formatTime(secs)} left</Text>
                  </View>
                ) : (
                  <Text style={styles.price}>{priceFor(sku)}</Text>
                )}
              </View>
              <TouchableOpacity
                style={[styles.buyBtn, { backgroundColor: meta.color }, isBuying && styles.buyBtnDisabled]}
                onPress={() => buy(sku)}
                disabled={isBuying}
              >
                {isBuying ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.buyText}>{active ? 'EXTEND' : 'BUY'}</Text>
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
  activeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 4,
  },
  activeText: {
    color: '#2ecc71',
    fontSize: 13,
    fontWeight: '700',
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
