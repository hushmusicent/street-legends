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
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { getAllItems, getPlayer, equipItem } from '../services/api';
import api from '../services/api';

const RARITY_COLORS: Record<string, string> = {
  common: '#9e9e9e',
  uncommon: '#4caf50',
  rare: '#2196f3',
  epic: '#9c27b0',
  legendary: '#ff9800',
};

const SLOT_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  weapon: 'flash',
  armor: 'shield',
  accessory: 'diamond',
  vehicle: 'car-sport',
};

const RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary'];

interface ShopItem {
  id: string;
  name: string;
  description: string;
  equipment_type: string;
  rarity: string;
  stats_bonus: Record<string, number>;
  level_requirement: number;
  value: number;
  shop_price?: number;
  icon_url?: string;
}

// Custom Shop Item Icon Component
const ShopItemIcon = ({ 
  item, 
  size = 24, 
  color 
}: { 
  item: { icon_url?: string; equipment_type: string }; 
  size?: number; 
  color: string;
}) => {
  const [imageError, setImageError] = React.useState(false);
  
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
  
  return (
    <Ionicons 
      name={SLOT_ICONS[item.equipment_type] || 'cube'} 
      size={size} 
      color={color} 
    />
  );
};

export default function ShopScreen() {
  const { player, playerId, setPlayer } = useGameStore();
  const [items, setItems] = useState<ShopItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [buying, setBuying] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadShop();
  }, []);

  const loadShop = async () => {
    try {
      const allItems = await getAllItems();
      const itemList = Object.values(allItems) as ShopItem[];
      // Sort by rarity then level
      itemList.sort((a, b) => {
        const ra = RARITY_ORDER.indexOf(a.rarity);
        const rb = RARITY_ORDER.indexOf(b.rarity);
        if (ra !== rb) return ra - rb;
        return a.level_requirement - b.level_requirement;
      });
      setItems(itemList);
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
      const p = await getPlayer(playerId);
      setPlayer(p);
    }
    setRefreshing(false);
  };

  const handleBuy = async (item: ShopItem) => {
    if (!playerId || !player) return;

    if (player.cash < item.value) {
      Alert.alert('Not Enough Cash', `You need $${item.value} but only have $${player.cash}.`);
      return;
    }

    if (player.level < item.level_requirement) {
      Alert.alert('Level Too Low', `You need to be Level ${item.level_requirement} to buy this.`);
      return;
    }

    Alert.alert(
      'Buy Item',
      `Buy ${item.name} for $${item.value}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Buy',
          onPress: async () => {
            try {
              setBuying(item.id);
              await api.post(`/players/${playerId}/buy-item?item_id=${item.id}`);
              const p = await getPlayer(playerId);
              setPlayer(p);
              Alert.alert('Purchased!', `${item.name} added to your inventory!`);
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Purchase failed');
            } finally {
              setBuying(null);
            }
          },
        },
      ]
    );
  };

  const filteredItems = filter === 'all'
    ? items
    : items.filter(i => i.equipment_type === filter);

  const filters = [
    { key: 'all', label: 'All', icon: 'grid' as keyof typeof Ionicons.glyphMap },
    { key: 'weapon', label: 'Weapons', icon: 'flash' as keyof typeof Ionicons.glyphMap },
    { key: 'armor', label: 'Armor', icon: 'shield' as keyof typeof Ionicons.glyphMap },
    { key: 'accessory', label: 'Acc', icon: 'diamond' as keyof typeof Ionicons.glyphMap },
    { key: 'vehicle', label: 'Rides', icon: 'car-sport' as keyof typeof Ionicons.glyphMap },
  ];

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#f39c12" />
        <Text style={styles.loadingText}>Loading shop...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Ionicons name="storefront" size={24} color="#f39c12" />
          <Text style={styles.headerTitle}>BLACK MARKET</Text>
        </View>
        <View style={styles.cashBadge}>
          <Ionicons name="cash" size={16} color="#f39c12" />
          <Text style={styles.cashText}>${player?.cash || 0}</Text>
        </View>
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterBar}>
        {filters.map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterTab, filter === f.key && styles.filterTabActive]}
            onPress={() => setFilter(f.key)}
          >
            <Ionicons name={f.icon} size={16} color={filter === f.key ? '#f39c12' : '#666'} />
            <Text style={[styles.filterLabel, filter === f.key && styles.filterLabelActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Items List */}
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#f39c12" />}
      >
        {filteredItems.map((item) => {
          const rarityColor = RARITY_COLORS[item.rarity] || '#9e9e9e';
          const canBuy = (player?.cash || 0) >= item.value && (player?.level || 0) >= item.level_requirement;
          const isBuying = buying === item.id;

          return (
            <View key={item.id} style={[styles.itemCard, { borderLeftColor: rarityColor, borderLeftWidth: 3 }]}>
              <View style={[styles.itemIcon, { backgroundColor: `${rarityColor}15` }]}>
                <ShopItemIcon item={item} size={24} color={rarityColor} />
              </View>

              <View style={styles.itemInfo}>
                <View style={styles.itemRow}>
                  <Text style={[styles.itemName, { color: rarityColor }]}>{item.name}</Text>
                  <Text style={[styles.rarityTag, { color: rarityColor }]}>
                    {item.rarity.toUpperCase()}
                  </Text>
                </View>
                <Text style={styles.itemDesc} numberOfLines={1}>{item.description}</Text>
                <View style={styles.statsRow}>
                  {Object.entries(item.stats_bonus).map(([stat, val]) => (
                    <Text
                      key={stat}
                      style={[styles.statText, { color: (val as number) > 0 ? '#4caf50' : '#f44336' }]}
                    >
                      {(val as number) > 0 ? '+' : ''}{val as number} {stat}
                    </Text>
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
                    <Ionicons name="cash" size={14} color={canBuy ? '#fff' : '#555'} />
                    <Text style={[styles.buyBtnText, !canBuy && styles.buyBtnTextDisabled]}>
                      ${item.value}
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0a0a' },
  loadingText: { color: '#888', marginTop: 12 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  backBtn: { width: 44, height: 44, justifyContent: 'center', alignItems: 'center' },
  headerCenter: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  headerTitle: { color: '#f39c12', fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  cashBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(243,156,18,0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 4,
  },
  cashText: { color: '#f39c12', fontSize: 14, fontWeight: '700' },

  filterBar: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  filterTab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    borderRadius: 8,
    gap: 4,
  },
  filterTabActive: { backgroundColor: 'rgba(243,156,18,0.15)' },
  filterLabel: { color: '#666', fontSize: 11, fontWeight: '600' },
  filterLabelActive: { color: '#f39c12' },

  scrollContent: { padding: 12, paddingBottom: 40 },

  itemCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  itemIcon: {
    width: 44,
    height: 44,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  itemInfo: { flex: 1, marginLeft: 10 },
  itemRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemName: { fontSize: 14, fontWeight: '700' },
  rarityTag: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  itemDesc: { color: '#666', fontSize: 11, marginTop: 2 },
  statsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  statText: { fontSize: 11, fontWeight: '600' },
  levelReq: { color: '#f44336', fontSize: 10, fontWeight: '600', marginTop: 3 },

  buyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f39c12',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginLeft: 8,
    gap: 4,
    minWidth: 60,
    justifyContent: 'center',
  },
  buyBtnDisabled: { backgroundColor: '#222' },
  buyBtnText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  buyBtnTextDisabled: { color: '#555' },
});
