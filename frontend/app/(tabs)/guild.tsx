import React, { useEffect, useState, useRef, useCallback } from 'react';
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
  KeyboardAvoidingView,
  Platform,
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
  getGuildChat,
  sendGuildMessage,
  GuildChatMessage,
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
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<GuildChatMessage[]>([]);
  const [chatMessage, setChatMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const chatScrollRef = useRef<ScrollView>(null);
  const chatPollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadData();
    return () => {
      // Clean up chat polling on unmount
      if (chatPollRef.current) {
        clearInterval(chatPollRef.current);
      }
    };
  }, []);

  // Start chat polling when player has a guild
  useEffect(() => {
    if (playerGuild && playerId) {
      loadChatMessages();
      // Poll for new messages every 5 seconds
      chatPollRef.current = setInterval(() => {
        loadChatMessages(true);
      }, 5000);
    } else {
      setChatMessages([]);
      if (chatPollRef.current) {
        clearInterval(chatPollRef.current);
      }
    }
    
    return () => {
      if (chatPollRef.current) {
        clearInterval(chatPollRef.current);
      }
    };
  }, [playerGuild?.id, playerId]);

  const loadChatMessages = async (silent: boolean = false) => {
    if (!playerGuild?.id || !playerId) return;
    
    if (!silent) setLoadingChat(true);
    try {
      const messages = await getGuildChat(playerGuild.id, playerId);
      setChatMessages(messages);
      // Scroll to bottom on new messages
      setTimeout(() => {
        chatScrollRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error) {
      console.error('Failed to load chat:', error);
    } finally {
      setLoadingChat(false);
    }
  };

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
    if (playerGuild) {
      await loadChatMessages();
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
              setChatMessages([]);
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

  const handleSendMessage = async () => {
    if (!chatMessage.trim() || !playerGuild?.id || !playerId || sendingMessage) return;
    
    const messageText = chatMessage.trim();
    setChatMessage('');
    setSendingMessage(true);
    
    try {
      const newMessage = await sendGuildMessage(playerGuild.id, playerId, messageText);
      setChatMessages(prev => [...prev, newMessage]);
      setTimeout(() => {
        chatScrollRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send message');
      setChatMessage(messageText); // Restore message on error
    } finally {
      setSendingMessage(false);
    }
  };

  const formatMessageTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    
    if (minutes < 1) return 'now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  // Calculate guild's total reputation from all members
  const guildTotalRep = playerGuild?.member_details?.reduce(
    (sum, member) => sum + (member.reputation || 0), 0
  ) || playerGuild?.total_reputation || 0;

  const otherGuilds = guilds.filter(g => g.id !== playerGuild?.id);

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#e74c3c" />
          }
        >
          <Text style={styles.title}>GUILD</Text>

          {/* Player's Guild */}
          {playerGuild ? (
            <>
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

                {/* Prominent Reputation Display */}
                <View style={styles.reputationCard}>
                  <View style={styles.reputationHeader}>
                    <Ionicons name="star" size={28} color="#f39c12" />
                    <Text style={styles.reputationTitle}>GUILD REPUTATION</Text>
                  </View>
                  <Text style={styles.reputationScore}>{guildTotalRep.toLocaleString()}</Text>
                  <Text style={styles.reputationSubtext}>Combined rep from all members</Text>
                </View>

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
                    <Ionicons name="flash" size={20} color="#9b59b6" />
                    <Text style={styles.guildStatValue}>{playerGuild.level}</Text>
                    <Text style={styles.guildStatLabel}>Level</Text>
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
                    <View style={styles.memberRep}>
                      <Ionicons name="star" size={12} color="#f39c12" />
                      <Text style={styles.memberRepText}>{member.reputation || 0}</Text>
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

              {/* Guild Chat Section */}
              <View style={styles.chatSection}>
                <View style={styles.chatHeader}>
                  <Ionicons name="chatbubbles" size={20} color="#3498db" />
                  <Text style={styles.chatTitle}>GUILD CHAT</Text>
                  <View style={styles.chatOnlineBadge}>
                    <View style={styles.onlineDot} />
                    <Text style={styles.chatOnlineText}>Live</Text>
                  </View>
                </View>
                
                <View style={styles.chatContainer}>
                  <ScrollView 
                    ref={chatScrollRef}
                    style={styles.chatScroll}
                    contentContainerStyle={styles.chatScrollContent}
                    nestedScrollEnabled={true}
                    showsVerticalScrollIndicator={true}
                  >
                    {loadingChat && chatMessages.length === 0 ? (
                      <View style={styles.chatLoading}>
                        <Text style={styles.chatLoadingText}>Loading chat...</Text>
                      </View>
                    ) : chatMessages.length === 0 ? (
                      <View style={styles.chatEmpty}>
                        <Ionicons name="chatbubble-outline" size={32} color="#333" />
                        <Text style={styles.chatEmptyText}>No messages yet</Text>
                        <Text style={styles.chatEmptySubtext}>Be the first to say something!</Text>
                      </View>
                    ) : (
                      chatMessages.map((msg) => {
                        const isOwnMessage = msg.player_id === playerId;
                        return (
                          <View 
                            key={msg.id} 
                            style={[
                              styles.chatMessage,
                              isOwnMessage && styles.chatMessageOwn
                            ]}
                          >
                            <View style={styles.chatMessageHeader}>
                              <Text style={[
                                styles.chatMessageName,
                                isOwnMessage && styles.chatMessageNameOwn
                              ]}>
                                {msg.player_name}
                              </Text>
                              <Text style={styles.chatMessageLevel}>Lv.{msg.player_level}</Text>
                              <Text style={styles.chatMessageTime}>{formatMessageTime(msg.timestamp)}</Text>
                            </View>
                            <Text style={styles.chatMessageText}>{msg.message}</Text>
                          </View>
                        );
                      })
                    )}
                  </ScrollView>
                </View>
                
                {/* Chat Input */}
                <View style={styles.chatInputContainer}>
                  <TextInput
                    style={styles.chatInput}
                    placeholder="Type a message..."
                    placeholderTextColor="#555"
                    value={chatMessage}
                    onChangeText={setChatMessage}
                    maxLength={500}
                    multiline
                    editable={!sendingMessage}
                  />
                  <TouchableOpacity 
                    style={[
                      styles.chatSendButton,
                      (!chatMessage.trim() || sendingMessage) && styles.chatSendButtonDisabled
                    ]}
                    onPress={handleSendMessage}
                    disabled={!chatMessage.trim() || sendingMessage}
                  >
                    <Ionicons 
                      name={sendingMessage ? "hourglass" : "send"} 
                      size={20} 
                      color={!chatMessage.trim() || sendingMessage ? "#555" : "#fff"} 
                    />
                  </TouchableOpacity>
                </View>
              </View>
            </>
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

          {/* Other Guilds Section - Separate Scrollable Window */}
          <View style={styles.otherGuildsSection}>
            <View style={styles.otherGuildsHeader}>
              <Ionicons name="globe-outline" size={20} color="#888" />
              <Text style={styles.otherGuildsTitle}>
                {playerGuild ? 'OTHER GUILDS' : 'AVAILABLE GUILDS'}
              </Text>
              <Text style={styles.otherGuildsCount}>{otherGuilds.length}</Text>
            </View>
            
            <View style={styles.otherGuildsContainer}>
              <ScrollView 
                style={styles.otherGuildsScroll}
                nestedScrollEnabled={true}
                showsVerticalScrollIndicator={true}
              >
                {otherGuilds.length === 0 ? (
                  <View style={styles.emptyGuildsContainer}>
                    <Ionicons name="search-outline" size={32} color="#444" />
                    <Text style={styles.emptyText}>
                      {playerGuild 
                        ? 'No other guilds exist yet.' 
                        : 'No guilds available. Be the first to create one!'}
                    </Text>
                  </View>
                ) : (
                  otherGuilds.map((guild) => (
                    <View key={guild.id} style={styles.guildCard}>
                      <View style={styles.guildCardHeader}>
                        <View style={styles.guildCardLeft}>
                          <View style={styles.guildCardIcon}>
                            <Ionicons name="shield-half" size={18} color="#e74c3c" />
                          </View>
                          <View>
                            <Text style={styles.guildCardName}>{guild.name}</Text>
                            <Text style={styles.guildCardTag}>[{guild.tag}]</Text>
                          </View>
                        </View>
                        <View style={styles.guildCardLevel}>
                          <Text style={styles.guildCardLevelText}>Lv.{guild.level}</Text>
                        </View>
                      </View>
                      <Text style={styles.guildCardDesc} numberOfLines={2}>{guild.description}</Text>
                      <View style={styles.guildCardFooter}>
                        <View style={styles.guildCardStats}>
                          <View style={styles.guildCardStatItem}>
                            <Ionicons name="people" size={14} color="#888" />
                            <Text style={styles.guildCardStatText}>{guild.members?.length || 0}</Text>
                          </View>
                          <View style={styles.guildCardStatItem}>
                            <Ionicons name="star" size={14} color="#f39c12" />
                            <Text style={styles.guildCardStatText}>{guild.total_reputation || 0}</Text>
                          </View>
                        </View>
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
              </ScrollView>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

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
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
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
    marginBottom: 16,
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
  // Reputation Card Styles
  reputationCard: {
    backgroundColor: 'rgba(243, 156, 18, 0.1)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 2,
    borderColor: 'rgba(243, 156, 18, 0.3)',
    alignItems: 'center',
  },
  reputationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  reputationTitle: {
    color: '#f39c12',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 2,
    marginLeft: 8,
  },
  reputationScore: {
    color: '#f39c12',
    fontSize: 48,
    fontWeight: '900',
    textShadowColor: 'rgba(243, 156, 18, 0.5)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 10,
  },
  reputationSubtext: {
    color: '#888',
    fontSize: 12,
    marginTop: 4,
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
    flex: 1,
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
  memberRep: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(243, 156, 18, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  memberRepText: {
    color: '#f39c12',
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 4,
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
  // Chat Section Styles
  chatSection: {
    backgroundColor: 'rgba(52, 152, 219, 0.05)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(52, 152, 219, 0.3)',
    marginBottom: 16,
  },
  chatHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(52, 152, 219, 0.2)',
  },
  chatTitle: {
    color: '#3498db',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 2,
    marginLeft: 8,
    flex: 1,
  },
  chatOnlineBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(46, 204, 113, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  onlineDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#2ecc71',
    marginRight: 4,
  },
  chatOnlineText: {
    color: '#2ecc71',
    fontSize: 10,
    fontWeight: '600',
  },
  chatContainer: {
    height: 250,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 12,
  },
  chatScroll: {
    flex: 1,
  },
  chatScrollContent: {
    padding: 12,
    flexGrow: 1,
  },
  chatLoading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    height: 200,
  },
  chatLoadingText: {
    color: '#666',
    fontSize: 14,
  },
  chatEmpty: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    height: 200,
  },
  chatEmptyText: {
    color: '#666',
    fontSize: 14,
    marginTop: 8,
  },
  chatEmptySubtext: {
    color: '#444',
    fontSize: 12,
    marginTop: 4,
  },
  chatMessage: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#444',
  },
  chatMessageOwn: {
    backgroundColor: 'rgba(52, 152, 219, 0.15)',
    borderLeftColor: '#3498db',
  },
  chatMessageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  chatMessageName: {
    color: '#aaa',
    fontSize: 12,
    fontWeight: '600',
  },
  chatMessageNameOwn: {
    color: '#3498db',
  },
  chatMessageLevel: {
    color: '#666',
    fontSize: 10,
    marginLeft: 6,
  },
  chatMessageTime: {
    color: '#555',
    fontSize: 10,
    marginLeft: 'auto',
  },
  chatMessageText: {
    color: '#ddd',
    fontSize: 14,
    lineHeight: 20,
  },
  chatInputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  chatInput: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 12,
    padding: 12,
    paddingTop: 12,
    color: '#fff',
    fontSize: 14,
    maxHeight: 80,
    borderWidth: 1,
    borderColor: '#333',
  },
  chatSendButton: {
    backgroundColor: '#3498db',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
  },
  chatSendButtonDisabled: {
    backgroundColor: '#222',
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
  // Other Guilds Section Styles
  otherGuildsSection: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#222',
  },
  otherGuildsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  otherGuildsTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginLeft: 8,
    flex: 1,
  },
  otherGuildsCount: {
    color: '#666',
    fontSize: 12,
    backgroundColor: '#222',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  otherGuildsContainer: {
    maxHeight: 250,
    borderRadius: 12,
    overflow: 'hidden',
  },
  otherGuildsScroll: {
    maxHeight: 250,
  },
  emptyGuildsContainer: {
    alignItems: 'center',
    padding: 30,
  },
  emptyText: {
    color: '#666',
    textAlign: 'center',
    marginTop: 12,
  },
  guildCard: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#1a1a1a',
  },
  guildCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  guildCardLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  guildCardIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  guildCardName: {
    color: '#fff',
    fontSize: 15,
    fontWeight: 'bold',
  },
  guildCardTag: {
    color: '#e74c3c',
    fontSize: 11,
  },
  guildCardLevel: {
    backgroundColor: '#333',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  guildCardLevelText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
  },
  guildCardDesc: {
    color: '#777',
    fontSize: 12,
    marginBottom: 10,
    lineHeight: 16,
  },
  guildCardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  guildCardStats: {
    flexDirection: 'row',
    gap: 12,
  },
  guildCardStatItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  guildCardStatText: {
    color: '#888',
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
