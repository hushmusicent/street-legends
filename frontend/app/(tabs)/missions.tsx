import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import { getActiveMissions, cancelMission } from '../../services/api';

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: '#27ae60',
  medium: '#f39c12',
  hard: '#e74c3c',
};

const MISSION_TYPE_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  defeat_monsters: 'skull',
  travel_distance: 'navigate',
  walk_steps: 'footsteps',
  bounty: 'cash',
};

const MISSION_TYPE_LABELS: Record<string, string> = {
  defeat_monsters: 'Defeat Monsters',
  travel_distance: 'Travel Distance',
  walk_steps: 'Walk Steps',
  bounty: 'Bounty Hunt',
};

export default function MissionsTrackerScreen() {
  const { playerId, player } = useGameStore();
  const missionRefreshTrigger = useGameStore((s) => s.missionRefreshTrigger);
  const [missions, setMissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMissions = useCallback(async () => {
    if (!playerId) {
      setLoading(false);
      setRefreshing(false);
      return;
    }
    try {
      const data = await getActiveMissions(playerId);
      setMissions(data);
    } catch (err) {
      console.error('Failed to fetch active missions:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [playerId]);

  useEffect(() => {
    fetchMissions();
  }, [fetchMissions]);

  // Event-driven refresh: re-fetch when battle won, mission accepted/cancelled
  useEffect(() => {
    if (missionRefreshTrigger > 0) {
      fetchMissions();
    }
  }, [missionRefreshTrigger]);

  // Gentle background refresh every 30s as fallback
  useEffect(() => {
    if (!playerId) return;
    const interval = setInterval(() => {
      fetchMissions();
    }, 30000);
    return () => clearInterval(interval);
  }, [playerId, fetchMissions]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchMissions();
  }, [fetchMissions]);

  const handleMissionTap = (missionId: string) => {
    router.push(`/mission/${missionId}`);
  };

  const handleCancel = (mission: any) => {
    Alert.alert(
      'Cancel Mission',
      `Abandon "${mission.title}"? All progress will be lost.`,
      [
        { text: 'Keep', style: 'cancel' },
        {
          text: 'Cancel Mission',
          style: 'destructive',
          onPress: async () => {
            if (!playerId) return;
            try {
              await cancelMission(mission.id, playerId);
              setMissions((prev) => prev.filter((m) => m.id !== mission.id));
              useGameStore.getState().triggerMissionRefresh();
            } catch (err: any) {
              Alert.alert('Error', err?.response?.data?.detail || 'Failed to cancel');
            }
          },
        },
      ]
    );
  };

  const formatTarget = (mission: any) => {
    const target = mission.goal_target || 0;
    if (mission.mission_type === 'travel_distance') {
      return target >= 1000 ? `${(target / 1000).toFixed(1)}km` : `${target}m`;
    } else if (mission.mission_type === 'walk_steps') {
      return `${target.toLocaleString()} steps`;
    } else if (mission.mission_type === 'defeat_monsters') {
      return `${target} monsters`;
    } else if (mission.mission_type === 'bounty') {
      return `${target} ${mission.bounty_enemy || 'targets'}`;
    }
    return `${target}`;
  };

  const getProgress = (mission: any) => {
    const progress = mission.goal_progress || 0;
    const target = mission.goal_target || 1;
    return Math.min(1, progress / target);
  };

  const isComplete = (mission: any) => {
    return (mission.goal_progress || 0) >= (mission.goal_target || 999);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#e74c3c" />
          <Text style={styles.loadingText}>Loading missions...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Ionicons name="document-text" size={28} color="#FBBC04" />
          <Text style={styles.headerTitle}>MISSION LOG</Text>
        </View>
        <View style={styles.headerBadge}>
          <Text style={styles.headerBadgeText}>{missions.length}</Text>
        </View>
      </View>

      {/* Stats Row */}
      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Ionicons name="checkmark-circle" size={16} color="#4caf50" />
          <Text style={styles.statText}>{player?.missions_completed || 0} Completed</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="time" size={16} color="#FBBC04" />
          <Text style={styles.statText}>{missions.length} Active</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="flame" size={16} color="#e74c3c" />
          <Text style={styles.statText}>
            {missions.filter(m => isComplete(m)).length} Ready
          </Text>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#e74c3c"
            colors={['#e74c3c']}
          />
        }
      >
        {missions.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="map-outline" size={64} color="#333" />
            <Text style={styles.emptyTitle}>No Active Missions</Text>
            <Text style={styles.emptySubtitle}>
              Find missions on the map and accept them to track progress here.
            </Text>
            <TouchableOpacity
              style={styles.goToMapBtn}
              onPress={() => router.push('/(tabs)')}
            >
              <Ionicons name="navigate" size={18} color="#fff" />
              <Text style={styles.goToMapText}>GO TO MAP</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            {/* Ready to Claim section */}
            {missions.filter(m => isComplete(m)).length > 0 && (
              <View style={styles.section}>
                <View style={styles.sectionHeader}>
                  <Ionicons name="trophy" size={18} color="#4caf50" />
                  <Text style={[styles.sectionTitle, { color: '#4caf50' }]}>READY TO CLAIM</Text>
                </View>
                {missions
                  .filter(m => isComplete(m))
                  .map(mission => (
                    <MissionCard
                      key={mission.id}
                      mission={mission}
                      onPress={() => handleMissionTap(mission.id)}
                      onCancel={() => handleCancel(mission)}
                      isReady
                    />
                  ))}
              </View>
            )}

            {/* In Progress section */}
            {missions.filter(m => !isComplete(m)).length > 0 && (
              <View style={styles.section}>
                <View style={styles.sectionHeader}>
                  <Ionicons name="hourglass" size={18} color="#FBBC04" />
                  <Text style={[styles.sectionTitle, { color: '#FBBC04' }]}>IN PROGRESS</Text>
                </View>
                {missions
                  .filter(m => !isComplete(m))
                  .map(mission => (
                    <MissionCard
                      key={mission.id}
                      mission={mission}
                      onPress={() => handleMissionTap(mission.id)}
                      onCancel={() => handleCancel(mission)}
                    />
                  ))}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function MissionCard({
  mission,
  onPress,
  onCancel,
  isReady = false,
}: {
  mission: any;
  onPress: () => void;
  onCancel: () => void;
  isReady?: boolean;
}) {
  const progress = mission.goal_progress || 0;
  const target = mission.goal_target || 1;
  const progressPct = Math.min(1, progress / target);
  const diffColor = DIFFICULTY_COLORS[mission.difficulty] || '#f39c12';
  const typeIcon = MISSION_TYPE_ICONS[mission.mission_type] || 'help-circle';
  const typeLabel = MISSION_TYPE_LABELS[mission.mission_type] || mission.mission_type;
  const isBounty = mission.mission_type === 'bounty';

  const formatProgressText = () => {
    if (mission.mission_type === 'travel_distance') {
      const pStr = progress >= 1000 ? `${(progress / 1000).toFixed(1)}km` : `${progress}m`;
      const tStr = target >= 1000 ? `${(target / 1000).toFixed(1)}km` : `${target}m`;
      return `${pStr} / ${tStr}`;
    } else if (mission.mission_type === 'walk_steps') {
      return `${progress.toLocaleString()} / ${target.toLocaleString()} steps`;
    }
    return `${progress} / ${target}`;
  };

  return (
    <TouchableOpacity
      style={[
        styles.missionCard,
        { borderLeftColor: isReady ? '#4caf50' : diffColor },
        isReady && styles.missionCardReady,
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.cardTop}>
        <View style={styles.cardIconWrap}>
          <Text style={styles.cardEmoji}>{isBounty ? '💲' : '☎️'}</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle} numberOfLines={1}>
            {mission.title}
          </Text>
          <View style={styles.cardBadges}>
            <View style={[styles.typeBadge, { backgroundColor: `${diffColor}22` }]}>
              <Ionicons name={typeIcon} size={11} color={diffColor} />
              <Text style={[styles.typeBadgeText, { color: diffColor }]}>{typeLabel}</Text>
            </View>
            <View style={[styles.typeBadge, { backgroundColor: `${diffColor}22` }]}>
              <Text style={[styles.typeBadgeText, { color: diffColor }]}>
                {(mission.difficulty || 'medium').toUpperCase()}
              </Text>
            </View>
          </View>
        </View>
        {isReady ? (
          <View style={styles.readyIndicator}>
            <Ionicons name="checkmark-circle" size={24} color="#4caf50" />
          </View>
        ) : (
          <View style={styles.progressPctWrap}>
            <Text style={styles.progressPctText}>{Math.round(progressPct * 100)}%</Text>
          </View>
        )}
      </View>

      {/* Progress Bar */}
      <View style={styles.cardProgressRow}>
        <View style={styles.cardProgressBg}>
          <View
            style={[
              styles.cardProgressFill,
              {
                width: `${progressPct * 100}%`,
                backgroundColor: isReady ? '#4caf50' : diffColor,
              },
            ]}
          />
        </View>
      </View>
      <Text style={styles.cardProgressText}>{formatProgressText()}</Text>

      {/* Rewards preview + Cancel */}
      <View style={styles.cardBottom}>
        <View style={styles.cardRewards}>
          <View style={styles.cardRewardItem}>
            <Ionicons name="cash" size={13} color="#f39c12" />
            <Text style={styles.cardRewardText}>${mission.rewards?.cash}</Text>
          </View>
          <View style={styles.cardRewardItem}>
            <Ionicons name="star" size={13} color="#3498db" />
            <Text style={styles.cardRewardText}>{mission.rewards?.xp} XP</Text>
          </View>
          {mission.rewards?.reputation > 0 && (
            <View style={styles.cardRewardItem}>
              <Ionicons name="ribbon" size={13} color="#9b59b6" />
              <Text style={styles.cardRewardText}>{mission.rewards.reputation} REP</Text>
            </View>
          )}
        </View>
        <View style={styles.cardActions}>
          {isReady && (
            <View style={styles.claimHint}>
              <Text style={styles.claimHintText}>TAP TO CLAIM</Text>
            </View>
          )}
          <TouchableOpacity style={styles.cancelBtn} onPress={onCancel} activeOpacity={0.7}>
            <Ionicons name="close-circle" size={14} color="#e74c3c" />
            <Text style={styles.cancelBtnText}>CANCEL</Text>
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    color: '#666',
    fontSize: 14,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerTitle: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
  },
  headerBadge: {
    backgroundColor: '#e74c3c',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    minWidth: 28,
    alignItems: 'center',
  },
  headerBadgeText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '800',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statText: {
    color: '#aaa',
    fontSize: 12,
    fontWeight: '700',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    gap: 12,
  },
  emptyTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '800',
    marginTop: 8,
  },
  emptySubtitle: {
    color: '#666',
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 40,
    lineHeight: 20,
  },
  goToMapBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#e74c3c',
    borderRadius: 12,
    paddingHorizontal: 24,
    paddingVertical: 12,
    marginTop: 12,
  },
  goToMapText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 1,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 2,
  },
  // Mission Card
  missionCard: {
    backgroundColor: '#141414',
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    borderLeftWidth: 4,
  },
  missionCardReady: {
    backgroundColor: '#0f1a0f',
    borderWidth: 1,
    borderColor: '#4caf5033',
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  cardIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: '#1a1a2e',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardEmoji: {
    fontSize: 22,
  },
  cardInfo: {
    flex: 1,
  },
  cardTitle: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '800',
  },
  cardBadges: {
    flexDirection: 'row',
    gap: 6,
    marginTop: 4,
  },
  typeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  typeBadgeText: {
    fontSize: 10,
    fontWeight: '800',
  },
  readyIndicator: {
    padding: 4,
  },
  progressPctWrap: {
    padding: 4,
  },
  progressPctText: {
    color: '#aaa',
    fontSize: 14,
    fontWeight: '800',
  },
  cardProgressRow: {
    marginBottom: 4,
  },
  cardProgressBg: {
    height: 8,
    backgroundColor: '#222',
    borderRadius: 4,
    overflow: 'hidden',
  },
  cardProgressFill: {
    height: 8,
    borderRadius: 4,
  },
  cardProgressText: {
    color: '#888',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 8,
  },
  cardRewards: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  cardBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardRewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  cardRewardText: {
    color: '#999',
    fontSize: 12,
    fontWeight: '700',
  },
  claimHint: {
    marginLeft: 'auto',
    backgroundColor: '#4caf5022',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  claimHintText: {
    color: '#4caf50',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1,
  },
  cancelBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(231, 76, 60, 0.12)',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.25)',
  },
  cancelBtnText: {
    color: '#e74c3c',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1,
  },
});
