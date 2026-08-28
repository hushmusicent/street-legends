import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  ActivityIndicator,
  Image,
  Platform,
  Modal,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { manipulateAsync, SaveFormat } from 'expo-image-manipulator';
import { useGameStore } from '../../stores/gameStore';
import {
  getPlayer,
  getPlayerSkills,
  getPlayerInventoryDetails,
  getPlayerEquipmentDetails,
  equipItem,
  unequipItem,
  uploadProfilePic,
  getProfilePic,
  getOwnedTerritories,
  deleteItem,
  sellItem,
  collectTerritoryIncome,
  getTerritoryIncomePreview,
  equipSkill,
  unequipSkill,
  repairItem,
} from '../../services/api';
import { HealthBar } from '../../components/HealthBar';
import { StatBar } from '../../components/StatBar';
import { Skill } from '../../types/game';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { showGameToast } from '../../components/GameToast';

type TabType = 'status' | 'equipment' | 'items' | 'skills';

const CLASS_COLORS: Record<string, string> = {
  street_soldier: '#e74c3c',
  hacker: '#3498db',
  enforcer: '#f39c12',
  ghost: '#9b59b6',
};

const CLASS_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  street_soldier: 'fitness',
  hacker: 'hardware-chip',
  enforcer: 'hammer',
  ghost: 'eye-off',
};

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

const SLOT_LABELS: Record<string, string> = {
  weapon: 'Weapon',
  armor: 'Armor',
  accessory: 'Accessory',
  vehicle: 'Vehicle',
};

interface EquipmentItem {
  id: string;
  name: string;
  description: string;
  equipment_type: string;
  rarity: string;
  stats_bonus: Record<string, number>;
  level_requirement: number;
  value: number;
  durability?: number;
  max_durability?: number;
  is_broken?: boolean;
  inventory_index?: number;
}

export default function CharacterScreen() {
  const { player, playerId, setPlayer, clearPlayer } = useGameStore();
  const setGlobalProfilePic = useGameStore(s => s.setProfilePic);
  const [activeTab, setActiveTab] = useState<TabType>('status');
  const [refreshing, setRefreshing] = useState(false);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [inventory, setInventory] = useState<EquipmentItem[]>([]);
  const [equipped, setEquipped] = useState<Record<string, EquipmentItem | null>>({});
  const [loading, setLoading] = useState(false);
  const [profilePic, setProfilePic] = useState<string | null>(null);
  const [uploadingPic, setUploadingPic] = useState(false);
  const [showPicMenu, setShowPicMenu] = useState(false);
  const [ownedTerritories, setOwnedTerritories] = useState<any[]>([]);

  useEffect(() => {
    if (playerId) loadAllData();
  }, [playerId]);

  // Refresh data when screen comes into focus (important after capturing territories)
  useFocusEffect(
    useCallback(() => {
      if (playerId) loadAllData();
    }, [playerId])
  );

  // Refresh data when switching tabs
  useEffect(() => {
    if (playerId && (activeTab === 'equipment' || activeTab === 'items')) {
      loadAllData();
    }
  }, [activeTab]);

  const loadAllData = async () => {
    if (!playerId) return;
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        getPlayer(playerId),
        getPlayerSkills(playerId),
        getPlayerInventoryDetails(playerId),
        getPlayerEquipmentDetails(playerId),
        getProfilePic(playerId),
        getOwnedTerritories(playerId),
      ]);
      if (results[0].status === 'fulfilled') setPlayer(results[0].value);
      if (results[1].status === 'fulfilled') setSkills(results[1].value);
      if (results[2].status === 'fulfilled') setInventory(results[2].value);
      if (results[3].status === 'fulfilled') setEquipped(results[3].value);
      if (results[4].status === 'fulfilled' && results[4].value.profile_pic) {
        setProfilePic(results[4].value.profile_pic);
        setGlobalProfilePic(results[4].value.profile_pic);
      }
      if (results[5].status === 'fulfilled') setOwnedTerritories(results[5].value || []);
    } catch (error) {
      console.error('Failed to load character data:', error);
    }
    setLoading(false);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadAllData();
    setRefreshing(false);
  };

  const handleEquip = async (item: EquipmentItem) => {
    if (!playerId) return;
    try {
      await equipItem(playerId, item.id);
      await loadAllData();
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to equip item');
    }
  };

  const handleUnequip = async (slot: string) => {
    if (!playerId) return;
    try {
      await unequipItem(playerId, slot);
      await loadAllData();
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to unequip item');
    }
  };

  const handleDeleteItem = (item: EquipmentItem) => {
    Alert.alert('Drop Item', `Are you sure you want to drop "${item.name}"? This cannot be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Drop',
        style: 'destructive',
        onPress: async () => {
          if (!playerId) return;
          try {
            await deleteItem(playerId, item.id);
            await loadAllData();
            Alert.alert('Dropped', `${item.name} has been discarded.`);
          } catch (error: any) {
            Alert.alert('Error', error?.response?.data?.detail || 'Failed to drop item');
          }
        },
      },
    ]);
  };

  const handleSellItem = (item: EquipmentItem) => {
    const sellPrice = Math.max(1, Math.floor((item as any).value / 2 || 5));
    Alert.alert('Sell Item', `Sell "${item.name}" for $${sellPrice}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: `Sell for $${sellPrice}`,
        onPress: async () => {
          if (!playerId) return;
          try {
            const result = await sellItem(playerId, item.id);
            await loadAllData();
            Alert.alert('Sold!', result.message);
          } catch (error: any) {
            Alert.alert('Error', error?.response?.data?.detail || 'Failed to sell item');
          }
        },
      },
    ]);
  };

  const handleRepairItem = async (item: EquipmentItem) => {
    if (!playerId || item.inventory_index === undefined) return;
    
    const maxDur = item.max_durability || 100;
    const curDur = item.durability || maxDur;
    const damagePercent = (maxDur - curDur) / maxDur;
    const rarityMult: Record<string, number> = { common: 0.3, uncommon: 0.4, rare: 0.5, epic: 0.6, legendary: 0.8 };
    const mult = rarityMult[item.rarity] || 0.5;
    const repairCost = Math.max(1, Math.floor(item.value * mult * damagePercent));
    
    Alert.alert(
      'Repair Item',
      `Repair "${item.name}" for $${repairCost}?\n\nCurrent: ${curDur}/${maxDur}\nAfter repair: ${maxDur}/${maxDur}`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: `Repair $${repairCost}`,
          onPress: async () => {
            try {
              const result = await repairItem(playerId, item.inventory_index!);
              await loadAllData();
              showGameToast({
                type: 'success',
                title: 'Item Repaired!',
                message: result.message,
                duration: 2500,
              });
            } catch (error: any) {
              Alert.alert('Error', error?.response?.data?.detail || 'Failed to repair item');
            }
          },
        },
      ]
    );
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => {
          await AsyncStorage.removeItem('playerId');
          clearPlayer();
          router.replace('/');
        },
      },
    ]);
  };

  const pickImage = async () => {
    if (!playerId) return;
    setShowPicMenu(true);
  };

  const launchCamera = async () => {
    setShowPicMenu(false);
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission needed', 'Camera access is required to take photos.');
        return;
      }
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.7,
      });
      if (!result.canceled && result.assets[0]) {
        await processAndUpload(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Camera error:', error);
      Alert.alert('Error', 'Failed to open camera. Please try again.');
    }
  };

  const launchGallery = async () => {
    setShowPicMenu(false);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.7,
      });
      if (!result.canceled && result.assets[0]) {
        await processAndUpload(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Gallery error:', error);
      Alert.alert('Error', 'Failed to open gallery. Please try again.');
    }
  };

  const processAndUpload = async (uri: string) => {
    if (!playerId) return;
    try {
      setUploadingPic(true);
      // Resize to 200x200 and compress heavily for fast upload
      const manipulated = await manipulateAsync(
        uri,
        [{ resize: { width: 200, height: 200 } }],
        { compress: 0.5, format: SaveFormat.JPEG, base64: true }
      );
      if (manipulated.base64) {
        const imageData = `data:image/jpeg;base64,${manipulated.base64}`;
        await uploadProfilePic(playerId, imageData);
        setProfilePic(imageData);
        setGlobalProfilePic(imageData);
        Alert.alert('Success', 'Profile picture updated!');
      } else {
        Alert.alert('Error', 'Could not process the image. Please try again.');
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      const detail = error?.response?.data?.detail || 'Failed to upload picture. Please try a smaller image.';
      Alert.alert('Upload Failed', detail);
    } finally {
      setUploadingPic(false);
    }
  };

  if (!player) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
        <Text style={styles.loadingText}>Loading character...</Text>
      </View>
    );
  }

  const classColor = CLASS_COLORS[player.character_class] || '#e74c3c';
  const xpProgress = (player.xp / player.xp_to_next) * 100;

  // Tab buttons
  const tabs: { key: TabType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
    { key: 'status', label: 'Status', icon: 'person' },
    { key: 'equipment', label: 'Equip', icon: 'shield-checkmark' },
    { key: 'items', label: 'Items', icon: 'bag' },
    { key: 'skills', label: 'Skills', icon: 'flash' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      {/* Character Header - always visible */}
      <View style={styles.header}>
        <TouchableOpacity onPress={pickImage} activeOpacity={0.7}>
          <View style={[styles.avatarContainer, { borderColor: classColor }]}>
            {profilePic ? (
              <Image source={{ uri: profilePic }} style={styles.avatarImage} />
            ) : (
              <Ionicons name={CLASS_ICONS[player.character_class]} size={32} color={classColor} />
            )}
            {uploadingPic && (
              <View style={styles.avatarOverlay}>
                <ActivityIndicator size="small" color="#fff" />
              </View>
            )}
            <View style={styles.cameraButton}>
              <Ionicons name="camera" size={12} color="#fff" />
            </View>
          </View>
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.playerName}>{player.name}</Text>
          <Text style={[styles.playerClass, { color: classColor }]}>
            {player.character_class.replace('_', ' ').toUpperCase()}
          </Text>
          <View style={styles.levelRow}>
            <View style={[styles.levelBadge, { backgroundColor: classColor }]}>
              <Text style={styles.levelText}>Lv.{player.level}</Text>
            </View>
            <View style={styles.xpBarSmall}>
              <View style={[styles.xpFillSmall, { width: `${Math.min(xpProgress, 100)}%`, backgroundColor: classColor }]} />
            </View>
            <Text style={styles.xpTextSmall}>{player.xp}/{player.xp_to_next}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutBtn}>
          <Ionicons name="log-out-outline" size={22} color="#666" />
        </TouchableOpacity>
      </View>

      {/* Tab Bar */}
      <View style={styles.tabBar}>
        {tabs.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && { borderBottomColor: classColor, borderBottomWidth: 2 }]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Ionicons
              name={tab.icon}
              size={18}
              color={activeTab === tab.key ? classColor : '#666'}
            />
            <Text style={[styles.tabLabel, activeTab === tab.key && { color: classColor }]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={classColor} />
        }
      >
        {activeTab === 'status' && (
          <StatusTab player={player} classColor={classColor} territories={ownedTerritories} playerId={playerId} />
        )}
        {activeTab === 'equipment' && (
          <EquipmentTab
            equipped={equipped}
            classColor={classColor}
            onUnequip={handleUnequip}
            playerLevel={player.level}
          />
        )}
        {activeTab === 'items' && (
          <ItemsTab
            inventory={inventory}
            classColor={classColor}
            onEquip={handleEquip}
            onDelete={handleDeleteItem}
            onSell={handleSellItem}
            onRepair={handleRepairItem}
            playerLevel={player.level}
            playerCash={player.cash}
          />
        )}
        {activeTab === 'skills' && (
          <SkillsTab 
            skills={skills} 
            classColor={classColor} 
            playerLevel={player.level} 
            playerId={playerId || ''}
            onRefresh={loadAllData}
          />
        )}
      </ScrollView>

      {/* Profile Picture Menu Modal */}
      <Modal
        visible={showPicMenu}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowPicMenu(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setShowPicMenu(false)}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>Profile Picture</Text>
            <Text style={styles.modalSubtitle}>Choose how to set your character image</Text>

            <TouchableOpacity style={styles.modalOption} onPress={launchCamera}>
              <View style={[styles.modalOptionIcon, { backgroundColor: 'rgba(231,76,60,0.1)' }]}>
                <Ionicons name="camera" size={24} color="#e74c3c" />
              </View>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Take Photo</Text>
                <Text style={styles.modalOptionDesc}>Use your camera to take a selfie</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#444" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.modalOption} onPress={launchGallery}>
              <View style={[styles.modalOptionIcon, { backgroundColor: 'rgba(52,152,219,0.1)' }]}>
                <Ionicons name="images" size={24} color="#3498db" />
              </View>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Choose from Gallery</Text>
                <Text style={styles.modalOptionDesc}>Pick a photo from your library</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#444" />
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.modalCancel} 
              onPress={() => setShowPicMenu(false)}
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

// ========== STATUS TAB ==========
function StatusTab({ player, classColor, territories, playerId }: { player: any; classColor: string; territories: any[]; playerId: string }) {
  const totalIncome = territories.reduce((sum: number, t: any) => sum + (t.rewards?.passive_income || 0), 0);
  const [collecting, setCollecting] = useState(false);
  const [incomePreview, setIncomePreview] = useState<{ available_income: number; ready_territories: number; total_territories: number; next_collection_hours: number } | null>(null);

  useEffect(() => {
    if (playerId && territories.length > 0) {
      getTerritoryIncomePreview(playerId).then(setIncomePreview).catch(() => {});
    }
  }, [playerId, territories.length]);

  return (
    <View>
      {/* Health & Energy */}
      <View style={styles.section}>
        <HealthBar current={player.stats.health} max={player.stats.max_health} label="HEALTH" color="#e74c3c" />
        <View style={{ height: 12 }} />
        <HealthBar current={player.stats.energy} max={player.stats.max_energy} label="ENERGY" color="#3498db" />
      </View>

      {/* Stats */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>COMBAT STATS</Text>
        <View style={styles.statsGrid}>
          <StatBar icon="flash" label="Attack" value={player.stats.attack} color="#e74c3c" />
          <StatBar icon="shield" label="Defense" value={player.stats.defense} color="#3498db" />
          <StatBar icon="speedometer" label="Speed" value={player.stats.speed} color="#2ecc71" />
          <StatBar icon="dice" label="Luck" value={player.stats.luck} color="#f39c12" />
        </View>
      </View>

      {/* Resources */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>RESOURCES</Text>
        <View style={styles.resourcesRow}>
          <View style={styles.resourceItem}>
            <Ionicons name="cash" size={24} color="#f39c12" />
            <Text style={styles.resourceValue}>${player.cash}</Text>
            <Text style={styles.resourceLabel}>Cash</Text>
          </View>
          <View style={styles.resourceItem}>
            <Ionicons name="star" size={24} color="#9b59b6" />
            <Text style={styles.resourceValue}>{player.reputation}</Text>
            <Text style={styles.resourceLabel}>Rep</Text>
          </View>
          <View style={styles.resourceItem}>
            <Ionicons name="trophy" size={24} color="#27ae60" />
            <Text style={styles.resourceValue}>{player.wins}</Text>
            <Text style={styles.resourceLabel}>Wins</Text>
          </View>
          <View style={styles.resourceItem}>
            <Ionicons name="briefcase" size={24} color="#3498db" />
            <Text style={styles.resourceValue}>{player.missions_completed}</Text>
            <Text style={styles.resourceLabel}>Missions</Text>
          </View>
        </View>
      </View>

      {/* My Territories */}
      <View style={styles.section}>
        <View style={styles.terrSectionHeader}>
          <Text style={styles.sectionTitle}>MY TERRITORIES</Text>
          <View style={styles.terrCountBadge}>
            <Text style={styles.terrCountText}>{territories.length}</Text>
          </View>
        </View>
        {territories.length === 0 ? (
          <View style={styles.terrEmpty}>
            <Ionicons name="flag-outline" size={36} color="#555" />
            <Text style={styles.terrEmptyText}>No territories owned</Text>
            <Text style={styles.terrEmptyHint}>Capture territories on the map to earn daily income!</Text>
          </View>
        ) : (
          <>
            <View style={styles.terrIncomeBar}>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Ionicons name="trending-up" size={18} color="#4caf50" />
                  <Text style={styles.terrIncomeText}>Daily Income: ${totalIncome}</Text>
                </View>
                {incomePreview && incomePreview.available_income > 0 && (
                  <Text style={styles.terrAvailableText}>
                    Available: ${incomePreview.available_income} from {incomePreview.ready_territories} territory{incomePreview.ready_territories !== 1 ? 'ies' : 'y'}
                  </Text>
                )}
                {incomePreview && incomePreview.available_income === 0 && incomePreview.next_collection_hours > 0 && (
                  <Text style={styles.terrCooldownText}>
                    Next in: {incomePreview.next_collection_hours}h
                  </Text>
                )}
              </View>
              <TouchableOpacity
                style={[styles.collectBtn, collecting && { opacity: 0.6 }, incomePreview && incomePreview.available_income > 0 && styles.collectBtnReady]}
                onPress={async () => {
                  if (collecting || !playerId) return;
                  setCollecting(true);
                  try {
                    const result = await collectTerritoryIncome(playerId);
                    if (result.income > 0) {
                      showGameToast({
                        type: 'success',
                        title: `$${result.income} Collected!`,
                        message: `Income from ${result.territories} territory${result.territories !== 1 ? 'ies' : 'y'}`,
                        duration: 3000,
                      });
                    } else {
                      showGameToast({
                        type: 'info',
                        title: 'No Income Ready',
                        message: 'Come back in 24 hours',
                        duration: 2500,
                      });
                    }
                    // Refresh preview
                    const preview = await getTerritoryIncomePreview(playerId);
                    setIncomePreview(preview);
                  } catch (err: any) {
                    showGameToast({
                      type: 'error',
                      title: 'Collection Failed',
                      message: err?.response?.data?.detail || 'Try again later',
                    });
                  } finally {
                    setCollecting(false);
                  }
                }}
                disabled={collecting}
                activeOpacity={0.7}
              >
                {collecting ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <>
                    <Ionicons name="wallet" size={14} color="#fff" />
                    <Text style={styles.collectBtnText}>COLLECT</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
            {territories.map((t: any) => (
              <View key={t.id} style={[styles.terrCard, { borderLeftColor: t.color || classColor }]}>
                <View style={[styles.terrColorDot, { backgroundColor: t.color || classColor }]} />
                <View style={styles.terrCardInfo}>
                  <Text style={styles.terrCardName}>{t.name}</Text>
                  <Text style={styles.terrCardIncome}>
                    <Ionicons name="cash-outline" size={13} color="#f39c12" /> ${t.rewards?.passive_income || 0}/day
                  </Text>
                </View>
                <View style={styles.terrCardBoss}>
                  <Text style={styles.terrCardBossLv}>Lv.{t.boss?.level || '?'}</Text>
                </View>
              </View>
            ))}
          </>
        )}
      </View>

      {/* Battle Record */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>BATTLE RECORD</Text>
        <View style={styles.battleRecord}>
          <View style={styles.recordItem}>
            <Text style={[styles.recordValue, { color: '#4caf50' }]}>{player.wins}</Text>
            <Text style={styles.recordLabel}>Wins</Text>
          </View>
          <View style={styles.recordDivider} />
          <View style={styles.recordItem}>
            <Text style={[styles.recordValue, { color: '#f44336' }]}>{player.losses}</Text>
            <Text style={styles.recordLabel}>Losses</Text>
          </View>
          <View style={styles.recordDivider} />
          <View style={styles.recordItem}>
            <Text style={[styles.recordValue, { color: '#ff9800' }]}>
              {player.wins + player.losses > 0
                ? Math.round((player.wins / (player.wins + player.losses)) * 100)
                : 0}%
            </Text>
            <Text style={styles.recordLabel}>Win Rate</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

// ========== EQUIPMENT TAB ==========
function EquipmentTab({
  equipped,
  classColor,
  onUnequip,
  playerLevel,
}: {
  equipped: Record<string, EquipmentItem | null>;
  classColor: string;
  onUnequip: (slot: string) => void;
  playerLevel: number;
}) {
  const slots = ['weapon', 'armor', 'accessory', 'vehicle'];

  return (
    <View>
      <Text style={styles.sectionTitle}>EQUIPPED GEAR</Text>
      {slots.map((slot) => {
        const item = equipped[slot];
        const rarityColor = item ? RARITY_COLORS[item.rarity] || '#9e9e9e' : '#333';
        
        // Durability info for equipped items
        const durability = item?.durability ?? 100;
        const maxDurability = item?.max_durability ?? 100;
        const durabilityPercent = item ? (durability / maxDurability) * 100 : 100;
        
        // Durability bar color
        let durabilityColor = '#4caf50';
        if (durabilityPercent <= 25) durabilityColor = '#e74c3c';
        else if (durabilityPercent <= 50) durabilityColor = '#f39c12';

        return (
          <View key={slot} style={[styles.equipSlot, { borderLeftColor: rarityColor, borderLeftWidth: 3 }]}>
            <View style={[styles.slotIcon, { backgroundColor: item ? `${rarityColor}20` : '#1a1a1a' }]}>
              <Ionicons name={SLOT_ICONS[slot]} size={24} color={item ? rarityColor : '#444'} />
              {item?.is_broken && (
                <View style={styles.brokenBadge}>
                  <Ionicons name="warning" size={10} color="#e74c3c" />
                </View>
              )}
            </View>
            <View style={styles.slotInfo}>
              <Text style={styles.slotLabel}>{SLOT_LABELS[slot]}</Text>
              {item ? (
                <>
                  <Text style={[styles.slotItemName, { color: item.is_broken ? '#666' : rarityColor }]}>
                    {item.name} {item.is_broken && '(BROKEN)'}
                  </Text>
                  {/* Durability bar for equipped item */}
                  <View style={styles.durabilityContainer}>
                    <View style={[styles.durabilityBarBg, { height: 4 }]}>
                      <View 
                        style={[
                          styles.durabilityBar, 
                          { width: `${durabilityPercent}%`, backgroundColor: durabilityColor }
                        ]} 
                      />
                    </View>
                    <Text style={[styles.durabilityText, { color: durabilityColor, fontSize: 9 }]}>
                      {durability}/{maxDurability}
                    </Text>
                  </View>
                  <View style={styles.statBonusRow}>
                    {Object.entries(item.stats_bonus).map(([stat, val]) => (
                      <Text
                        key={stat}
                        style={[styles.statBonusText, { color: item.is_broken ? '#555' : ((val as number) > 0 ? '#4caf50' : '#f44336') }]}
                      >
                        {(val as number) > 0 ? '+' : ''}{val as number} {stat}
                      </Text>
                    ))}
                  </View>
                </>
              ) : (
                <Text style={styles.emptySlotText}>Empty - No item equipped</Text>
              )}
            </View>
            {item && (
              <TouchableOpacity
                style={styles.unequipBtn}
                onPress={() => onUnequip(slot)}
              >
                <Ionicons name="close-circle" size={24} color="#666" />
              </TouchableOpacity>
            )}
          </View>
        );
      })}

      {/* Total bonus summary */}
      <View style={[styles.section, { marginTop: 16 }]}>
        <Text style={styles.sectionTitle}>EQUIPMENT BONUSES</Text>
        <View style={styles.bonusSummary}>
          {(() => {
            const totals: Record<string, number> = {};
            Object.values(equipped).forEach((item) => {
              if (item?.stats_bonus) {
                Object.entries(item.stats_bonus).forEach(([stat, val]) => {
                  totals[stat] = (totals[stat] || 0) + (val as number);
                });
              }
            });
            const entries = Object.entries(totals);
            if (entries.length === 0) {
              return <Text style={styles.emptySlotText}>No bonuses - equip gear to boost stats</Text>;
            }
            return entries.map(([stat, val]) => (
              <View key={stat} style={styles.bonusItem}>
                <Text style={styles.bonusStat}>{stat.charAt(0).toUpperCase() + stat.slice(1)}</Text>
                <Text style={[styles.bonusValue, { color: val > 0 ? '#4caf50' : '#f44336' }]}>
                  {val > 0 ? '+' : ''}{val}
                </Text>
              </View>
            ));
          })()}
        </View>
      </View>
    </View>
  );
}

// ========== ITEMS TAB ==========
function ItemsTab({
  inventory,
  classColor,
  onEquip,
  onDelete,
  onSell,
  onRepair,
  playerLevel,
  playerCash,
}: {
  inventory: EquipmentItem[];
  classColor: string;
  onEquip: (item: EquipmentItem) => void;
  onDelete: (item: EquipmentItem) => void;
  onSell: (item: EquipmentItem) => void;
  onRepair: (item: EquipmentItem) => void;
  playerLevel: number;
  playerCash: number;
}) {
  if (inventory.length === 0) {
    return (
      <View style={styles.emptyState}>
        <Ionicons name="bag-outline" size={64} color="#333" />
        <Text style={styles.emptyStateTitle}>No Items</Text>
        <Text style={styles.emptyStateText}>
          Defeat enemies and complete missions to earn loot!
        </Text>
      </View>
    );
  }

  // Calculate repair cost (30-80% of item value based on rarity)
  const getRepairCost = (item: EquipmentItem) => {
    const maxDur = item.max_durability || 100;
    const curDur = item.durability || maxDur;
    const damagePercent = (maxDur - curDur) / maxDur;
    const rarityMult: Record<string, number> = { common: 0.3, uncommon: 0.4, rare: 0.5, epic: 0.6, legendary: 0.8 };
    const mult = rarityMult[item.rarity] || 0.5;
    return Math.max(1, Math.floor(item.value * mult * damagePercent));
  };

  return (
    <View>
      <Text style={styles.sectionTitle}>INVENTORY ({inventory.length})</Text>
      {inventory.map((item, index) => {
        const rarityColor = RARITY_COLORS[item.rarity] || '#9e9e9e';
        const canEquip = playerLevel >= item.level_requirement && !item.is_broken;
        const sellPrice = Math.max(1, Math.floor((item as any).value / 2 || 5));
        const durability = item.durability ?? 100;
        const maxDurability = item.max_durability ?? 100;
        const durabilityPercent = (durability / maxDurability) * 100;
        const needsRepair = durability < maxDurability;
        const repairCost = needsRepair ? getRepairCost(item) : 0;
        const canAffordRepair = playerCash >= repairCost;

        // Durability bar color based on condition
        let durabilityColor = '#4caf50'; // Green
        if (durabilityPercent <= 25) durabilityColor = '#e74c3c'; // Red
        else if (durabilityPercent <= 50) durabilityColor = '#f39c12'; // Orange

        return (
          <View 
            key={`${item.id}-${index}`} 
            style={[
              styles.itemCard, 
              { borderLeftColor: rarityColor, borderLeftWidth: 3 },
              item.is_broken && styles.brokenItemCard
            ]}
          >
            <View style={[styles.itemIconWrap, { backgroundColor: `${rarityColor}20` }]}>
              <Ionicons name={SLOT_ICONS[item.equipment_type] || 'cube'} size={22} color={item.is_broken ? '#666' : rarityColor} />
              {item.is_broken && (
                <View style={styles.brokenBadge}>
                  <Ionicons name="warning" size={12} color="#e74c3c" />
                </View>
              )}
            </View>
            <View style={styles.itemInfo}>
              <View style={styles.itemHeader}>
                <Text style={[styles.itemName, { color: item.is_broken ? '#666' : rarityColor }]}>
                  {item.name} {item.is_broken && '(BROKEN)'}
                </Text>
                <Text style={[styles.rarityBadge, { color: item.is_broken ? '#666' : rarityColor }]}>
                  {item.rarity.toUpperCase()}
                </Text>
              </View>
              <Text style={[styles.itemDesc, item.is_broken && { color: '#555' }]} numberOfLines={1}>{item.description}</Text>
              
              {/* Durability Bar */}
              <View style={styles.durabilityContainer}>
                <View style={styles.durabilityBarBg}>
                  <View 
                    style={[
                      styles.durabilityBar, 
                      { width: `${durabilityPercent}%`, backgroundColor: durabilityColor }
                    ]} 
                  />
                </View>
                <Text style={[styles.durabilityText, { color: durabilityColor }]}>
                  {durability}/{maxDurability}
                </Text>
              </View>

              <View style={styles.statBonusRow}>
                {Object.entries(item.stats_bonus).map(([stat, val]) => (
                  <Text
                    key={stat}
                    style={[styles.statBonusText, { color: item.is_broken ? '#555' : ((val as number) > 0 ? '#4caf50' : '#f44336') }]}
                  >
                    {(val as number) > 0 ? '+' : ''}{val as number} {stat}
                  </Text>
                ))}
              </View>
              {!canEquip && !item.is_broken && (
                <Text style={styles.levelReqText}>Requires Lv.{item.level_requirement}</Text>
              )}
              {/* Action buttons row */}
              <View style={styles.itemActions}>
                {needsRepair ? (
                  <TouchableOpacity
                    style={[styles.itemActionBtn, styles.repairActionBtn, !canAffordRepair && styles.equipBtnDisabled]}
                    onPress={() => canAffordRepair && onRepair(item)}
                    disabled={!canAffordRepair}
                  >
                    <Ionicons name="construct" size={14} color={canAffordRepair ? '#fff' : '#555'} />
                    <Text style={[styles.itemActionText, !canAffordRepair && { color: '#555' }]}>
                      REPAIR ${repairCost}
                    </Text>
                  </TouchableOpacity>
                ) : (
                  <TouchableOpacity
                    style={[styles.itemActionBtn, styles.equipActionBtn, !canEquip && styles.equipBtnDisabled]}
                    onPress={() => canEquip && onEquip(item)}
                    disabled={!canEquip}
                  >
                    <Ionicons name="checkmark-circle" size={14} color={canEquip ? '#fff' : '#555'} />
                    <Text style={[styles.itemActionText, !canEquip && { color: '#555' }]}>EQUIP</Text>
                  </TouchableOpacity>
                )}
                <TouchableOpacity
                  style={[styles.itemActionBtn, styles.sellActionBtn]}
                  onPress={() => onSell(item)}
                >
                  <Ionicons name="cash" size={14} color="#f39c12" />
                  <Text style={[styles.itemActionText, { color: '#f39c12' }]}>SELL ${sellPrice}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.itemActionBtn, styles.deleteActionBtn]}
                  onPress={() => onDelete(item)}
                >
                  <Ionicons name="trash" size={14} color="#e74c3c" />
                  <Text style={[styles.itemActionText, { color: '#e74c3c' }]}>DROP</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        );
      })}
    </View>
  );
}

// ========== SKILLS TAB ==========
function SkillsTab({
  skills,
  classColor,
  playerLevel,
  playerId,
  onRefresh,
}: {
  skills: any;
  classColor: string;
  playerLevel: number;
  playerId: string;
  onRefresh: () => void;
}) {
  const [equipping, setEquipping] = useState<string | null>(null);
  
  const SKILL_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
    heavy_strike: 'hammer',
    quick_shot: 'flash',
    defensive_stance: 'shield',
    critical_aim: 'eye',
    heal: 'medkit',
    rage: 'flame',
    execute: 'skull',
    counter_strike: 'sync',
    blinding_flash: 'flashlight',
    iron_skin: 'body',
    adrenaline_rush: 'pulse',
    double_tap: 'git-compare',
    smoke_bomb: 'cloud',
    berserker: 'bonfire',
    tactical_reload: 'reload',
    armor_pierce: 'arrow-forward',
    venomous_strike: 'bug',
    battle_cry: 'megaphone',
    headshot: 'locate',
    fortress: 'business',
    lifesteal: 'heart-half',
    chain_attack: 'link',
    medic: 'bandage',
    rampage: 'thunderstorm',
    evasion: 'footsteps',
    assassinate: 'cut',
    blood_pact: 'water',
    titanium_shell: 'hardware-chip',
    obliterate: 'nuclear',
    regenerate: 'leaf',
    phantom_strike: 'eye-off',
    war_machine: 'construct',
    drain_life: 'nutrition',
    massacre: 'warning',
    diamond_armor: 'diamond',
    phoenix_heal: 'sunny',
    annihilate: 'planet',
    vampire: 'moon',
    juggernaut: 'fitness',
    omega_heal: 'sparkles',
    death_blow: 'hand-left',
    eternal_guard: 'infinite',
    soul_reaper: 'logo-snapchat',
    armageddon: 'flame',
    immortal: 'star',
    extinction: 'skull',
    divine_shield: 'ribbon',
    apocalypse: 'globe',
    titan_soul: 'trophy',
    rebirth: 'refresh-circle',
    godslayer: 'flash',
  };

  const handleEquip = async (skillId: string) => {
    try {
      setEquipping(skillId);
      await equipSkill(playerId, skillId);
      onRefresh();
      Alert.alert('Success', 'Skill equipped!');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to equip skill');
    } finally {
      setEquipping(null);
    }
  };

  const handleUnequip = async (skillId: string) => {
    try {
      setEquipping(skillId);
      await unequipSkill(playerId, skillId);
      onRefresh();
      Alert.alert('Success', 'Skill unequipped!');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to unequip skill');
    } finally {
      setEquipping(null);
    }
  };

  // Handle both old format (array) and new format (object with skills array)
  const skillsList = Array.isArray(skills) ? skills : (skills?.skills || []);
  const equippedSkills = skills?.equipped_skills || [];
  const maxEquipped = skills?.max_equipped || 4;

  if (skillsList.length === 0) {
    return (
      <View style={styles.emptyState}>
        <Ionicons name="flash-outline" size={64} color="#333" />
        <Text style={styles.emptyStateTitle}>No Skills Yet</Text>
        <Text style={styles.emptyStateText}>Buy skills from Gun Shops to unlock powerful abilities!</Text>
      </View>
    );
  }

  // Separate equipped, owned but not equipped, and not owned skills
  const equippedList = skillsList.filter((s: any) => s.equipped);
  const ownedNotEquipped = skillsList.filter((s: any) => s.owned && !s.equipped);
  const notOwned = skillsList.filter((s: any) => !s.owned && s.can_unlock);
  const locked = skillsList.filter((s: any) => !s.owned && !s.can_unlock);

  return (
    <ScrollView>
      {/* Equipped Skills */}
      <View style={styles.skillSectionHeader}>
        <Text style={styles.sectionTitle}>EQUIPPED ({equippedList.length}/{maxEquipped})</Text>
        <Text style={styles.skillSectionSubtitle}>Active in battle</Text>
      </View>
      {equippedList.map((skill: any) => (
        <View key={skill.id} style={[styles.skillRow, { borderLeftColor: classColor, borderLeftWidth: 3 }]}>
          <View style={[styles.skillIconWrap, { backgroundColor: `${classColor}20` }]}>
            <Ionicons
              name={SKILL_ICONS[skill.id] || 'flash'}
              size={24}
              color={classColor}
            />
          </View>
          <View style={styles.skillInfo}>
            <Text style={styles.skillName}>{skill.name}</Text>
            <View style={styles.skillDetails}>
              {skill.damage_mult && <Text style={styles.skillStat}>{skill.damage_mult}x DMG</Text>}
              {skill.defense_buff && <Text style={[styles.skillStat, { color: '#2196f3' }]}>{skill.defense_buff}x DEF</Text>}
              {skill.heal_percent && <Text style={[styles.skillStat, { color: '#4caf50' }]}>{Math.round(skill.heal_percent * 100)}% Heal</Text>}
              {skill.lifesteal && <Text style={[styles.skillStat, { color: '#e91e63' }]}>{Math.round(skill.lifesteal * 100)}% Steal</Text>}
              <Text style={styles.skillCost}>{skill.cost} EN</Text>
            </View>
          </View>
          <TouchableOpacity
            style={[styles.skillActionBtn, { backgroundColor: '#f44336' }]}
            onPress={() => handleUnequip(skill.id)}
            disabled={equipping === skill.id}
          >
            {equipping === skill.id ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.skillActionText}>REMOVE</Text>
            )}
          </TouchableOpacity>
        </View>
      ))}

      {/* Owned but not equipped */}
      {ownedNotEquipped.length > 0 && (
        <>
          <View style={styles.skillSectionHeader}>
            <Text style={styles.sectionTitle}>OWNED SKILLS ({ownedNotEquipped.length})</Text>
            <Text style={styles.skillSectionSubtitle}>Tap to equip</Text>
          </View>
          {ownedNotEquipped.map((skill: any) => (
            <View key={skill.id} style={[styles.skillRow, { borderLeftColor: '#4caf50', borderLeftWidth: 3 }]}>
              <View style={[styles.skillIconWrap, { backgroundColor: 'rgba(76,175,80,0.2)' }]}>
                <Ionicons
                  name={SKILL_ICONS[skill.id] || 'flash'}
                  size={24}
                  color="#4caf50"
                />
              </View>
              <View style={styles.skillInfo}>
                <Text style={styles.skillName}>{skill.name}</Text>
                <View style={styles.skillDetails}>
                  {skill.damage_mult && <Text style={styles.skillStat}>{skill.damage_mult}x DMG</Text>}
                  {skill.defense_buff && <Text style={[styles.skillStat, { color: '#2196f3' }]}>{skill.defense_buff}x DEF</Text>}
                  {skill.heal_percent && <Text style={[styles.skillStat, { color: '#4caf50' }]}>{Math.round(skill.heal_percent * 100)}% Heal</Text>}
                  {skill.lifesteal && <Text style={[styles.skillStat, { color: '#e91e63' }]}>{Math.round(skill.lifesteal * 100)}% Steal</Text>}
                  <Text style={styles.skillCost}>{skill.cost} EN</Text>
                </View>
              </View>
              <TouchableOpacity
                style={[styles.skillActionBtn, { backgroundColor: classColor }]}
                onPress={() => handleEquip(skill.id)}
                disabled={equipping === skill.id || equippedList.length >= maxEquipped}
              >
                {equipping === skill.id ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.skillActionText}>EQUIP</Text>
                )}
              </TouchableOpacity>
            </View>
          ))}
        </>
      )}

      {/* Hint to buy more skills */}
      {ownedNotEquipped.length === 0 && equippedList.length < 4 && (
        <View style={styles.skillHint}>
          <Ionicons name="storefront-outline" size={20} color="#888" />
          <Text style={styles.skillHintText}>Buy more skills from Gun Shops!</Text>
        </View>
      )}
      
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

// ========== STYLES ==========
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0a0a' },
  loadingText: { color: '#888', marginTop: 12, fontSize: 14 },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  avatarContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(255,255,255,0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    overflow: 'hidden',
  },
  avatarImage: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  avatarOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 28,
  },
  cameraButton: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    backgroundColor: '#e74c3c',
    width: 22,
    height: 22,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#0a0a0a',
  },
  headerInfo: { flex: 1, marginLeft: 12 },
  playerName: { fontSize: 18, fontWeight: 'bold', color: '#fff' },
  playerClass: { fontSize: 11, fontWeight: '600', letterSpacing: 1.5, marginTop: 2 },
  levelRow: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  levelBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  levelText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  xpBarSmall: { flex: 1, height: 6, backgroundColor: '#222', borderRadius: 3, marginLeft: 8, overflow: 'hidden' },
  xpFillSmall: { height: '100%', borderRadius: 3 },
  xpTextSmall: { color: '#555', fontSize: 10, marginLeft: 6 },
  logoutBtn: { padding: 8 },

  // Tab Bar
  tabBar: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 4,
  },
  tabLabel: { fontSize: 12, color: '#666', fontWeight: '600' },

  scrollContent: { padding: 16, paddingBottom: 40 },

  // Section
  section: { marginBottom: 24 },
  sectionTitle: { color: '#666', fontSize: 11, fontWeight: '700', letterSpacing: 2, marginBottom: 12 },

  // Stats
  statsGrid: { gap: 8 },

  // Resources
  resourcesRow: { flexDirection: 'row', gap: 8 },
  resourceItem: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: '#111',
    padding: 14,
    borderRadius: 12,
  },
  resourceValue: { color: '#fff', fontSize: 18, fontWeight: 'bold', marginTop: 6 },
  resourceLabel: { color: '#555', fontSize: 10, marginTop: 2 },

  // Battle Record
  battleRecord: {
    flexDirection: 'row',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  recordItem: { flex: 1, alignItems: 'center' },
  recordValue: { fontSize: 24, fontWeight: 'bold' },
  recordLabel: { color: '#666', fontSize: 11, marginTop: 4 },
  recordDivider: { width: 1, height: 32, backgroundColor: '#222' },

  // Equipment Slots
  equipSlot: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
  },
  slotIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  slotInfo: { flex: 1, marginLeft: 12 },
  slotLabel: { color: '#666', fontSize: 10, fontWeight: '600', letterSpacing: 1, textTransform: 'uppercase' },
  slotItemName: { fontSize: 15, fontWeight: '700', marginTop: 2 },
  emptySlotText: { color: '#444', fontSize: 13, fontStyle: 'italic', marginTop: 2 },
  unequipBtn: { padding: 8 },

  // Stat Bonus
  statBonusRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  statBonusText: { fontSize: 11, fontWeight: '600' },

  // Bonus Summary
  bonusSummary: {
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  bonusItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  bonusStat: { color: '#999', fontSize: 12 },
  bonusValue: { fontSize: 14, fontWeight: 'bold' },

  // Item Cards
  itemCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  itemIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  itemInfo: { flex: 1, marginLeft: 10 },
  itemHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemName: { fontSize: 14, fontWeight: '700' },
  rarityBadge: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  itemDesc: { color: '#666', fontSize: 11, marginTop: 2 },
  levelReqText: { color: '#f44336', fontSize: 10, fontWeight: '600', marginTop: 3 },
  itemActions: {
    flexDirection: 'row' as const,
    gap: 6,
    marginTop: 8,
  },
  itemActionBtn: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    gap: 4,
  },
  equipActionBtn: {
    backgroundColor: '#1a3a1a',
  },
  sellActionBtn: {
    backgroundColor: '#3a2a0a',
  },
  deleteActionBtn: {
    backgroundColor: '#3a1a1a',
  },
  itemActionText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '800' as const,
  },
  equipBtn: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    marginLeft: 8,
  },
  equipBtnDisabled: { backgroundColor: '#222' },
  equipBtnText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  equipBtnTextDisabled: { color: '#555' },

  // Skills
  skillRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  skillLocked: { opacity: 0.5 },
  skillIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  skillInfo: { flex: 1, marginLeft: 12 },
  skillName: { color: '#fff', fontSize: 15, fontWeight: '700' },
  skillDetails: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  skillStat: { color: '#e74c3c', fontSize: 11, fontWeight: '600' },
  skillCost: { color: '#2196f3', fontSize: 11, fontWeight: '600' },
  lockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  lockText: { color: '#666', fontSize: 11, fontWeight: '600' },
  unlockBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  skillSectionHeader: {
    marginTop: 16,
    marginBottom: 8,
  },
  skillSectionSubtitle: {
    color: '#666',
    fontSize: 11,
    marginTop: 2,
  },
  skillActionBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    minWidth: 70,
    alignItems: 'center',
  },
  skillActionText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  skillDesc: {
    color: '#888',
    fontSize: 11,
    marginTop: 2,
  },
  priceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(243, 156, 18, 0.15)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  priceText: {
    color: '#f39c12',
    fontSize: 12,
    fontWeight: '700',
  },
  skillHint: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 20,
    marginTop: 10,
  },
  skillHintText: {
    color: '#888',
    fontSize: 13,
  },

  // Empty State
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyStateTitle: { color: '#555', fontSize: 18, fontWeight: '700', marginTop: 16 },
  emptyStateText: { color: '#444', fontSize: 13, textAlign: 'center', marginTop: 8, paddingHorizontal: 32 },

  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    paddingBottom: 40,
  },
  modalHandle: {
    width: 40,
    height: 4,
    backgroundColor: '#444',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '800',
    textAlign: 'center',
  },
  modalSubtitle: {
    color: '#666',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 6,
    marginBottom: 20,
  },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    padding: 16,
    borderRadius: 14,
    marginBottom: 10,
  },
  modalOptionIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalOptionText: {
    flex: 1,
    marginLeft: 14,
  },
  modalOptionTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  modalOptionDesc: {
    color: '#666',
    fontSize: 12,
    marginTop: 2,
  },
  modalCancel: {
    alignItems: 'center',
    paddingVertical: 14,
    marginTop: 6,
  },
  modalCancelText: {
    color: '#888',
    fontSize: 16,
    fontWeight: '600',
  },
  // Territory styles
  terrSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  terrCountBadge: {
    backgroundColor: '#f39c12',
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginLeft: 10,
  },
  terrCountText: {
    color: '#000',
    fontSize: 12,
    fontWeight: '800',
  },
  terrEmpty: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  terrEmptyText: {
    color: '#777',
    fontSize: 15,
    fontWeight: '700',
    marginTop: 10,
  },
  terrEmptyHint: {
    color: '#555',
    fontSize: 12,
    marginTop: 4,
    textAlign: 'center',
  },
  terrIncomeBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a2e1a',
    borderRadius: 10,
    padding: 10,
    marginBottom: 10,
    gap: 8,
  },
  terrIncomeText: {
    color: '#4caf50',
    fontSize: 14,
    fontWeight: '800',
  },
  terrAvailableText: {
    color: '#f39c12',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 3,
  },
  terrCooldownText: {
    color: '#888',
    fontSize: 11,
    fontStyle: 'italic',
    marginTop: 3,
  },
  collectBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#555',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minWidth: 90,
    justifyContent: 'center',
  },
  collectBtnReady: {
    backgroundColor: '#4caf50',
  },
  collectBtnText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
  terrCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
    borderLeftWidth: 4,
  },
  terrColorDot: {
    width: 12,
    height: 12,
    borderRadius: 3,
    marginRight: 10,
  },
  terrCardInfo: {
    flex: 1,
  },
  terrCardName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  terrCardIncome: {
    color: '#aaa',
    fontSize: 12,
    marginTop: 2,
  },
  terrCardBoss: {
    backgroundColor: '#222',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  terrCardBossLv: {
    color: '#f39c12',
    fontSize: 11,
    fontWeight: '800',
  },
  // Durability styles
  durabilityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginVertical: 4,
  },
  durabilityBarBg: {
    flex: 1,
    height: 6,
    backgroundColor: '#222',
    borderRadius: 3,
    overflow: 'hidden',
  },
  durabilityBar: {
    height: '100%',
    borderRadius: 3,
  },
  durabilityText: {
    fontSize: 10,
    fontWeight: '700',
    minWidth: 50,
    textAlign: 'right',
  },
  brokenItemCard: {
    opacity: 0.7,
    borderLeftColor: '#e74c3c',
    backgroundColor: 'rgba(231, 76, 60, 0.05)',
  },
  brokenBadge: {
    position: 'absolute',
    bottom: -4,
    right: -4,
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    padding: 2,
  },
  repairActionBtn: {
    backgroundColor: '#27ae60',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
});
