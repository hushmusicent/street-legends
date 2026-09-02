import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Image } from 'react-native';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { getPlayer } from '../services/api';
import { GameButton } from '../components/GameButton';
import { Ionicons } from '@expo/vector-icons';
import { OptionsModal } from '../components/OptionsModal';

export default function Index() {
  const { playerId, setPlayer, setPlayerId, loadStoredPlayerId, setLoading, isLoading } = useGameStore();
  const [error, setError] = useState<string | null>(null);
  const [showOptions, setShowOptions] = useState(false);

  useEffect(() => {
    initializeApp();
  }, []);

  const handleNavigate = async (path: string) => {
    router.push(path as any);
  };

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
          setPlayerId('');
        }
      }
    } catch (err) {
      setError('Failed to initialize app');
    } finally {
      setLoading(false);
    }
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
          <Image 
            source={{ uri: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/f52b6eadcf254e84b2d978f139a47593_sl_2_512.png' }}
            style={styles.logoImage}
            resizeMode="contain"
          />
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
          title="LOGIN"
          onPress={() => handleNavigate('/login')}
          variant="primary"
          icon="log-in"
          size="large"
          style={styles.loginButton}
        />
        <GameButton
          title="SIGN UP"
          onPress={() => handleNavigate('/create-character')}
          variant="secondary"
          icon="person-add"
          size="large"
          style={styles.signupButton}
        />
        <TouchableOpacity style={styles.optionsBtn} onPress={() => setShowOptions(true)} activeOpacity={0.7}>
          <Ionicons name="settings-sharp" size={22} color="#888" />
          <Text style={styles.optionsBtnText}>OPTIONS</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.howToPlayBtn} onPress={() => handleNavigate('/instructions')} activeOpacity={0.7}>
          <Ionicons name="help-circle" size={22} color="#f59e0b" />
          <Text style={styles.howToPlayBtnText}>HOW TO PLAY</Text>
        </TouchableOpacity>
        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>

      <OptionsModal
        visible={showOptions}
        onClose={() => setShowOptions(false)}
        onToggleMute={() => {}}
        isMuted={false}
        showQuit={false}
      />
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
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 3,
    borderColor: '#e74c3c',
    overflow: 'hidden',
  },
  logoImage: {
    width: 110,
    height: 110,
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
    gap: 12,
  },
  loginButton: {
    width: '100%',
  },
  signupButton: {
    width: '100%',
  },
  optionsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  optionsBtnText: {
    color: '#888',
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 2,
  },
  howToPlayBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f59e0b40',
    backgroundColor: '#f59e0b10',
  },
  howToPlayBtnText: {
    color: '#f59e0b',
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 2,
  },
  errorText: {
    color: '#e74c3c',
    marginTop: 16,
    textAlign: 'center',
  },
});
