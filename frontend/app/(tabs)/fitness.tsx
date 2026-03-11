import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Pedometer } from 'expo-sensors';
import { useGameStore } from '../../stores/gameStore';
import { getFitnessData, updateSteps, claimStepGoal } from '../../services/api';

const GOAL_COLORS = ['#3498db', '#f39c12', '#e74c3c'];
const GOAL_ICONS: Array<'walk' | 'bicycle' | 'rocket'> = ['walk', 'bicycle', 'rocket'];

export default function FitnessScreen() {
  const { playerId } = useGameStore();
  const [steps, setSteps] = useState(0);
  const [fitnessData, setFitnessData] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [claiming, setClaiming] = useState<number | null>(null);
  const [pedometerAvailable, setPedometerAvailable] = useState(false);
  const subscriptionRef = useRef<any>(null);
  const baseStepsRef = useRef(0);

  const loadFitnessData = useCallback(async () => {
    if (!playerId) return;
    try {
      const data = await getFitnessData(playerId);
      setFitnessData(data);
      if (data.steps > steps) {
        setSteps(data.steps);
        baseStepsRef.current = data.steps;
      }
    } catch (err) {
      console.log('Error loading fitness:', err);
    }
  }, [playerId]);

  useEffect(() => {
    loadFitnessData();
  }, [loadFitnessData]);

  // Setup pedometer
  useEffect(() => {
    let sub: any = null;

    const setup = async () => {
      try {
        // MUST request permissions first (especially on Android)
        const { status } = await Pedometer.requestPermissionsAsync();
        if (status !== 'granted') {
          console.log('Pedometer permission denied:', status);
          setPedometerAvailable(false);
          // Still load backend data
          await loadFitnessData();
          return;
        }

        const available = await Pedometer.isAvailableAsync();
        setPedometerAvailable(available);

        if (available) {
          // Get steps since midnight
          const now = new Date();
          const midnight = new Date(now);
          midnight.setHours(0, 0, 0, 0);

          try {
            const result = await Pedometer.getStepCountAsync(midnight, now);
            if (result && result.steps > 0) {
              setSteps(result.steps);
              baseStepsRef.current = result.steps;
              if (playerId) {
                await updateSteps(playerId, result.steps);
              }
            }
          } catch (e) {
            console.log('Pedometer history not available:', e);
          }

          // Watch for new steps in real time
          sub = Pedometer.watchStepCount((result) => {
            const newSteps = baseStepsRef.current + result.steps;
            setSteps(newSteps);
            if (playerId) {
              updateSteps(playerId, newSteps).catch(() => {});
            }
          });
          subscriptionRef.current = sub;
        } else {
          // Pedometer not available, load from backend
          await loadFitnessData();
        }
      } catch (err) {
        console.log('Pedometer setup error:', err);
        setPedometerAvailable(false);
        await loadFitnessData();
      }
    };

    setup();

    return () => {
      if (sub) sub.remove();
    };
  }, [playerId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadFitnessData();
    setRefreshing(false);
  };

  const handleClaim = async (goalSteps: number) => {
    if (!playerId || claiming) return;
    setClaiming(goalSteps);
    try {
      const result = await claimStepGoal(playerId, goalSteps);
      Alert.alert('Reward Claimed!', result.message);
      await loadFitnessData();
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail || 'Failed to claim reward');
    } finally {
      setClaiming(null);
    }
  };

  const calories = Math.round(steps * 0.04 * 10) / 10;
  const distanceKm = Math.round(steps * 0.00078 * 100) / 100;
  const goals = fitnessData?.goals || [
    { goal: 3000, label: 'Walker', description: 'Earn 200 XP' },
    { goal: 6000, label: 'Jogger', description: 'Earn 500 XP' },
    { goal: 10000, label: 'Runner', description: 'Earn 1000 XP + Attack Boost' },
  ];
  const claimed = fitnessData?.claimed_goals || [];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#e74c3c" />}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>FITNESS TRACKER</Text>
          <Text style={styles.headerDate}>
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
          </Text>
        </View>

        {/* Steps Ring */}
        <View style={styles.stepsCard}>
          <View style={styles.stepsRing}>
            <View style={styles.stepsInner}>
              <Ionicons name="footsteps" size={32} color="#e74c3c" />
              <Text style={styles.stepsCount}>{steps.toLocaleString()}</Text>
              <Text style={styles.stepsLabel}>STEPS</Text>
            </View>
            {/* Progress ring visual */}
            <View style={[styles.ringProgress, { transform: [{ rotate: `${Math.min(360, (steps / 10000) * 360)}deg` }] }]} />
          </View>

          {!pedometerAvailable && Platform.OS !== 'web' && (
            <View style={styles.pedWarning}>
              <Ionicons name="warning" size={14} color="#f39c12" />
              <Text style={styles.pedWarningText}>Step tracking needs Physical Activity permission. Check your device Settings &gt; Apps &gt; Permissions &gt; Physical Activity.</Text>
            </View>
          )}
          {Platform.OS === 'web' && (
            <View style={styles.pedWarning}>
              <Ionicons name="phone-portrait" size={14} color="#3498db" />
              <Text style={styles.pedWarningText}>Open on your phone via Expo Go to track real steps</Text>
            </View>
          )}
        </View>

        {/* Stats Row */}
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Ionicons name="flame" size={28} color="#ff6b35" />
            <Text style={styles.statValue}>{calories}</Text>
            <Text style={styles.statLabel}>Calories</Text>
          </View>
          <View style={styles.statCard}>
            <Ionicons name="navigate" size={28} color="#3498db" />
            <Text style={styles.statValue}>{distanceKm}</Text>
            <Text style={styles.statLabel}>km</Text>
          </View>
          <View style={styles.statCard}>
            <Ionicons name="time" size={28} color="#9b59b6" />
            <Text style={styles.statValue}>{Math.round(steps / 100)}</Text>
            <Text style={styles.statLabel}>min Active</Text>
          </View>
        </View>

        {/* Step Goals */}
        <Text style={styles.sectionTitle}>DAILY GOALS</Text>
        {goals.map((goal: any, idx: number) => {
          const progress = Math.min(1, steps / goal.goal);
          const isReached = steps >= goal.goal;
          const isClaimed = claimed.includes(goal.goal);
          const color = GOAL_COLORS[idx] || '#e74c3c';
          const icon = GOAL_ICONS[idx] || 'walk';

          return (
            <View key={goal.goal} style={[styles.goalCard, isClaimed && styles.goalClaimed]}>
              <View style={styles.goalTop}>
                <View style={[styles.goalIcon, { backgroundColor: `${color}22` }]}>
                  <Ionicons name={icon} size={24} color={color} />
                </View>
                <View style={styles.goalInfo}>
                  <Text style={styles.goalLabel}>{goal.label}</Text>
                  <Text style={styles.goalDesc}>{goal.description}</Text>
                  <Text style={styles.goalSteps}>
                    {Math.min(steps, goal.goal).toLocaleString()} / {goal.goal.toLocaleString()} steps
                  </Text>
                </View>
                {isClaimed ? (
                  <View style={styles.claimedBadge}>
                    <Ionicons name="checkmark-circle" size={20} color="#4caf50" />
                    <Text style={styles.claimedText}>Done</Text>
                  </View>
                ) : isReached ? (
                  <TouchableOpacity
                    style={[styles.claimBtn, { backgroundColor: color }]}
                    onPress={() => handleClaim(goal.goal)}
                    disabled={claiming === goal.goal}
                  >
                    <Text style={styles.claimBtnText}>
                      {claiming === goal.goal ? '...' : 'CLAIM'}
                    </Text>
                  </TouchableOpacity>
                ) : (
                  <View style={styles.lockedBadge}>
                    <Ionicons name="lock-closed" size={16} color="#555" />
                  </View>
                )}
              </View>
              {/* Progress bar */}
              <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${progress * 100}%`, backgroundColor: color }]} />
              </View>
            </View>
          );
        })}

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    alignItems: 'center',
    marginBottom: 20,
  },
  headerTitle: {
    color: '#e74c3c',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
  },
  headerDate: {
    color: '#777',
    fontSize: 13,
    marginTop: 4,
  },
  stepsCard: {
    alignItems: 'center',
    marginBottom: 24,
  },
  stepsRing: {
    width: 180,
    height: 180,
    borderRadius: 90,
    borderWidth: 6,
    borderColor: '#222',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  stepsInner: {
    alignItems: 'center',
  },
  stepsCount: {
    color: '#fff',
    fontSize: 40,
    fontWeight: '900',
    marginTop: 4,
  },
  stepsLabel: {
    color: '#888',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 2,
  },
  ringProgress: {
    position: 'absolute',
    top: -6,
    left: 84,
    width: 6,
    height: 12,
    backgroundColor: '#e74c3c',
    borderRadius: 3,
  },
  pedWarning: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  pedWarningText: {
    color: '#888',
    fontSize: 12,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#141414',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#1e1e1e',
  },
  statValue: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '800',
    marginTop: 6,
  },
  statLabel: {
    color: '#666',
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
  },
  sectionTitle: {
    color: '#aaa',
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: 12,
  },
  goalCard: {
    backgroundColor: '#141414',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#1e1e1e',
  },
  goalClaimed: {
    opacity: 0.6,
  },
  goalTop: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  goalIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  goalInfo: {
    flex: 1,
  },
  goalLabel: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '800',
  },
  goalDesc: {
    color: '#aaa',
    fontSize: 12,
    marginTop: 2,
  },
  goalSteps: {
    color: '#666',
    fontSize: 11,
    marginTop: 2,
  },
  claimBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 10,
  },
  claimBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '900',
  },
  claimedBadge: {
    alignItems: 'center',
  },
  claimedText: {
    color: '#4caf50',
    fontSize: 10,
    fontWeight: '700',
    marginTop: 2,
  },
  lockedBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  progressBg: {
    height: 6,
    backgroundColor: '#222',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: 6,
    borderRadius: 3,
  },
});
