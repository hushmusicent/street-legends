import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import { completeMission, getPlayer } from '../../services/api';
import api from '../../services/api';
import { GameButton } from '../../components/GameButton';
import { Mission } from '../../types/game';

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: '#27ae60',
  medium: '#f39c12',
  hard: '#e74c3c',
};

export default function MissionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { playerId, nearbyMissions, setPlayer, setCurrentMission } = useGameStore();
  const removeMission = useGameStore((s) => s.removeMission);
  const [mission, setMission] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [rewards, setRewards] = useState<any>(null);
  const [levelUp, setLevelUp] = useState(false);
  const [progress, setProgress] = useState(0);
  const [target, setTarget] = useState(0);

  useEffect(() => {
    const found = nearbyMissions.find((m) => m.id === id);
    if (found) {
      setMission(found);
      setCurrentMission(found);
      setProgress(found.goal_progress || 0);
      setTarget(found.goal_target || 0);
      setAccepted(!!found.accepted_by);
    }
    setLoading(false);
  }, [id, nearbyMissions]);

  const handleAccept = async () => {
    if (!id || !playerId) return;
    setAccepting(true);
    try {
      await api.post(`/missions/${id}/accept?player_id=${playerId}`);
      setAccepted(true);
      Alert.alert('Mission Accepted!', 'Go out and complete the objective!');
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail || 'Failed to accept mission');
    } finally {
      setAccepting(false);
    }
  };

  const handleComplete = async () => {
    if (!id || !playerId || !mission) return;
    try {
      setCompleting(true);
      const result = await completeMission(id, playerId);
      setRewards(result.rewards);
      setLevelUp(result.level_up);
      setCompleted(true);
      const updatedPlayer = await getPlayer(playerId);
      setPlayer(updatedPlayer);
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail || 'Cannot complete yet');
    } finally {
      setCompleting(false);
    }
  };

  const handleExit = () => {
    if (completed && id) {
      removeMission(id);
    }
    setCurrentMission(null);
    router.back();
  };

  const goalProgress = target > 0 ? Math.min(1, progress / target) : 0;
  const goalComplete = progress >= target && target > 0;

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#e74c3c" />
      </SafeAreaView>
    );
  }

  if (!mission) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Ionicons name="alert-circle" size={64} color="#e74c3c" />
          <Text style={styles.errorText}>Mission not found</Text>
          <GameButton title="BACK" onPress={() => router.back()} />
        </View>
      </SafeAreaView>
    );
  }

  const MISSION_TYPE_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
    defeat_monsters: 'skull',
    travel_distance: 'navigate',
    walk_steps: 'footsteps',
    bounty: 'skull',
  };

  const MISSION_TYPE_LABELS: Record<string, string> = {
    defeat_monsters: 'Defeat Monsters',
    travel_distance: 'Travel Distance',
    walk_steps: 'Walk Steps',
    bounty: 'Bounty Contract',
  };

  const isBounty = mission.mission_type === 'bounty';
  const diffColor = DIFFICULTY_COLORS[mission.difficulty] || '#f39c12';
  const typeIcon = MISSION_TYPE_ICONS[mission.mission_type] || 'help-circle';
  const typeLabel = MISSION_TYPE_LABELS[mission.mission_type] || mission.mission_type;

  // Format target display
  let targetDisplay = `${target}`;
  if (mission.mission_type === 'travel_distance') {
    targetDisplay = target >= 1000 ? `${(target / 1000).toFixed(1)}km` : `${target}m`;
  } else if (mission.mission_type === 'walk_steps') {
    targetDisplay = `${target.toLocaleString()} steps`;
  } else if (mission.mission_type === 'defeat_monsters') {
    targetDisplay = `${target} monsters`;
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header - Phone Booth or Bounty */}
        <View style={styles.phoneBoothHeader}>
          <View style={[styles.phoneIcon, isBounty && { borderColor: '#4CAF50', backgroundColor: '#0a1a0a' }]}>
            <Text style={styles.phoneEmoji}>{isBounty ? '💲' : '☎️'}</Text>
          </View>
          <Text style={[styles.phoneLabel, isBounty && { color: '#4CAF50' }]}>
            {isBounty ? 'BOUNTY CONTRACT' : 'PHONE BOOTH'}
          </Text>
        </View>

        {/* Mission Card */}
        <View style={[styles.missionCard, { borderTopColor: diffColor }]}>
          <View style={styles.titleRow}>
            <Ionicons name={typeIcon} size={24} color={diffColor} />
            <View style={styles.titleInfo}>
              <Text style={styles.missionTitle}>{mission.title}</Text>
              <View style={styles.badges}>
                <View style={[styles.badge, { backgroundColor: `${diffColor}22` }]}>
                  <Text style={[styles.badgeText, { color: diffColor }]}>
                    {(mission.difficulty || 'medium').toUpperCase()}
                  </Text>
                </View>
                <View style={[styles.badge, { backgroundColor: '#1a1a2e' }]}>
                  <Text style={[styles.badgeText, { color: '#aaa' }]}>{typeLabel}</Text>
                </View>
              </View>
            </View>
          </View>

          <Text style={styles.dialogue}>"{mission.dialogue}"</Text>

          {/* Objective */}
          <View style={styles.objectiveBox}>
            <Text style={styles.objectiveLabel}>OBJECTIVE</Text>
            <Text style={styles.objectiveText}>{mission.description}</Text>
          </View>

          {/* Goal Progress */}
          {accepted && !completed && (
            <View style={styles.progressSection}>
              <Text style={styles.progressLabel}>PROGRESS</Text>
              <View style={styles.progressRow}>
                <View style={styles.progressBarBg}>
                  <View
                    style={[
                      styles.progressBarFill,
                      { width: `${goalProgress * 100}%`, backgroundColor: goalComplete ? '#4caf50' : diffColor },
                    ]}
                  />
                </View>
                <Text style={[styles.progressText, goalComplete && { color: '#4caf50' }]}>
                  {progress}/{target}
                </Text>
              </View>
              {goalComplete && (
                <View style={styles.completeReady}>
                  <Ionicons name="checkmark-circle" size={18} color="#4caf50" />
                  <Text style={styles.completeReadyText}>Goal reached! Claim your reward.</Text>
                </View>
              )}
              {!goalComplete && (
                <Text style={styles.progressHint}>
                  {mission.mission_type === 'defeat_monsters'
                    ? 'Defeat monsters on the map to make progress.'
                    : mission.mission_type === 'travel_distance'
                    ? 'Move around in the real world to cover distance.'
                    : 'Walk to accumulate steps.'}
                </Text>
              )}
            </View>
          )}

          {/* Rewards */}
          <View style={styles.rewardsSection}>
            <Text style={styles.rewardsLabel}>REWARDS</Text>
            <View style={styles.rewardsRow}>
              <View style={styles.rewardItem}>
                <Ionicons name="cash" size={20} color="#f39c12" />
                <Text style={styles.rewardValue}>${mission.rewards?.cash}</Text>
              </View>
              <View style={styles.rewardItem}>
                <Ionicons name="star" size={20} color="#3498db" />
                <Text style={styles.rewardValue}>{mission.rewards?.xp} XP</Text>
              </View>
              <View style={styles.rewardItem}>
                <Ionicons name="ribbon" size={20} color="#9b59b6" />
                <Text style={styles.rewardValue}>{mission.rewards?.reputation} REP</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Completed State */}
        {completed && rewards && (
          <View style={styles.completedCard}>
            <Ionicons name="trophy" size={48} color="#f39c12" />
            <Text style={styles.completedTitle}>MISSION COMPLETE!</Text>
            {levelUp && <Text style={styles.levelUpText}>LEVEL UP!</Text>}
            <View style={styles.rewardsRow}>
              <View style={styles.rewardItem}>
                <Ionicons name="cash" size={20} color="#f39c12" />
                <Text style={styles.rewardValue}>+${rewards.cash}</Text>
              </View>
              <View style={styles.rewardItem}>
                <Ionicons name="star" size={20} color="#3498db" />
                <Text style={styles.rewardValue}>+{rewards.xp} XP</Text>
              </View>
            </View>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actions}>
          {completed ? (
            <GameButton title="BACK TO MAP" onPress={handleExit} />
          ) : !accepted ? (
            <>
              <GameButton
                title={accepting ? 'ACCEPTING...' : 'ACCEPT MISSION'}
                onPress={handleAccept}
                disabled={accepting}
              />
              <TouchableOpacity style={styles.declineBtn} onPress={handleExit}>
                <Text style={styles.declineBtnText}>DECLINE</Text>
              </TouchableOpacity>
            </>
          ) : goalComplete ? (
            <>
              <GameButton
                title={completing ? 'CLAIMING...' : 'CLAIM REWARD'}
                onPress={handleComplete}
                disabled={completing}
              />
              <TouchableOpacity style={styles.declineBtn} onPress={handleExit}>
                <Text style={styles.declineBtnText}>BACK TO MAP</Text>
              </TouchableOpacity>
            </>
          ) : (
            <TouchableOpacity style={styles.declineBtn} onPress={handleExit}>
              <Text style={styles.declineBtnText}>BACK TO MAP</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  scrollContent: {
    padding: 16,
  },
  errorText: {
    color: '#fff',
    fontSize: 18,
    marginVertical: 16,
  },
  phoneBoothHeader: {
    alignItems: 'center',
    marginBottom: 20,
  },
  phoneIcon: {
    width: 80,
    height: 80,
    borderRadius: 20,
    backgroundColor: '#1a1a2e',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#FBBC04',
    marginBottom: 10,
  },
  phoneEmoji: {
    fontSize: 40,
  },
  phoneLabel: {
    color: '#FBBC04',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 3,
  },
  missionCard: {
    backgroundColor: '#141414',
    borderRadius: 16,
    padding: 20,
    borderTopWidth: 4,
    marginBottom: 16,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  titleInfo: {
    flex: 1,
  },
  missionTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
  },
  badges: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 6,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '800',
  },
  dialogue: {
    color: '#aaa',
    fontSize: 14,
    fontStyle: 'italic',
    marginBottom: 16,
    lineHeight: 20,
  },
  objectiveBox: {
    backgroundColor: '#0d0d1a',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    borderLeftWidth: 3,
    borderLeftColor: '#FBBC04',
  },
  objectiveLabel: {
    color: '#FBBC04',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 4,
  },
  objectiveText: {
    color: '#ddd',
    fontSize: 14,
    fontWeight: '600',
  },
  progressSection: {
    marginBottom: 16,
  },
  progressLabel: {
    color: '#aaa',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 8,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  progressBarBg: {
    flex: 1,
    height: 10,
    backgroundColor: '#222',
    borderRadius: 5,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: 10,
    borderRadius: 5,
  },
  progressText: {
    color: '#aaa',
    fontSize: 13,
    fontWeight: '800',
    minWidth: 60,
    textAlign: 'right',
  },
  completeReady: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  completeReadyText: {
    color: '#4caf50',
    fontSize: 13,
    fontWeight: '700',
  },
  progressHint: {
    color: '#555',
    fontSize: 12,
    marginTop: 6,
  },
  rewardsSection: {
    marginTop: 4,
  },
  rewardsLabel: {
    color: '#aaa',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 8,
  },
  rewardsRow: {
    flexDirection: 'row',
    gap: 16,
  },
  rewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  rewardValue: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  completedCard: {
    backgroundColor: '#1a2e1a',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#4caf50',
  },
  completedTitle: {
    color: '#4caf50',
    fontSize: 22,
    fontWeight: '900',
    marginTop: 8,
    letterSpacing: 2,
  },
  levelUpText: {
    color: '#f39c12',
    fontSize: 18,
    fontWeight: '900',
    marginTop: 4,
  },
  actions: {
    gap: 12,
    marginTop: 8,
  },
  declineBtn: {
    alignItems: 'center',
    padding: 14,
  },
  declineBtnText: {
    color: '#888',
    fontSize: 14,
    fontWeight: '700',
  },
});
