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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import { getBattle, battleAction, getPlayerSkills, getPlayer } from '../../services/api';
import { HealthBar } from '../../components/HealthBar';
import { GameButton } from '../../components/GameButton';
import { Battle, Skill } from '../../types/game';
import { getEnemyBattleImage } from '../../assets/enemyImages';

export default function BattleScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { playerId, setPlayer, setCurrentBattle } = useGameStore();
  const removeMonster = useGameStore((s) => s.removeMonster);
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
      setSkills(data.filter((s) => s.unlocked));
    } catch (error) {
      console.error('Failed to load skills:', error);
    }
  };

  const executeAction = async (action: string, skillId?: string) => {
    if (!id || actionLoading) return;

    try {
      setActionLoading(true);
      const result = await battleAction(id, action, skillId);
      setBattle(result);
      setCurrentBattle(result);
      setShowSkills(false);

      if (result.status !== 'active') {
        // Refresh player data
        if (playerId) {
          const playerData = await getPlayer(playerId);
          setPlayer(playerData);
        }
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleExit = () => {
    // Remove defeated monster from map
    if (battle && battle.status === 'won' && battle.enemy_type === 'monster') {
      removeMonster(battle.enemy_id);
    }
    setCurrentBattle(null);
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
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.turnText}>TURN {battle.turn}</Text>
        {isActive && <Text style={styles.battleStatus}>BATTLE IN PROGRESS</Text>}
      </View>

      {/* Enemy Section */}
      <View style={styles.enemySection}>
        <View style={[styles.enemyAvatar, enemyImage && styles.enemyAvatarThug]}>
          {enemyImage ? (
            <Image source={{ uri: enemyImage }} style={styles.enemyImage} />
          ) : (
            <Ionicons
              name={battle.enemy_type === 'monster' ? 'skull' : 'person'}
              size={48}
              color="#e74c3c"
            />
          )}
        </View>
        <Text style={styles.enemyName}>{battle.enemy_name}</Text>
        <HealthBar
          current={battle.enemy_health}
          max={battle.enemy_max_health}
          color="#e74c3c"
        />
      </View>

      {/* VS Divider */}
      <View style={styles.vsDivider}>
        <View style={styles.vsLine} />
        <Text style={styles.vsText}>VS</Text>
        <View style={styles.vsLine} />
      </View>

      {/* Player Section */}
      <View style={styles.playerSection}>
        <View style={styles.playerStats}>
          <View style={styles.statBox}>
            <HealthBar
              current={battle.player_health}
              max={battle.player_max_health}
              label="HEALTH"
              color="#27ae60"
            />
          </View>
          <View style={styles.energyBox}>
            <Text style={styles.energyLabel}>ENERGY</Text>
            <Text style={styles.energyValue}>{battle.player_energy}</Text>
          </View>
        </View>
      </View>

      {/* Combat Log */}
      <View style={styles.logSection}>
        <Text style={styles.logTitle}>COMBAT LOG</Text>
        <ScrollView style={styles.logScroll}>
          {battle.combat_log.slice(-5).map((log, index) => (
            <Text key={index} style={styles.logEntry}>
              {log}
            </Text>
          ))}
        </ScrollView>
      </View>

      {/* Battle Result */}
      {!isActive && (
        <View style={[styles.resultOverlay, isVictory ? styles.victoryOverlay : styles.defeatOverlay]}>
          <Ionicons
            name={isVictory ? 'trophy' : 'skull'}
            size={64}
            color={isVictory ? '#f39c12' : '#e74c3c'}
          />
          <Text style={styles.resultText}>
            {isVictory ? 'VICTORY!' : isDefeat ? 'DEFEAT!' : 'FLED!'}
          </Text>
          {battle.rewards && (
            <View style={styles.rewardsContainer}>
              <Text style={styles.rewardsTitle}>REWARDS</Text>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={20} color="#f39c12" />
                  <Text style={styles.rewardValue}>${battle.rewards.cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={20} color="#3498db" />
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

      {/* Action Buttons */}
      {isActive && (
        <View style={styles.actions}>
          {showSkills ? (
            <View style={styles.skillsPanel}>
              <View style={styles.skillsHeader}>
                <Text style={styles.skillsTitle}>SELECT SKILL</Text>
                <TouchableOpacity onPress={() => setShowSkills(false)}>
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
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
                    <Ionicons name="flash" size={20} color="#e74c3c" />
                    <Text style={styles.skillName}>{skill.name}</Text>
                    <Text style={styles.skillCost}>{skill.cost} Energy</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          ) : (
            <View style={styles.actionGrid}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => executeAction('attack')}
                disabled={actionLoading}
              >
                <Ionicons name="flash" size={28} color="#fff" />
                <Text style={styles.actionText}>ATTACK</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, styles.skillActionButton]}
                onPress={() => setShowSkills(true)}
                disabled={actionLoading}
              >
                <Ionicons name="sparkles" size={28} color="#fff" />
                <Text style={styles.actionText}>SKILLS</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, styles.defendButton]}
                onPress={() => executeAction('defend')}
                disabled={actionLoading}
              >
                <Ionicons name="shield" size={28} color="#fff" />
                <Text style={styles.actionText}>DEFEND</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, styles.fleeButton]}
                onPress={() => executeAction('flee')}
                disabled={actionLoading}
              >
                <Ionicons name="exit" size={28} color="#fff" />
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
  header: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  turnText: {
    color: '#f39c12',
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  battleStatus: {
    color: '#e74c3c',
    fontSize: 12,
    letterSpacing: 2,
    marginTop: 4,
  },
  enemySection: {
    alignItems: 'center',
    paddingHorizontal: 40,
    paddingVertical: 20,
  },
  enemyAvatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(231, 76, 60, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 3,
    borderColor: '#e74c3c',
  },
  enemyAvatarThug: {
    width: 100,
    height: 100,
    borderRadius: 50,
    overflow: 'hidden',
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    borderColor: '#ff6b35',
    borderWidth: 3,
  },
  enemyImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  enemyName: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  vsDivider: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  vsLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#333',
  },
  vsText: {
    color: '#666',
    fontSize: 18,
    fontWeight: 'bold',
    marginHorizontal: 16,
  },
  playerSection: {
    paddingHorizontal: 20,
    paddingVertical: 20,
  },
  playerStats: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statBox: {
    flex: 1,
  },
  energyBox: {
    backgroundColor: 'rgba(52, 152, 219, 0.2)',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    marginLeft: 12,
    minWidth: 80,
  },
  energyLabel: {
    color: '#3498db',
    fontSize: 10,
    fontWeight: '600',
  },
  energyValue: {
    color: '#3498db',
    fontSize: 24,
    fontWeight: 'bold',
  },
  logSection: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    marginHorizontal: 20,
    borderRadius: 12,
    padding: 12,
  },
  logTitle: {
    color: '#666',
    fontSize: 10,
    letterSpacing: 2,
    marginBottom: 8,
  },
  logScroll: {
    flex: 1,
  },
  logEntry: {
    color: '#aaa',
    fontSize: 13,
    marginBottom: 4,
    lineHeight: 18,
  },
  actions: {
    padding: 20,
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#e74c3c',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skillActionButton: {
    backgroundColor: '#9b59b6',
  },
  defendButton: {
    backgroundColor: '#3498db',
  },
  fleeButton: {
    backgroundColor: '#7f8c8d',
  },
  actionText: {
    color: '#fff',
    fontWeight: 'bold',
    marginTop: 4,
    letterSpacing: 1,
  },
  skillsPanel: {
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    borderRadius: 12,
    padding: 16,
  },
  skillsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  skillsTitle: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  skillButton: {
    backgroundColor: 'rgba(231, 76, 60, 0.2)',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginRight: 12,
    minWidth: 100,
    borderWidth: 1,
    borderColor: '#e74c3c',
  },
  skillDisabled: {
    opacity: 0.4,
  },
  skillName: {
    color: '#fff',
    fontWeight: '600',
    marginTop: 8,
    fontSize: 12,
  },
  skillCost: {
    color: '#3498db',
    fontSize: 10,
    marginTop: 4,
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
    fontSize: 36,
    fontWeight: 'bold',
    marginTop: 16,
    letterSpacing: 4,
  },
  rewardsContainer: {
    marginTop: 32,
    alignItems: 'center',
  },
  rewardsTitle: {
    color: '#888',
    fontSize: 12,
    letterSpacing: 2,
    marginBottom: 16,
  },
  rewardsRow: {
    flexDirection: 'row',
  },
  rewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    marginHorizontal: 8,
  },
  rewardValue: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  continueButton: {
    marginTop: 40,
    minWidth: 200,
  },
});
