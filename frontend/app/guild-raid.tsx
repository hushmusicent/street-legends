import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { GameButton } from '../components/GameButton';
import {
  startGuildRaid,
  joinGuildRaid,
  leaveGuildRaid,
  beginGuildRaid,
  getActiveGuildRaid,
  getAvailableGuildRaids,
  guildRaidFight,
  retreatGuildRaid,
  getGuildRaidHistory,
  getPlayer,
  GuildRaid,
} from '../services/api';

const MAX_RAID_LEVELS = 20;
const MAX_PLAYERS = 3;

export default function GuildRaidScreen() {
  const { playerId, playerGuild, setPlayer } = useGameStore();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeRaid, setActiveRaid] = useState<GuildRaid | null>(null);
  const [availableRaids, setAvailableRaids] = useState<GuildRaid[]>([]);
  const [raidHistory, setRaidHistory] = useState<GuildRaid[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const shakeAnim = useRef(new Animated.Value(0)).current;
  const combatLogRef = useRef<ScrollView>(null);

  useEffect(() => {
    loadRaidData();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    // Poll for updates when in a raid
    if (activeRaid && (activeRaid.status === 'waiting' || activeRaid.status === 'in_progress')) {
      pollRef.current = setInterval(() => {
        loadRaidData(true);
      }, 3000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [activeRaid?.status]);

  const loadRaidData = async (silent: boolean = false) => {
    if (!playerGuild?.id || !playerId) return;
    if (!silent) setLoading(true);
    try {
      const [active, available, history] = await Promise.all([
        getActiveGuildRaid(playerGuild.id, playerId),
        getAvailableGuildRaids(playerGuild.id, playerId),
        getGuildRaidHistory(playerGuild.id, playerId, 5),
      ]);
      setActiveRaid(active);
      setAvailableRaids(available);
      setRaidHistory(history);
      
      // Scroll to bottom of combat log
      setTimeout(() => {
        combatLogRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error) {
      console.error('Failed to load raid data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartRaid = async () => {
    if (!playerGuild?.id || !playerId) return;
    try {
      setProcessing(true);
      const raid = await startGuildRaid(playerGuild.id, playerId);
      setActiveRaid(raid);
      Alert.alert('Raid Created!', 'Waiting for other guild members to join...');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start raid');
    } finally {
      setProcessing(false);
    }
  };

  const handleJoinRaid = async (raidId: string) => {
    if (!playerGuild?.id || !playerId) return;
    try {
      setProcessing(true);
      const raid = await joinGuildRaid(playerGuild.id, raidId, playerId);
      setActiveRaid(raid);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to join raid');
    } finally {
      setProcessing(false);
    }
  };

  const handleLeaveRaid = async () => {
    if (!playerGuild?.id || !playerId || !activeRaid) return;
    Alert.alert('Leave Raid', 'Are you sure you want to leave this raid?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Leave',
        style: 'destructive',
        onPress: async () => {
          try {
            setProcessing(true);
            await leaveGuildRaid(playerGuild.id, activeRaid.id, playerId);
            setActiveRaid(null);
            await loadRaidData();
          } catch (error: any) {
            Alert.alert('Error', error.response?.data?.detail || 'Failed to leave raid');
          } finally {
            setProcessing(false);
          }
        },
      },
    ]);
  };

  const handleBeginRaid = async () => {
    if (!playerGuild?.id || !playerId || !activeRaid) return;
    try {
      setProcessing(true);
      const raid = await beginGuildRaid(playerGuild.id, activeRaid.id, playerId);
      setActiveRaid(raid);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to begin raid');
    } finally {
      setProcessing(false);
    }
  };

  const handleFight = async (action: 'attack' | 'defend') => {
    if (!playerGuild?.id || !playerId || !activeRaid || processing) return;
    try {
      setProcessing(true);
      
      // Shake animation for attacks
      if (action === 'attack') {
        Animated.sequence([
          Animated.timing(shakeAnim, { toValue: 10, duration: 50, useNativeDriver: true }),
          Animated.timing(shakeAnim, { toValue: -10, duration: 50, useNativeDriver: true }),
          Animated.timing(shakeAnim, { toValue: 10, duration: 50, useNativeDriver: true }),
          Animated.timing(shakeAnim, { toValue: 0, duration: 50, useNativeDriver: true }),
        ]).start();
      }
      
      const raid = await guildRaidFight(playerGuild.id, activeRaid.id, playerId, action);
      setActiveRaid(raid);
      
      // If raid ended, refresh player data for updated rewards
      if (raid.status === 'completed' || raid.status === 'failed' || raid.status === 'retreated') {
        const playerData = await getPlayer(playerId);
        setPlayer(playerData);
        
        const status = raid.status === 'completed' ? '🏆 Victory!' : 
                       raid.status === 'failed' ? '💀 Defeat' : '🏳️ Retreated';
        const rewards = raid.final_rewards_per_player;
        Alert.alert(
          status,
          `Enemies Defeated: ${raid.enemies_defeated}\n\nYour Share:\n💰 $${rewards?.cash || 0}\n⭐ ${rewards?.xp || 0} XP\n🔥 ${rewards?.reputation || 0} Rep`
        );
      }
      
      setTimeout(() => {
        combatLogRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to execute action');
    } finally {
      setProcessing(false);
    }
  };

  const handleRetreat = async () => {
    if (!playerGuild?.id || !playerId || !activeRaid) return;
    Alert.alert(
      'Retreat from Raid',
      'Are you sure? You will keep accumulated rewards but the raid will end.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Retreat',
          style: 'destructive',
          onPress: async () => {
            try {
              setProcessing(true);
              const raid = await retreatGuildRaid(playerGuild.id, activeRaid.id, playerId);
              setActiveRaid(raid);
              
              // Refresh player data
              const playerData = await getPlayer(playerId);
              setPlayer(playerData);
              
              const rewards = raid.final_rewards_per_player;
              Alert.alert(
                '🏳️ Retreated',
                `Enemies Defeated: ${raid.enemies_defeated}\n\nYour Share:\n💰 $${rewards?.cash || 0}\n⭐ ${rewards?.xp || 0} XP\n🔥 ${rewards?.reputation || 0} Rep`
              );
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to retreat');
            } finally {
              setProcessing(false);
            }
          },
        },
      ]
    );
  };

  const isLeader = activeRaid?.leader_id === playerId;

  if (!playerGuild) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.title}>GUILD RAIDS</Text>
        </View>
        <View style={styles.noGuildContainer}>
          <Ionicons name="shield-outline" size={64} color="#444" />
          <Text style={styles.noGuildText}>Join a guild to participate in raids!</Text>
          <GameButton title="GO TO GUILDS" onPress={() => router.push('/(tabs)/guild')} variant="primary" />
        </View>
      </SafeAreaView>
    );
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#9b59b6" />
          <Text style={styles.loadingText}>Loading raids...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Active raid in progress
  if (activeRaid && activeRaid.status === 'in_progress') {
    const enemy = activeRaid.current_enemy;
    const progress = (activeRaid.current_level / MAX_RAID_LEVELS) * 100;
    
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Header */}
          <View style={styles.raidHeader}>
            <Text style={styles.raidTitle}>⚔️ GUILD RAID</Text>
            <View style={styles.levelBadge}>
              <Text style={styles.levelBadgeText}>Level {activeRaid.current_level}/{MAX_RAID_LEVELS}</Text>
            </View>
          </View>

          {/* Progress Bar */}
          <View style={styles.progressContainer}>
            <View style={styles.progressBar}>
              <View style={[styles.progressFill, { width: `${progress}%` }]} />
            </View>
            <Text style={styles.progressText}>{activeRaid.enemies_defeated} enemies defeated</Text>
          </View>

          {/* Accumulated Rewards */}
          <View style={styles.rewardsCard}>
            <Text style={styles.rewardsTitle}>Accumulated Rewards</Text>
            <View style={styles.rewardsRow}>
              <View style={styles.rewardItem}>
                <Ionicons name="cash" size={16} color="#2ecc71" />
                <Text style={styles.rewardText}>${activeRaid.accumulated_rewards.cash}</Text>
              </View>
              <View style={styles.rewardItem}>
                <Ionicons name="star" size={16} color="#f39c12" />
                <Text style={styles.rewardText}>{activeRaid.accumulated_rewards.xp} XP</Text>
              </View>
              <View style={styles.rewardItem}>
                <Ionicons name="flame" size={16} color="#e74c3c" />
                <Text style={styles.rewardText}>{activeRaid.accumulated_rewards.reputation} Rep</Text>
              </View>
            </View>
          </View>

          {/* Enemy Card */}
          {enemy && (
            <Animated.View style={[styles.enemyCard, { transform: [{ translateX: shakeAnim }] }]}>
              <View style={styles.enemyHeader}>
                <Text style={[styles.enemyName, enemy.is_boss && styles.bossName]}>
                  {enemy.is_boss ? '👑 ' : ''}{enemy.name}
                </Text>
                <Text style={styles.enemyLevel}>Lv.{enemy.level}</Text>
              </View>
              <View style={styles.healthBarContainer}>
                <View style={styles.healthBarBg}>
                  <View 
                    style={[
                      styles.healthBarFill, 
                      { width: `${(enemy.stats.health / enemy.stats.max_health) * 100}%` },
                      enemy.is_boss && styles.bossHealthBar
                    ]} 
                  />
                </View>
                <Text style={styles.healthText}>
                  {enemy.stats.health}/{enemy.stats.max_health} HP
                </Text>
              </View>
              <View style={styles.enemyStats}>
                <Text style={styles.enemyStat}>⚔️ ATK: {enemy.stats.attack}</Text>
                <Text style={styles.enemyStat}>🛡️ DEF: {enemy.stats.defense}</Text>
              </View>
            </Animated.View>
          )}

          {/* Party Status */}
          <View style={styles.partyCard}>
            <Text style={styles.partyTitle}>Party ({activeRaid.participants.length}/{MAX_PLAYERS})</Text>
            {activeRaid.participants.map((p) => (
              <View key={p.player_id} style={styles.partyMember}>
                <View style={styles.partyMemberInfo}>
                  <Text style={[styles.partyMemberName, p.player_id === playerId && styles.selfName]}>
                    {p.player_name} {p.player_id === activeRaid.leader_id ? '👑' : ''}
                  </Text>
                  <Text style={styles.partyMemberLevel}>Lv.{p.player_level}</Text>
                </View>
                <View style={styles.partyMemberHealthBar}>
                  <View 
                    style={[
                      styles.partyMemberHealthFill, 
                      { width: `${(p.current_health / p.max_health) * 100}%` }
                    ]} 
                  />
                </View>
                <Text style={styles.partyMemberHealth}>{p.current_health}/{p.max_health}</Text>
              </View>
            ))}
          </View>

          {/* Combat Log */}
          <View style={styles.combatLogCard}>
            <Text style={styles.combatLogTitle}>Combat Log</Text>
            <ScrollView 
              ref={combatLogRef}
              style={styles.combatLog} 
              nestedScrollEnabled
            >
              {activeRaid.combat_log.slice(-10).map((log, idx) => (
                <Text key={idx} style={styles.combatLogEntry}>{log}</Text>
              ))}
            </ScrollView>
          </View>

          {/* Action Buttons */}
          <View style={styles.actionButtons}>
            <TouchableOpacity
              style={[styles.actionButton, styles.attackButton]}
              onPress={() => handleFight('attack')}
              disabled={processing}
            >
              <Ionicons name="flash" size={24} color="#fff" />
              <Text style={styles.actionButtonText}>ATTACK</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionButton, styles.defendButton]}
              onPress={() => handleFight('defend')}
              disabled={processing}
            >
              <Ionicons name="shield" size={24} color="#fff" />
              <Text style={styles.actionButtonText}>DEFEND</Text>
            </TouchableOpacity>
          </View>

          {isLeader && (
            <TouchableOpacity style={styles.retreatButton} onPress={handleRetreat} disabled={processing}>
              <Ionicons name="flag" size={18} color="#e74c3c" />
              <Text style={styles.retreatButtonText}>Retreat (Keep Rewards)</Text>
            </TouchableOpacity>
          )}

          {processing && <ActivityIndicator color="#9b59b6" style={{ marginTop: 16 }} />}
        </ScrollView>
      </SafeAreaView>
    );
  }

  // Waiting lobby
  if (activeRaid && activeRaid.status === 'waiting') {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.header}>
            <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
            <Text style={styles.title}>RAID LOBBY</Text>
          </View>

          <View style={styles.lobbyCard}>
            <View style={styles.lobbyHeader}>
              <Ionicons name="people" size={32} color="#9b59b6" />
              <Text style={styles.lobbyTitle}>Waiting for Players...</Text>
            </View>

            <View style={styles.lobbyParticipants}>
              <Text style={styles.lobbySubtitle}>
                Party ({activeRaid.participants.length}/{MAX_PLAYERS})
              </Text>
              {activeRaid.participants.map((p) => (
                <View key={p.player_id} style={styles.lobbyMember}>
                  <Ionicons 
                    name={p.player_id === activeRaid.leader_id ? "star" : "person"} 
                    size={20} 
                    color={p.player_id === activeRaid.leader_id ? "#f39c12" : "#888"} 
                  />
                  <Text style={styles.lobbyMemberName}>
                    {p.player_name} {p.player_id === activeRaid.leader_id ? '(Leader)' : ''}
                  </Text>
                  <Text style={styles.lobbyMemberLevel}>Lv.{p.player_level}</Text>
                </View>
              ))}
              
              {/* Empty slots */}
              {Array.from({ length: MAX_PLAYERS - activeRaid.participants.length }).map((_, idx) => (
                <View key={`empty-${idx}`} style={styles.lobbyMemberEmpty}>
                  <Ionicons name="person-outline" size={20} color="#444" />
                  <Text style={styles.lobbyMemberEmptyText}>Waiting...</Text>
                </View>
              ))}
            </View>

            <Text style={styles.lobbyInfo}>
              You can start with just yourself, or wait for up to {MAX_PLAYERS} players.
            </Text>

            {isLeader ? (
              <View style={styles.lobbyActions}>
                <GameButton
                  title="START RAID"
                  onPress={handleBeginRaid}
                  icon="play"
                  variant="primary"
                  loading={processing}
                />
                <TouchableOpacity style={styles.cancelButton} onPress={handleLeaveRaid} disabled={processing}>
                  <Text style={styles.cancelButtonText}>Cancel Raid</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.lobbyActions}>
                <Text style={styles.waitingText}>Waiting for leader to start...</Text>
                <TouchableOpacity style={styles.cancelButton} onPress={handleLeaveRaid} disabled={processing}>
                  <Text style={styles.cancelButtonText}>Leave Raid</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // Raid ended - show results
  if (activeRaid && (activeRaid.status === 'completed' || activeRaid.status === 'failed' || activeRaid.status === 'retreated')) {
    const rewards = activeRaid.final_rewards_per_player;
    const statusIcon = activeRaid.status === 'completed' ? '🏆' : activeRaid.status === 'failed' ? '💀' : '🏳️';
    const statusText = activeRaid.status === 'completed' ? 'VICTORY!' : activeRaid.status === 'failed' ? 'DEFEAT' : 'RETREATED';
    
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.resultsCard}>
            <Text style={styles.resultsIcon}>{statusIcon}</Text>
            <Text style={[
              styles.resultsTitle, 
              activeRaid.status === 'completed' ? styles.victoryText : styles.defeatText
            ]}>
              {statusText}
            </Text>
            
            <View style={styles.resultsStats}>
              <View style={styles.resultsStat}>
                <Text style={styles.resultsStatLabel}>Levels Cleared</Text>
                <Text style={styles.resultsStatValue}>{activeRaid.current_level - (activeRaid.status === 'completed' ? 0 : 1)}/{MAX_RAID_LEVELS}</Text>
              </View>
              <View style={styles.resultsStat}>
                <Text style={styles.resultsStatLabel}>Enemies Defeated</Text>
                <Text style={styles.resultsStatValue}>{activeRaid.enemies_defeated}</Text>
              </View>
            </View>

            <View style={styles.resultsRewards}>
              <Text style={styles.resultsRewardsTitle}>Your Rewards</Text>
              <View style={styles.resultsRewardRow}>
                <Ionicons name="cash" size={24} color="#2ecc71" />
                <Text style={styles.resultsRewardValue}>${rewards?.cash || 0}</Text>
              </View>
              <View style={styles.resultsRewardRow}>
                <Ionicons name="star" size={24} color="#f39c12" />
                <Text style={styles.resultsRewardValue}>{rewards?.xp || 0} XP</Text>
              </View>
              <View style={styles.resultsRewardRow}>
                <Ionicons name="flame" size={24} color="#e74c3c" />
                <Text style={styles.resultsRewardValue}>{rewards?.reputation || 0} Rep</Text>
              </View>
            </View>

            <View style={styles.resultsParty}>
              <Text style={styles.resultsPartyTitle}>Party Members</Text>
              {activeRaid.participants.map((p) => (
                <Text key={p.player_id} style={styles.resultsPartyMember}>
                  {p.player_name} (Lv.{p.player_level})
                </Text>
              ))}
            </View>

            <GameButton
              title="NEW RAID"
              onPress={() => {
                setActiveRaid(null);
                loadRaidData();
              }}
              icon="refresh"
              variant="primary"
            />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // No active raid - show options
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.title}>GUILD RAIDS</Text>
        </View>

        {/* Info Card */}
        <View style={styles.infoCard}>
          <Ionicons name="information-circle" size={24} color="#9b59b6" />
          <Text style={styles.infoText}>
            Fight through {MAX_RAID_LEVELS} levels of enemies with your guild! 
            Team up with up to {MAX_PLAYERS} members. Rewards are split equally.
          </Text>
        </View>

        {/* Start New Raid */}
        <View style={styles.startCard}>
          <Ionicons name="flash" size={40} color="#9b59b6" />
          <Text style={styles.startTitle}>Start a New Raid</Text>
          <Text style={styles.startSubtitle}>Create a raid lobby for your guild</Text>
          <GameButton
            title="START RAID"
            onPress={handleStartRaid}
            icon="play"
            variant="primary"
            loading={processing}
            style={styles.startButton}
          />
        </View>

        {/* Available Raids */}
        {availableRaids.length > 0 && (
          <View style={styles.availableSection}>
            <Text style={styles.sectionTitle}>JOIN A RAID</Text>
            {availableRaids.map((raid) => (
              <View key={raid.id} style={styles.availableRaidCard}>
                <View style={styles.availableRaidInfo}>
                  <Text style={styles.availableRaidLeader}>
                    {raid.participants[0]?.player_name}&apos;s Raid
                  </Text>
                  <Text style={styles.availableRaidPlayers}>
                    {raid.participants.length}/{MAX_PLAYERS} players
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.joinButton}
                  onPress={() => handleJoinRaid(raid.id)}
                  disabled={processing}
                >
                  <Text style={styles.joinButtonText}>JOIN</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}

        {/* History Toggle */}
        <TouchableOpacity 
          style={styles.historyToggle} 
          onPress={() => setShowHistory(!showHistory)}
        >
          <Ionicons name={showHistory ? "chevron-up" : "chevron-down"} size={20} color="#888" />
          <Text style={styles.historyToggleText}>Raid History</Text>
        </TouchableOpacity>

        {/* History */}
        {showHistory && raidHistory.length > 0 && (
          <View style={styles.historySection}>
            {raidHistory.map((raid) => {
              const isWin = raid.status === 'completed';
              return (
                <View key={raid.id} style={[styles.historyCard, isWin ? styles.historyWin : styles.historyLoss]}>
                  <View style={styles.historyCardHeader}>
                    <Text style={styles.historyCardStatus}>
                      {isWin ? '🏆' : raid.status === 'failed' ? '💀' : '🏳️'}
                    </Text>
                    <Text style={styles.historyCardLevel}>Level {raid.current_level}</Text>
                  </View>
                  <Text style={styles.historyCardRewards}>
                    +${raid.final_rewards_per_player?.cash || 0} | +{raid.final_rewards_per_player?.xp || 0} XP
                  </Text>
                </View>
              );
            })}
          </View>
        )}

        {showHistory && raidHistory.length === 0 && (
          <Text style={styles.noHistory}>No raid history yet</Text>
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
    paddingBottom: 40,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#888',
    marginTop: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  noGuildContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  noGuildText: {
    color: '#888',
    fontSize: 16,
    marginVertical: 20,
    textAlign: 'center',
  },
  // Info Card
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(155, 89, 182, 0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(155, 89, 182, 0.3)',
  },
  infoText: {
    flex: 1,
    color: '#aaa',
    fontSize: 13,
    marginLeft: 12,
    lineHeight: 18,
  },
  // Start Card
  startCard: {
    backgroundColor: 'rgba(155, 89, 182, 0.1)',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#9b59b6',
    marginBottom: 20,
  },
  startTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 12,
  },
  startSubtitle: {
    color: '#888',
    fontSize: 14,
    marginTop: 4,
    marginBottom: 16,
  },
  startButton: {
    width: '100%',
  },
  // Available Raids
  availableSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 12,
  },
  availableRaidCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
  },
  availableRaidInfo: {
    flex: 1,
  },
  availableRaidLeader: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  availableRaidPlayers: {
    color: '#888',
    fontSize: 12,
    marginTop: 4,
  },
  joinButton: {
    backgroundColor: '#9b59b6',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  joinButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  // History
  historyToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    marginBottom: 12,
  },
  historyToggleText: {
    color: '#888',
    marginLeft: 8,
  },
  historySection: {
    gap: 8,
  },
  historyCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderRadius: 10,
    padding: 12,
  },
  historyWin: {
    backgroundColor: 'rgba(46, 204, 113, 0.15)',
    borderLeftWidth: 3,
    borderLeftColor: '#2ecc71',
  },
  historyLoss: {
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
    borderLeftWidth: 3,
    borderLeftColor: '#e74c3c',
  },
  historyCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  historyCardStatus: {
    fontSize: 16,
  },
  historyCardLevel: {
    color: '#fff',
    fontWeight: '600',
  },
  historyCardRewards: {
    color: '#888',
    fontSize: 12,
  },
  noHistory: {
    color: '#666',
    textAlign: 'center',
    padding: 20,
  },
  // Lobby
  lobbyCard: {
    backgroundColor: 'rgba(155, 89, 182, 0.1)',
    borderRadius: 16,
    padding: 24,
    borderWidth: 2,
    borderColor: '#9b59b6',
  },
  lobbyHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  lobbyTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 12,
  },
  lobbySubtitle: {
    color: '#888',
    fontSize: 14,
    marginBottom: 12,
  },
  lobbyParticipants: {
    marginBottom: 20,
  },
  lobbyMember: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    gap: 12,
  },
  lobbyMemberName: {
    flex: 1,
    color: '#fff',
    fontWeight: '600',
  },
  lobbyMemberLevel: {
    color: '#888',
  },
  lobbyMemberEmpty: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.02)',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    gap: 12,
    borderWidth: 1,
    borderColor: '#333',
    borderStyle: 'dashed',
  },
  lobbyMemberEmptyText: {
    color: '#444',
  },
  lobbyInfo: {
    color: '#666',
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 20,
  },
  lobbyActions: {
    gap: 12,
  },
  cancelButton: {
    padding: 12,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#e74c3c',
  },
  waitingText: {
    color: '#888',
    textAlign: 'center',
    marginBottom: 12,
  },
  // Active Raid
  raidHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  raidTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  levelBadge: {
    backgroundColor: '#9b59b6',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  levelBadgeText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  progressContainer: {
    marginBottom: 16,
  },
  progressBar: {
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#9b59b6',
    borderRadius: 4,
  },
  progressText: {
    color: '#888',
    fontSize: 12,
    marginTop: 4,
    textAlign: 'center',
  },
  rewardsCard: {
    backgroundColor: 'rgba(243, 156, 18, 0.1)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(243, 156, 18, 0.3)',
  },
  rewardsTitle: {
    color: '#f39c12',
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 8,
  },
  rewardsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  rewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  rewardText: {
    color: '#fff',
    fontWeight: '600',
  },
  // Enemy Card
  enemyCard: {
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 2,
    borderColor: '#e74c3c',
  },
  enemyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  enemyName: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  bossName: {
    color: '#f39c12',
  },
  enemyLevel: {
    color: '#888',
    fontSize: 14,
  },
  healthBarContainer: {
    marginBottom: 12,
  },
  healthBarBg: {
    height: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 6,
    overflow: 'hidden',
  },
  healthBarFill: {
    height: '100%',
    backgroundColor: '#e74c3c',
    borderRadius: 6,
  },
  bossHealthBar: {
    backgroundColor: '#f39c12',
  },
  healthText: {
    color: '#888',
    fontSize: 11,
    textAlign: 'center',
    marginTop: 4,
  },
  enemyStats: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 24,
  },
  enemyStat: {
    color: '#aaa',
    fontSize: 13,
  },
  // Party Card
  partyCard: {
    backgroundColor: 'rgba(52, 152, 219, 0.1)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(52, 152, 219, 0.3)',
  },
  partyTitle: {
    color: '#3498db',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 10,
  },
  partyMember: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  partyMemberInfo: {
    width: 100,
  },
  partyMemberName: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  selfName: {
    color: '#3498db',
  },
  partyMemberLevel: {
    color: '#666',
    fontSize: 10,
  },
  partyMemberHealthBar: {
    flex: 1,
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 3,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  partyMemberHealthFill: {
    height: '100%',
    backgroundColor: '#2ecc71',
    borderRadius: 3,
  },
  partyMemberHealth: {
    color: '#888',
    fontSize: 10,
    width: 50,
    textAlign: 'right',
  },
  // Combat Log
  combatLogCard: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    maxHeight: 150,
  },
  combatLogTitle: {
    color: '#888',
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 8,
  },
  combatLog: {
    maxHeight: 100,
  },
  combatLogEntry: {
    color: '#aaa',
    fontSize: 12,
    marginBottom: 4,
    lineHeight: 16,
  },
  // Action Buttons
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  attackButton: {
    backgroundColor: '#e74c3c',
  },
  defendButton: {
    backgroundColor: '#3498db',
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  retreatButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    gap: 8,
  },
  retreatButtonText: {
    color: '#e74c3c',
  },
  // Results
  resultsCard: {
    backgroundColor: 'rgba(155, 89, 182, 0.1)',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#9b59b6',
  },
  resultsIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  resultsTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 24,
  },
  victoryText: {
    color: '#2ecc71',
  },
  defeatText: {
    color: '#e74c3c',
  },
  resultsStats: {
    flexDirection: 'row',
    gap: 40,
    marginBottom: 24,
  },
  resultsStat: {
    alignItems: 'center',
  },
  resultsStatLabel: {
    color: '#888',
    fontSize: 12,
  },
  resultsStatValue: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  resultsRewards: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 12,
    padding: 20,
    width: '100%',
    marginBottom: 24,
  },
  resultsRewardsTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 16,
  },
  resultsRewardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    marginBottom: 8,
  },
  resultsRewardValue: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  resultsParty: {
    marginBottom: 24,
    alignItems: 'center',
  },
  resultsPartyTitle: {
    color: '#888',
    fontSize: 12,
    marginBottom: 8,
  },
  resultsPartyMember: {
    color: '#aaa',
    fontSize: 14,
  },
});
