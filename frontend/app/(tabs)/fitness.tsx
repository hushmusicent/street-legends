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
  Linking,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Pedometer } from 'expo-sensors';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useGameStore } from '../../stores/gameStore';
import { getFitnessData, updateSteps, claimStepGoal, syncTravelDistance } from '../../services/api';
import { showGameToast } from '../../components/GameToast';

const GOAL_COLORS = ['#3498db', '#f39c12', '#e74c3c'];
const GOAL_ICONS: Array<'walk' | 'bicycle' | 'rocket'> = ['walk', 'bicycle', 'rocket'];
const METERS_PER_STEP = 0.762; // average step length
const UNSYNCED_DISTANCE_KEY = 'fitness_unsynced_distance';

// Haversine distance in meters
function getDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371e3;
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dp = ((lat2 - lat1) * Math.PI) / 180;
  const dl = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Format distance: meters when under 1km, km otherwise
function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)}m`;
  }
  return `${(meters / 1000).toFixed(2)}km`;
}

export default function FitnessScreen() {
  const { playerId } = useGameStore();
  const triggerMissionRefresh = useGameStore((s) => s.triggerMissionRefresh);
  const [steps, setSteps] = useState(0);
  const [fitnessData, setFitnessData] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [claiming, setClaiming] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [pedometerAvailable, setPedometerAvailable] = useState(false);
  const [trackingMode, setTrackingMode] = useState<'pedometer' | 'gps' | 'none'>('none');
  const [permStatus, setPermStatus] = useState<string>('checking');
  const [unsyncedDistance, setUnsyncedDistance] = useState(0); // in meters
  const subscriptionRef = useRef<any>(null);
  const baseStepsRef = useRef(0);
  const lastStepsRef = useRef(0); // Track steps at last sync to calculate delta
  const lastLocationRef = useRef<{ lat: number; lng: number } | null>(null);
  const gpsStepsRef = useRef(0);
  const locationSubRef = useRef<any>(null);

  // Load unsynced distance from storage on mount
  useEffect(() => {
    const loadUnsyncedDistance = async () => {
      try {
        const stored = await AsyncStorage.getItem(UNSYNCED_DISTANCE_KEY);
        if (stored) {
          setUnsyncedDistance(parseInt(stored, 10) || 0);
        }
      } catch (e) {
        console.log('Error loading unsynced distance:', e);
      }
    };
    loadUnsyncedDistance();
  }, []);

  // Save unsynced distance when it changes
  useEffect(() => {
    const saveUnsyncedDistance = async () => {
      try {
        await AsyncStorage.setItem(UNSYNCED_DISTANCE_KEY, unsyncedDistance.toString());
      } catch (e) {
        console.log('Error saving unsynced distance:', e);
      }
    };
    saveUnsyncedDistance();
  }, [unsyncedDistance]);

  const loadFitnessData = useCallback(async () => {
    if (!playerId) return;
    try {
      const data = await getFitnessData(playerId);
      setFitnessData(data);
      if (data.steps > steps) {
        setSteps(data.steps);
        baseStepsRef.current = data.steps;
        gpsStepsRef.current = data.steps;
      }
    } catch (err) {
      console.log('Error loading fitness:', err);
    }
  }, [playerId]);

  useEffect(() => {
    loadFitnessData();
  }, [loadFitnessData]);

  // Try pedometer first, fall back to GPS tracking
  useEffect(() => {
    let pedSub: any = null;
    let locSub: any = null;

    const setupPedometer = async (): Promise<boolean> => {
      try {
        const { status } = await Pedometer.requestPermissionsAsync();
        if (status !== 'granted') {
          setPermStatus('denied');
          return false;
        }
        const available = await Pedometer.isAvailableAsync();
        if (!available) {
          setPermStatus('unavailable');
          return false;
        }

        setPedometerAvailable(true);
        setTrackingMode('pedometer');
        setPermStatus('granted');

        // Get today's steps
        const now = new Date();
        const midnight = new Date(now);
        midnight.setHours(0, 0, 0, 0);
        try {
          const result = await Pedometer.getStepCountAsync(midnight, now);
          if (result && result.steps > 0) {
            setSteps(result.steps);
            baseStepsRef.current = result.steps;
            if (playerId) await updateSteps(playerId, result.steps);
          }
        } catch (e) {
          console.log('Step history unavailable:', e);
        }

        pedSub = Pedometer.watchStepCount(async (result) => {
          const newSteps = baseStepsRef.current + result.steps;
          const stepDelta = newSteps - lastStepsRef.current;
          
          // Accumulate unsynced distance (step delta * meters per step)
          if (stepDelta > 0) {
            const distanceDelta = Math.round(stepDelta * METERS_PER_STEP);
            setUnsyncedDistance(prev => prev + distanceDelta);
            lastStepsRef.current = newSteps;
          }
          
          setSteps(newSteps);
          if (playerId) {
            try {
              await updateSteps(playerId, newSteps);
            } catch (e) {
              console.log('Failed to sync steps:', e);
            }
          }
        });
        subscriptionRef.current = pedSub;
        return true;
      } catch {
        return false;
      }
    };

    const setupGPSTracking = async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          setTrackingMode('none');
          setPermStatus('no-location');
          return;
        }

        setTrackingMode('gps');
        setPermStatus('gps-active');

        // Get initial position
        const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
        lastLocationRef.current = { lat: loc.coords.latitude, lng: loc.coords.longitude };

        // Watch location changes to estimate steps from distance
        locSub = await Location.watchPositionAsync(
          { accuracy: Location.Accuracy.High, distanceInterval: 5, timeInterval: 3000 },
          async (newLoc) => {
            if (lastLocationRef.current) {
              const dist = getDistance(
                lastLocationRef.current.lat, lastLocationRef.current.lng,
                newLoc.coords.latitude, newLoc.coords.longitude
              );
              if (dist > 2 && dist < 100) { // filter noise (2m min, 100m max per update)
                const newStepsDelta = Math.round(dist / METERS_PER_STEP);
                gpsStepsRef.current += newStepsDelta;
                setSteps(gpsStepsRef.current);
                
                // Accumulate unsynced distance
                setUnsyncedDistance(prev => prev + Math.round(dist));
                
                if (playerId) {
                  try {
                    await updateSteps(playerId, gpsStepsRef.current);
                  } catch (e) {
                    console.log('Failed to sync steps:', e);
                  }
                }
              }
            }
            lastLocationRef.current = { lat: newLoc.coords.latitude, lng: newLoc.coords.longitude };
          }
        );
        locationSubRef.current = locSub;
      } catch (e) {
        console.log('GPS tracking error:', e);
        setTrackingMode('none');
      }
    };

    const init = async () => {
      await loadFitnessData();
      const pedOk = await setupPedometer();
      if (!pedOk) {
        // Pedometer failed, use GPS as fallback
        await setupGPSTracking();
      }
    };

    init();

    return () => {
      if (pedSub) pedSub.remove();
      if (locSub) locSub.remove();
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

  // Handle syncing distance to travel missions and applying vehicle wear
  const handleSyncToMissions = async () => {
    if (!playerId || syncing || unsyncedDistance === 0) return;
    setSyncing(true);
    
    try {
      const result = await syncTravelDistance(playerId, unsyncedDistance);
      
      // Build summary message
      let message = '';
      
      if (result.missions_updated && result.missions_updated.length > 0) {
        const missionSummary = result.missions_updated.map((m: any) => {
          const progressStr = formatDistance(m.new_progress);
          const targetStr = formatDistance(m.target);
          return `• ${m.title}: ${progressStr} / ${targetStr}${m.completed ? ' ✓' : ''}`;
        }).join('\n');
        message += `Travel Missions Updated:\n${missionSummary}`;
      } else {
        message += 'No travel missions to update.';
      }
      
      if (result.vehicle_damage > 0) {
        message += `\n\nVehicle Wear: -${result.vehicle_damage} durability`;
        if (result.vehicle_new_durability !== null) {
          message += ` (${result.vehicle_new_durability} remaining)`;
        }
      }
      
      // Reset unsynced distance ONLY after successful sync
      setUnsyncedDistance(0);
      
      // Trigger mission refresh to update UI elsewhere
      triggerMissionRefresh();
      
      Alert.alert(
        `Synced ${formatDistance(result.synced_distance)}!`,
        message
      );
      
    } catch (err: any) {
      Alert.alert('Sync Failed', err?.response?.data?.detail || 'Could not sync distance. Try again.');
    } finally {
      setSyncing(false);
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
              {trackingMode === 'gps' ? (
                <>
                  <Ionicons name="navigate" size={14} color="#4caf50" />
                  <Text style={[styles.pedWarningText, {color: '#4caf50'}]}>GPS step tracking active — walk around to count steps!</Text>
                </>
              ) : (
                <>
                  <Ionicons name="warning" size={14} color="#f39c12" />
                  <Text style={styles.pedWarningText}>Step sensor unavailable. Walk around on the map to track via GPS.</Text>
                </>
              )}
            </View>
          )}
          {pedometerAvailable && (
            <View style={styles.pedWarning}>
              <Ionicons name="checkmark-circle" size={14} color="#4caf50" />
              <Text style={[styles.pedWarningText, {color: '#4caf50'}]}>Step counter active</Text>
            </View>
          )}
          
          {/* Unsynced Distance Display */}
          <View style={styles.unsyncedContainer}>
            <Text style={styles.unsyncedLabel}>UNSYNCED DISTANCE</Text>
            <Text style={styles.unsyncedValue}>{formatDistance(unsyncedDistance)}</Text>
            <Text style={styles.unsyncedHint}>Walk to accumulate, then sync to missions</Text>
          </View>
          
          {/* Sync to Missions button */}
          <TouchableOpacity 
            style={[
              styles.syncButton, 
              (syncing || unsyncedDistance === 0) && styles.syncButtonDisabled
            ]}
            onPress={handleSyncToMissions}
            disabled={syncing || unsyncedDistance === 0}
          >
            {syncing ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Ionicons name="sync" size={16} color="#fff" />
            )}
            <Text style={styles.syncButtonText}>
              {syncing ? 'SYNCING...' : `SYNC TO MISSIONS (${formatDistance(unsyncedDistance)})`}
            </Text>
          </TouchableOpacity>
          
          {Platform.OS === 'web' && (
            <View style={styles.pedWarning}>
              <Ionicons name="phone-portrait" size={14} color="#3498db" />
              <Text style={styles.pedWarningText}>Open on your phone via Expo Go to track steps</Text>
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
  syncButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#e74c3c',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 16,
  },
  syncButtonDisabled: {
    backgroundColor: '#555',
    opacity: 0.7,
  },
  syncButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 1,
  },
  unsyncedContainer: {
    backgroundColor: '#1a2e1a',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a4a2a',
  },
  unsyncedLabel: {
    color: '#4caf50',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  unsyncedValue: {
    color: '#fff',
    fontSize: 28,
    fontWeight: '900',
  },
  unsyncedHint: {
    color: '#666',
    fontSize: 11,
    marginTop: 4,
  },
});
