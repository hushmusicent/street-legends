import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  TextInput,
  ActivityIndicator,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useGameStore } from '../../stores/gameStore';
import { 
  startBattle, 
  getFriendsList, 
  searchPlayers, 
  getFriendRequests,
  acceptFriendRequest,
  rejectFriendRequest,
  sendFriendRequest,
  removeFriend,
} from '../../services/api';
import { FriendInfo, PlayerSearchResult } from '../../types/game';

const CLASS_COLORS: Record<string, string> = {
  street_soldier: '#e74c3c',
  hacker: '#3498db',
  enforcer: '#f39c12',
  ghost: '#9b59b6',
};

type TabType = 'friends' | 'requests' | 'search';

export default function PvPScreen() {
  const { player, playerId, setCurrentBattle } = useGameStore();
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('friends');
  const [friends, setFriends] = useState<FriendInfo[]>([]);
  const [friendRequests, setFriendRequests] = useState<PlayerSearchResult[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const loadFriends = useCallback(async () => {
    if (!playerId) return;
    try {
      const friendsList = await getFriendsList(playerId);
      setFriends(friendsList);
    } catch (error) {
      console.error('Failed to load friends:', error);
    }
  }, [playerId]);

  const loadFriendRequests = useCallback(async () => {
    if (!playerId) return;
    try {
      const requests = await getFriendRequests(playerId);
      setFriendRequests(requests);
    } catch (error) {
      console.error('Failed to load friend requests:', error);
    }
  }, [playerId]);

  useEffect(() => {
    if (playerId) {
      loadFriends();
      loadFriendRequests();
    }
  }, [playerId, loadFriends, loadFriendRequests]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadFriends(), loadFriendRequests()]);
    setRefreshing(false);
  };

  const handleSearch = async () => {
    if (searchQuery.length < 2) {
      Alert.alert('Search', 'Please enter at least 2 characters to search');
      return;
    }
    setIsSearching(true);
    try {
      const results = await searchPlayers(searchQuery);
      // Filter out self
      const filtered = results.filter(p => p.id !== playerId);
      setSearchResults(filtered);
    } catch (error) {
      console.error('Search failed:', error);
      Alert.alert('Error', 'Failed to search players');
    } finally {
      setIsSearching(false);
    }
  };

  const handleChallenge = async (targetPlayer: FriendInfo) => {
    if (!playerId) return;

    Alert.alert(
      'Challenge Friend',
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

  const handleAcceptRequest = async (requesterId: string, requesterName: string) => {
    if (!playerId) return;
    setLoadingAction(requesterId);
    try {
      await acceptFriendRequest(playerId, requesterId);
      Alert.alert('Success', `You are now friends with ${requesterName}!`);
      await Promise.all([loadFriends(), loadFriendRequests()]);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to accept request');
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRejectRequest = async (requesterId: string) => {
    if (!playerId) return;
    setLoadingAction(requesterId);
    try {
      await rejectFriendRequest(playerId, requesterId);
      await loadFriendRequests();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to reject request');
    } finally {
      setLoadingAction(null);
    }
  };

  const handleSendFriendRequest = async (targetId: string, targetName: string) => {
    if (!playerId) return;
    setLoadingAction(targetId);
    try {
      const result = await sendFriendRequest(playerId, targetId);
      if (result.became_friends) {
        Alert.alert('Friends!', `You are now friends with ${targetName}!`);
        await loadFriends();
      } else {
        Alert.alert('Request Sent', `Friend request sent to ${targetName}`);
      }
      // Re-search to update UI
      if (searchQuery.length >= 2) {
        handleSearch();
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send friend request');
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRemoveFriend = async (friendId: string, friendName: string) => {
    if (!playerId) return;
    
    Alert.alert(
      'Remove Friend',
      `Are you sure you want to remove ${friendName} from your friends list?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            setLoadingAction(friendId);
            try {
              await removeFriend(playerId, friendId);
              await loadFriends();
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to remove friend');
            } finally {
              setLoadingAction(null);
            }
          },
        },
      ]
    );
  };

  const getPlayerAvatar = (p: FriendInfo | PlayerSearchResult) => {
    const profilePic = 'profile_picture' in p ? p.profile_picture : undefined;
    const legacyPic = 'profile_pic' in p ? p.profile_pic : undefined;
    
    if (profilePic) {
      return <Image source={{ uri: profilePic }} style={styles.avatarImage} />;
    } else if (legacyPic && legacyPic.startsWith('data:')) {
      return <Image source={{ uri: legacyPic }} style={styles.avatarImage} />;
    }
    return <Ionicons name="person" size={24} color="#fff" />;
  };

  const isFriend = (targetId: string) => friends.some(f => f.id === targetId);

  const renderFriendCard = (friend: FriendInfo) => (
    <View key={friend.id} style={styles.playerCard}>
      <View style={styles.playerInfo}>
        <View
          style={[
            styles.playerAvatar,
            { borderColor: CLASS_COLORS[friend.character_class] || '#e74c3c' },
          ]}
        >
          {getPlayerAvatar(friend)}
        </View>
        <View style={styles.playerDetails}>
          <View style={styles.nameRow}>
            <Text style={styles.playerName}>{friend.name}</Text>
            {friend.is_online && <View style={styles.onlineDot} />}
          </View>
          <Text
            style={[
              styles.playerClass,
              { color: CLASS_COLORS[friend.character_class] || '#e74c3c' },
            ]}
          >
            {friend.character_class.replace('_', ' ').toUpperCase()}
          </Text>
          <Text style={styles.statsText}>
            W:{friend.wins} L:{friend.losses} • Rep:{friend.reputation}
          </Text>
        </View>
      </View>
      <View style={styles.actionsContainer}>
        <View style={styles.levelBadge}>
          <Text style={styles.levelText}>Lv.{friend.level}</Text>
        </View>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={styles.challengeButton}
            onPress={() => handleChallenge(friend)}
          >
            <Ionicons name="flash" size={16} color="#fff" />
            <Text style={styles.buttonText}>Fight</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.removeButton}
            onPress={() => handleRemoveFriend(friend.id, friend.name)}
            disabled={loadingAction === friend.id}
          >
            {loadingAction === friend.id ? (
              <ActivityIndicator size="small" color="#666" />
            ) : (
              <Ionicons name="person-remove" size={16} color="#666" />
            )}
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );

  const renderRequestCard = (request: PlayerSearchResult) => (
    <View key={request.id} style={styles.playerCard}>
      <View style={styles.playerInfo}>
        <View
          style={[
            styles.playerAvatar,
            { borderColor: CLASS_COLORS[request.character_class] || '#e74c3c' },
          ]}
        >
          {getPlayerAvatar(request)}
        </View>
        <View style={styles.playerDetails}>
          <Text style={styles.playerName}>{request.name}</Text>
          <Text
            style={[
              styles.playerClass,
              { color: CLASS_COLORS[request.character_class] || '#e74c3c' },
            ]}
          >
            {request.character_class.replace('_', ' ').toUpperCase()}
          </Text>
        </View>
      </View>
      <View style={styles.actionsContainer}>
        <View style={styles.levelBadge}>
          <Text style={styles.levelText}>Lv.{request.level}</Text>
        </View>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={styles.acceptButton}
            onPress={() => handleAcceptRequest(request.id, request.name)}
            disabled={loadingAction === request.id}
          >
            {loadingAction === request.id ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Ionicons name="checkmark" size={16} color="#fff" />
                <Text style={styles.buttonText}>Accept</Text>
              </>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.rejectButton}
            onPress={() => handleRejectRequest(request.id)}
            disabled={loadingAction === request.id}
          >
            <Ionicons name="close" size={16} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );

  const renderSearchResultCard = (result: PlayerSearchResult) => {
    const alreadyFriend = isFriend(result.id);
    
    return (
      <View key={result.id} style={styles.playerCard}>
        <View style={styles.playerInfo}>
          <View
            style={[
              styles.playerAvatar,
              { borderColor: CLASS_COLORS[result.character_class] || '#e74c3c' },
            ]}
          >
            {getPlayerAvatar(result)}
          </View>
          <View style={styles.playerDetails}>
            <Text style={styles.playerName}>{result.name}</Text>
            <Text
              style={[
                styles.playerClass,
                { color: CLASS_COLORS[result.character_class] || '#e74c3c' },
              ]}
            >
              {result.character_class.replace('_', ' ').toUpperCase()}
            </Text>
            <Text style={styles.statsText}>
              Wins:{result.wins} • Rep:{result.reputation}
            </Text>
          </View>
        </View>
        <View style={styles.actionsContainer}>
          <View style={styles.levelBadge}>
            <Text style={styles.levelText}>Lv.{result.level}</Text>
          </View>
          {alreadyFriend ? (
            <View style={styles.friendBadge}>
              <Ionicons name="checkmark-circle" size={14} color="#27ae60" />
              <Text style={styles.friendBadgeText}>Friend</Text>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.addFriendButton}
              onPress={() => handleSendFriendRequest(result.id, result.name)}
              disabled={loadingAction === result.id}
            >
              {loadingAction === result.id ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="person-add" size={14} color="#fff" />
                  <Text style={styles.buttonText}>Add</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </View>
      </View>
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
        <Text style={styles.subtitle}>Challenge your friends to battle</Text>

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
                : player?.wins ? '100' : '0'}%
            </Text>
            <Text style={styles.statLabel}>Win Rate</Text>
          </View>
        </View>

        {/* Tabs */}
        <View style={styles.tabContainer}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'friends' && styles.activeTab]}
            onPress={() => setActiveTab('friends')}
          >
            <Ionicons name="people" size={18} color={activeTab === 'friends' ? '#e74c3c' : '#666'} />
            <Text style={[styles.tabText, activeTab === 'friends' && styles.activeTabText]}>
              Friends ({friends.length})
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'requests' && styles.activeTab]}
            onPress={() => setActiveTab('requests')}
          >
            <Ionicons name="mail" size={18} color={activeTab === 'requests' ? '#e74c3c' : '#666'} />
            <Text style={[styles.tabText, activeTab === 'requests' && styles.activeTabText]}>
              Requests {friendRequests.length > 0 && `(${friendRequests.length})`}
            </Text>
            {friendRequests.length > 0 && <View style={styles.notificationDot} />}
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'search' && styles.activeTab]}
            onPress={() => setActiveTab('search')}
          >
            <Ionicons name="search" size={18} color={activeTab === 'search' ? '#e74c3c' : '#666'} />
            <Text style={[styles.tabText, activeTab === 'search' && styles.activeTabText]}>
              Find
            </Text>
          </TouchableOpacity>
        </View>

        {/* Friends Tab */}
        {activeTab === 'friends' && (
          <View style={styles.tabContent}>
            {friends.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="people-outline" size={64} color="#333" />
                <Text style={styles.emptyText}>No friends yet</Text>
                <Text style={styles.emptySubtext}>Search for players to add friends!</Text>
                <TouchableOpacity
                  style={styles.emptyButton}
                  onPress={() => setActiveTab('search')}
                >
                  <Ionicons name="search" size={16} color="#fff" />
                  <Text style={styles.emptyButtonText}>Find Players</Text>
                </TouchableOpacity>
              </View>
            ) : (
              friends.map(renderFriendCard)
            )}
          </View>
        )}

        {/* Requests Tab */}
        {activeTab === 'requests' && (
          <View style={styles.tabContent}>
            {friendRequests.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="mail-outline" size={64} color="#333" />
                <Text style={styles.emptyText}>No pending requests</Text>
                <Text style={styles.emptySubtext}>Friend requests will appear here</Text>
              </View>
            ) : (
              friendRequests.map(renderRequestCard)
            )}
          </View>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <View style={styles.tabContent}>
            <View style={styles.searchContainer}>
              <TextInput
                style={styles.searchInput}
                placeholder="Search by username..."
                placeholderTextColor="#666"
                value={searchQuery}
                onChangeText={setSearchQuery}
                onSubmitEditing={handleSearch}
                returnKeyType="search"
                autoCapitalize="none"
              />
              <TouchableOpacity
                style={styles.searchButton}
                onPress={handleSearch}
                disabled={isSearching}
              >
                {isSearching ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Ionicons name="search" size={20} color="#fff" />
                )}
              </TouchableOpacity>
            </View>

            {searchResults.length > 0 ? (
              searchResults.map(renderSearchResultCard)
            ) : searchQuery.length >= 2 && !isSearching ? (
              <View style={styles.emptyState}>
                <Ionicons name="search-outline" size={64} color="#333" />
                <Text style={styles.emptyText}>No players found</Text>
                <Text style={styles.emptySubtext}>Try a different search term</Text>
              </View>
            ) : (
              <View style={styles.emptyState}>
                <Ionicons name="search" size={64} color="#333" />
                <Text style={styles.emptyText}>Find Players</Text>
                <Text style={styles.emptySubtext}>Enter a username to search</Text>
              </View>
            )}
          </View>
        )}

        {/* Tips */}
        <View style={styles.tipsSection}>
          <Text style={styles.tipsTitle}>PVP TIPS</Text>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#3498db" />
            <Text style={styles.tipText}>Challenge friends directly from your friends list</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#3498db" />
            <Text style={styles.tipText}>Higher level players give more reputation</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="information-circle" size={16} color="#3498db" />
            <Text style={styles.tipText}>Use skills strategically to win battles</Text>
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
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 6,
  },
  activeTab: {
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
  },
  tabText: {
    color: '#666',
    fontSize: 13,
    fontWeight: '600',
  },
  activeTabText: {
    color: '#e74c3c',
  },
  notificationDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#e74c3c',
    position: 'absolute',
    top: 8,
    right: 8,
  },
  tabContent: {
    minHeight: 200,
  },
  searchContainer: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: '#fff',
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  searchButton: {
    backgroundColor: '#e74c3c',
    borderRadius: 12,
    paddingHorizontal: 20,
    justifyContent: 'center',
    alignItems: 'center',
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
    textAlign: 'center',
  },
  emptyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e74c3c',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 20,
    gap: 8,
  },
  emptyButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  playerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
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
    overflow: 'hidden',
  },
  avatarImage: {
    width: '100%',
    height: '100%',
    borderRadius: 24,
  },
  playerDetails: {
    marginLeft: 12,
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  playerName: {
    color: '#fff',
    fontSize: 15,
    fontWeight: 'bold',
  },
  onlineDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#27ae60',
  },
  playerClass: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
    marginTop: 2,
  },
  statsText: {
    color: '#666',
    fontSize: 11,
    marginTop: 2,
  },
  actionsContainer: {
    alignItems: 'flex-end',
    gap: 8,
  },
  levelBadge: {
    backgroundColor: '#333',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  levelText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: 'bold',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 6,
  },
  challengeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e74c3c',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    gap: 4,
  },
  acceptButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#27ae60',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    gap: 4,
  },
  rejectButton: {
    backgroundColor: '#c0392b',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 6,
  },
  removeButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 6,
  },
  addFriendButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#3498db',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    gap: 4,
  },
  friendBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(39, 174, 96, 0.2)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    gap: 4,
  },
  friendBadgeText: {
    color: '#27ae60',
    fontSize: 12,
    fontWeight: '600',
  },
  buttonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
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
});
