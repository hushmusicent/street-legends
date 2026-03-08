import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ImageBackground } from 'react-native';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { getPlayer } from '../services/api';
import { GameButton } from '../components/GameButton';
import { Ionicons } from '@expo/vector-icons';

export default function Index() {
  const { playerId, player, setPlayer, setPlayerId, loadStoredPlayerId, setLoading, isLoading } = useGameStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setLoading(true);
      const storedId = await loadStoredPlayerId();
      
      if (storedId) {
        try {
          const playerData = await getPlayer(storedId);
          setPlayer(playerData);
          setPlayerId(storedId);
          router.replace('/(tabs)');
        } catch (err) {
          // Player not found, clear stored ID
          setPlayerId('');
        }
      }
    } catch (err) {
      setError('Failed to initialize app');
    } finally {
      setLoading(false);
    }
  };

  const handleNewGame = () => {
    router.push('/create-character');
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <Ionicons name="skull" size={80} color="#e74c3c" />
        </View>
        <Text style={styles.title}>STREET</Text>
        <Text style={styles.subtitle}>LEGENDS</Text>
        <Text style={styles.tagline}>GPS Crime RPG</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.featureList}>
          <View style={styles.featureItem}>
            <Ionicons name="location" size={24} color="#e74c3c" />
            <Text style={styles.featureText}>Real-World GPS Exploration</Text>
          </View>
          <View style={styles.featureItem}>
            <Ionicons name="flash" size={24} color="#f39c12" />
            <Text style={styles.featureText}>Intense Turn-Based Combat</Text>
          </View>
          <View style={styles.featureItem}>
            <Ionicons name="people" size={24} color="#3498db" />
            <Text style={styles.featureText}>Multiplayer PvP & Guilds</Text>
          </View>
          <View style={styles.featureItem}>
            <Ionicons name="sparkles" size={24} color="#9b59b6" />
            <Text style={styles.featureText}>AI-Generated Missions</Text>
          </View>
        </View>
      </View>

      <View style={styles.footer}>
        <GameButton
          title="START NEW GAME"
          onPress={handleNewGame}
          variant="primary"
          icon="game-controller"
          size="large"
          style={styles.startButton}
        />
        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 40,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#0a0a0a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#888',
    marginTop: 16,
    fontSize: 16,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 3,
    borderColor: '#e74c3c',
  },
  title: {
    fontSize: 48,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 8,
  },
  subtitle: {
    fontSize: 36,
    fontWeight: '700',
    color: '#e74c3c',
    letterSpacing: 12,
    marginTop: -8,
  },
  tagline: {
    fontSize: 14,
    color: '#666',
    letterSpacing: 4,
    marginTop: 12,
    textTransform: 'uppercase',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
  },
  featureList: {
    gap: 16,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    padding: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#e74c3c',
  },
  featureText: {
    color: '#fff',
    fontSize: 16,
    marginLeft: 16,
    fontWeight: '500',
  },
  footer: {
    alignItems: 'center',
  },
  startButton: {
    width: '100%',
  },
  errorText: {
    color: '#e74c3c',
    marginTop: 16,
    textAlign: 'center',
  },
});
