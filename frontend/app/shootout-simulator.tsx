import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  Modal,
  Image,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { showGameToast } from '../components/GameToast';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';
import { startShootout as apiStartShootout, completeShootout as apiCompleteShootout, getPlayer } from '../services/api';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// API URL
const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Game constants
const GAME_WIDTH = Math.min(SCREEN_WIDTH - 20, 380);
const GAME_HEIGHT = Math.min(SCREEN_HEIGHT - 200, 500);

// Character sprite URLs - 5 gang members with direct URLs (no bg removal needed for these)
const CHARACTER_SPRITES = {
  cowboy: {
    url: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/05168415d6654f72bab2f6c82452d7b0_AQPZH2SCZMVdkXQRiMWNEyzVehHj0Uw5NdWG-7hJbPMozETNm8mrmOmZ6STIjFFLLIKWtjwrDDFChRnmKlcLLXR7.jpg',
    name: 'Cowboy',
    emoji: '🤠',
  },
  bandana: {
    url: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/c07d7e1fbb8c44eb962c77a46b74a893_AQMN4ikUKuAU-0zhhOSDaZOWw65Nj9dItWHT1ZNubA4ZREzZJpzpFwzpd4R_LiwVETxLOe84jK2gVm-y0AnU4kDm.jpg',
    name: 'Bandana',
    emoji: '😎',
  },
  crewJacket: {
    url: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/8dca7a6977dd4701b3e1d791602862fb_crew3_cutout.png',
    name: 'Crew Jacket',
    emoji: '🧥',
  },
  dualGuns: {
    url: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/8b8d7d50201349a6a33bbeecbfb0ed5f_guy_2_guns_cutout.png',
    name: 'Dual Guns',
    emoji: '🔫',
  },
  girlRed: {
    url: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/3ae4914efaaf4047acf32ef42f44f11d_violent_tech_cutout.png',
    name: 'Girl Red',
    emoji: '👩',
  },
};

const SPRITE_KEYS = Object.keys(CHARACTER_SPRITES) as (keyof typeof CHARACTER_SPRITES)[];

// Helper function to get sprite URL
const getSpriteUrl = (spriteKey: keyof typeof CHARACTER_SPRITES): string => {
  return CHARACTER_SPRITES[spriteKey]?.url || '';
};

// 20 City backgrounds with different themes
const CITY_BACKGROUNDS: { [key: number]: { colors: string[]; name: string; timeOfDay: string } } = {
  1: { colors: ['#87CEEB', '#B0C4DE', '#778899'], name: 'Sunny Downtown', timeOfDay: 'day' },
  2: { colors: ['#FFD700', '#FFA500', '#FF6347'], name: 'Sunset Strip', timeOfDay: 'sunset' },
  3: { colors: ['#1a1a2e', '#16213e', '#0f3460'], name: 'Neon Night', timeOfDay: 'night' },
  4: { colors: ['#2d3436', '#636e72', '#b2bec3'], name: 'Rainy Streets', timeOfDay: 'rain' },
  5: { colors: ['#dfe6e9', '#b2bec3', '#636e72'], name: 'Snowy Winter', timeOfDay: 'snow' },
  6: { colors: ['#ff7675', '#fd79a8', '#a29bfe'], name: 'Neon District', timeOfDay: 'night' },
  7: { colors: ['#55efc4', '#81ecec', '#74b9ff'], name: 'Beach Town', timeOfDay: 'day' },
  8: { colors: ['#2d3436', '#4a4a4a', '#6c6c6c'], name: 'Industrial Zone', timeOfDay: 'overcast' },
  9: { colors: ['#ffeaa7', '#fdcb6e', '#f39c12'], name: 'Golden Hour', timeOfDay: 'sunset' },
  10: { colors: ['#0c0c0c', '#1a1a1a', '#2d2d2d'], name: 'Midnight Alley', timeOfDay: 'night' },
  11: { colors: ['#a8e6cf', '#dcedc1', '#ffd3b6'], name: 'Quiet Suburb', timeOfDay: 'day' },
  12: { colors: ['#e17055', '#d63031', '#c0392b'], name: 'Red Light District', timeOfDay: 'night' },
  13: { colors: ['#6c5ce7', '#a29bfe', '#dfe6e9'], name: 'Foggy Morning', timeOfDay: 'dawn' },
  14: { colors: ['#00b894', '#00cec9', '#0984e3'], name: 'Tech District', timeOfDay: 'day' },
  15: { colors: ['#2d3436', '#636e72', '#ff7675'], name: 'Bar District', timeOfDay: 'night' },
  16: { colors: ['#fab1a0', '#ffeaa7', '#dfe6e9'], name: 'Spring Morning', timeOfDay: 'day' },
  17: { colors: ['#0c0c0c', '#e17055', '#fdcb6e'], name: 'Fire District', timeOfDay: 'night' },
  18: { colors: ['#74b9ff', '#0984e3', '#2d3436'], name: 'Harbor Docks', timeOfDay: 'dusk' },
  19: { colors: ['#fdcb6e', '#e17055', '#d63031'], name: 'Desert Outskirts', timeOfDay: 'day' },
  20: { colors: ['#0c0c0c', '#6c5ce7', '#fd79a8'], name: 'Cyber City', timeOfDay: 'night' },
};

// Hide spot types
type HideSpotType = 'rooftop' | 'window' | 'doorway' | 'wall' | 'car' | 'street';

interface HideSpot {
  id: number;
  type: HideSpotType;
  x: number;
  y: number;
  width: number;
  height: number;
}

// Generate hide spots for each level
const generateHideSpots = (level: number): HideSpot[] => {
  const spots: HideSpot[] = [];
  const seed = level * 7919; // Prime number for variation
  
  // Rooftop spots (top of screen)
  spots.push({ id: 1, type: 'rooftop', x: 30, y: 40, width: 65, height: 75 });
  spots.push({ id: 2, type: 'rooftop', x: GAME_WIDTH / 2 - 32, y: 30, width: 65, height: 75 });
  spots.push({ id: 3, type: 'rooftop', x: GAME_WIDTH - 95, y: 45, width: 65, height: 75 });
  
  // Window spots (middle-upper)
  spots.push({ id: 4, type: 'window', x: 50, y: 130, width: 60, height: 70 });
  spots.push({ id: 5, type: 'window', x: GAME_WIDTH - 110, y: 125, width: 60, height: 70 });
  spots.push({ id: 6, type: 'window', x: GAME_WIDTH / 2 - 30, y: 140, width: 60, height: 70 });
  
  // Doorway spots (middle)
  spots.push({ id: 7, type: 'doorway', x: 20, y: 230, width: 65, height: 85 });
  spots.push({ id: 8, type: 'doorway', x: GAME_WIDTH - 85, y: 235, width: 65, height: 85 });
  
  // Wall spots (middle-lower)
  spots.push({ id: 9, type: 'wall', x: GAME_WIDTH / 2 - 35, y: 260, width: 70, height: 80 });
  spots.push({ id: 10, type: 'wall', x: 100, y: 280, width: 70, height: 80 });
  
  // Car spots (lower)
  spots.push({ id: 11, type: 'car', x: 40, y: 350, width: 70, height: 75 });
  spots.push({ id: 12, type: 'car', x: GAME_WIDTH - 110, y: 355, width: 70, height: 75 });
  
  // Street spots (bottom)
  spots.push({ id: 13, type: 'street', x: GAME_WIDTH / 2 - 35, y: GAME_HEIGHT - 100, width: 70, height: 80 });
  spots.push({ id: 14, type: 'street', x: 150, y: GAME_HEIGHT - 95, width: 70, height: 80 });
  
  return spots;
};

// Level configuration
interface LevelConfig {
  level: number;
  timeLimit: number; // seconds
  spawnInterval: number; // ms between spawns
  visibleDuration: number; // ms a gang member stays visible
  maxSimultaneous: number; // max gang members visible at once
  hitReward: number;
  xpPerHit: number;
}

const getLevelConfig = (level: number): LevelConfig => {
  const clampedLevel = Math.min(20, Math.max(1, level));
  
  // INTENSIFIED SETTINGS:
  // Level 1: 30s (was 60s), faster spawns, shorter visible duration
  // Level 20: 15s (was 25s), very fast spawns, very short visible duration
  const timeLimit = Math.max(15, 30 - (clampedLevel - 1) * 0.8); // 30s -> 15s (was 60s -> 25s)
  const spawnInterval = Math.max(180, 600 - (clampedLevel - 1) * 22); // Faster spawns (180-600ms, was 250-800ms)
  const visibleDuration = Math.max(400, 1200 - (clampedLevel - 1) * 40); // Much shorter visibility (400-1200ms, was 600-1800ms)
  const maxSimultaneous = Math.min(6, 3 + Math.floor(clampedLevel / 4)); // More simultaneous targets
  const hitReward = 5 + clampedLevel * 2;
  const xpPerHit = 2 + Math.floor(clampedLevel / 2);
  
  return {
    level: clampedLevel,
    timeLimit,
    spawnInterval,
    visibleDuration,
    maxSimultaneous,
    hitReward,
    xpPerHit,
  };
};

// Reward calculation
interface GameRewards {
  totalCash: number;
  totalXP: number;
  reputation: number;
}

const calculateRewards = (hits: number, level: number): GameRewards => {
  if (hits === 0) {
    return { totalCash: 0, totalXP: 0, reputation: 0 };
  }
  
  const config = getLevelConfig(level);
  const totalCash = hits * config.hitReward;
  const totalXP = hits * config.xpPerHit;
  const reputation = Math.max(1, Math.floor(hits / 3) + Math.floor(level / 5));
  
  return { totalCash, totalXP, reputation };
};

// Gang member popup data
interface GangMemberPopup {
  id: number;
  spotId: number;
  spriteKey: keyof typeof CHARACTER_SPRITES;
  opacity: Animated.Value;
  scale: Animated.Value;
  translateX: Animated.Value;
  translateY: Animated.Value;
  isHit: boolean;
  hideTimeout?: NodeJS.Timeout;
  movementAnimation?: Animated.CompositeAnimation;
}

export default function ShootoutSimulatorScreen() {
  const { shootoutId, shootoutName, difficulty, standalone } = useLocalSearchParams<{
    shootoutId: string;
    shootoutName: string;
    difficulty: string;
    standalone?: string;
  }>();

  const { playerId, player, setPlayer } = useGameStore();
  const invalidateMapQueries = useInvalidateMapQueries();
  const isStandalone = standalone === 'true';

  const level = parseInt(difficulty) || 1;
  const config = getLevelConfig(level);

  // Game state
  const [gameStarted, setGameStarted] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [timeLeft, setTimeLeft] = useState(config.timeLimit);
  const [hits, setHits] = useState(0);
  const [activePopups, setActivePopups] = useState<GangMemberPopup[]>([]);
  const [hideSpots] = useState<HideSpot[]>(() => generateHideSpots(level));
  const [showResults, setShowResults] = useState(false);
  const [rewards, setRewards] = useState<GameRewards | null>(null);
  const [hitEffects, setHitEffects] = useState<{ id: number; x: number; y: number; opacity: Animated.Value }[]>([]);
  const [gameId, setGameId] = useState<string | null>(null);

  // Refs
  const gameLoopRef = useRef<NodeJS.Timeout | null>(null);
  const spawnIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const popupIdRef = useRef(0);
  const hitEffectIdRef = useRef(0);

  // Background colors for current level
  const bgColors = CITY_BACKGROUNDS[level] || CITY_BACKGROUNDS[1];

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (gameLoopRef.current) clearInterval(gameLoopRef.current);
      if (spawnIntervalRef.current) clearInterval(spawnIntervalRef.current);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      activePopups.forEach(popup => {
        if (popup.hideTimeout) clearTimeout(popup.hideTimeout);
      });
    };
  }, []);

  // Spawn a new gang member
  const spawnGangMember = useCallback(() => {
    if (gameOver) return;

    setActivePopups(current => {
      if (current.length >= config.maxSimultaneous) return current;

      // Find available spots (not currently occupied)
      const occupiedSpotIds = current.map(p => p.spotId);
      const availableSpots = hideSpots.filter(s => !occupiedSpotIds.includes(s.id));
      
      if (availableSpots.length === 0) return current;

      // Pick random spot
      const spot = availableSpots[Math.floor(Math.random() * availableSpots.length)];
      
      // Pick random sprite
      const spriteKeys = Object.keys(CHARACTER_SPRITES) as (keyof typeof CHARACTER_SPRITES)[];
      const spriteKey = spriteKeys[Math.floor(Math.random() * spriteKeys.length)];

      // Movement range based on spot type - INCREASED for harder gameplay
      const moveRangeX = spot.type === 'street' ? 55 : (spot.type === 'car' ? 45 : 35); // Increased from 40/30/25
      const moveRangeY = spot.type === 'rooftop' ? 30 : (spot.type === 'window' ? 25 : 35); // Increased from 20/15/25

      const newPopup: GangMemberPopup = {
        id: ++popupIdRef.current,
        spotId: spot.id,
        spriteKey,
        opacity: new Animated.Value(0),
        scale: new Animated.Value(0.5),
        translateX: new Animated.Value(0),
        translateY: new Animated.Value(0),
        isHit: false,
      };

      // Animate popup appearance
      Animated.parallel([
        Animated.timing(newPopup.opacity, {
          toValue: 1,
          duration: 100, // Faster appearance
          useNativeDriver: true,
        }),
        Animated.spring(newPopup.scale, {
          toValue: 1,
          friction: 6,
          tension: 120,
          useNativeDriver: true,
        }),
      ]).start();

      // Create continuous side-to-side and up-down movement
      const movementDuration = 150 + Math.random() * 100; // MUCH faster movement (150-250ms per cycle, was 300-500ms)
      const randomStartX = Math.random() > 0.5 ? moveRangeX : -moveRangeX;
      const randomStartY = Math.random() > 0.5 ? moveRangeY : -moveRangeY;
      
      // Start movement animation loop
      const createMovementLoop = () => {
        const moveSequence = Animated.sequence([
          // Move to one side
          Animated.parallel([
            Animated.timing(newPopup.translateX, {
              toValue: randomStartX,
              duration: movementDuration,
              useNativeDriver: true,
            }),
            Animated.timing(newPopup.translateY, {
              toValue: randomStartY * 0.5,
              duration: movementDuration * 0.8,
              useNativeDriver: true,
            }),
          ]),
          // Move to other side
          Animated.parallel([
            Animated.timing(newPopup.translateX, {
              toValue: -randomStartX,
              duration: movementDuration,
              useNativeDriver: true,
            }),
            Animated.timing(newPopup.translateY, {
              toValue: -randomStartY * 0.5,
              duration: movementDuration * 0.8,
              useNativeDriver: true,
            }),
          ]),
          // Move back up/down
          Animated.parallel([
            Animated.timing(newPopup.translateX, {
              toValue: randomStartX * 0.5,
              duration: movementDuration * 0.7,
              useNativeDriver: true,
            }),
            Animated.timing(newPopup.translateY, {
              toValue: randomStartY,
              duration: movementDuration,
              useNativeDriver: true,
            }),
          ]),
          // Return towards center
          Animated.parallel([
            Animated.timing(newPopup.translateX, {
              toValue: -randomStartX * 0.3,
              duration: movementDuration * 0.6,
              useNativeDriver: true,
            }),
            Animated.timing(newPopup.translateY, {
              toValue: -randomStartY * 0.7,
              duration: movementDuration * 0.9,
              useNativeDriver: true,
            }),
          ]),
        ]);
        
        newPopup.movementAnimation = Animated.loop(moveSequence);
        newPopup.movementAnimation.start();
      };
      
      // Start movement after a tiny delay so it doesn't interfere with appear animation
      setTimeout(createMovementLoop, 100);

      // Set timeout to hide
      const visibleTime = config.visibleDuration + (Math.random() * 300 - 150); // Less randomness
      newPopup.hideTimeout = setTimeout(() => {
        hideGangMember(newPopup.id);
      }, visibleTime);

      return [...current, newPopup];
    });
  }, [config.maxSimultaneous, config.visibleDuration, hideSpots, gameOver]);

  // Hide a gang member (retreat)
  const hideGangMember = useCallback((popupId: number) => {
    setActivePopups(current => {
      const popup = current.find(p => p.id === popupId);
      if (!popup) return current;

      // Stop movement animation
      if (popup.movementAnimation) {
        popup.movementAnimation.stop();
      }

      // Animate retreat
      Animated.parallel([
        Animated.timing(popup.opacity, {
          toValue: 0,
          duration: 80, // Faster retreat
          useNativeDriver: true,
        }),
        Animated.timing(popup.scale, {
          toValue: 0.5,
          duration: 80,
          useNativeDriver: true,
        }),
      ]).start(() => {
        setActivePopups(prev => prev.filter(p => p.id !== popupId));
      });

      return current;
    });
  }, []);

  // Handle tap on gang member
  const handleTap = useCallback((popup: GangMemberPopup, spot: HideSpot) => {
    if (popup.isHit || gameOver) return;

    // Stop movement animation immediately
    if (popup.movementAnimation) {
      popup.movementAnimation.stop();
    }

    // Mark as hit
    setActivePopups(current =>
      current.map(p =>
        p.id === popup.id ? { ...p, isHit: true } : p
      )
    );

    // Clear hide timeout
    if (popup.hideTimeout) {
      clearTimeout(popup.hideTimeout);
    }

    // Increment hits
    setHits(h => h + 1);

    // Add hit effect
    const effectId = ++hitEffectIdRef.current;
    const effectOpacity = new Animated.Value(1);
    setHitEffects(prev => [...prev, { id: effectId, x: spot.x + spot.width / 2, y: spot.y + spot.height / 2, opacity: effectOpacity }]);

    // Animate hit effect
    Animated.timing(effectOpacity, {
      toValue: 0,
      duration: 400, // Slightly faster
      useNativeDriver: true,
    }).start(() => {
      setHitEffects(prev => prev.filter(e => e.id !== effectId));
    });

    // Animate gang member "hit" and remove
    Animated.sequence([
      Animated.timing(popup.scale, {
        toValue: 1.3,
        duration: 80, // Faster hit response
        useNativeDriver: true,
      }),
      Animated.parallel([
        Animated.timing(popup.opacity, {
          toValue: 0,
          duration: 150,
          useNativeDriver: true,
        }),
        Animated.timing(popup.scale, {
          toValue: 0,
          duration: 150,
          useNativeDriver: true,
        }),
      ]),
    ]).start(() => {
      setActivePopups(prev => prev.filter(p => p.id !== popup.id));
    });
  }, [gameOver]);

  // Start game
  const startGame = useCallback(async () => {
    let newGameId: string | null = null;
    
    // Start shootout on backend (for cooldown tracking and game session creation)
    if (!isStandalone && playerId && shootoutId) {
      try {
        const result = await apiStartShootout(shootoutId, playerId);
        newGameId = result.game_id;
        setGameId(newGameId);
      } catch (e: any) {
        const errorMsg = e.response?.data?.detail || e.message || 'Failed to start shootout';
        showGameToast(errorMsg, 'error');
        return;
      }
    } else if (isStandalone && playerId) {
      // For standalone mode, create a temporary game session via a dedicated endpoint
      try {
        const response = await fetch(`${API_URL}/api/shootouts/standalone/start?player_id=${playerId}&level=${level}`, {
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error('Failed to start standalone game');
        }
        const result = await response.json();
        newGameId = result.game_id;
        setGameId(newGameId);
      } catch (e: any) {
        console.log('Standalone mode - continuing without backend tracking');
        // In standalone mode, we can still play locally
      }
    }

    setGameStarted(true);
    setGameOver(false);
    setHits(0);
    setTimeLeft(config.timeLimit);
    setActivePopups([]);
    setShowResults(false);
    setRewards(null);

    // Start spawning gang members
    spawnIntervalRef.current = setInterval(() => {
      spawnGangMember();
    }, config.spawnInterval);

    // Initial spawn
    setTimeout(() => spawnGangMember(), 300);

    // Start timer
    timerIntervalRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          endGame();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [config.timeLimit, config.spawnInterval, spawnGangMember, isStandalone, playerId, shootoutId, level]);

  // End game
  const endGame = useCallback(async () => {
    setGameOver(true);

    // Clear all intervals
    if (spawnIntervalRef.current) {
      clearInterval(spawnIntervalRef.current);
      spawnIntervalRef.current = null;
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }

    // Clear all popup timeouts
    activePopups.forEach(popup => {
      if (popup.hideTimeout) clearTimeout(popup.hideTimeout);
    });

    // Calculate rewards locally for display
    const gameRewards = calculateRewards(hits, level);
    setRewards(gameRewards);

    // Complete on backend and get real rewards
    if (gameId && playerId) {
      try {
        const result = await apiCompleteShootout(gameId, hits, isStandalone);
        
        // Update rewards from backend response if available
        if (result.rewards) {
          setRewards({
            totalCash: result.rewards.cash || 0,
            totalXP: result.rewards.xp || 0,
            reputation: result.rewards.reputation || 0,
          });
        }
        
        // Refresh player data to get updated balances
        if (playerId) {
          try {
            const updatedPlayer = await getPlayer(playerId);
            setPlayer(updatedPlayer);
          } catch (playerErr) {
            console.error('Failed to refresh player data:', playerErr);
          }
        }
        
        invalidateMapQueries();
        
        if (result.message) {
          showGameToast(result.message, 'success');
        }
      } catch (e: any) {
        console.error('Failed to complete shootout:', e);
        // Still show local rewards even if backend call fails
        showGameToast('Rewards may not have saved. Check your balance.', 'error');
      }
    }

    // Show results after a short delay
    setTimeout(() => {
      setShowResults(true);
    }, 500);
  }, [hits, level, isStandalone, playerId, gameId, setPlayer, invalidateMapQueries, activePopups]);

  // Manual end game (for timer reaching 0)
  useEffect(() => {
    if (timeLeft <= 0 && gameStarted && !gameOver) {
      endGame();
    }
  }, [timeLeft, gameStarted, gameOver, endGame]);

  // Close handler
  const handleClose = () => {
    router.back();
  };

  // Render city background
  const renderCityBackground = () => {
    const isNight = bgColors.timeOfDay === 'night' || bgColors.timeOfDay === 'dusk';
    
    return (
      <View style={[styles.cityBackground, { backgroundColor: bgColors.colors[0] }]}>
        {/* Sky gradient */}
        <View style={[styles.skyGradient, { backgroundColor: bgColors.colors[1] }]} />
        
        {/* Buildings - Back row */}
        <View style={styles.buildingsBack}>
          {[0, 1, 2, 3, 4].map(i => (
            <View
              key={`back-${i}`}
              style={[
                styles.buildingBack,
                {
                  left: i * (GAME_WIDTH / 5),
                  height: 80 + (i % 3) * 30,
                  backgroundColor: isNight ? '#1a1a2e' : '#4a4a5a',
                },
              ]}
            >
              {/* Windows */}
              {[0, 1, 2].map(row => (
                <View key={row} style={styles.windowRow}>
                  {[0, 1].map(col => (
                    <View
                      key={col}
                      style={[
                        styles.windowSmall,
                        { backgroundColor: isNight ? (Math.random() > 0.5 ? '#ffeaa7' : '#444') : '#74b9ff' },
                      ]}
                    />
                  ))}
                </View>
              ))}
            </View>
          ))}
        </View>

        {/* Buildings - Front row */}
        <View style={styles.buildingsFront}>
          {[0, 1, 2, 3].map(i => (
            <View
              key={`front-${i}`}
              style={[
                styles.buildingFront,
                {
                  left: i * (GAME_WIDTH / 4) + 20,
                  height: 180 + (i % 2) * 50,
                  backgroundColor: isNight ? '#2d2d3d' : '#636e72',
                },
              ]}
            >
              {/* Large windows */}
              {[0, 1, 2, 3, 4].map(row => (
                <View key={row} style={styles.windowRow}>
                  {[0, 1, 2].map(col => (
                    <View
                      key={col}
                      style={[
                        styles.windowLarge,
                        { backgroundColor: isNight ? (Math.random() > 0.4 ? '#ffeaa7' : '#333') : '#81ecec' },
                      ]}
                    />
                  ))}
                </View>
              ))}
              {/* Door */}
              <View style={[styles.door, { backgroundColor: isNight ? '#1a1a1a' : '#2d3436' }]} />
            </View>
          ))}
        </View>

        {/* Street */}
        <View style={[styles.street, { backgroundColor: bgColors.colors[2] }]}>
          {/* Street lines */}
          <View style={styles.streetLine} />
          <View style={[styles.streetLine, { top: 20 }]} />
          
          {/* Parked cars */}
          <View style={[styles.parkedCar, { left: 30, backgroundColor: '#e74c3c' }]} />
          <View style={[styles.parkedCar, { left: GAME_WIDTH - 80, backgroundColor: '#3498db' }]} />
        </View>

        {/* Level indicator */}
        <View style={styles.levelBadge}>
          <Text style={styles.levelBadgeText}>{bgColors.name}</Text>
        </View>
      </View>
    );
  };

  // Render gang member popup
  const renderGangMember = (popup: GangMemberPopup) => {
    const spot = hideSpots.find(s => s.id === popup.spotId);
    if (!spot) return null;

    return (
      <Animated.View
        key={popup.id}
        style={[
          styles.gangMemberContainer,
          {
            left: spot.x,
            top: spot.y,
            width: spot.width,
            height: spot.height,
            opacity: popup.opacity,
            transform: [
              { scale: popup.scale },
              { translateX: popup.translateX },
              { translateY: popup.translateY },
            ],
          },
        ]}
      >
        <TouchableOpacity
          style={styles.gangMemberTouchable}
          onPress={() => handleTap(popup, spot)}
          activeOpacity={0.8}
          disabled={popup.isHit}
        >
          {/* Hide spot indicator */}
          <View style={[styles.hideSpotBg, styles[`hideSpot_${spot.type}` as keyof typeof styles] as any]} />
          
          {/* Gang member sprite */}
          <Image
            source={{ uri: getSpriteUrl(popup.spriteKey) }}
            style={[
              styles.gangMemberSprite,
              popup.isHit && styles.gangMemberHit,
            ]}
            resizeMode="contain"
          />
        </TouchableOpacity>
      </Animated.View>
    );
  };

  // Render hit effect
  const renderHitEffect = (effect: { id: number; x: number; y: number; opacity: Animated.Value }) => (
    <Animated.View
      key={effect.id}
      style={[
        styles.hitEffect,
        {
          left: effect.x - 30,
          top: effect.y - 30,
          opacity: effect.opacity,
        },
      ]}
    >
      <Text style={styles.hitEffectText}>💥 HIT!</Text>
    </Animated.View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.closeButton} onPress={handleClose}>
          <Ionicons name="close" size={28} color="#fff" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>SHOOTOUT</Text>
          <Text style={styles.headerSubtitle}>Level {level} - {bgColors.name}</Text>
        </View>
        <View style={styles.headerRight}>
          {gameStarted && !gameOver && (
            <View style={styles.timerContainer}>
              <Ionicons name="time" size={18} color={timeLeft <= 10 ? '#e74c3c' : '#f39c12'} />
              <Text style={[styles.timerText, timeLeft <= 10 && styles.timerTextLow]}>{Math.ceil(timeLeft)}s</Text>
            </View>
          )}
        </View>
      </View>

      {/* Stats Bar */}
      <View style={styles.statsBar}>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>HITS</Text>
          <Text style={styles.statValue}>{hits}</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>REWARD</Text>
          <Text style={styles.statValue}>${hits * config.hitReward}</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>TIME</Text>
          <Text style={[styles.statValue, timeLeft <= 10 && styles.statValueLow]}>{Math.ceil(timeLeft)}s</Text>
        </View>
      </View>

      {/* Game Area */}
      <View style={styles.gameContainer}>
        {/* City Background */}
        {renderCityBackground()}

        {/* Gang Member Popups */}
        {activePopups.map(renderGangMember)}

        {/* Hit Effects */}
        {hitEffects.map(renderHitEffect)}

        {/* Start Screen */}
        {!gameStarted && (
          <View style={styles.startOverlay}>
            <View style={styles.startBox}>
              <Text style={styles.startTitle}>🎯 SHOOTOUT SIMULATOR</Text>
              <Text style={styles.startSubtitle}>Level {level}</Text>
              <Text style={styles.startInstructions}>
                Tap the gang members as they pop up!{'\n'}
                Time: {Math.floor(config.timeLimit)}s{'\n'}
                Reward: ${config.hitReward}/hit
              </Text>
              <TouchableOpacity style={styles.startButton} onPress={startGame}>
                <Text style={styles.startButtonText}>START</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>

      {/* Results Modal */}
      <Modal visible={showResults} transparent animationType="fade">
        <View style={styles.resultsOverlay}>
          <View style={styles.resultsBox}>
            <Text style={styles.resultsTitle}>
              {hits >= 15 ? '🏆 EXCELLENT!' : hits >= 10 ? '🎯 GREAT!' : hits >= 5 ? '👍 GOOD!' : '💪 PRACTICE MORE!'}
            </Text>
            <Text style={styles.resultsSubtitle}>SHOOTOUT COMPLETE</Text>
            
            <View style={styles.resultsStats}>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Hits:</Text>
                <Text style={styles.resultValue}>{hits}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Cash Earned:</Text>
                <Text style={[styles.resultValue, styles.resultCash]}>${rewards?.totalCash || 0}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>XP Earned:</Text>
                <Text style={[styles.resultValue, styles.resultXP]}>+{rewards?.totalXP || 0}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Rep Gained:</Text>
                <Text style={[styles.resultValue, styles.resultRep]}>+{rewards?.reputation || 0}</Text>
              </View>
            </View>

            <View style={styles.resultsActions}>
              <TouchableOpacity style={styles.resultsButton} onPress={handleClose}>
                <Text style={styles.resultsButtonText}>DONE</Text>
              </TouchableOpacity>
            </View>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#1a1a1a',
  },
  closeButton: {
    padding: 4,
  },
  headerCenter: {
    alignItems: 'center',
  },
  headerTitle: {
    color: '#f39c12',
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  headerSubtitle: {
    color: '#888',
    fontSize: 11,
    marginTop: 2,
  },
  headerRight: {
    width: 60,
    alignItems: 'flex-end',
  },
  timerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  timerText: {
    color: '#f39c12',
    fontSize: 16,
    fontWeight: 'bold',
  },
  timerTextLow: {
    color: '#e74c3c',
  },
  statsBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 10,
    backgroundColor: '#1a1a1a',
    borderBottomWidth: 2,
    borderBottomColor: '#333',
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    color: '#666',
    fontSize: 10,
    letterSpacing: 1,
  },
  statValue: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  statValueLow: {
    color: '#e74c3c',
  },
  gameContainer: {
    flex: 1,
    width: GAME_WIDTH,
    height: GAME_HEIGHT,
    alignSelf: 'center',
    marginVertical: 10,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 3,
    borderColor: '#333',
  },
  
  // City background styles
  cityBackground: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  skyGradient: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '30%',
    opacity: 0.5,
  },
  buildingsBack: {
    position: 'absolute',
    top: 50,
    left: 0,
    right: 0,
    height: 120,
  },
  buildingBack: {
    position: 'absolute',
    width: GAME_WIDTH / 5 - 5,
    bottom: 0,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  buildingsFront: {
    position: 'absolute',
    top: 100,
    left: 0,
    right: 0,
    height: 250,
  },
  buildingFront: {
    position: 'absolute',
    width: GAME_WIDTH / 4 - 30,
    bottom: 0,
    borderTopLeftRadius: 6,
    borderTopRightRadius: 6,
    padding: 5,
  },
  windowRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 4,
  },
  windowSmall: {
    width: 10,
    height: 12,
    borderRadius: 1,
  },
  windowLarge: {
    width: 14,
    height: 18,
    borderRadius: 2,
  },
  door: {
    position: 'absolute',
    bottom: 0,
    left: '30%',
    width: '40%',
    height: 30,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  street: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 80,
  },
  streetLine: {
    position: 'absolute',
    top: 10,
    left: '10%',
    right: '10%',
    height: 3,
    backgroundColor: '#ffeaa7',
    opacity: 0.5,
  },
  parkedCar: {
    position: 'absolute',
    bottom: 15,
    width: 50,
    height: 25,
    borderRadius: 6,
  },
  levelBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  levelBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },

  // Gang member styles
  gangMemberContainer: {
    position: 'absolute',
    zIndex: 10,
  },
  gangMemberTouchable: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  hideSpotBg: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: 8,
    opacity: 0.3,
  },
  hideSpot_rooftop: {
    backgroundColor: '#2d3436',
  },
  hideSpot_window: {
    backgroundColor: '#636e72',
  },
  hideSpot_doorway: {
    backgroundColor: '#2d2d2d',
  },
  hideSpot_wall: {
    backgroundColor: '#4a4a4a',
  },
  hideSpot_car: {
    backgroundColor: '#1a1a1a',
  },
  hideSpot_street: {
    backgroundColor: '#2d3436',
  },
  gangMemberSprite: {
    width: '100%',
    height: '100%',
  },
  gangMemberHit: {
    tintColor: '#ff0000',
  },

  // Hit effect
  hitEffect: {
    position: 'absolute',
    width: 60,
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 20,
  },
  hitEffectText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffeaa7',
    textShadowColor: '#e74c3c',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 4,
  },

  // Start overlay
  startOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  startBox: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#f39c12',
    width: '85%',
  },
  startTitle: {
    color: '#f39c12',
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  startSubtitle: {
    color: '#888',
    fontSize: 16,
    marginBottom: 16,
  },
  startInstructions: {
    color: '#aaa',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 20,
  },
  startButton: {
    backgroundColor: '#f39c12',
    paddingHorizontal: 48,
    paddingVertical: 14,
    borderRadius: 10,
  },
  startButtonText: {
    color: '#000',
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 2,
  },

  // Results modal
  resultsOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  resultsBox: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#27ae60',
    width: '85%',
  },
  resultsTitle: {
    color: '#f39c12',
    fontSize: 26,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  resultsSubtitle: {
    color: '#888',
    fontSize: 14,
    letterSpacing: 2,
    marginBottom: 20,
  },
  resultsStats: {
    width: '100%',
    marginBottom: 20,
  },
  resultRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  resultLabel: {
    color: '#888',
    fontSize: 14,
  },
  resultValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  resultCash: {
    color: '#27ae60',
  },
  resultXP: {
    color: '#3498db',
  },
  resultRep: {
    color: '#9b59b6',
  },
  resultsActions: {
    flexDirection: 'row',
    gap: 16,
  },
  resultsButton: {
    backgroundColor: '#27ae60',
    paddingHorizontal: 40,
    paddingVertical: 12,
    borderRadius: 10,
  },
  resultsButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
});
