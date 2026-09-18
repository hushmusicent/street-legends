import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Image, ScrollView, Platform } from 'react-native';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { getPlayer, API_URL } from '../services/api';
import { GameButton } from '../components/GameButton';
import { Ionicons } from '@expo/vector-icons';
import { OptionsModal } from '../components/OptionsModal';

// Sponsor logo URLs (processed through rembg to remove white backgrounds)
const APPSOLUT_LOGO = `${API_URL}/api/sprites/remove-bg?url=${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/cab2fc2b9acc4ae2bcc31468e1b881a1_appsolut_header_4096x2304.jpg')}`;
const HUSH_LOGO = `${API_URL}/api/sprites/remove-bg?url=${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/334c2ba3642c4dbe8d637f25db5a761c_Resized_mainlogo.jpeg')}`;

export default function Index() {
  const { setPlayer, setPlayerId, loadStoredPlayerId, setLoading } = useGameStore();
  const [error, setError] = useState<string | null>(null);
  const [showOptions, setShowOptions] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const initRef = useRef(false);

  useEffect(() => {
    // Prevent double initialization
    if (initRef.current) return;
    initRef.current = true;
    
    initializeApp();
  }, []);

  const handleNavigate = async (path: string) => {
    router.push(path as any);
  };

  const initializeApp = async () => {
    console.log('[Init] Starting app initialization...');
    
    // Set a hard deadline - always show content after 3 seconds
    const forceCompleteTimer = setTimeout(() => {
      console.log('[Init] Force completing initialization');
      setIsInitializing(false);
      setLoading(false);
    }, 3000);
    
    try {
      // Try to load stored player ID with a short timeout
      let storedId: string | null = null;
      try {
        const loadPromise = loadStoredPlayerId();
        const timeoutPromise = new Promise<null>((resolve) => 
          setTimeout(() => resolve(null), 2000)
        );
        storedId = await Promise.race([loadPromise, timeoutPromise]);
        console.log('[Init] Stored ID:', storedId ? 'found' : 'not found');
      } catch (e) {
        console.log('[Init] Error loading stored ID:', e);
        storedId = null;
      }

      if (storedId) {
        // Try to fetch player data with a short timeout
        try {
          const fetchPromise = getPlayer(storedId);
          const timeoutPromise = new Promise<null>((resolve) => 
            setTimeout(() => resolve(null), 2500)
          );
          const playerData = await Promise.race([fetchPromise, timeoutPromise]);
          
          if (playerData) {
            console.log('[Init] Player data loaded, navigating to tabs');
            setPlayer(playerData);
            setPlayerId(storedId);
            clearTimeout(forceCompleteTimer);
            setIsInitializing(false);
            setLoading(false);
            router.replace('/(tabs)');
            return;
          }
        } catch (e) {
          console.log('[Init] Error fetching player:', e);
        }
        // Clear stored ID if fetch failed
        setPlayerId('');
      }
      
      // Show login screen
      console.log('[Init] Showing login screen');
      clearTimeout(forceCompleteTimer);
      setIsInitializing(false);
      setLoading(false);
    } catch (e) {
      console.log('[Init] Initialization error:', e);
      clearTimeout(forceCompleteTimer);
      setError('Failed to initialize');
      setIsInitializing(false);
      setLoading(false);
    }
  };

  // Show loading screen only briefly
  if (isInitializing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
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
        
        {/* Sponsor Logos */}
        <View style={styles.sponsorSection}>
          <Text style={styles.sponsorLabel}>Sponsored by</Text>
          <View style={styles.sponsorLogos}>
            <Image 
              source={{ uri: APPSOLUT_LOGO }}
              style={styles.sponsorLogo}
              resizeMode="contain"
            />
            <Image 
              source={{ uri: HUSH_LOGO }}
              style={styles.sponsorLogo}
              resizeMode="contain"
            />
          </View>
        </View>
      </View>
      </ScrollView>

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
  },
  scrollContent: {
    flexGrow: 1,
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
  featureList: {
    gap: 12,
    marginTop: 24,
    marginBottom: 24,
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
  sponsorSection: {
    marginTop: 28,
    alignItems: 'center',
    paddingBottom: 24,
  },
  sponsorLabel: {
    color: '#444',
    fontSize: 10,
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginBottom: 14,
  },
  sponsorLogos: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 48,
  },
  sponsorLogo: {
    width: 120,
    height: 60,
    opacity: 0.75,
  },
});
