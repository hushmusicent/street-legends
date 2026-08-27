import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useGameStore } from '../../stores/gameStore';
import { getNearbyPlayers, startBattle, spawnCastles, startCastleGame } from '../../services/api';
import { NearbyPlayer } from '../../types/game';

const CLASS_COLORS: Record<string, string> = {
  street_soldier: '#e74c3c',
  hacker: '#3498db',
  enforcer: '#f39c12',
  ghost: '#9b59b6',
};

export default function PvPScreen() {
  const { player, playerId, currentPosition, nearbyPlayers, setNearbyPlayers, setCurrentBattle } = useGameStore();
  const [refreshing, setRefreshing] = useState(false);
  const [nearbyCastles, setNearbyCastles] = useState<any[]>([]);
  const [loadingCastleId, setLoadingCastleId] = useState<string | null>(null);

  useEffect(() => {
    if (playerId && currentPosition) {
      loadNearbyPlayers();
      loadNearbyCastles();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerId, currentPosition]);

  const loadNearbyPlayers = async () => {
    if (!playerId) return;
    try {
      const players = await getNearbyPlayers(playerId, 1000); // 1km radius for PvP
      setNearbyPlayers(players);
    } catch (error) {
      console.error('Failed to load nearby players:', error);
    }
  };

  const loadNearbyCastles = async () => {
    if (!currentPosition || !player) return;
    try {
      const castles = await spawnCastles(currentPosition.latitude, currentPosition.longitude, player.level);
      setNearbyCastles(castles);
    } catch (error) {
      console.error('Failed to load nearby castles:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadNearbyPlayers(), loadNearbyCastles()]);
    setRefreshing(false);
  };

  const handleStartCastleGame = async (castle: any) => {
    if (!playerId || loadingCastleId) return;
    setLoadingCastleId(castle.id);
    
    try {
      const gameData = await startCastleGame(castle.id, playerId);
      
      // Navigate to the castle game screen
      router.push({
        pathname: '/castle-game',
        params: { gameData: JSON.stringify(gameData) },
      });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Failed to start castle game';
      Alert.alert('Cannot Attack', errorMsg);
    } finally {
      setLoadingCastleId(null);
    }
  };

  const handleChallenge = async (targetPlayer: NearbyPlayer) => {
    if (!playerId) return;

    Alert.alert(
      'Challenge Player',
      `Challenge ${targetPlayer.name} (Level ${targetPlayer.level}) to a PvP battle?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Fight!',
          style: 'destructive',
          onPress: async () => {
            try {
              const battle = await startBattle(playerId, 'player', targetPlayer.id);
              setCurrentBattle(battle);
              router.push(`/battle/${battle.id}`);
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to start battle');
            }
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#e74c3c" />
        }
      >
        <Text style={styles.title}>PVP ARENA</Text>
        <Text style={styles.subtitle}>Challenge nearby players</Text>

        {/* Player Stats */}
        <View style={styles.myStats}>
          <View style={styles.statItem}>
            <Ionicons name="trophy" size={24} color="#27ae60" />
            <Text style={styles.statValue}>{player?.wins || 0}</Text>
            <Text style={styles.statLabel}>Wins</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.statItem}>
            <Ionicons name="close-circle" size={24} color="#e74c3c" />
            <Text style={styles.statValue}>{player?.losses || 0}</Text>
            <Text style={styles.statLabel}>Losses</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.statItem}>
            <Ionicons name="stats-chart" size={24} color="#f39c12" />
            <Text style={styles.statValue}>
              {player?.wins && player.losses
                ? ((player.wins / (player.wins + player.losses)) * 100).toFixed(0)
                : 0}%
            </Text>
            <Text style={styles.statLabel}>Win Rate</Text>
          </View>
        </View>

        {/* Nearby Players */}
        <Text style={styles.sectionTitle}>NEARBY OPPONENTS ({nearbyPlayers.length})</Text>

        {nearbyPlayers.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="people-outline" size={64} color="#333" />
            <Text style={styles.emptyText}>No players nearby</Text>
            <Text style={styles.emptySubtext}>Move around to find opponents!</Text>
          </View>
        ) : (
          nearbyPlayers.map((targetPlayer) => (
            <TouchableOpacity
              key={targetPlayer.id}
              style={styles.playerCard}
              onPress={() => handleChallenge(targetPlayer)}
              activeOpacity={0.8}
            >
              <View style={styles.playerInfo}>
                <View
                  style={[
                    styles.playerAvatar,
                    { borderColor: CLASS_COLORS[targetPlayer.character_class] || '#e74c3c' },
                  ]}
                >
                  <Ionicons name="person" size={24} color="#fff" />
                </View>
                <View style={styles.playerDetails}>
                  <Text style={styles.playerName}>{targetPlayer.name}</Text>
                  <Text
                    style={[
                      styles.playerClass,
                      { color: CLASS_COLORS[targetPlayer.character_class] || '#e74c3c' },
                    ]}
                  >
                    {targetPlayer.character_class.replace('_', ' ').toUpperCase()}
                  </Text>
                </View>
              </View>
              <View style={styles.playerMeta}>
                <View style={styles.levelBadge}>
                  <Text style={styles.levelText}>Lv.{targetPlayer.level}</Text>
                </View>
                <Text style={styles.distanceText}>{targetPlayer.distance}m</Text>
              </View>
              <View style={styles.challengeArrow}>
                <Ionicons name="flash" size={24} color="#e74c3c" />
              </View>
            </TouchableOpacity>
          ))
        )}

        {/* Tips */}
        <View style={styles.tipsSection}>
          <Text style={styles.tipsTitle}>PVP TIPS</Text>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#3498db" />
            <Text style={styles.tipText}>Higher level players give more reputation</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#3498db" />
            <Text style={styles.tipText}>Use skills strategically to win battles</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#3498db" />
            <Text style={styles.tipText}>Guild members cannot battle each other</Text>
          </View>
        </View>

        {/* Castle Cannon Mini-Game Section */}
        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>🏰 CASTLE ASSAULT ({nearbyCastles.length})</Text>
        
        {nearbyCastles.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={{ fontSize: 48 }}>🏰</Text>
            <Text style={styles.emptyText}>No fortresses nearby</Text>
            <Text style={styles.emptySubtext}>Explore the map to find gang hideouts!</Text>
          </View>
        ) : (
          nearbyCastles.map((castle) => (
            <TouchableOpacity
              key={castle.id}
              style={styles.castleCard}
              onPress={() => handleStartCastleGame(castle)}
              activeOpacity={0.8}
              disabled={loadingCastleId === castle.id}
            >
              <View style={styles.castleInfo}>
                <View style={styles.castleIcon}>
                  <Text style={{ fontSize: 28 }}>🏰</Text>
                </View>
                <View style={styles.castleDetails}>
                  <Text style={styles.castleName}>{castle.name}</Text>
                  <Text style={styles.castleDifficulty}>
                    {'⚔️'.repeat(castle.difficulty)} Level {castle.difficulty}
                  </Text>
                </View>
              </View>
              <View style={styles.castleMeta}>
                <View style={styles.castleReward}>
                  <Ionicons name="cash" size={14} color="#f39c12" />
                  <Text style={styles.rewardText}>${castle.min_reward}-${castle.max_reward}</Text>
                </View>
                <Text style={styles.xpText}>+{castle.xp_reward} XP</Text>
              </View>
              <View style={styles.castleArrow}>
                {loadingCastleId === castle.id ? (
                  <ActivityIndicator size="small" color="#8B4513" />
                ) : (
                  <Ionicons name="flame" size={24} color="#8B4513" />
                )}
              </View>
            </TouchableOpacity>
          ))
        )}

        {/* Castle Mini-game Tips */}
        <View style={[styles.tipsSection, { backgroundColor: 'rgba(139, 69, 19, 0.15)', marginTop: 16 }]}>
          <Text style={[styles.tipsTitle, { color: '#CD853F' }]}>CANNON TIPS</Text>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#CD853F" />
            <Text style={styles.tipText}>Drag on screen to aim the cannon</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#CD853F" />
            <Text style={styles.tipText}>You have 3 shots to eliminate all targets</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#CD853F" />
            <Text style={styles.tipText}>Destroy blocks to make enemies fall</Text>
          </View>
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
  scrollContent: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    color: '#888',
    marginBottom: 24,
  },
  myStats: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 8,
  },
  statLabel: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
  divider: {
    width: 1,
    height: 50,
    backgroundColor: '#333',
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 16,
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
  },
  emptyText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
  },
  emptySubtext: {
    color: '#666',
    marginTop: 8,
  },
  playerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#222',
  },
  playerInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  playerAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#222',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
  },
  playerDetails: {
    marginLeft: 12,
  },
  playerName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  playerClass: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1,
  },
  playerMeta: {
    alignItems: 'flex-end',
    marginRight: 12,
  },
  levelBadge: {
    backgroundColor: '#333',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  levelText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  distanceText: {
    color: '#666',
    fontSize: 11,
    marginTop: 4,
  },
  challengeArrow: {
    padding: 8,
  },
  tipsSection: {
    marginTop: 24,
    backgroundColor: 'rgba(52, 152, 219, 0.1)',
    borderRadius: 12,
    padding: 16,
  },
  tipsTitle: {
    color: '#3498db',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 12,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  tipText: {
    color: '#888',
    fontSize: 13,
    marginLeft: 8,
  },
  // Castle Mini-game styles
  castleCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 69, 19, 0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#8B4513',
  },
  castleInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  castleIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(139, 69, 19, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  castleDetails: {
    marginLeft: 12,
  },
  castleName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  castleDifficulty: {
    fontSize: 11,
    color: '#CD853F',
    fontWeight: '600',
    marginTop: 2,
  },
  castleMeta: {
    alignItems: 'flex-end',
    marginRight: 12,
  },
  castleReward: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  rewardText: {
    color: '#f39c12',
    fontSize: 12,
    fontWeight: 'bold',
  },
  xpText: {
    color: '#9b59b6',
    fontSize: 11,
    marginTop: 4,
    fontWeight: '600',
  },
  castleArrow: {
    padding: 8,
  },
});
