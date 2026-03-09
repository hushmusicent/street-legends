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
import { router } from 'expo-router';
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
} from '../../services/api';
import { HealthBar } from '../../components/HealthBar';
import { StatBar } from '../../components/StatBar';
import { Skill } from '../../types/game';
import AsyncStorage from '@react-native-async-storage/async-storage';

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

  useEffect(() => {
    if (playerId) loadAllData();
  }, [playerId]);

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
      ]);
      if (results[0].status === 'fulfilled') setPlayer(results[0].value);
      if (results[1].status === 'fulfilled') setSkills(results[1].value);
      if (results[2].status === 'fulfilled') setInventory(results[2].value);
      if (results[3].status === 'fulfilled') setEquipped(results[3].value);
      if (results[4].status === 'fulfilled' && results[4].value.profile_pic) {
        setProfilePic(results[4].value.profile_pic);
        setGlobalProfilePic(results[4].value.profile_pic);
      }
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
          <StatusTab player={player} classColor={classColor} />
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
            playerLevel={player.level}
          />
        )}
        {activeTab === 'skills' && (
          <SkillsTab skills={skills} classColor={classColor} playerLevel={player.level} />
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
function StatusTab({ player, classColor }: { player: any; classColor: string }) {
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

        return (
          <View key={slot} style={[styles.equipSlot, { borderLeftColor: rarityColor, borderLeftWidth: 3 }]}>
            <View style={[styles.slotIcon, { backgroundColor: item ? `${rarityColor}20` : '#1a1a1a' }]}>
              <Ionicons name={SLOT_ICONS[slot]} size={24} color={item ? rarityColor : '#444'} />
            </View>
            <View style={styles.slotInfo}>
              <Text style={styles.slotLabel}>{SLOT_LABELS[slot]}</Text>
              {item ? (
                <>
                  <Text style={[styles.slotItemName, { color: rarityColor }]}>{item.name}</Text>
                  <View style={styles.statBonusRow}>
                    {Object.entries(item.stats_bonus).map(([stat, val]) => (
                      <Text
                        key={stat}
                        style={[styles.statBonusText, { color: (val as number) > 0 ? '#4caf50' : '#f44336' }]}
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
  playerLevel,
}: {
  inventory: EquipmentItem[];
  classColor: string;
  onEquip: (item: EquipmentItem) => void;
  playerLevel: number;
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

  return (
    <View>
      <Text style={styles.sectionTitle}>INVENTORY ({inventory.length})</Text>
      {inventory.map((item, index) => {
        const rarityColor = RARITY_COLORS[item.rarity] || '#9e9e9e';
        const canEquip = playerLevel >= item.level_requirement;

        return (
          <View key={`${item.id}-${index}`} style={[styles.itemCard, { borderLeftColor: rarityColor, borderLeftWidth: 3 }]}>
            <View style={[styles.itemIconWrap, { backgroundColor: `${rarityColor}20` }]}>
              <Ionicons name={SLOT_ICONS[item.equipment_type] || 'cube'} size={22} color={rarityColor} />
            </View>
            <View style={styles.itemInfo}>
              <View style={styles.itemHeader}>
                <Text style={[styles.itemName, { color: rarityColor }]}>{item.name}</Text>
                <Text style={[styles.rarityBadge, { color: rarityColor }]}>
                  {item.rarity.toUpperCase()}
                </Text>
              </View>
              <Text style={styles.itemDesc} numberOfLines={1}>{item.description}</Text>
              <View style={styles.statBonusRow}>
                {Object.entries(item.stats_bonus).map(([stat, val]) => (
                  <Text
                    key={stat}
                    style={[styles.statBonusText, { color: (val as number) > 0 ? '#4caf50' : '#f44336' }]}
                  >
                    {(val as number) > 0 ? '+' : ''}{val as number} {stat}
                  </Text>
                ))}
              </View>
              {!canEquip && (
                <Text style={styles.levelReqText}>Requires Lv.{item.level_requirement}</Text>
              )}
            </View>
            <TouchableOpacity
              style={[styles.equipBtn, !canEquip && styles.equipBtnDisabled]}
              onPress={() => canEquip && onEquip(item)}
              disabled={!canEquip}
            >
              <Text style={[styles.equipBtnText, !canEquip && styles.equipBtnTextDisabled]}>
                EQUIP
              </Text>
            </TouchableOpacity>
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
}: {
  skills: Skill[];
  classColor: string;
  playerLevel: number;
}) {
  const SKILL_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
    heavy_strike: 'hammer',
    quick_shot: 'flash',
    defensive_stance: 'shield',
    critical_aim: 'eye',
    heal: 'medkit',
    rage: 'flame',
    execute: 'skull',
  };

  if (skills.length === 0) {
    return (
      <View style={styles.emptyState}>
        <Ionicons name="flash-outline" size={64} color="#333" />
        <Text style={styles.emptyStateTitle}>No Skills Yet</Text>
        <Text style={styles.emptyStateText}>Level up to unlock powerful abilities!</Text>
      </View>
    );
  }

  return (
    <View>
      <Text style={styles.sectionTitle}>ABILITIES</Text>
      {skills.map((skill) => {
        const unlocked = playerLevel >= skill.unlock_level;
        return (
          <View key={skill.id} style={[styles.skillRow, !unlocked && styles.skillLocked]}>
            <View style={[styles.skillIconWrap, { backgroundColor: unlocked ? `${classColor}20` : '#1a1a1a' }]}>
              <Ionicons
                name={SKILL_ICONS[skill.id] || 'flash'}
                size={24}
                color={unlocked ? classColor : '#444'}
              />
            </View>
            <View style={styles.skillInfo}>
              <Text style={[styles.skillName, !unlocked && { color: '#555' }]}>{skill.name}</Text>
              <View style={styles.skillDetails}>
                {skill.damage_mult && (
                  <Text style={styles.skillStat}>
                    {skill.damage_mult}x DMG
                  </Text>
                )}
                {skill.defense_buff && (
                  <Text style={[styles.skillStat, { color: '#2196f3' }]}>
                    {skill.defense_buff}x DEF
                  </Text>
                )}
                {skill.heal_percent && (
                  <Text style={[styles.skillStat, { color: '#4caf50' }]}>
                    {Math.round(skill.heal_percent * 100)}% Heal
                  </Text>
                )}
                {skill.crit_chance && (
                  <Text style={[styles.skillStat, { color: '#ff9800' }]}>
                    {Math.round(skill.crit_chance * 100)}% Crit
                  </Text>
                )}
                <Text style={styles.skillCost}>{skill.cost} Energy</Text>
              </View>
            </View>
            {!unlocked ? (
              <View style={styles.lockBadge}>
                <Ionicons name="lock-closed" size={14} color="#666" />
                <Text style={styles.lockText}>Lv.{skill.unlock_level}</Text>
              </View>
            ) : (
              <View style={[styles.unlockBadge, { backgroundColor: `${classColor}20` }]}>
                <Ionicons name="checkmark" size={16} color={classColor} />
              </View>
            )}
          </View>
        );
      })}
    </View>
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
});
