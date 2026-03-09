import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Location from 'expo-location';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import {
  getPlayer,
  updatePlayerPosition,
  spawnMonsters,
  generateMissions,
  getNearbyPlayers,
  startBattle,
} from '../../services/api';
import { Monster, Mission, NearbyPlayer } from '../../types/game';
import { GameMap } from '../../components/GameMap';

// Calculate distance between two points in meters
const getDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
};

export default function MapScreen() {
  const {
    player,
    playerId,
    setPlayer,
    currentPosition,
    setCurrentPosition,
    nearbyMonsters,
    setNearbyMonsters,
    nearbyMissions,
    setNearbyMissions,
    nearbyPlayers,
    setNearbyPlayers,
    setCurrentBattle,
  } = useGameStore();

  const [loading, setLoading] = useState(true);
  const [selectedMarker, setSelectedMarker] = useState<{
    type: 'monster' | 'mission' | 'player';
    data: any;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [isTracking, setIsTracking] = useState(false);
  const [heading, setHeading] = useState<number>(0);
  
  const locationSubscription = useRef<Location.LocationSubscription | null>(null);
  const headingSubscription = useRef<Location.LocationSubscription | null>(null);
  const lastEntityLoadPos = useRef<{ lat: number; lon: number } | null>(null);
  const lastServerUpdateTime = useRef<number>(0);
  const entitiesCache = useRef<{ time: number; data: any } | null>(null);

  useEffect(() => {
    initializeLocation();
    return () => {
      if (locationSubscription.current) locationSubscription.current.remove();
      if (headingSubscription.current) headingSubscription.current.remove();
    };
  }, []);

  // Only load entities when position changes significantly (50m+)
  useEffect(() => {
    if (currentPosition && player) {
      const shouldLoad = !lastEntityLoadPos.current || 
        getDistance(
          lastEntityLoadPos.current.lat,
          lastEntityLoadPos.current.lon,
          currentPosition.latitude,
          currentPosition.longitude
        ) > 50;
      
      if (shouldLoad) {
        loadNearbyEntities();
        lastEntityLoadPos.current = {
          lat: currentPosition.latitude,
          lon: currentPosition.longitude
        };
      }
    }
  }, [currentPosition?.latitude, currentPosition?.longitude]);

  const initializeLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        // Use default location (New York) for demo when permission denied
        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
        setCurrentPosition(defaultPos);
        if (playerId) {
          updatePlayerPosition(playerId, defaultPos).catch(console.error);
          getPlayer(playerId).then(setPlayer).catch(console.error);
        }
        setLoading(false);
        startLocationTracking();
        return;
      }

      // Get initial position quickly with balanced accuracy
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      const position = {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      };

      setCurrentPosition(position);
      
      if (playerId) {
        // Update position on server and fetch player data
        updatePlayerPosition(playerId, position).catch(console.error);
        getPlayer(playerId).then(setPlayer).catch(console.error);
      }

      setLoading(false);
      startLocationTracking();
      
    } catch (error: any) {
      // Fallback to default location on error
      const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
      setCurrentPosition(defaultPos);
      setLoading(false);
    }
  };

  const startLocationTracking = async () => {
    try {
      if (locationSubscription.current) {
        locationSubscription.current.remove();
      }

      setIsTracking(true);
      
      // Track position - frequent local updates for smooth movement, server every 5s
      locationSubscription.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          timeInterval: 1000,
          distanceInterval: 1,
        },
        (loc) => {
          const newPos = {
            latitude: loc.coords.latitude,
            longitude: loc.coords.longitude,
          };
          setCurrentPosition(newPos);
          
          if (loc.coords.heading !== null && loc.coords.heading >= 0) {
            setHeading(loc.coords.heading);
          }
          
          // Throttle server updates to every 5 seconds
          const now = Date.now();
          if (playerId && now - lastServerUpdateTime.current > 5000) {
            lastServerUpdateTime.current = now;
            updatePlayerPosition(playerId, newPos).catch(console.error);
          }
        }
      );
      
      // Heading updates for compass direction
      try {
        headingSubscription.current = await Location.watchHeadingAsync((h) => {
          if (h.trueHeading >= 0) setHeading(h.trueHeading);
          else if (h.magHeading >= 0) setHeading(h.magHeading);
        });
      } catch {}
      
    } catch (error) {
      setIsTracking(false);
    }
  };

  const loadNearbyEntities = useCallback(async () => {
    if (!currentPosition || !player || !playerId) return;

    // Check cache (30 second TTL)
    const now = Date.now();
    if (entitiesCache.current && now - entitiesCache.current.time < 30000) {
      return;
    }

    try {
      // Ensure server knows our position before fetching entities
      await updatePlayerPosition(playerId, currentPosition).catch(() => {});

      // Use allSettled so one failure doesn't block others
      const results = await Promise.allSettled([
        spawnMonsters(currentPosition.latitude, currentPosition.longitude, player.level),
        generateMissions(currentPosition.latitude, currentPosition.longitude, player.level),
        getNearbyPlayers(playerId, 500),
      ]);

      const monsters = results[0].status === 'fulfilled' ? results[0].value : [];
      const missions = results[1].status === 'fulfilled' ? results[1].value : [];
      const players = results[2].status === 'fulfilled' ? results[2].value : [];

      setNearbyMonsters(monsters);
      setNearbyMissions(missions);
      setNearbyPlayers(players);
      
      entitiesCache.current = { time: now, data: { monsters, missions, players } };
    } catch (error) {
      console.error('Failed to load entities:', error);
    }
  }, [currentPosition, player, playerId]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    entitiesCache.current = null; // Clear cache
    lastEntityLoadPos.current = null; // Force reload
    await loadNearbyEntities();
    setRefreshing(false);
  }, [loadNearbyEntities]);

  const handleStartBattle = useCallback(async (monster: Monster) => {
    if (!playerId) return;
    try {
      const battle = await startBattle(playerId, 'monster', monster.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start battle');
    }
  }, [playerId]);

  const handleStartMission = useCallback((mission: Mission) => {
    setSelectedMarker(null);
    router.push(`/mission/${mission.id}`);
  }, []);

  const handlePvPChallenge = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId) return;
    try {
      const battle = await startBattle(playerId, 'player', targetPlayer.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start PvP');
    }
  }, [playerId]);

  // Memoize markers to prevent re-renders
  const mapMarkers = useMemo(() => [
    ...nearbyMonsters.map((m) => ({
      id: m.id,
      coordinate: m.position,
      type: 'monster' as const,
      level: m.level,
      name: m.name,
    })),
    ...nearbyMissions.map((m) => ({
      id: m.id,
      coordinate: m.position,
      type: 'mission' as const,
      name: m.title,
    })),
    ...nearbyPlayers.map((p) => ({
      id: p.id,
      coordinate: p.position,
      type: 'player' as const,
      level: p.level,
      name: p.name,
    })),
  ], [nearbyMonsters, nearbyMissions, nearbyPlayers]);

  const handleMarkerPress = useCallback((marker: any) => {
    if (marker.type === 'monster') {
      const monster = nearbyMonsters.find((m) => m.id === marker.id);
      if (monster) setSelectedMarker({ type: 'monster', data: monster });
    } else if (marker.type === 'mission') {
      const mission = nearbyMissions.find((m) => m.id === marker.id);
      if (mission) setSelectedMarker({ type: 'mission', data: mission });
    } else if (marker.type === 'player') {
      const targetPlayer = nearbyPlayers.find((p) => p.id === marker.id);
      if (targetPlayer) setSelectedMarker({ type: 'player', data: targetPlayer });
    }
  }, [nearbyMonsters, nearbyMissions, nearbyPlayers]);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4285F4" />
        <Text style={styles.loadingText}>Finding your location...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {currentPosition && (
        <GameMap
          center={currentPosition}
          markers={mapMarkers}
          heading={heading}
          onMarkerPress={handleMarkerPress}
        />
      )}

      <SafeAreaView style={styles.hud}>
        <View style={styles.playerHud}>
          <Text style={styles.playerName}>{player?.name}</Text>
          <Text style={styles.playerLevel}>Lv.{player?.level}</Text>
        </View>
        <View style={styles.hudRight}>
          <View style={[styles.gpsIndicator, isTracking && styles.gpsActive]}>
            <Ionicons name="navigate" size={14} color={isTracking ? '#34A853' : '#888'} />
          </View>
          <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh} disabled={refreshing}>
            <Ionicons name="refresh" size={22} color="#5F6368" style={refreshing ? styles.rotating : undefined} />
          </TouchableOpacity>
        </View>
      </SafeAreaView>

      {/* Quick action cards */}
      <View style={styles.entityList}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {nearbyMonsters.slice(0, 3).map((monster) => (
            <TouchableOpacity
              key={monster.id}
              style={[styles.entityCard, styles.monsterCard]}
              onPress={() => setSelectedMarker({ type: 'monster', data: monster })}
            >
              <Ionicons name="skull" size={18} color="#EA4335" />
              <Text style={styles.entityName}>{monster.name}</Text>
              <Text style={styles.entityLevel}>Lv.{monster.level}</Text>
            </TouchableOpacity>
          ))}
          {nearbyMissions.slice(0, 2).map((mission) => (
            <TouchableOpacity
              key={mission.id}
              style={[styles.entityCard, styles.missionCard]}
              onPress={() => setSelectedMarker({ type: 'mission', data: mission })}
            >
              <Ionicons name="briefcase" size={18} color="#FBBC04" />
              <Text style={styles.entityName} numberOfLines={1}>{mission.title}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Popup */}
      {selectedMarker && (
        <View style={styles.popup}>
          <TouchableOpacity style={styles.popupClose} onPress={() => setSelectedMarker(null)}>
            <Ionicons name="close" size={24} color="#5F6368" />
          </TouchableOpacity>

          {selectedMarker.type === 'monster' && (
            <View>
              <View style={styles.popupHeader}>
                <Ionicons name="skull" size={28} color="#EA4335" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Level {selectedMarker.data.level}</Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={14} color="#34A853" />
                  <Text style={styles.rewardText}>${selectedMarker.data.loot_cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={14} color="#4285F4" />
                  <Text style={styles.rewardText}>{selectedMarker.data.loot_xp} XP</Text>
                </View>
              </View>
              <TouchableOpacity style={styles.actionButton} onPress={() => handleStartBattle(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>FIGHT</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'mission' && (
            <View>
              <View style={styles.popupHeader}>
                <Ionicons name="briefcase" size={28} color="#FBBC04" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.title}</Text>
                  <Text style={styles.popupSubtitle}>{selectedMarker.data.difficulty.toUpperCase()}</Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={14} color="#34A853" />
                  <Text style={styles.rewardText}>${selectedMarker.data.rewards.cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={14} color="#4285F4" />
                  <Text style={styles.rewardText}>{selectedMarker.data.rewards.xp} XP</Text>
                </View>
              </View>
              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#FBBC04'}]} onPress={() => handleStartMission(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>START</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'player' && (
            <View>
              <View style={styles.popupHeader}>
                <Ionicons name="person" size={28} color="#4285F4" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Lv.{selectedMarker.data.level} • {selectedMarker.data.distance}m</Text>
                </View>
              </View>
              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#4285F4'}]} onPress={() => handlePvPChallenge(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>CHALLENGE</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
  loadingText: { color: '#5F6368', marginTop: 12, fontSize: 14 },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff', padding: 24 },
  errorTitle: { color: '#202124', fontSize: 18, fontWeight: '600', marginTop: 16 },
  errorText: { color: '#5F6368', marginTop: 8, textAlign: 'center' },
  retryButton: { marginTop: 20, backgroundColor: '#4285F4', paddingHorizontal: 24, paddingVertical: 10, borderRadius: 20 },
  retryText: { color: '#fff', fontWeight: '600' },
  hud: { position: 'absolute', top: 0, left: 0, right: 0, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingTop: 4 },
  playerHud: { backgroundColor: '#fff', paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  playerName: { color: '#202124', fontWeight: '600', fontSize: 14 },
  playerLevel: { color: '#4285F4', fontWeight: '600', marginLeft: 6, fontSize: 14 },
  hudRight: { flexDirection: 'row', alignItems: 'center' },
  gpsIndicator: { backgroundColor: '#fff', padding: 8, borderRadius: 20, marginRight: 6, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  gpsActive: { backgroundColor: '#E8F5E9' },
  refreshButton: { backgroundColor: '#fff', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  rotating: { opacity: 0.5 },
  entityList: { position: 'absolute', bottom: 90, left: 0, right: 0, paddingHorizontal: 8 },
  entityCard: { backgroundColor: '#fff', borderRadius: 12, padding: 10, marginHorizontal: 4, alignItems: 'center', minWidth: 85, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  monsterCard: { borderLeftWidth: 3, borderLeftColor: '#EA4335' },
  missionCard: { borderLeftWidth: 3, borderLeftColor: '#FBBC04' },
  entityName: { color: '#202124', fontSize: 11, fontWeight: '600', marginTop: 4, maxWidth: 70 },
  entityLevel: { color: '#5F6368', fontSize: 10, marginTop: 2 },
  popup: { position: 'absolute', bottom: 170, left: 12, right: 12, backgroundColor: '#fff', borderRadius: 16, padding: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.2, shadowRadius: 8, elevation: 5 },
  popupClose: { position: 'absolute', top: 10, right: 10, zIndex: 1 },
  popupHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  popupHeaderText: { marginLeft: 10 },
  popupTitle: { color: '#202124', fontSize: 16, fontWeight: '600' },
  popupSubtitle: { color: '#5F6368', fontSize: 12 },
  rewardsRow: { flexDirection: 'row', marginBottom: 12 },
  rewardItem: { flexDirection: 'row', alignItems: 'center', marginRight: 16 },
  rewardText: { color: '#202124', marginLeft: 4, fontWeight: '600', fontSize: 13 },
  actionButton: { backgroundColor: '#EA4335', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, borderRadius: 8 },
  actionButtonText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
