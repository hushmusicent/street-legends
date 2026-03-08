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
import { GameButton } from '../../components/GameButton';
import { Mission } from '../../types/game';

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: '#27ae60',
  medium: '#f39c12',
  hard: '#e74c3c',
};

const MISSION_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  combat: 'flash',
  delivery: 'car',
  investigation: 'search',
  heist: 'diamond',
};

export default function MissionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { playerId, nearbyMissions, setPlayer, setCurrentMission } = useGameStore();
  const [mission, setMission] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [rewards, setRewards] = useState<any>(null);
  const [levelUp, setLevelUp] = useState(false);

  useEffect(() => {
    // Find mission from nearby missions
    const found = nearbyMissions.find((m) => m.id === id);
    if (found) {
      setMission(found);
      setCurrentMission(found);
    }
    setLoading(false);
  }, [id, nearbyMissions]);

  const handleComplete = async () => {
    if (!id || !playerId || !mission) return;

    try {
      setCompleting(true);
      const result = await completeMission(id, playerId);
      setRewards(result.rewards);
      setLevelUp(result.level_up);
      setCompleted(true);

      // Refresh player data
      const playerData = await getPlayer(playerId);
      setPlayer(playerData);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to complete mission');
    } finally {
      setCompleting(false);
    }
  };

  const handleExit = () => {
    setCurrentMission(null);
    router.back();
  };

  if (loading || !mission) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
        <Text style={styles.loadingText}>Loading mission...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Close Button */}
        <TouchableOpacity style={styles.closeButton} onPress={handleExit}>
          <Ionicons name="close" size={28} color="#888" />
        </TouchableOpacity>

        {/* Mission Header */}
        <View style={styles.header}>
          <View
            style={[
              styles.missionIcon,
              { backgroundColor: `${DIFFICULTY_COLORS[mission.difficulty]}30` },
            ]}
          >
            <Ionicons
              name={MISSION_ICONS[mission.mission_type] || 'briefcase'}
              size={40}
              color={DIFFICULTY_COLORS[mission.difficulty]}
            />
          </View>
          <Text style={styles.missionType}>{mission.mission_type.toUpperCase()}</Text>
          <Text style={styles.missionTitle}>{mission.title}</Text>
          <View style={styles.difficultyBadge}>
            <Text
              style={[styles.difficultyText, { color: DIFFICULTY_COLORS[mission.difficulty] }]}
            >
              {mission.difficulty.toUpperCase()}
            </Text>
          </View>
        </View>

        {/* Dialogue */}
        <View style={styles.dialogueBox}>
          <Ionicons name="chatbubble" size={20} color="#f39c12" />
          <Text style={styles.dialogueText}>"{mission.dialogue}"</Text>
        </View>

        {/* Description */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>BRIEFING</Text>
          <Text style={styles.description}>{mission.description}</Text>
        </View>

        {/* Objectives */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>OBJECTIVES</Text>
          {mission.objectives.map((objective, index) => (
            <View key={index} style={styles.objectiveItem}>
              <View style={styles.objectiveCheckbox}>
                {completed ? (
                  <Ionicons name="checkmark" size={16} color="#27ae60" />
                ) : (
                  <View style={styles.emptyCheckbox} />
                )}
              </View>
              <Text style={[styles.objectiveText, completed && styles.completedObjective]}>
                {objective}
              </Text>
            </View>
          ))}
        </View>

        {/* Rewards */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>REWARDS</Text>
          <View style={styles.rewardsGrid}>
            <View style={styles.rewardCard}>
              <Ionicons name="cash" size={28} color="#f39c12" />
              <Text style={styles.rewardValue}>${mission.rewards.cash}</Text>
              <Text style={styles.rewardLabel}>Cash</Text>
            </View>
            <View style={styles.rewardCard}>
              <Ionicons name="star" size={28} color="#3498db" />
              <Text style={styles.rewardValue}>{mission.rewards.xp}</Text>
              <Text style={styles.rewardLabel}>XP</Text>
            </View>
            {mission.rewards.reputation && (
              <View style={styles.rewardCard}>
                <Ionicons name="trending-up" size={28} color="#9b59b6" />
                <Text style={styles.rewardValue}>{mission.rewards.reputation}</Text>
                <Text style={styles.rewardLabel}>Rep</Text>
              </View>
            )}
          </View>
        </View>

        {/* Requirements */}
        <View style={styles.requirementsRow}>
          <View style={styles.requirementItem}>
            <Ionicons name="person" size={16} color="#888" />
            <Text style={styles.requirementText}>Level {mission.level_requirement}+</Text>
          </View>
          <View style={styles.requirementItem}>
            <Ionicons name="time" size={16} color="#888" />
            <Text style={styles.requirementText}>{mission.time_limit_minutes} min</Text>
          </View>
        </View>

        {/* Action Button */}
        {!completed ? (
          <GameButton
            title="COMPLETE MISSION"
            onPress={handleComplete}
            variant="success"
            icon="checkmark-circle"
            size="large"
            loading={completing}
            style={styles.actionButton}
          />
        ) : (
          <View style={styles.completedContainer}>
            <Ionicons name="checkmark-circle" size={64} color="#27ae60" />
            <Text style={styles.completedText}>MISSION COMPLETE!</Text>
            {levelUp && (
              <View style={styles.levelUpBadge}>
                <Ionicons name="arrow-up" size={20} color="#f39c12" />
                <Text style={styles.levelUpText}>LEVEL UP!</Text>
              </View>
            )}
            {rewards && (
              <View style={styles.earnedRewards}>
                <Text style={styles.earnedTitle}>You earned:</Text>
                <Text style={styles.earnedText}>
                  ${rewards.cash} Cash | {rewards.xp} XP
                  {rewards.reputation ? ` | ${rewards.reputation} Rep` : ''}
                </Text>
              </View>
            )}
            <GameButton
              title="BACK TO MAP"
              onPress={handleExit}
              variant="primary"
              icon="map"
              style={styles.backButton}
            />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
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
    backgroundColor: '#0a0a0a',
  },
  loadingText: {
    color: '#888',
    marginTop: 16,
  },
  scrollContent: {
    padding: 24,
  },
  closeButton: {
    position: 'absolute',
    top: 0,
    right: 0,
    padding: 8,
    zIndex: 1,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  missionIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  missionType: {
    color: '#888',
    fontSize: 12,
    letterSpacing: 2,
  },
  missionTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 8,
  },
  difficultyBadge: {
    marginTop: 12,
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  difficultyText: {
    fontSize: 12,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  dialogueBox: {
    backgroundColor: 'rgba(243, 156, 18, 0.1)',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: '#f39c12',
  },
  dialogueText: {
    color: '#fff',
    fontStyle: 'italic',
    fontSize: 15,
    lineHeight: 22,
    marginLeft: 12,
    flex: 1,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 12,
  },
  description: {
    color: '#aaa',
    fontSize: 15,
    lineHeight: 22,
  },
  objectiveItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    padding: 14,
    borderRadius: 8,
    marginBottom: 8,
  },
  objectiveCheckbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#444',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  emptyCheckbox: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#333',
  },
  objectiveText: {
    color: '#fff',
    fontSize: 14,
    flex: 1,
  },
  completedObjective: {
    textDecorationLine: 'line-through',
    color: '#666',
  },
  rewardsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  rewardCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    minWidth: 100,
  },
  rewardValue: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 8,
  },
  rewardLabel: {
    color: '#666',
    fontSize: 11,
    marginTop: 4,
  },
  requirementsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 24,
  },
  requirementItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
  },
  requirementText: {
    color: '#888',
    marginLeft: 6,
    fontSize: 13,
  },
  actionButton: {
    marginTop: 16,
  },
  completedContainer: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  completedText: {
    color: '#27ae60',
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 16,
    letterSpacing: 2,
  },
  levelUpBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(243, 156, 18, 0.2)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginTop: 16,
  },
  levelUpText: {
    color: '#f39c12',
    fontWeight: 'bold',
    marginLeft: 8,
  },
  earnedRewards: {
    marginTop: 24,
    alignItems: 'center',
  },
  earnedTitle: {
    color: '#888',
    fontSize: 12,
  },
  earnedText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginTop: 4,
  },
  backButton: {
    marginTop: 32,
    minWidth: 200,
  },
});
