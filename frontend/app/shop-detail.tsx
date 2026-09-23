import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { buyFromShop, getPlayer, buySkill } from '../services/api';
import { SFX } from '../hooks/useSoundEffects';

const RARITY_COLORS: Record<string, string> = {
  common: '#9e9e9e',
  uncommon: '#4caf50',
  rare: '#2196f3',
  epic: '#9c27b0',
  legendary: '#ff9800',
  mythic: '#e91e63',
};

const SLOT_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  weapon: 'flash',
  armor: 'shield',
  accessory: 'diamond',
  vehicle: 'car-sport',
};

interface ShopItem {
  id: string;
  name: string;
  description: string;
  equipment_type: string;
  rarity: string;
  stats_bonus: Record<string, number>;
  level_requirement: number;
  value: number;
  shop_price: number;
  icon_url?: string;
}

// Custom Shop Item Icon Component
const ShopDetailItemIcon = ({ 
  item, 
  size = 26, 
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
        style={{ width: size + 8, height: size + 8 }}
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

interface ShopSkill {
  id: string;
  name: string;
  description: string;
  unlock_level: number;
  cost: number;
  value: number;
  shop_price: number;
  damage_mult?: number;
  heal_percent?: number;
  defense_buff?: number;
  item_type: string;
  icon_url?: string;
}

// Custom Skill Icon Component
const SkillIcon = ({ 
  skill, 
  size = 26, 
  color 
}: { 
  skill: { icon_url?: string }; 
  size?: number; 
  color: string;
}) => {
  const [imageError, setImageError] = React.useState(false);
  
  if (skill.icon_url && !imageError) {
    return (
      <Image
        source={{ uri: skill.icon_url }}
        style={{ width: size + 8, height: size + 8 }}
        resizeMode="contain"
        onError={() => setImageError(true)}
      />
    );
  }
  
  return <Ionicons name="flash" size={size} color={color} />;
};

export default function ShopDetailScreen() {
  const { shopData } = useLocalSearchParams<{ shopData: string }>();
  const { player, playerId, setPlayer } = useGameStore();
  const [buying, setBuying] = useState<string | null>(null);
  const [buyingSkill, setBuyingSkill] = useState<string | null>(null);

  let shop: any = null;
  try {
    shop = JSON.parse(shopData || '{}');
  } catch {
    shop = {};
  }

  const stock: ShopItem[] = shop.stock || [];
  const skillsForSale: ShopSkill[] = shop.skills_for_sale || [];

  // Play shop ambient sound when entering based on shop type
  useEffect(() => {
    if (!shop?.name) return;
    
    const shopNameLower = (shop.name || '').toLowerCase();
    if (shopNameLower.includes('gun') || shopNameLower.includes('weapon') || shopNameLower.includes('armory')) {
      SFX.gunShop();
    } else if (shopNameLower.includes('club') || shopNameLower.includes('bar') || shopNameLower.includes('lounge')) {
      SFX.nightclub();
    } else if (shopNameLower.includes('restaurant') || shopNameLower.includes('diner') || shopNameLower.includes('food')) {
      SFX.restaurant();
    }
  }, [shop?.name]);

  const handleBuy = async (item: ShopItem) => {
    if (!playerId || !player) return;

    if (player.cash < item.shop_price) {
      Alert.alert('Not Enough Cash', `You need $${item.shop_price} but only have $${player.cash}.`);
      return;
    }

    Alert.alert('Buy Item', `Buy ${item.name} for $${item.shop_price}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Buy',
        onPress: async () => {
          try {
            setBuying(item.id);
            await buyFromShop(playerId, item.id, item.shop_price);
            const p = await getPlayer(playerId);
            setPlayer(p);
            SFX.purchase(); // Play purchase sound
            Alert.alert('Purchased!', `${item.name} added to your inventory!`);
          } catch (error: any) {
            Alert.alert('Error', error.response?.data?.detail || 'Purchase failed');
          } finally {
            setBuying(null);
          }
        },
      },
    ]);
  };

  const handleBuySkill = async (skill: ShopSkill) => {
    if (!playerId || !player) return;

    if (player.cash < skill.shop_price) {
      Alert.alert('Not Enough Cash', `You need $${skill.shop_price} but only have $${player.cash}.`);
      return;
    }

    Alert.alert('Buy Skill', `Buy ${skill.name} for $${skill.shop_price}?\n\n${skill.description}`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Buy',
        onPress: async () => {
          try {
            setBuyingSkill(skill.id);
            await buySkill(playerId, skill.id);
            const p = await getPlayer(playerId);
            setPlayer(p);
            SFX.purchase(); // Play purchase sound
            Alert.alert('Skill Purchased!', `${skill.name} learned! Go to Character > Skills to equip it.`);
          } catch (error: any) {
            Alert.alert('Error', error.response?.data?.detail || 'Purchase failed');
          } finally {
            setBuyingSkill(null);
          }
        },
      },
    ]);
  };

  if (!shop || !shop.name) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorState}>
          <Ionicons name="alert-circle" size={48} color="#f44336" />
          <Text style={styles.errorText}>Shop not found</Text>
          <TouchableOpacity style={styles.backBtnLarge} onPress={() => router.back()}>
            <Text style={styles.backBtnText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const isDiscount = shop.price_multiplier < 1;
  const discountPct = isDiscount ? Math.round((1 - shop.price_multiplier) * 100) : 0;

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Ionicons name="storefront" size={22} color="#FF6F00" />
          <Text style={styles.headerTitle} numberOfLines={1}>{shop.name}</Text>
        </View>
        <View style={styles.cashBadge}>
          <Ionicons name="cash" size={14} color="#f39c12" />
          <Text style={styles.cashText}>${player?.cash || 0}</Text>
        </View>
      </View>

      {/* Shop info banner */}
      {isDiscount && (
        <View style={styles.saleBanner}>
          <Ionicons name="pricetag" size={16} color="#fff" />
          <Text style={styles.saleText}>SALE! {discountPct}% OFF all items!</Text>
        </View>
      )}
      {shop.price_multiplier > 1.2 && (
        <View style={[styles.saleBanner, { backgroundColor: '#f44336' }]}>
          <Ionicons name="warning" size={16} color="#fff" />
          <Text style={styles.saleText}>Premium prices at this location</Text>
        </View>
      )}

      {/* Stock */}
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Skills Section */}
        {skillsForSale.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>SKILLS FOR SALE ({skillsForSale.length})</Text>
            {skillsForSale.map((skill, idx) => {
              const canBuy = (player?.cash || 0) >= skill.shop_price && (player?.level || 0) >= skill.unlock_level;
              const isBuying = buyingSkill === skill.id;
              const originalPrice = skill.value;
              const isOnSale = skill.shop_price < originalPrice;

              return (
                <View key={`skill-${skill.id}-${idx}`} style={[styles.itemCard, { borderLeftColor: '#9c27b0', borderLeftWidth: 3 }]}>
                  <View style={[styles.itemIcon, { backgroundColor: 'rgba(156,39,176,0.15)' }]}>
                    <SkillIcon skill={skill} size={24} color="#9c27b0" />
                  </View>

                  <View style={styles.itemInfo}>
                    <View style={styles.itemRow}>
                      <Text style={[styles.itemName, { color: '#9c27b0' }]}>{skill.name}</Text>
                      <Text style={[styles.rarityTag, { color: '#9c27b0' }]}>SKILL</Text>
                    </View>
                    <Text style={styles.itemDesc} numberOfLines={2}>{skill.description}</Text>
                    <View style={styles.statsRow}>
                      <Text style={styles.statText}>Cost: {skill.cost} Energy</Text>
                      {skill.damage_mult && <Text style={[styles.statText, { color: '#f44336' }]}>{skill.damage_mult}x DMG</Text>}
                      {skill.heal_percent && <Text style={[styles.statText, { color: '#4caf50' }]}>{Math.round(skill.heal_percent * 100)}% Heal</Text>}
                      {skill.defense_buff && <Text style={[styles.statText, { color: '#2196f3' }]}>{skill.defense_buff}x DEF</Text>}
                    </View>
                    {(player?.level || 0) < skill.unlock_level && (
                      <Text style={styles.levelReq}>Requires Lv.{skill.unlock_level}</Text>
                    )}
                  </View>

                  <View style={styles.priceCol}>
                    {isOnSale && (
                      <Text style={styles.originalPrice}>${originalPrice}</Text>
                    )}
                    <TouchableOpacity
                      style={[styles.buyBtn, { backgroundColor: '#9c27b0' }, !canBuy && styles.buyBtnDisabled]}
                      onPress={() => canBuy && handleBuySkill(skill)}
                      disabled={!canBuy || isBuying}
                    >
                      {isBuying ? (
                        <ActivityIndicator size="small" color="#fff" />
                      ) : (
                        <>
                          <Ionicons name="cash" size={13} color={canBuy ? '#fff' : '#555'} />
                          <Text style={[styles.buyBtnText, !canBuy && styles.buyBtnTextDisabled]}>
                            ${skill.shop_price}
                          </Text>
                        </>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })}
            <View style={{ height: 16 }} />
          </>
        )}

        <Text style={styles.sectionTitle}>AVAILABLE STOCK ({stock.length})</Text>

        {stock.map((item, idx) => {
          const rarityColor = RARITY_COLORS[item.rarity] || '#9e9e9e';
          const canBuy = (player?.cash || 0) >= item.shop_price && (player?.level || 0) >= item.level_requirement;
          const isBuying = buying === item.id;
          const originalPrice = item.value;
          const isOnSale = item.shop_price < originalPrice;

          return (
            <View key={`${item.id}-${idx}`} style={[styles.itemCard, { borderLeftColor: rarityColor, borderLeftWidth: 3 }]}>
              <View style={[styles.itemIcon, { backgroundColor: `${rarityColor}15` }]}>
                <ShopDetailItemIcon item={item} size={24} color={rarityColor} />
              </View>

              <View style={styles.itemInfo}>
                <View style={styles.itemRow}>
                  <Text style={[styles.itemName, { color: rarityColor }]}>{item.name}</Text>
                  <Text style={[styles.rarityTag, { color: rarityColor }]}>{item.rarity.toUpperCase()}</Text>
                </View>
                <Text style={styles.itemDesc} numberOfLines={1}>{item.description}</Text>
                <View style={styles.statsRow}>
                  {Object.entries(item.stats_bonus).map(([stat, val]) => (
                    <Text key={stat} style={[styles.statText, { color: (val as number) > 0 ? '#4caf50' : '#f44336' }]}>
                      {(val as number) > 0 ? '+' : ''}{val as number} {stat}
                    </Text>
                  ))}
                </View>
                {(player?.level || 0) < item.level_requirement && (
                  <Text style={styles.levelReq}>Requires Lv.{item.level_requirement}</Text>
                )}
              </View>

              <View style={styles.priceCol}>
                {isOnSale && (
                  <Text style={styles.originalPrice}>${originalPrice}</Text>
                )}
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
                        ${item.shop_price}
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  errorState: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: '#f44336', fontSize: 16, marginTop: 12 },
  backBtnLarge: { marginTop: 16, backgroundColor: '#333', paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8 },
  backBtnText: { color: '#fff', fontWeight: '600' },

  header: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 12, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: '#1a1a1a',
  },
  backBtn: { width: 44, height: 44, justifyContent: 'center', alignItems: 'center' },
  headerCenter: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerTitle: { color: '#FF6F00', fontSize: 16, fontWeight: '800', letterSpacing: 1 },
  cashBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: 'rgba(243,156,18,0.15)', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 14,
  },
  cashText: { color: '#f39c12', fontSize: 13, fontWeight: '700' },

  saleBanner: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: '#4caf50', paddingVertical: 8,
  },
  saleText: { color: '#fff', fontWeight: '700', fontSize: 13 },

  scrollContent: { padding: 12, paddingBottom: 40 },
  sectionTitle: { color: '#666', fontSize: 11, fontWeight: '700', letterSpacing: 2, marginBottom: 12 },

  itemCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#111', borderRadius: 12, padding: 12, marginBottom: 8,
  },
  itemIcon: { width: 44, height: 44, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  itemInfo: { flex: 1, marginLeft: 10 },
  itemRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemName: { fontSize: 14, fontWeight: '700' },
  rarityTag: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  itemDesc: { color: '#666', fontSize: 11, marginTop: 2 },
  statsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  statText: { fontSize: 11, fontWeight: '600' },
  levelReq: { color: '#f44336', fontSize: 10, fontWeight: '600', marginTop: 3 },

  priceCol: { alignItems: 'center', marginLeft: 8 },
  originalPrice: { color: '#666', fontSize: 11, textDecorationLine: 'line-through', marginBottom: 2 },
  buyBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#FF6F00', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8,
    minWidth: 60, justifyContent: 'center',
  },
  buyBtnDisabled: { backgroundColor: '#222' },
  buyBtnText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  buyBtnTextDisabled: { color: '#555' },
});
