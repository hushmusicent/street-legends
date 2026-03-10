import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getLeaderboard } from '../../services/api';
import { LeaderboardEntry } from '../../types/game';
import { useGameStore } from '../../stores/gameStore';

const CLASS_COLORS: Record<string, string> = {
  street_soldier: '#e74c3c',
  hacker: '#3498db',
  enforcer: '#f39c12',
  ghost: '#9b59b6',
};

const RANK_COLORS: Record<number, string> = {
  1: '#FFD700',
  2: '#C0C0C0',
  3: '#CD7F32',
};

export default function LeaderboardScreen() {
  const { playerId } = useGameStore();
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadLeaderboard();
  }, []);

  const loadLeaderboard = async () => {
    try {
      const data = await getLeaderboard(50);
      setLeaderboard(data);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadLeaderboard();
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#e74c3c" />
        }
      >
        <View style={styles.header}>
          <Ionicons name="trophy" size={32} color="#f39c12" />
          <Text style={styles.title}>LEADERBOARD</Text>
        </View>

        {/* Top 3 Podium */}
        {leaderboard.length >= 3 && (
          <View style={styles.podium}>
            {/* 2nd Place */}
            <View style={styles.podiumItem}>
              <View style={[styles.podiumAvatar, { borderColor: RANK_COLORS[2] }]}>
                {leaderboard[1]?.profile_pic ? (
                  <Image source={{ uri: leaderboard[1].profile_pic }} style={styles.podiumAvatarImg} />
                ) : (
                  <Ionicons name="person" size={24} color="#fff" />
                )}
              </View>
              <Text style={styles.podiumName}>{leaderboard[1]?.name}</Text>
              <Text style={styles.podiumRep}>{leaderboard[1]?.reputation} REP</Text>
              <View style={[styles.podiumRank, { backgroundColor: RANK_COLORS[2], height: 60 }]}>
                <Text style={styles.podiumRankText}>2</Text>
              </View>
            </View>

            {/* 1st Place */}
            <View style={styles.podiumItem}>
              <Ionicons name="crown" size={24} color="#FFD700" style={styles.crown} />
              <View style={[styles.podiumAvatar, styles.firstPlace, { borderColor: RANK_COLORS[1] }]}>
                {leaderboard[0]?.profile_pic ? (
                  <Image source={{ uri: leaderboard[0].profile_pic }} style={styles.podiumAvatarImgFirst} />
                ) : (
                  <Ionicons name="person" size={28} color="#fff" />
                )}
              </View>
              <Text style={styles.podiumName}>{leaderboard[0]?.name}</Text>
              <Text style={styles.podiumRep}>{leaderboard[0]?.reputation} REP</Text>
              <View style={[styles.podiumRank, { backgroundColor: RANK_COLORS[1], height: 80 }]}>
                <Text style={styles.podiumRankText}>1</Text>
              </View>
            </View>

            {/* 3rd Place */}
            <View style={styles.podiumItem}>
              <View style={[styles.podiumAvatar, { borderColor: RANK_COLORS[3] }]}>
                {leaderboard[2]?.profile_pic ? (
                  <Image source={{ uri: leaderboard[2].profile_pic }} style={styles.podiumAvatarImg} />
                ) : (
                  <Ionicons name="person" size={24} color="#fff" />
                )}
              </View>
              <Text style={styles.podiumName}>{leaderboard[2]?.name}</Text>
              <Text style={styles.podiumRep}>{leaderboard[2]?.reputation} REP</Text>
              <View style={[styles.podiumRank, { backgroundColor: RANK_COLORS[3], height: 40 }]}>
                <Text style={styles.podiumRankText}>3</Text>
              </View>
            </View>
          </View>
        )}

        {/* Rest of leaderboard */}
        <View style={styles.list}>
          {leaderboard.slice(3).map((entry) => (
            <View
              key={entry.id}
              style={[
                styles.listItem,
                entry.id === playerId && styles.myRank,
              ]}
            >
              <Text style={styles.rank}>#{entry.rank}</Text>
              <View
                style={[
                  styles.avatar,
                  { borderColor: CLASS_COLORS[entry.character_class] || '#e74c3c' },
                ]}
              >
                {entry.profile_pic ? (
                  <Image source={{ uri: entry.profile_pic }} style={styles.avatarImg} />
                ) : (
                  <Ionicons name="person" size={16} color="#fff" />
                )}
              </View>
              <View style={styles.info}>
                <Text style={styles.name}>
                  {entry.name}
                  {entry.id === playerId && <Text style={styles.youBadge}> (YOU)</Text>}
                </Text>
                <Text
                  style={[
                    styles.class,
                    { color: CLASS_COLORS[entry.character_class] || '#888' },
                  ]}
                >
                  Lv.{entry.level} {entry.character_class.replace('_', ' ')}
                </Text>
              </View>
              <View style={styles.stats}>
                <Text style={styles.reputation}>{entry.reputation}</Text>
                <Text style={styles.repLabel}>REP</Text>
              </View>
              <View style={styles.wins}>
                <Ionicons name="trophy" size={14} color="#27ae60" />
                <Text style={styles.winsText}>{entry.wins}</Text>
              </View>
            </View>
          ))}
        </View>

        {leaderboard.length === 0 && (
          <View style={styles.emptyState}>
            <Ionicons name="trophy-outline" size={64} color="#333" />
            <Text style={styles.emptyText}>No rankings yet</Text>
            <Text style={styles.emptySubtext}>Be the first to climb the ranks!</Text>
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
  scrollContent: {
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginLeft: 12,
  },
  podium: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'flex-end',
    marginBottom: 32,
    paddingTop: 40,
  },
  podiumItem: {
    alignItems: 'center',
    marginHorizontal: 8,
  },
  crown: {
    marginBottom: 4,
  },
  podiumAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#222',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    marginBottom: 8,
    overflow: 'hidden',
  },
  firstPlace: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  podiumAvatarImg: {
    width: 42,
    height: 42,
    borderRadius: 21,
  },
  podiumAvatarImgFirst: {
    width: 50,
    height: 50,
    borderRadius: 25,
  },
  podiumName: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
    marginBottom: 4,
  },
  podiumRep: {
    color: '#888',
    fontSize: 10,
    marginBottom: 8,
  },
  podiumRank: {
    width: 50,
    justifyContent: 'center',
    alignItems: 'center',
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
  },
  podiumRankText: {
    color: '#000',
    fontSize: 24,
    fontWeight: 'bold',
  },
  list: {
    gap: 8,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    padding: 12,
  },
  myRank: {
    borderWidth: 1,
    borderColor: '#e74c3c',
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
  },
  rank: {
    color: '#888',
    fontSize: 14,
    fontWeight: 'bold',
    width: 40,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#222',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    overflow: 'hidden',
  },
  avatarImg: {
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  info: {
    flex: 1,
    marginLeft: 12,
  },
  name: {
    color: '#fff',
    fontWeight: '600',
  },
  youBadge: {
    color: '#e74c3c',
    fontSize: 10,
  },
  class: {
    fontSize: 11,
    marginTop: 2,
  },
  stats: {
    alignItems: 'flex-end',
    marginRight: 16,
  },
  reputation: {
    color: '#f39c12',
    fontSize: 16,
    fontWeight: 'bold',
  },
  repLabel: {
    color: '#666',
    fontSize: 10,
  },
  wins: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(39, 174, 96, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  winsText: {
    color: '#27ae60',
    marginLeft: 4,
    fontWeight: 'bold',
    fontSize: 12,
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
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
});
