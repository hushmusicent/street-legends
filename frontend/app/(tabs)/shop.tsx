import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
  Modal,
  Pressable,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import { getConsumableShop, buyConsumable, getPlayer, buyHouse, getPlayerHouse, getInventoryHouses, placeHouse, moveHouseToInventory } from '../../services/api';
import api from '../../services/api';
import { GodPotions } from '../../components/GodPotions';
import { getBundledIcon } from '../../assets/icons/iconMap';

type FilterKey = 'all' | 'health_recharge' | 'energy_recharge' | 'combo' | 'consumable' | 'house';
const HOUSES = [
  { tier: 'apartment', name: 'Street Apartment', price: 100000, image: require('../../assets/houses/house-apartment.jpg'), blurb: 'A rough city pad. Four walls, a barred window, and a door that locks.' },
  { tier: 'cabin', name: 'Country Cabin', price: 500000, image: require('../../assets/houses/house-cabin.jpg'), blurb: 'Wood walls, open fields, and quiet. Room to breathe.' },
  { tier: 'mansion', name: 'Luxury Mansion', price: 1000000, image: require('../../assets/houses/house-mansion.jpg'), blurb: 'Marble floors, a chandelier, and gardens. You made it.' },
];

const HOUSE_STYLES = StyleSheet.create({
  houseCard: { backgroundColor: '#111', borderRadius: 12, marginBottom: 12, overflow: 'hidden' },
  houseImage: { width: '100%', height: 180, resizeMode: 'cover' },
  houseInfo: { padding: 12 },
  houseName: { color: '#fff', fontSize: 18, fontWeight: '800' },
  houseBlurb: { color: '#999', fontSize: 13, marginTop: 4 },
  houseWarn: { color: '#f39c12', fontSize: 12, marginTop: 8, fontWeight: '700' },
  houseOwnedBadge: { backgroundColor: 'rgba(76,175,80,0.2)', borderRadius: 8, paddingVertical: 8, alignItems: 'center', marginTop: 10 },
  houseOwnedText: { color: '#4caf50', fontWeight: '800', fontSize: 13 },
  houseBuyBtn: { backgroundColor: '#f39c12', borderRadius: 8, paddingVertical: 10, alignItems: 'center', marginTop: 10 },
  houseBuyBtnDisabled: { backgroundColor: '#333' },
  houseBuyText: { color: '#fff', fontWeight: '800', fontSize: 14 },
  houseOwnedNote: { color: '#888', fontSize: 12, textAlign: 'center', marginTop: 4, marginBottom: 12 },
});


const RARITY_COLORS: Record<string, string> = {
  common: '#9e9e9e',
  uncommon: '#4caf50',
  rare: '#2196f3',
  epic: '#9c27b0',
  legendary: '#ff9800',
  mythic: '#e91e63',
};

const CATEGORY_CONFIG: Record<string, { label: string; icon: keyof typeof Ionicons.glyphMap; color: string }> = {
  health_recharge: { label: 'Health', icon: 'heart', color: '#e74c3c' },
  energy_recharge: { label: 'Energy', icon: 'battery-charging', color: '#3498db' },
  combo: { label: 'Combo', icon: 'fast-food', color: '#2ecc71' },
  consumable: { label: 'Stims', icon: 'fitness', color: '#9c27b0' },
};

const ITEM_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  medkit: 'medkit',
  'battery-charging': 'battery-charging',
  'fast-food': 'fast-food',
  heart: 'heart',
  flash: 'flash',
};

interface ConsumableItem {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  rarity: string;
  effect: Record<string, any>;
  price: number;
  level_requirement: number;
  icon_url?: string;
}

// Custom Consumable Icon Component
const ConsumableIcon = ({ 
  item, 
  size = 24, 
  color 
}: { 
  item: { id?: string; icon_url?: string; icon: string }; 
  size?: number; 
  color: string;
}) => {
  const [imageError, setImageError] = React.useState(false);
  
  // Bundled icon ships with the app: instant, works offline
  const bundledIcon = getBundledIcon(item.id);
  if (bundledIcon) {
    return (
      <Image
        source={bundledIcon}
        style={{ width: size + 6, height: size + 6 }}
        resizeMode="contain"
      />
    );
  }

  if (item.icon_url && !imageError) {
    return (
      <Image
        source={{ uri: item.icon_url }}
        style={{ width: size + 6, height: size + 6 }}
        resizeMode="contain"
        onError={() => setImageError(true)}
      />
    );
  }
  
  const iconName = ITEM_ICONS[item.icon] || 'flask';
  return <Ionicons name={iconName} size={size} color={color} />;
};

interface Buff {
  id: string;
  item_id: string;
  name: string;
  type: string;
  amount: number;
  battles_remaining: number;
  icon: string;
}

export default function ShopTabScreen() {
  const { player, playerId, setPlayer } = useGameStore();
  const [items, setItems] = useState<ConsumableItem[]>([]);
  const [activeBuffs, setActiveBuffs] = useState<Buff[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [buying, setBuying] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterKey>('all');
  const [myHouse, setMyHouse] = useState<any | null>(null);
  const [inventoryHouses, setInventoryHouses] = useState<any[]>([]);
  const [placingHouse, setPlacingHouse] = useState<string | null>(null);
  const [buyingHouse, setBuyingHouse] = useState<string | null>(null);
  const [successModal, setSuccessModal] = useState<{ visible: boolean; message: string; effects: string[] }>({
    visible: false, message: '', effects: [],
  });

  useEffect(() => {
    loadShop();
  }, []);

  const loadShop = async () => {
    try {
      const [data, buffs] = await Promise.all([
        getConsumableShop(),
        playerId ? api.get(`/players/${playerId}/buffs`).then(r => r.data) : Promise.resolve([]),
      ]);
      setItems(data);
      setActiveBuffs(buffs);
      if (playerId) {
        try { const h = await getPlayerHouse(playerId); setMyHouse(h); } catch (_) {}
        try { const inv = await getInventoryHouses(playerId); setInventoryHouses(inv || []); } catch (_) {}
      }
    } catch (error) {
      console.error('Failed to load shop:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadShop();
    if (playerId) {
      try {
        const p = await getPlayer(playerId);
        setPlayer(p);
        const buffs = await api.get(`/players/${playerId}/buffs`).then(r => r.data);
        setActiveBuffs(buffs);
      } catch (_) {}
    }
    setRefreshing(false);
  };

  const handleBuy = async (item: ConsumableItem) => {
    if (!playerId || !player) return;

    if (player.cash < item.price) {
      Alert.alert('Not Enough Cash', `You need $${item.price} but only have $${player.cash}.`);
      return;
    }
    if (player.level < item.level_requirement) {
      Alert.alert('Level Too Low', `You need Level ${item.level_requirement} to buy this.`);
      return;
    }

    try {
      setBuying(item.id);
      const result = await buyConsumable(playerId, item.id);
      // Update player state from response
      if (result.player) {
        setPlayer(result.player);
      } else {
        const p = await getPlayer(playerId);
        setPlayer(p);
      }
      setSuccessModal({ visible: true, message: result.message, effects: result.effects || [] });
      // Reload buffs after purchase
      try {
        const buffs = await api.get(`/players/${playerId}/buffs`).then(r => r.data);
        setActiveBuffs(buffs);
      } catch (_) {}
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Purchase failed');
    } finally {
      setBuying(null);
    }
  };

  const handlePlaceHouse = (h: any) => {
    if (!playerId || !player?.position) {
      Alert.alert('Place House', 'Your location is not available yet.');
      return;
    }
    Alert.alert('Place House?', `Drop ${h.name} right where you are standing?`, [
      { text: 'Not Yet', style: 'cancel' },
      { text: 'Place It', onPress: async () => {
        setPlacingHouse(h.id);
        try {
          const res = await placeHouse(h.id, playerId, player.position.latitude, player.position.longitude);
          setMyHouse(res.house);
          setInventoryHouses((prev) => prev.filter((x) => x.id !== h.id));
          Alert.alert('House Placed', `${h.name} is now on the map where you stand.`);
        } catch (e: any) {
          Alert.alert('Place Failed', e?.response?.data?.detail || e?.message || 'Could not place house.');
        } finally {
          setPlacingHouse(null);
        }
      } },
    ]);
  };

  const handleBuyHouse = (h: typeof HOUSES[0]) => {
    if (!playerId || !player) return;
    const pos = (player as any).position;
    if (!pos) { Alert.alert('No Location', 'We need your location to place the house.'); return; }
    if (player.cash < h.price) { Alert.alert('Not Enough Cash', `You need $${h.price.toLocaleString()} but only have $${player.cash.toLocaleString()}.`); return; }
    const warn = myHouse
      ? `You already own ${myHouse.name}. Buying ${h.name} will REPLACE it (the old house is gone). Are you sure?`
      : `Buy ${h.name} for $${h.price.toLocaleString()}? A house icon will be placed where you are standing right now.`;
    Alert.alert('Are You Sure?', warn, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Buy', onPress: async () => {
        try {
          setBuyingHouse(h.tier);
          const res = await buyHouse(playerId, h.tier, pos.latitude, pos.longitude);
          setMyHouse(res.house);
          const p = await getPlayer(playerId);
          setPlayer(p);
          Alert.alert('House Bought', `${h.name} is yours! Look for the \u{1F3E0} icon on the map.`);
        } catch (e: any) {
          Alert.alert('Error', e.response?.data?.detail || 'Purchase failed');
        } finally { setBuyingHouse(null); }
      } },
    ]);
  };

  const filteredItems = filter === 'all' ? items : items.filter(i => i.category === filter);

  const filters: { key: FilterKey; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
    { key: 'all', label: 'All', icon: 'grid' },
    { key: 'health_recharge', label: 'HP', icon: 'heart' },
    { key: 'energy_recharge', label: 'EN', icon: 'battery-charging' },
    { key: 'combo', label: 'Combo', icon: 'fast-food' },
    { key: 'consumable', label: 'Stims', icon: 'fitness' },
    { key: 'house', label: 'House', icon: 'home' },
  ];

  const getEffectText = (effect: Record<string, any>): string[] => {
    const lines: string[] = [];
    if (effect.restore_health) lines.push(`+${effect.restore_health} HP`);
    if (effect.restore_health_full) lines.push('Full HP Restore');
    if (effect.restore_energy) lines.push(`+${effect.restore_energy} Energy`);
    if (effect.restore_energy_full) lines.push('Full Energy Restore');
    if (effect.temp_max_health) lines.push(`+${effect.temp_max_health} Max HP (${effect.duration_battles} battles)`);
    if (effect.temp_max_energy) lines.push(`+${effect.temp_max_energy} Max EN (${effect.duration_battles} battles)`);
    if (effect.temp_health_percent) lines.push(`+${Math.round(effect.temp_health_percent * 100)}% HP (instant)`);
    if (effect.temp_energy_percent) lines.push(`+${Math.round(effect.temp_energy_percent * 100)}% Energy (instant)`);
    return lines;
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#f39c12" />
        <Text style={styles.loadingText}>Loading shop...</Text>
      </View>
    );
  }

  const hpPercent = player ? Math.round((player.stats.health / player.stats.max_health) * 100) : 100;
  const enPercent = player ? Math.round((player.stats.energy / player.stats.max_energy) * 100) : 100;

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Ionicons name="storefront" size={24} color="#f39c12" />
          <Text style={styles.headerTitle}>SUPPLY SHOP</Text>
        </View>
        <View style={styles.cashBadge}>
          <Ionicons name="cash" size={16} color="#f39c12" />
          <Text style={styles.cashText} numberOfLines={1} adjustsFontSizeToFit>${(player?.cash || 0).toLocaleString()}</Text>
        </View>
      </View>

      {/* Player Stats Bar */}
      <View style={styles.statsBar}>
        <View style={styles.statBarItem}>
          <View style={styles.statBarLabel}>
            <Ionicons name="heart" size={14} color="#e74c3c" />
            <Text style={styles.statBarText}>HP</Text>
          </View>
          <View style={styles.miniBar}>
            <View style={[styles.miniBarFill, { width: `${hpPercent}%`, backgroundColor: '#e74c3c' }]} />
          </View>
          <Text style={styles.statBarValue}>{player?.stats.health}/{player?.stats.max_health}</Text>
        </View>
        <View style={styles.statBarItem}>
          <View style={styles.statBarLabel}>
            <Ionicons name="flash" size={14} color="#3498db" />
            <Text style={styles.statBarText}>EN</Text>
          </View>
          <View style={styles.miniBar}>
            <View style={[styles.miniBarFill, { width: `${enPercent}%`, backgroundColor: '#3498db' }]} />
          </View>
          <Text style={styles.statBarValue}>{player?.stats.energy}/{player?.stats.max_energy}</Text>
        </View>
      </View>

      {/* Active Buffs */}
      {activeBuffs.length > 0 && (
        <View style={styles.buffsBar}>
          <Text style={styles.buffsTitle}>ACTIVE BOOSTS</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.buffsContent}>
            {activeBuffs.map((buff, idx) => (
              <View key={buff.id || idx} style={styles.buffChip}>
                <Ionicons
                  name={buff.type === 'max_health' ? 'heart' : 'flash'}
                  size={12}
                  color={buff.type === 'max_health' ? '#e91e63' : '#9c27b0'}
                />
                <Text style={styles.buffChipText}>+{buff.amount} {buff.type === 'max_health' ? 'HP' : 'EN'}</Text>
                <View style={styles.buffCountBadge}>
                  <Text style={styles.buffCountText}>{buff.battles_remaining}</Text>
                </View>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Filter Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll} contentContainerStyle={styles.filterContent}>
        {filters.map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterTab, filter === f.key && styles.filterTabActive]}
            onPress={() => setFilter(f.key)}
          >
            <Ionicons name={f.icon} size={14} color={filter === f.key ? '#f39c12' : '#999'} />
            <Text style={[styles.filterLabel, filter === f.key && styles.filterLabelActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <GodPotions playerId={playerId} />

      {filter === 'house' ? (
        <ScrollView style={styles.itemsScroll} contentContainerStyle={styles.scrollContent}>
          {inventoryHouses.length > 0 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ color: '#f39c12', fontWeight: '800', fontSize: 14, marginBottom: 8 }}>YOUR INVENTORY — PLACE IT WHERE YOU STAND</Text>
              {inventoryHouses.map((h: any) => {
                const img = HOUSES.find((x) => x.tier === h.tier)?.image;
                return (
                  <View key={h.id} style={HOUSE_STYLES.houseCard}>
                    {img ? (<Image source={img} style={HOUSE_STYLES.houseImage} />) : null}
                    <View style={HOUSE_STYLES.houseInfo}>
                      <Text style={HOUSE_STYLES.houseName}>{h.name}</Text>
                      <Text style={HOUSE_STYLES.houseBlurb}>In your inventory — {h.items?.length || 0}/{h.item_limit || 6} items inside.</Text>
                      <TouchableOpacity
                        style={[HOUSE_STYLES.houseBuyBtn, placingHouse === h.id && HOUSE_STYLES.houseBuyBtnDisabled]}
                        disabled={placingHouse === h.id}
                        onPress={() => handlePlaceHouse(h)}
                      >
                        {placingHouse === h.id ? (
                          <ActivityIndicator size="small" color="#fff" />
                        ) : (
                          <Text style={HOUSE_STYLES.houseBuyText}>PLACE HERE</Text>
                        )}
                      </TouchableOpacity>
                    </View>
                  </View>
                );
              })}
            </View>
          )}
          {HOUSES.map((h) => {
            const owned = myHouse?.tier === h.tier;
            const canAfford = (player?.cash || 0) >= h.price;
            return (
              <View key={h.tier} style={HOUSE_STYLES.houseCard}>
                <Image source={h.image} style={HOUSE_STYLES.houseImage} />
                <View style={HOUSE_STYLES.houseInfo}>
                  <Text style={HOUSE_STYLES.houseName}>{h.name}</Text>
                  <Text style={HOUSE_STYLES.houseBlurb}>{h.blurb}</Text>
                  {myHouse && !owned && (
                    <Text style={HOUSE_STYLES.houseWarn}>You already own {myHouse.name} — buying replaces it.</Text>
                  )}
                  {owned ? (
                    <View style={{ flexDirection: 'row', gap: 10 }}>
                      <View style={{ flex: 1 }}>
                      <View style={HOUSE_STYLES.houseOwnedBadge}>
                        <Text style={HOUSE_STYLES.houseOwnedText}>YOUR HOUSE</Text>
                      </View>
                      </View>
                      <View style={{ flex: 1 }}>
                        <TouchableOpacity
                          style={{ backgroundColor: '#1e88e5', paddingVertical: 12, borderRadius: 8, alignItems: 'center' }}
                          onPress={() => {
                            if (!(myHouse.id) || !playerId) { Alert.alert('Move House', 'No house to move.'); return; }
                            Alert.alert('Move House?', `Your house will go into your inventory. You can place it again anytime from the Shop House tab.`, [
                              { text: 'Keep It Here', style: 'cancel' },
                              { text: 'Move', onPress: async () => {
                                try {
                                  await moveHouseToInventory(myHouse.id, playerId);
                                  Alert.alert('House Moved', 'Your house is in your inventory. Place it again from the INVENTORY section in the Shop House tab.');
                                } catch (err: any) {
                                  Alert.alert('Move Failed', err?.response?.data?.detail || err?.message || 'Could not move house.');
                                }
                              } },
                            ]);
                          }}
                        >
                          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>MOVE</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  ) : (
                    <TouchableOpacity
                      style={[HOUSE_STYLES.houseBuyBtn, !canAfford && HOUSE_STYLES.houseBuyBtnDisabled]}
                      disabled={!canAfford || buyingHouse === h.tier}
                      onPress={() => handleBuyHouse(h)}
                    >
                      {buyingHouse === h.tier ? (
                        <ActivityIndicator size="small" color="#fff" />
                      ) : (
                        <Text style={HOUSE_STYLES.houseBuyText}>BUY ${h.price.toLocaleString()}</Text>
                      )}
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            );
          })}
          {myHouse && (
            <Text style={HOUSE_STYLES.houseOwnedNote}>You own: {myHouse.name} — tap its 🏠 icon on the map to enter, hide, or sell.</Text>
          )}
        </ScrollView>
      ) : (
      <>
      {/* Items List */}
      <ScrollView
        style={styles.itemsScroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#f39c12" />}
      >
        {filteredItems.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="cart-outline" size={64} color="#333" />
            <Text style={styles.emptyTitle}>No Items</Text>
            <Text style={styles.emptyText}>No items in this category.</Text>
          </View>
        ) : (
          filteredItems.map((item) => {
            const rarityColor = RARITY_COLORS[item.rarity] || '#9e9e9e';
            const catConfig = CATEGORY_CONFIG[item.category];
            const canBuy = (player?.cash || 0) >= item.price && (player?.level || 0) >= item.level_requirement;
            const isBuying = buying === item.id;
            const effectLines = getEffectText(item.effect);
            const isStim = item.category === 'consumable';

            return (
              <View key={item.id} style={[styles.itemCard, { borderLeftColor: catConfig?.color || rarityColor, borderLeftWidth: 3 }]}>
                <View style={[styles.itemIcon, { backgroundColor: `${catConfig?.color || rarityColor}15` }]}>
                  <ConsumableIcon
                    item={item}
                    size={24}
                    color={catConfig?.color || rarityColor}
                  />
                </View>

                <View style={styles.itemInfo}>
                  <View style={styles.itemRow}>
                    <Text style={[styles.itemName, { color: '#fff' }]}>{item.name}</Text>
                    <Text style={[styles.rarityTag, { color: rarityColor }]}>
                      {item.rarity.toUpperCase()}
                    </Text>
                  </View>
                  <Text style={styles.itemDesc} numberOfLines={1}>{item.description}</Text>
                  <View style={styles.effectsRow}>
                    {effectLines.map((eff, idx) => (
                      <View key={idx} style={[styles.effectChip, isStim && styles.effectChipSpecial]}>
                        <Text style={[styles.effectText, isStim && styles.effectTextSpecial]}>{eff}</Text>
                      </View>
                    ))}
                  </View>
                  {(player?.level || 0) < item.level_requirement && (
                    <Text style={styles.levelReq}>Requires Lv.{item.level_requirement}</Text>
                  )}
                </View>

                <TouchableOpacity
                  style={[styles.buyBtn, !canBuy && styles.buyBtnDisabled]}
                  onPress={() => canBuy && handleBuy(item)}
                  disabled={!canBuy || isBuying}
                >
                  {isBuying ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <>
                      <Ionicons name="cash" size={13} color={canBuy ? '#fff' : '#555'} />
                      <Text style={[styles.buyBtnText, !canBuy && styles.buyBtnTextDisabled]}>
                        ${item.price}
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            );
          })
        )}
      </ScrollView>
      </>
      )}

      {/* Success Modal */}
      <Modal
        visible={successModal.visible}
        transparent
        animationType="fade"
        onRequestClose={() => setSuccessModal({ visible: false, message: '', effects: [] })}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setSuccessModal({ visible: false, message: '', effects: [] })}>
          <View style={styles.successModal}>
            <View style={styles.successIconWrap}>
              <Ionicons name="checkmark-circle" size={48} color="#4caf50" />
            </View>
            <Text style={styles.successTitle}>{successModal.message}</Text>
            {successModal.effects.map((eff, idx) => (
              <View key={idx} style={styles.successEffectRow}>
                <Ionicons name="arrow-forward" size={14} color="#4caf50" />
                <Text style={styles.successEffectText}>{eff}</Text>
              </View>
            ))}
            <TouchableOpacity
              style={styles.successBtn}
              onPress={() => setSuccessModal({ visible: false, message: '', effects: [] })}
            >
              <Text style={styles.successBtnText}>OK</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0a0a' },
  loadingText: { color: '#888', marginTop: 12 },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerTitle: { color: '#f39c12', fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  cashBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: 'rgba(243,156,18,0.15)',
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16,
  },
  cashText: { color: '#f39c12', fontSize: 14, fontWeight: '700' },

  // Stats Bar
  statsBar: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  statBarItem: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6 },
  statBarLabel: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  statBarText: { color: '#888', fontSize: 10, fontWeight: '700' },
  miniBar: { flex: 1, height: 6, backgroundColor: '#222', borderRadius: 3, overflow: 'hidden' },
  miniBarFill: { height: '100%', borderRadius: 3 },
  statBarValue: { color: '#666', fontSize: 10, fontWeight: '600', minWidth: 50, textAlign: 'right' },

  // Active Buffs
  buffsBar: {
    paddingHorizontal: 16, paddingVertical: 8,
    borderBottomWidth: 1, borderBottomColor: '#1a1a1a',
  },
  buffsTitle: { color: '#ce93d8', fontSize: 10, fontWeight: '800', letterSpacing: 1, marginBottom: 6 },
  buffsContent: { gap: 6 },
  buffChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: 'rgba(156,39,176,0.12)', paddingHorizontal: 10, paddingVertical: 5,
    borderRadius: 12, borderWidth: 1, borderColor: 'rgba(156,39,176,0.25)',
  },
  buffChipText: { color: '#ce93d8', fontSize: 11, fontWeight: '700' },
  buffCountBadge: {
    backgroundColor: 'rgba(156,39,176,0.3)', borderRadius: 8,
    paddingHorizontal: 5, paddingVertical: 1, marginLeft: 2,
  },
  buffCountText: { color: '#e1bee7', fontSize: 9, fontWeight: '800' },

  // Filter
  filterScroll: { maxHeight: 46, minHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a', backgroundColor: '#0a0a0a' },
  filterContent: { paddingHorizontal: 12, paddingVertical: 8, gap: 6 },
  filterTab: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16,
    backgroundColor: '#111',
  },
  filterTabActive: { backgroundColor: 'rgba(243,156,18,0.15)', borderWidth: 1, borderColor: 'rgba(243,156,18,0.3)' },
  filterLabel: { color: '#999', fontSize: 11, fontWeight: '600' },
  filterLabelActive: { color: '#f39c12' },

  // Content
  scrollContent: { padding: 12, paddingBottom: 40 },
  itemsScroll: { flex: 1 },

  // Empty
  emptyState: { alignItems: 'center', paddingVertical: 48 },
  emptyTitle: { color: '#555', fontSize: 18, fontWeight: '700', marginTop: 16 },
  emptyText: { color: '#444', fontSize: 13, marginTop: 8 },

  // Item Card
  itemCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#111', borderRadius: 12, padding: 12, marginBottom: 8,
  },
  itemIcon: {
    width: 44, height: 44, borderRadius: 12,
    justifyContent: 'center', alignItems: 'center',
  },
  itemInfo: { flex: 1, marginLeft: 10 },
  itemRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemName: { fontSize: 14, fontWeight: '700' },
  rarityTag: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  itemDesc: { color: '#666', fontSize: 11, marginTop: 2 },
  effectsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 4 },
  effectChip: {
    backgroundColor: 'rgba(76,175,80,0.1)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6,
  },
  effectChipSpecial: { backgroundColor: 'rgba(156,39,176,0.15)' },
  effectText: { color: '#4caf50', fontSize: 10, fontWeight: '700' },
  effectTextSpecial: { color: '#ce93d8' },
  levelReq: { color: '#f44336', fontSize: 10, fontWeight: '600', marginTop: 3 },

  // Buy Button
  buyBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#f39c12', paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: 8, marginLeft: 8, minWidth: 60, justifyContent: 'center',
  },
  buyBtnDisabled: { backgroundColor: '#222' },
  buyBtnText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  buyBtnTextDisabled: { color: '#555' },

  // Success Modal
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center', alignItems: 'center',
  },
  successModal: {
    backgroundColor: '#1a1a1a', borderRadius: 20, padding: 24,
    marginHorizontal: 40, alignItems: 'center', width: 300,
  },
  successIconWrap: { marginBottom: 12 },
  successTitle: { color: '#fff', fontSize: 18, fontWeight: '800', textAlign: 'center', marginBottom: 12 },
  successEffectRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  successEffectText: { color: '#4caf50', fontSize: 14, fontWeight: '600' },
  successBtn: {
    backgroundColor: '#4caf50', paddingHorizontal: 32, paddingVertical: 10,
    borderRadius: 10, marginTop: 16,
  },
  successBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
});
