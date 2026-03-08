import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  Platform,
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

const MONSTER_COLORS: Record<string, string> = {
  humanoid: '#e74c3c',
  boss: '#9b59b6',
  tech: '#3498db',
  stealth: '#1abc9c',
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
  const [locationError, setLocationError] = useState<string | null>(null);
  const [selectedMarker, setSelectedMarker] = useState<{
    type: 'monster' | 'mission' | 'player';
    data: any;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    initializeLocation();
  }, []);

  useEffect(() => {
    if (currentPosition && player) {
      loadNearbyEntities();
    }
  }, [currentPosition]);

  const initializeLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        // Use a default location for demo/web
        const defaultPosition = {
          latitude: 40.7128,
          longitude: -74.0060,
        };
        setCurrentPosition(defaultPosition);
        
        if (playerId) {
          await updatePlayerPosition(playerId, defaultPosition);
          const playerData = await getPlayer(playerId);
          setPlayer(playerData);
        }
        setLoading(false);
        return;
      }

      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });

      const position = {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      };

      setCurrentPosition(position);

      if (playerId) {
        await updatePlayerPosition(playerId, position);
        const playerData = await getPlayer(playerId);
        setPlayer(playerData);
      }

      // Start watching position
      Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          distanceInterval: 10,
        },
        (loc) => {
          const newPos = {
            latitude: loc.coords.latitude,
            longitude: loc.coords.longitude,
          };
          setCurrentPosition(newPos);
          if (playerId) {
            updatePlayerPosition(playerId, newPos).catch(console.error);
          }
        }
      );
    } catch (error) {
      // Use default location on error
      const defaultPosition = {
        latitude: 40.7128,
        longitude: -74.0060,
      };
      setCurrentPosition(defaultPosition);
    } finally {
      setLoading(false);
    }
  };

  const loadNearbyEntities = async () => {
    if (!currentPosition || !player || !playerId) return;

    try {
      const [monsters, missions, players] = await Promise.all([
        spawnMonsters(currentPosition.latitude, currentPosition.longitude, player.level),
        generateMissions(currentPosition.latitude, currentPosition.longitude, player.level),
        getNearbyPlayers(playerId, 500),
      ]);

      setNearbyMonsters(monsters);
      setNearbyMissions(missions);
      setNearbyPlayers(players);
    } catch (error) {
      console.error('Failed to load entities:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadNearbyEntities();
    setRefreshing(false);
  };

  const handleStartBattle = async (monster: Monster) => {
    if (!playerId) return;

    try {
      const battle = await startBattle(playerId, 'monster', monster.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start battle');
    }
  };

  const handleStartMission = (mission: Mission) => {
    setSelectedMarker(null);
    router.push(`/mission/${mission.id}`);
  };

  const handlePvPChallenge = async (targetPlayer: NearbyPlayer) => {
    if (!playerId) return;

    try {
      const battle = await startBattle(playerId, 'player', targetPlayer.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start PvP');
    }
  };

  // Convert entities to map markers
  const mapMarkers = [
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
  ];

  const handleMarkerPress = (marker: any) => {
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
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
        <Text style={styles.loadingText}>Getting your location...</Text>
      </View>
    );
  }

  if (locationError) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="location-outline" size={64} color="#e74c3c" />
        <Text style={styles.errorText}>{locationError}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={initializeLocation}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {currentPosition && (
        <GameMap
          center={currentPosition}
          markers={mapMarkers}
          onMarkerPress={handleMarkerPress}
        />
      )}

      {/* HUD */}
      <SafeAreaView style={styles.hud}>
        <View style={styles.playerHud}>
          <Text style={styles.playerName}>{player?.name}</Text>
          <Text style={styles.playerLevel}>Lv.{player?.level}</Text>
        </View>
        <TouchableOpacity
          style={styles.refreshButton}
          onPress={handleRefresh}
          disabled={refreshing}
        >
          <Ionicons
            name="refresh"
            size={24}
            color="#fff"
            style={refreshing ? styles.rotating : undefined}
          />
        </TouchableOpacity>
      </SafeAreaView>

      {/* Entity List */}
      <View style={styles.entityList}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {nearbyMonsters.slice(0, 3).map((monster) => (
            <TouchableOpacity
              key={monster.id}
              style={[styles.entityCard, styles.monsterCard]}
              onPress={() => setSelectedMarker({ type: 'monster', data: monster })}
            >
              <Ionicons name="skull" size={20} color="#e74c3c" />
              <Text style={styles.entityName}>{monster.name}</Text>
              <Text style={styles.entityLevel}>Lv.{monster.level}</Text>
            </TouchableOpacity>
          ))}
          {nearbyMissions.slice(0, 3).map((mission) => (
            <TouchableOpacity
              key={mission.id}
              style={[styles.entityCard, styles.missionCard]}
              onPress={() => setSelectedMarker({ type: 'mission', data: mission })}
            >
              <Ionicons name="briefcase" size={20} color="#f39c12" />
              <Text style={styles.entityName} numberOfLines={1}>{mission.title}</Text>
              <Text style={styles.entityLevel}>{mission.difficulty}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Selected marker popup */}
      {selectedMarker && (
        <View style={styles.popup}>
          <TouchableOpacity
            style={styles.popupClose}
            onPress={() => setSelectedMarker(null)}
          >
            <Ionicons name="close" size={24} color="#888" />
          </TouchableOpacity>

          {selectedMarker.type === 'monster' && (
            <View style={styles.popupContent}>
              <View style={styles.popupHeader}>
                <Ionicons
                  name="skull"
                  size={32}
                  color={MONSTER_COLORS[selectedMarker.data.monster_type]}
                />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Level {selectedMarker.data.level}</Text>
                </View>
              </View>
              <Text style={styles.popupDescription}>{selectedMarker.data.description}</Text>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={16} color="#f39c12" />
                  <Text style={styles.rewardText}>${selectedMarker.data.loot_cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={16} color="#3498db" />
                  <Text style={styles.rewardText}>{selectedMarker.data.loot_xp} XP</Text>
                </View>
              </View>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => handleStartBattle(selectedMarker.data)}
              >
                <Ionicons name="flash" size={20} color="#fff" />
                <Text style={styles.actionButtonText}>FIGHT</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'mission' && (
            <View style={styles.popupContent}>
              <View style={styles.popupHeader}>
                <Ionicons name="briefcase" size={32} color="#f39c12" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.title}</Text>
                  <Text style={styles.popupSubtitle}>
                    {selectedMarker.data.difficulty.toUpperCase()} - Lv.{selectedMarker.data.level_requirement}+
                  </Text>
                </View>
              </View>
              <Text style={styles.popupDescription}>{selectedMarker.data.description}</Text>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={16} color="#f39c12" />
                  <Text style={styles.rewardText}>${selectedMarker.data.rewards.cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={16} color="#3498db" />
                  <Text style={styles.rewardText}>{selectedMarker.data.rewards.xp} XP</Text>
                </View>
              </View>
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#f39c12' }]}
                onPress={() => handleStartMission(selectedMarker.data)}
              >
                <Ionicons name="navigate" size={20} color="#fff" />
                <Text style={styles.actionButtonText}>START MISSION</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'player' && (
            <View style={styles.popupContent}>
              <View style={styles.popupHeader}>
                <Ionicons name="person" size={32} color="#3498db" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>
                    Level {selectedMarker.data.level} {selectedMarker.data.character_class.replace('_', ' ')}
                  </Text>
                </View>
              </View>
              <Text style={styles.popupDescription}>
                Distance: {selectedMarker.data.distance}m away
              </Text>
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#9b59b6' }]}
                onPress={() => handlePvPChallenge(selectedMarker.data)}
              >
                <Ionicons name="flash" size={20} color="#fff" />
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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0a0a0a',
    padding: 24,
  },
  errorText: {
    color: '#888',
    marginTop: 16,
    textAlign: 'center',
    fontSize: 16,
  },
  retryButton: {
    marginTop: 24,
    backgroundColor: '#e74c3c',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  hud: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  playerHud: {
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
  },
  playerName: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  playerLevel: {
    color: '#e74c3c',
    fontWeight: 'bold',
    marginLeft: 8,
  },
  refreshButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rotating: {
    opacity: 0.5,
  },
  entityList: {
    position: 'absolute',
    bottom: 100,
    left: 0,
    right: 0,
    paddingHorizontal: 12,
  },
  entityCard: {
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    borderRadius: 12,
    padding: 12,
    marginHorizontal: 4,
    alignItems: 'center',
    minWidth: 100,
    borderWidth: 1,
  },
  monsterCard: {
    borderColor: '#e74c3c',
  },
  missionCard: {
    borderColor: '#f39c12',
  },
  entityName: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 4,
    maxWidth: 80,
  },
  entityLevel: {
    color: '#888',
    fontSize: 10,
    marginTop: 2,
  },
  popup: {
    position: 'absolute',
    bottom: 180,
    left: 16,
    right: 16,
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#333',
  },
  popupClose: {
    position: 'absolute',
    top: 12,
    right: 12,
    zIndex: 1,
  },
  popupContent: {},
  popupHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  popupHeaderText: {
    marginLeft: 12,
  },
  popupTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  popupSubtitle: {
    color: '#888',
    fontSize: 14,
  },
  popupDescription: {
    color: '#aaa',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  rewardsRow: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  rewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 20,
  },
  rewardText: {
    color: '#fff',
    marginLeft: 6,
    fontWeight: 'bold',
  },
  actionButton: {
    backgroundColor: '#e74c3c',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    borderRadius: 8,
  },
  actionButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
    marginLeft: 8,
  },
});
