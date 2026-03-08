import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useGameStore } from '../../stores/gameStore';
import { getPlayer, getPlayerSkills } from '../../services/api';
import { HealthBar } from '../../components/HealthBar';
import { StatBar } from '../../components/StatBar';
import { Skill } from '../../types/game';
import AsyncStorage from '@react-native-async-storage/async-storage';

const CLASS_COLORS: Record<string, string> = {
  street_soldier: '#e74c3c',
  hacker: '#3498db',
  enforcer: '#f39c12',
  ghost: '#9b59b6',
};

const CLASS_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  street_soldier: 'fitness',
  hacker: 'hardware-chip',
  enforcer: 'hammer',
  ghost: 'eye-off',
};

export default function CharacterScreen() {
  const { player, playerId, setPlayer, clearPlayer } = useGameStore();
  const [refreshing, setRefreshing] = useState(false);
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    if (playerId) {
      loadPlayerData();
    }
  }, [playerId]);

  const loadPlayerData = async () => {
    if (!playerId) return;
    try {
      const [playerData, skillsData] = await Promise.all([
        getPlayer(playerId),
        getPlayerSkills(playerId),
      ]);
      setPlayer(playerData);
      setSkills(skillsData);
    } catch (error) {
      console.error('Failed to load player data:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadPlayerData();
    setRefreshing(false);
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await AsyncStorage.removeItem('playerId');
            clearPlayer();
            router.replace('/');
          },
        },
      ]
    );
  };

  if (!player) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  const classColor = CLASS_COLORS[player.character_class] || '#e74c3c';
  const xpProgress = (player.xp / player.xp_to_next) * 100;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#e74c3c" />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={[styles.avatarContainer, { borderColor: classColor }]}>
            <Ionicons name={CLASS_ICONS[player.character_class]} size={48} color={classColor} />
          </View>
          <Text style={styles.playerName}>{player.name}</Text>
          <Text style={[styles.playerClass, { color: classColor }]}>
            {player.character_class.replace('_', ' ').toUpperCase()}
          </Text>
        </View>

        {/* Level & XP */}
        <View style={styles.levelSection}>
          <View style={styles.levelBadge}>
            <Text style={styles.levelLabel}>LEVEL</Text>
            <Text style={styles.levelValue}>{player.level}</Text>
          </View>
          <View style={styles.xpContainer}>
            <View style={styles.xpBar}>
              <View style={[styles.xpFill, { width: `${xpProgress}%` }]} />
            </View>
            <Text style={styles.xpText}>
              {player.xp} / {player.xp_to_next} XP
            </Text>
          </View>
        </View>

        {/* Health & Energy */}
        <View style={styles.section}>
          <HealthBar
            current={player.stats.health}
            max={player.stats.max_health}
            label="HEALTH"
            color="#e74c3c"
          />
          <View style={{ height: 12 }} />
          <HealthBar
            current={player.stats.energy}
            max={player.stats.max_energy}
            label="ENERGY"
            color="#3498db"
          />
        </View>

        {/* Stats */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>STATS</Text>
          <View style={styles.statsGrid}>
            <StatBar icon="flash" label="Attack" value={player.stats.attack} color="#e74c3c" />
            <StatBar icon="shield" label="Defense" value={player.stats.defense} color="#3498db" />
            <StatBar icon="speedometer" label="Speed" value={player.stats.speed} color="#2ecc71" />
            <StatBar icon="dice" label="Luck" value={player.stats.luck} color="#f39c12" />
          </View>
        </View>

        {/* Currency & Stats */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>RESOURCES</Text>
          <View style={styles.resourcesRow}>
            <View style={styles.resourceItem}>
              <Ionicons name="cash" size={24} color="#f39c12" />
              <Text style={styles.resourceValue}>${player.cash}</Text>
              <Text style={styles.resourceLabel}>Cash</Text>
            </View>
            <View style={styles.resourceItem}>
              <Ionicons name="star" size={24} color="#9b59b6" />
              <Text style={styles.resourceValue}>{player.reputation}</Text>
              <Text style={styles.resourceLabel}>Rep</Text>
            </View>
            <View style={styles.resourceItem}>
              <Ionicons name="trophy" size={24} color="#27ae60" />
              <Text style={styles.resourceValue}>{player.wins}</Text>
              <Text style={styles.resourceLabel}>Wins</Text>
            </View>
            <View style={styles.resourceItem}>
              <Ionicons name="briefcase" size={24} color="#3498db" />
              <Text style={styles.resourceValue}>{player.missions_completed}</Text>
              <Text style={styles.resourceLabel}>Missions</Text>
            </View>
          </View>
        </View>

        {/* Skills */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>SKILLS</Text>
          <View style={styles.skillsGrid}>
            {skills.map((skill) => (
              <View
                key={skill.id}
                style={[
                  styles.skillCard,
                  !skill.unlocked && styles.skillLocked,
                ]}
              >
                <Ionicons
                  name="flash"
                  size={20}
                  color={skill.unlocked ? '#e74c3c' : '#555'}
                />
                <Text style={[styles.skillName, !skill.unlocked && styles.lockedText]}>
                  {skill.name}
                </Text>
                <Text style={styles.skillCost}>{skill.cost} Energy</Text>
                {!skill.unlocked && (
                  <Text style={styles.skillUnlock}>Lv.{skill.unlock_level}</Text>
                )}
              </View>
            ))}
          </View>
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out" size={20} color="#e74c3c" />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </ScrollView>
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
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  avatarContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    marginBottom: 16,
  },
  playerName: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  playerClass: {
    fontSize: 14,
    fontWeight: '600',
    letterSpacing: 2,
    marginTop: 4,
  },
  levelSection: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  levelBadge: {
    backgroundColor: '#e74c3c',
    width: 70,
    height: 70,
    borderRadius: 35,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  levelLabel: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 10,
    fontWeight: '600',
  },
  levelValue: {
    color: '#fff',
    fontSize: 28,
    fontWeight: 'bold',
  },
  xpContainer: {
    flex: 1,
  },
  xpBar: {
    height: 12,
    backgroundColor: '#333',
    borderRadius: 6,
    overflow: 'hidden',
    marginBottom: 4,
  },
  xpFill: {
    height: '100%',
    backgroundColor: '#e74c3c',
    borderRadius: 6,
  },
  xpText: {
    color: '#888',
    fontSize: 12,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 12,
  },
  statsGrid: {
    gap: 8,
  },
  resourcesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  resourceItem: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    padding: 16,
    borderRadius: 12,
    marginHorizontal: 4,
  },
  resourceValue: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 8,
  },
  resourceLabel: {
    color: '#666',
    fontSize: 10,
    marginTop: 4,
  },
  skillsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillCard: {
    width: '48%',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  skillLocked: {
    opacity: 0.5,
  },
  skillName: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 4,
    textAlign: 'center',
  },
  lockedText: {
    color: '#666',
  },
  skillCost: {
    color: '#3498db',
    fontSize: 10,
    marginTop: 2,
  },
  skillUnlock: {
    color: '#f39c12',
    fontSize: 10,
    marginTop: 2,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderWidth: 1,
    borderColor: '#e74c3c',
    borderRadius: 8,
    marginTop: 16,
  },
  logoutText: {
    color: '#e74c3c',
    fontWeight: '600',
    marginLeft: 8,
  },
});
