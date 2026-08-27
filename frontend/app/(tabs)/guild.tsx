import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  RefreshControl,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import { GameButton } from '../../components/GameButton';
import {
  getGuild,
  createGuild,
  joinGuild,
  leaveGuild,
  listGuilds,
  getPlayer,
} from '../../services/api';
import { Guild } from '../../types/game';

export default function GuildScreen() {
  const { player, playerId, setPlayer, playerGuild, setPlayerGuild } = useGameStore();
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newGuildName, setNewGuildName] = useState('');
  const [newGuildTag, setNewGuildTag] = useState('');
  const [newGuildDesc, setNewGuildDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const guildsList = await listGuilds();
      setGuilds(guildsList);

      if (player?.guild_id) {
        const guild = await getGuild(player.guild_id);
        setPlayerGuild(guild);
      }
    } catch (error) {
      console.error('Failed to load guilds:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    if (playerId) {
      const playerData = await getPlayer(playerId);
      setPlayer(playerData);
    }
    setRefreshing(false);
  };

  const handleCreateGuild = async () => {
    if (!newGuildName || !newGuildTag || !playerId) return;

    try {
      setCreating(true);
      const guild = await createGuild(newGuildName, newGuildTag, newGuildDesc, playerId);
      setPlayerGuild(guild);
      setShowCreateModal(false);
      setNewGuildName('');
      setNewGuildTag('');
      setNewGuildDesc('');
      await handleRefresh();
      Alert.alert('Success', 'Guild created successfully!');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create guild');
    } finally {
      setCreating(false);
    }
  };

  const handleJoinGuild = async (guildId: string) => {
    if (!playerId) return;

    try {
      await joinGuild(guildId, playerId);
      await handleRefresh();
      Alert.alert('Success', 'Joined guild successfully!');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to join guild');
    }
  };

  const handleLeaveGuild = async () => {
    if (!player?.guild_id || !playerId) return;

    Alert.alert(
      'Leave Guild',
      'Are you sure you want to leave your guild?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Leave',
          style: 'destructive',
          onPress: async () => {
            try {
              await leaveGuild(player.guild_id!, playerId);
              setPlayerGuild(null);
              await handleRefresh();
              Alert.alert('Success', 'Left guild successfully!');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to leave guild');
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
        <Text style={styles.title}>GUILD</Text>

        {/* Player's Guild */}
        {playerGuild ? (
          <View style={styles.myGuildSection}>
            <View style={styles.guildHeader}>
              <View style={styles.guildIcon}>
                <Ionicons name="shield" size={40} color="#e74c3c" />
              </View>
              <View style={styles.guildInfo}>
                <Text style={styles.guildName}>{playerGuild.name}</Text>
                <Text style={styles.guildTag}>[{playerGuild.tag}]</Text>
              </View>
              <View style={styles.guildLevel}>
                <Text style={styles.guildLevelLabel}>LV</Text>
                <Text style={styles.guildLevelValue}>{playerGuild.level}</Text>
              </View>
            </View>

            <Text style={styles.guildDescription}>{playerGuild.description}</Text>

            <View style={styles.guildStats}>
              <View style={styles.guildStat}>
                <Ionicons name="people" size={20} color="#3498db" />
                <Text style={styles.guildStatValue}>{playerGuild.members?.length || 0}</Text>
                <Text style={styles.guildStatLabel}>Members</Text>
              </View>
              <View style={styles.guildStat}>
                <Ionicons name="trophy" size={20} color="#f39c12" />
                <Text style={styles.guildStatValue}>{playerGuild.total_wins}</Text>
                <Text style={styles.guildStatLabel}>Wins</Text>
              </View>
              <View style={styles.guildStat}>
                <Ionicons name="flag" size={20} color="#e74c3c" />
                <Text style={styles.guildStatValue}>{playerGuild.territory_count}</Text>
                <Text style={styles.guildStatLabel}>Territories</Text>
              </View>
            </View>

            {/* Members List */}
            <Text style={styles.sectionTitle}>MEMBERS</Text>
            {playerGuild.member_details?.map((member) => (
              <View key={member.id} style={styles.memberRow}>
                <View style={styles.memberAvatar}>
                  <Ionicons name="person" size={16} color="#fff" />
                </View>
                <View style={styles.memberInfo}>
                  <Text style={styles.memberName}>
                    {member.name}
                    {member.id === playerGuild.leader_id && (
                      <Text style={styles.leaderBadge}> LEADER</Text>
                    )}
                  </Text>
                  <Text style={styles.memberClass}>
                    Lv.{member.level} {member.character_class.replace('_', ' ')}
                  </Text>
                </View>
              </View>
            ))}

            {player?.id !== playerGuild.leader_id && (
              <TouchableOpacity style={styles.leaveButton} onPress={handleLeaveGuild}>
                <Ionicons name="exit" size={20} color="#e74c3c" />
                <Text style={styles.leaveButtonText}>Leave Guild</Text>
              </TouchableOpacity>
            )}
          </View>
        ) : (
          <View style={styles.noGuildSection}>
            <Ionicons name="people-outline" size={64} color="#333" />
            <Text style={styles.noGuildText}>You are not in a guild</Text>
            <Text style={styles.noGuildSubtext}>Join or create a guild to team up!</Text>
            <GameButton
              title="CREATE GUILD"
              onPress={() => setShowCreateModal(true)}
              icon="add"
              variant="primary"
              style={styles.createButton}
            />
          </View>
        )}

        {/* Available Guilds - Show for everyone, filter out own guild */}
        <View style={styles.availableSection}>
          <Text style={styles.sectionTitle}>
            {playerGuild ? 'OTHER GUILDS' : 'AVAILABLE GUILDS'}
          </Text>
          {guilds.filter(g => g.id !== playerGuild?.id).length === 0 ? (
            <Text style={styles.emptyText}>
              {playerGuild 
                ? 'No other guilds exist yet.' 
                : 'No guilds available. Be the first to create one!'}
            </Text>
          ) : (
            guilds
              .filter(g => g.id !== playerGuild?.id)
              .map((guild) => (
                <View key={guild.id} style={styles.guildCard}>
                  <View style={styles.guildCardHeader}>
                    <View>
                      <Text style={styles.guildCardName}>{guild.name}</Text>
                      <Text style={styles.guildCardTag}>[{guild.tag}]</Text>
                    </View>
                    <View style={styles.guildCardLevel}>
                      <Text style={styles.guildCardLevelText}>Lv.{guild.level}</Text>
                    </View>
                  </View>
                  <Text style={styles.guildCardDesc}>{guild.description}</Text>
                  <View style={styles.guildCardFooter}>
                    <Text style={styles.guildCardMembers}>
                      <Ionicons name="people" size={14} color="#888" /> {guild.members?.length || 0} members
                    </Text>
                    {!playerGuild && (
                      <TouchableOpacity
                        style={styles.joinButton}
                        onPress={() => handleJoinGuild(guild.id)}
                      >
                        <Text style={styles.joinButtonText}>JOIN</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              ))
          )}
        </View>
      </ScrollView>

      {/* Create Guild Modal */}
      <Modal visible={showCreateModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <TouchableOpacity
              style={styles.modalClose}
              onPress={() => setShowCreateModal(false)}
            >
              <Ionicons name="close" size={24} color="#888" />
            </TouchableOpacity>

            <Text style={styles.modalTitle}>CREATE GUILD</Text>

            <TextInput
              style={styles.input}
              placeholder="Guild Name"
              placeholderTextColor="#555"
              value={newGuildName}
              onChangeText={setNewGuildName}
              maxLength={20}
            />

            <TextInput
              style={styles.input}
              placeholder="Tag (3-5 chars)"
              placeholderTextColor="#555"
              value={newGuildTag}
              onChangeText={setNewGuildTag}
              maxLength={5}
              autoCapitalize="characters"
            />

            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Description"
              placeholderTextColor="#555"
              value={newGuildDesc}
              onChangeText={setNewGuildDesc}
              maxLength={100}
              multiline
              numberOfLines={3}
            />

            <GameButton
              title="CREATE"
              onPress={handleCreateGuild}
              icon="shield"
              variant="primary"
              loading={creating}
              disabled={!newGuildName || !newGuildTag}
            />
          </View>
        </View>
      </Modal>
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
    marginBottom: 24,
  },
  myGuildSection: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#e74c3c',
  },
  guildHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  guildIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(231, 76, 60, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  guildInfo: {
    flex: 1,
    marginLeft: 16,
  },
  guildName: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
  },
  guildTag: {
    fontSize: 14,
    color: '#e74c3c',
    fontWeight: '600',
  },
  guildLevel: {
    backgroundColor: '#e74c3c',
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
  },
  guildLevelLabel: {
    fontSize: 10,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  guildLevelValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  guildDescription: {
    color: '#888',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  guildStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  guildStat: {
    alignItems: 'center',
  },
  guildStatValue: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 4,
  },
  guildStatLabel: {
    color: '#666',
    fontSize: 10,
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 12,
  },
  memberRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  memberAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#333',
    justifyContent: 'center',
    alignItems: 'center',
  },
  memberInfo: {
    marginLeft: 12,
  },
  memberName: {
    color: '#fff',
    fontWeight: '600',
  },
  leaderBadge: {
    color: '#f39c12',
    fontSize: 10,
  },
  memberClass: {
    color: '#666',
    fontSize: 12,
  },
  leaveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderWidth: 1,
    borderColor: '#e74c3c',
    borderRadius: 8,
    marginTop: 16,
  },
  leaveButtonText: {
    color: '#e74c3c',
    fontWeight: '600',
    marginLeft: 8,
  },
  noGuildSection: {
    alignItems: 'center',
    padding: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    marginBottom: 24,
  },
  noGuildText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
  },
  noGuildSubtext: {
    color: '#666',
    marginTop: 8,
    marginBottom: 24,
  },
  createButton: {
    width: '100%',
  },
  availableSection: {
    marginTop: 24,
  },
  emptyText: {
    color: '#666',
    textAlign: 'center',
    padding: 20,
  },
  guildCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#222',
  },
  guildCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  guildCardName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  guildCardTag: {
    color: '#e74c3c',
    fontSize: 12,
  },
  guildCardLevel: {
    backgroundColor: '#333',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  guildCardLevelText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  guildCardDesc: {
    color: '#888',
    fontSize: 13,
    marginBottom: 12,
  },
  guildCardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  guildCardMembers: {
    color: '#666',
    fontSize: 12,
  },
  joinButton: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 6,
  },
  joinButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
  },
  modalClose: {
    position: 'absolute',
    top: 16,
    right: 16,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 24,
  },
  input: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 8,
    padding: 16,
    color: '#fff',
    fontSize: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
});
