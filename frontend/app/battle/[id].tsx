import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { showGameToast } from '../../components/GameToast';
import { useGameStore } from '../../stores/gameStore';
import { getBattle, battleAction, getPlayerSkills, getPlayer, getActiveMissions } from '../../services/api';
import { HealthBar } from '../../components/HealthBar';
import { GameButton } from '../../components/GameButton';
import { Battle, Skill } from '../../types/game';
import { getEnemyBattleImage } from '../../assets/enemyImages';
import { SFX } from '../../hooks/useSoundEffects';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');
const COMPACT = SCREEN_HEIGHT < 750;

export default function BattleScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { playerId, setPlayer, setCurrentBattle } = useGameStore();
  const removeMonster = useGameStore((s) => s.removeMonster);
  const triggerMissionRefresh = useGameStore((s) => s.triggerMissionRefresh);
  const [battle, setBattle] = useState<Battle | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showSkills, setShowSkills] = useState(false);

  useEffect(() => {
    loadBattle();
    loadSkills();
  }, [id]);

  const loadBattle = async () => {
    if (!id) return;
    try {
      const data = await getBattle(id);
      setBattle(data);
      setCurrentBattle(data);
    } catch (error) {
      Alert.alert('Error', 'Failed to load battle');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const loadSkills = async () => {
    if (!playerId) return;
    try {
      const data = await getPlayerSkills(playerId);
      // New API returns { skills: [...], equipped_skills: [...], ... }
      // We need only equipped skills for battle
      const skillsArray = data.skills || data;
      // Filter to only equipped skills (or fall back to unlocked for backwards compatibility)
      const equippedSkills = Array.isArray(skillsArray) 
        ? skillsArray.filter((s: any) => s.equipped || s.unlocked)
        : [];
      setSkills(equippedSkills);
    } catch (error) {
      console.error('Failed to load skills:', error);
    }
  };

  const executeAction = async (action: string, skillId?: string) => {
    if (!id || !playerId || actionLoading) return;
    setActionLoading(true);
    
    try {
      const result = await battleAction(id, action, skillId);
      setBattle(result);
      setCurrentBattle(result);
      
      // Parse combat log for sound effects - only use custom sounds
      const lastLogs = result.combat_log?.slice(-2) || [];
      for (const log of lastLogs) {
        const logLower = log.toLowerCase();
        if (logLower.includes('critical')) {
          SFX.criticalHit();
        } else if (logLower.includes('missed')) {
          SFX.miss();
        } else if (logLower.includes('damage') && !logLower.includes('critical') && !logLower.includes('missed')) {
          // Regular attack that landed
          SFX.attack();
        }
      }

      if (result.status !== 'active') {
        // Play victory or defeat sound
        if (result.status === 'won') {
          SFX.victory();
          // Immediately remove enemy from map when battle is won
          if (result.enemy_id) {
            removeMonster(result.enemy_id);
          }
        } else if (result.status === 'lost') {
          SFX.defeat();
        }
        
        if (playerId) {
          const playerData = await getPlayer(playerId);
          setPlayer(playerData);
          triggerMissionRefresh();

          if (result.status === 'won') {
            try {
              const activeMissions = await getActiveMissions(playerId);
              const enemyName = result.enemy_name || '';
              const bountyMissions = activeMissions.filter((m: any) => m.mission_type === 'bounty');
              for (const bm of bountyMissions) {
                const be = (bm.bounty_enemy || '').toLowerCase();
                if (be && enemyName.toLowerCase().includes(be)) {
                  showGameToast({
                    type: 'success',
                    title: 'Bounty Progress!',
                    message: `${bm.title}: ${bm.goal_progress}/${bm.goal_target} ${bm.bounty_enemy} defeated`,
                    duration: 4000,
                  });
                  break;
                }
              }
            } catch (_) { /* silent */ }
          }
        }
      }
    } catch (error: any) {
      SFX.miss(); // Play miss sound on error
      Alert.alert('Error', error?.response?.data?.detail || 'Action failed');
    } finally {
      setActionLoading(false);
      setShowSkills(false);
    }
  };

  const handleExit = () => {
    if (battle?.status === 'won' && battle?.enemy_id) {
      removeMonster(battle.enemy_id);
    }
    router.back();
  };

  if (loading || !battle) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
        <Text style={styles.loadingText}>Loading battle...</Text>
      </View>
    );
  }

  const isActive = battle.status === 'active';
  const isVictory = battle.status === 'won';
  const isDefeat = battle.status === 'lost';
  const enemyImage = getEnemyBattleImage(battle.enemy_name || '');

  return (
    <SafeAreaView style={styles.container}>
      {/* Top Section: Enemy + Player (compact, no scroll needed) */}
      <View style={styles.topSection}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.turnText}>TURN {battle.turn}</Text>
          {isActive && <Text style={styles.battleStatus}>BATTLE IN PROGRESS</Text>}
        </View>

        {/* Enemy */}
        <View style={styles.enemySection}>
          <View style={[styles.enemyAvatar, enemyImage && styles.enemyAvatarWithImage]}>
            {enemyImage ? (
              <Image source={{ uri: enemyImage }} style={styles.enemyImage} />
            ) : (
              <Ionicons
                name={battle.enemy_type === 'monster' ? 'skull' : 'person'}
                size={COMPACT ? 32 : 40}
                color="#e74c3c"
              />
            )}
          </View>
          <View style={styles.enemyInfo}>
            <Text style={styles.enemyName}>{battle.enemy_name}</Text>
            <HealthBar current={battle.enemy_health} max={battle.enemy_max_health} color="#e74c3c" />
          </View>
        </View>

        {/* VS + Player */}
        <View style={styles.playerRow}>
          <View style={styles.playerHP}>
            <HealthBar current={battle.player_health} max={battle.player_max_health} label="HP" color="#27ae60" />
          </View>
          <View style={styles.energyBadge}>
            <Ionicons name="flash" size={14} color="#3498db" />
            <Text style={styles.energyValue}>{battle.player_energy}</Text>
          </View>
        </View>
      </View>

      {/* Combat Log (fills remaining space) */}
      <View style={styles.logSection}>
        <Text style={styles.logTitle}>COMBAT LOG</Text>
        <ScrollView style={styles.logScroll} showsVerticalScrollIndicator={false}>
          {battle.combat_log.slice(-6).map((log, index) => (
            <Text key={index} style={styles.logEntry}>{log}</Text>
          ))}
        </ScrollView>
      </View>

      {/* Battle Result Overlay */}
      {!isActive && (
        <View style={[styles.resultOverlay, isVictory ? styles.victoryOverlay : styles.defeatOverlay]}>
          <Ionicons
            name={isVictory ? 'trophy' : 'skull'}
            size={56}
            color={isVictory ? '#f39c12' : '#e74c3c'}
          />
          <Text style={styles.resultText}>
            {isVictory ? 'VICTORY!' : isDefeat ? 'DEFEAT!' : 'FLED!'}
          </Text>
          {battle.rewards && (
            <View style={styles.rewardsContainer}>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={18} color="#f39c12" />
                  <Text style={styles.rewardValue}>${battle.rewards.cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={18} color="#3498db" />
                  <Text style={styles.rewardValue}>{battle.rewards.xp} XP</Text>
                </View>
              </View>
            </View>
          )}
          <GameButton
            title="CONTINUE"
            onPress={handleExit}
            variant="primary"
            icon="arrow-forward"
            style={styles.continueButton}
          />
        </View>
      )}

      {/* Action Buttons (always visible at bottom) */}
      {isActive && (
        <View style={styles.actions}>
          {showSkills ? (
            <View style={styles.skillsPanel}>
              <View style={styles.skillsHeader}>
                <Text style={styles.skillsTitle}>SELECT SKILL</Text>
                <TouchableOpacity onPress={() => setShowSkills(false)} style={styles.skillCloseBtn}>
                  <Ionicons name="close-circle" size={28} color="#888" />
                </TouchableOpacity>
              </View>
              <ScrollView style={styles.skillsScroll} showsVerticalScrollIndicator={false}>
                <View style={styles.skillsGrid}>
                  {skills.map((skill) => (
                    <TouchableOpacity
                      key={skill.id}
                      style={[
                        styles.skillButton,
                        skill.cost > battle.player_energy && styles.skillDisabled,
                      ]}
                      onPress={() => executeAction('skill', skill.id)}
                      disabled={skill.cost > battle.player_energy || actionLoading}
                    >
                      <Ionicons name="flash" size={18} color="#e74c3c" />
                      <Text style={styles.skillName} numberOfLines={1}>{skill.name}</Text>
                      <Text style={styles.skillCost}>{skill.cost} EN</Text>
                    </TouchableOpacity>
                  ))}
                  {skills.length === 0 && (
                    <View style={styles.noSkills}>
                      <Ionicons name="alert-circle-outline" size={24} color="#666" />
                      <Text style={styles.noSkillsText}>No skills equipped</Text>
                    </View>
                  )}
                </View>
              </ScrollView>
            </View>
          ) : (
            <View style={styles.actionGrid}>
              <TouchableOpacity
                style={[styles.actionButton, styles.attackBtn]}
                onPress={() => executeAction('attack')}
                disabled={actionLoading}
              >
                <Ionicons name="flash" size={24} color="#fff" />
                <Text style={styles.actionText}>ATTACK</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, styles.skillBtn]}
                onPress={() => setShowSkills(true)}
                disabled={actionLoading}
              >
                <Ionicons name="sparkles" size={24} color="#fff" />
                <Text style={styles.actionText}>SKILLS</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, styles.defendBtn]}
                onPress={() => executeAction('defend')}
                disabled={actionLoading}
              >
                <Ionicons name="shield" size={24} color="#fff" />
                <Text style={styles.actionText}>DEFEND</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, styles.fleeBtn]}
                onPress={() => executeAction('flee')}
                disabled={actionLoading}
              >
                <Ionicons name="exit" size={24} color="#fff" />
                <Text style={styles.actionText}>FLEE</Text>
              </TouchableOpacity>
            </View>
          )}

          {actionLoading && (
            <View style={styles.actionLoadingOverlay}>
              <ActivityIndicator size="large" color="#e74c3c" />
            </View>
          )}
        </View>
      )}
    </SafeAreaView>
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

  // Top section: enemy + player (compact)
  topSection: {
    paddingHorizontal: 16,
  },
  header: {
    alignItems: 'center',
    paddingVertical: COMPACT ? 6 : 10,
  },
  turnText: {
    color: '#f39c12',
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  battleStatus: {
    color: '#e74c3c',
    fontSize: 10,
    letterSpacing: 2,
    marginTop: 2,
  },

  // Enemy section: horizontal layout for compactness
  enemySection: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(231, 76, 60, 0.08)',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.2)',
  },
  enemyAvatar: {
    width: COMPACT ? 56 : 68,
    height: COMPACT ? 56 : 68,
    borderRadius: COMPACT ? 28 : 34,
    backgroundColor: 'rgba(231, 76, 60, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#e74c3c',
  },
  enemyAvatarWithImage: {
    overflow: 'hidden',
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    borderColor: '#ff6b35',
  },
  enemyImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  enemyInfo: {
    flex: 1,
    marginLeft: 14,
  },
  enemyName: {
    color: '#fff',
    fontSize: COMPACT ? 18 : 22,
    fontWeight: 'bold',
    marginBottom: 8,
  },

  // Player row
  playerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
    paddingHorizontal: 4,
  },
  playerHP: {
    flex: 1,
  },
  energyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(52, 152, 219, 0.2)',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginLeft: 10,
    borderWidth: 1,
    borderColor: 'rgba(52, 152, 219, 0.3)',
  },
  energyValue: {
    color: '#3498db',
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 4,
  },

  // Combat Log
  logSection: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    marginHorizontal: 16,
    marginTop: 10,
    borderRadius: 12,
    padding: 10,
    minHeight: 60,
  },
  logTitle: {
    color: '#555',
    fontSize: 9,
    letterSpacing: 2,
    marginBottom: 4,
  },
  logScroll: {
    flex: 1,
  },
  logEntry: {
    color: '#aaa',
    fontSize: 12,
    marginBottom: 3,
    lineHeight: 16,
  },

  // Action Buttons
  actions: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 8,
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  actionButton: {
    width: '47%',
    flexGrow: 1,
    borderRadius: 12,
    paddingVertical: COMPACT ? 12 : 14,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 8,
  },
  attackBtn: { backgroundColor: '#e74c3c' },
  skillBtn: { backgroundColor: '#9b59b6' },
  defendBtn: { backgroundColor: '#3498db' },
  fleeBtn: { backgroundColor: '#7f8c8d' },
  actionText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
    letterSpacing: 1,
  },

  // Skills Panel (vertical grid, scrollable)
  skillsPanel: {
    backgroundColor: 'rgba(20, 10, 30, 0.95)',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: 'rgba(155, 89, 182, 0.4)',
    maxHeight: SCREEN_HEIGHT * 0.35,
  },
  skillsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  skillsTitle: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  skillCloseBtn: {
    padding: 4,
  },
  skillsScroll: {
    flexGrow: 0,
  },
  skillsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillButton: {
    backgroundColor: 'rgba(155, 89, 182, 0.15)',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    alignItems: 'center',
    width: '47%',
    flexGrow: 1,
    borderWidth: 1,
    borderColor: 'rgba(155, 89, 182, 0.4)',
  },
  skillDisabled: {
    opacity: 0.35,
  },
  skillName: {
    color: '#fff',
    fontWeight: '600',
    marginTop: 4,
    fontSize: 12,
    textAlign: 'center',
  },
  skillCost: {
    color: '#3498db',
    fontSize: 10,
    marginTop: 2,
    fontWeight: '600',
  },
  noSkills: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 16,
  },
  noSkillsText: {
    color: '#666',
    fontSize: 13,
  },

  actionLoadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },

  // Result overlay
  resultOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  victoryOverlay: {},
  defeatOverlay: {},
  resultText: {
    color: '#fff',
    fontSize: 32,
    fontWeight: 'bold',
    marginTop: 12,
    letterSpacing: 4,
  },
  rewardsContainer: {
    marginTop: 24,
    alignItems: 'center',
  },
  rewardsRow: {
    flexDirection: 'row',
  },
  rewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 8,
    marginHorizontal: 6,
  },
  rewardValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 6,
  },
  continueButton: {
    marginTop: 32,
    minWidth: 200,
  },
});
