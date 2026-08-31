import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TouchableWithoutFeedback,
  Dimensions,
  Animated,
  Modal,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { startShootout, completeShootout } from '../services/api';
import { showGameToast } from '../components/GameToast';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';
import Constants from 'expo-constants';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Game constants
const GAME_WIDTH = Math.min(SCREEN_WIDTH - 20, 380);
const GAME_HEIGHT = Math.min(SCREEN_HEIGHT - 280, 420);
const CROSSHAIR_SIZE = 60;
const GANG_MEMBER_WIDTH = 70;
const GANG_MEMBER_HEIGHT = 100;
const TOTAL_SHOTS = 12;

// API base URL for background removal
const API_BASE_URL = Constants.expoConfig?.extra?.EXPO_BACKEND_URL || process.env.EXPO_PUBLIC_API_URL || '';

// Character sprite URLs
const CHARACTER_SPRITES = {
  cowboy: {
    original: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/05168415d6654f72bab2f6c82452d7b0_AQPZH2SCZMVdkXQRiMWNEyzVehHj0Uw5NdWG-7hJbPMozETNm8mrmOmZ6STIjFFLLIKWtjwrDDFChRnmKlcLLXR7.jpg',
    needsBgRemoval: true,
    name: 'Cowboy',
  },
  bandana: {
    original: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/c07d7e1fbb8c44eb962c77a46b74a893_AQMN4ikUKuAU-0zhhOSDaZOWw65Nj9dItWHT1ZNubA4ZREzZJpzpFwzpd4R_LiwVETxLOe84jK2gVm-y0AnU4kDm.jpg',
    needsBgRemoval: true,
    name: 'Bandana',
  },
  crewJacket: {
    original: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/8dca7a6977dd4701b3e1d791602862fb_crew3_cutout.png',
    needsBgRemoval: false,
    name: 'Crew Jacket',
  },
  dualGuns: {
    original: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/8b8d7d50201349a6a33bbeecbfb0ed5f_guy_2_guns_cutout.png',
    needsBgRemoval: false,
    name: 'Dual Guns',
  },
  girlRed: {
    original: 'https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/3ae4914efaaf4047acf32ef42f44f11d_violent_tech_cutout.png',
    needsBgRemoval: false,
    name: 'Girl Red',
  },
};

// Get sprite URL (with background removal if needed)
const getSpriteUrl = (spriteKey: keyof typeof CHARACTER_SPRITES): string => {
  const sprite = CHARACTER_SPRITES[spriteKey];
  if (sprite.needsBgRemoval) {
    return `${API_BASE_URL}/api/sprites/remove-bg?url=${encodeURIComponent(sprite.original)}`;
  }
  return sprite.original;
};

// 24-bit pixel art colors
const COLORS = {
  background: '#1a1a2e',
  street: '#2d2d2d',
  building: '#3d3d4d',
  buildingAccent: '#4a4a5a',
  crosshair: '#ff3333',
  crosshairGlow: 'rgba(255, 51, 51, 0.3)',
  hitFlash: '#ffff00',
};

// Level configuration - 20 levels
interface LevelConfig {
  level: number;
  timeLimit: number;
  crosshairSpeed: number;
  crosshairErratic: number;
  hitReward: number;
  xpPerHit: number;
  characterCount: number; // 3 at low levels, 5 at high levels
}

const getLevelConfig = (level: number): LevelConfig => {
  const clampedLevel = Math.min(20, Math.max(1, level));
  
  const timeLimit = Math.max(15, 45 - (clampedLevel - 1) * 1.5);
  const crosshairSpeed = 2 + (clampedLevel - 1) * 0.32;
  const crosshairErratic = Math.max(10, 60 - (clampedLevel - 1) * 2.6);
  const hitReward = 5 + clampedLevel * 2;
  const xpPerHit = 2 + Math.floor(clampedLevel / 2);
  
  // Lower levels (1-7): 3 characters, Medium (8-14): 4 characters, High (15-20): 5 characters
  let characterCount = 3;
  if (clampedLevel >= 15) characterCount = 5;
  else if (clampedLevel >= 8) characterCount = 4;
  
  return {
    level: clampedLevel,
    timeLimit,
    crosshairSpeed,
    crosshairErratic,
    hitReward,
    xpPerHit,
    characterCount,
  };
};

// Gang member data
interface GangMember {
  id: number;
  x: number;
  y: number;
  spriteKey: keyof typeof CHARACTER_SPRITES;
  isHit: boolean;
  hitAnim: Animated.Value;
  width: number;
  height: number;
}

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

// Position configurations for different levels
const getPositionConfig = (level: number, characterCount: number): { x: number; y: number; spriteKey: keyof typeof CHARACTER_SPRITES; width: number; height: number }[] => {
  const allSprites: (keyof typeof CHARACTER_SPRITES)[] = ['cowboy', 'bandana', 'crewJacket', 'dualGuns', 'girlRed'];
  
  // Shuffle sprites based on level to create variety
  const shuffledSprites = [...allSprites].sort(() => {
    // Use level as seed for consistent shuffling per level
    return Math.sin(level * 12345) - 0.5;
  });
  
  // Different layout patterns based on level ranges
  const levelMod = level % 5; // Creates 5 different patterns
  
  if (characterCount === 3) {
    // Lower levels - 3 characters with wide spacing
    const positions3Wide = [
      [
        { x: 30, y: GAME_HEIGHT - 180, width: 70, height: 100 },
        { x: GAME_WIDTH / 2 - 35, y: GAME_HEIGHT - 200, width: 70, height: 100 },
        { x: GAME_WIDTH - 100, y: GAME_HEIGHT - 180, width: 70, height: 100 },
      ],
      [
        { x: 50, y: GAME_HEIGHT - 190, width: 65, height: 95 },
        { x: GAME_WIDTH / 2 - 32, y: GAME_HEIGHT - 170, width: 65, height: 95 },
        { x: GAME_WIDTH - 115, y: GAME_HEIGHT - 195, width: 65, height: 95 },
      ],
      [
        { x: 20, y: GAME_HEIGHT - 175, width: 75, height: 105 },
        { x: GAME_WIDTH / 2 - 37, y: GAME_HEIGHT - 210, width: 75, height: 105 },
        { x: GAME_WIDTH - 95, y: GAME_HEIGHT - 185, width: 75, height: 105 },
      ],
      [
        { x: 60, y: GAME_HEIGHT - 185, width: 68, height: 98 },
        { x: GAME_WIDTH / 2 - 34, y: GAME_HEIGHT - 195, width: 68, height: 98 },
        { x: GAME_WIDTH - 128, y: GAME_HEIGHT - 175, width: 68, height: 98 },
      ],
      [
        { x: 40, y: GAME_HEIGHT - 195, width: 72, height: 102 },
        { x: GAME_WIDTH / 2 - 36, y: GAME_HEIGHT - 180, width: 72, height: 102 },
        { x: GAME_WIDTH - 112, y: GAME_HEIGHT - 190, width: 72, height: 102 },
      ],
    ];
    
    return positions3Wide[levelMod].map((pos, i) => ({
      ...pos,
      spriteKey: shuffledSprites[i % shuffledSprites.length],
    }));
  }
  
  if (characterCount === 4) {
    // Medium levels - 4 characters with moderate spacing
    const positions4 = [
      [
        { x: 15, y: GAME_HEIGHT - 175, width: 65, height: 95 },
        { x: GAME_WIDTH / 3 - 32, y: GAME_HEIGHT - 195, width: 65, height: 95 },
        { x: (2 * GAME_WIDTH / 3) - 32, y: GAME_HEIGHT - 185, width: 65, height: 95 },
        { x: GAME_WIDTH - 80, y: GAME_HEIGHT - 180, width: 65, height: 95 },
      ],
      [
        { x: 25, y: GAME_HEIGHT - 185, width: 62, height: 92 },
        { x: GAME_WIDTH / 4 - 31, y: GAME_HEIGHT - 200, width: 62, height: 92 },
        { x: GAME_WIDTH / 2 - 31, y: GAME_HEIGHT - 175, width: 62, height: 92 },
        { x: GAME_WIDTH - 87, y: GAME_HEIGHT - 190, width: 62, height: 92 },
      ],
      [
        { x: 35, y: GAME_HEIGHT - 190, width: 68, height: 98 },
        { x: GAME_WIDTH / 3 - 34, y: GAME_HEIGHT - 180, width: 68, height: 98 },
        { x: (2 * GAME_WIDTH / 3) - 34, y: GAME_HEIGHT - 200, width: 68, height: 98 },
        { x: GAME_WIDTH - 103, y: GAME_HEIGHT - 185, width: 68, height: 98 },
      ],
      [
        { x: 20, y: GAME_HEIGHT - 180, width: 64, height: 94 },
        { x: GAME_WIDTH / 4, y: GAME_HEIGHT - 195, width: 64, height: 94 },
        { x: GAME_WIDTH / 2 + 10, y: GAME_HEIGHT - 185, width: 64, height: 94 },
        { x: GAME_WIDTH - 84, y: GAME_HEIGHT - 195, width: 64, height: 94 },
      ],
      [
        { x: 30, y: GAME_HEIGHT - 195, width: 66, height: 96 },
        { x: GAME_WIDTH / 3 - 33, y: GAME_HEIGHT - 175, width: 66, height: 96 },
        { x: (2 * GAME_WIDTH / 3) - 33, y: GAME_HEIGHT - 190, width: 66, height: 96 },
        { x: GAME_WIDTH - 96, y: GAME_HEIGHT - 180, width: 66, height: 96 },
      ],
    ];
    
    return positions4[levelMod].map((pos, i) => ({
      ...pos,
      spriteKey: shuffledSprites[i % shuffledSprites.length],
    }));
  }
  
  // High levels - 5 characters with tighter/overlapping spacing
  const positions5Tight = [
    [
      { x: 10, y: GAME_HEIGHT - 175, width: 58, height: 88 },
      { x: 55, y: GAME_HEIGHT - 195, width: 58, height: 88 },
      { x: GAME_WIDTH / 2 - 29, y: GAME_HEIGHT - 210, width: 58, height: 88 },
      { x: GAME_WIDTH - 113, y: GAME_HEIGHT - 190, width: 58, height: 88 },
      { x: GAME_WIDTH - 68, y: GAME_HEIGHT - 175, width: 58, height: 88 },
    ],
    [
      { x: 15, y: GAME_HEIGHT - 185, width: 55, height: 85 },
      { x: 60, y: GAME_HEIGHT - 175, width: 55, height: 85 },
      { x: GAME_WIDTH / 2 - 27, y: GAME_HEIGHT - 200, width: 55, height: 85 },
      { x: GAME_WIDTH - 115, y: GAME_HEIGHT - 180, width: 55, height: 85 },
      { x: GAME_WIDTH - 60, y: GAME_HEIGHT - 195, width: 55, height: 85 },
    ],
    [
      { x: 5, y: GAME_HEIGHT - 190, width: 60, height: 90 },
      { x: 50, y: GAME_HEIGHT - 205, width: 60, height: 90 },
      { x: GAME_WIDTH / 2 - 30, y: GAME_HEIGHT - 180, width: 60, height: 90 },
      { x: GAME_WIDTH - 110, y: GAME_HEIGHT - 200, width: 60, height: 90 },
      { x: GAME_WIDTH - 55, y: GAME_HEIGHT - 185, width: 60, height: 90 },
    ],
    [
      { x: 20, y: GAME_HEIGHT - 180, width: 56, height: 86 },
      { x: 65, y: GAME_HEIGHT - 200, width: 56, height: 86 },
      { x: GAME_WIDTH / 2 - 28, y: GAME_HEIGHT - 190, width: 56, height: 86 },
      { x: GAME_WIDTH - 121, y: GAME_HEIGHT - 175, width: 56, height: 86 },
      { x: GAME_WIDTH - 65, y: GAME_HEIGHT - 200, width: 56, height: 86 },
    ],
    [
      { x: 8, y: GAME_HEIGHT - 195, width: 57, height: 87 },
      { x: 58, y: GAME_HEIGHT - 180, width: 57, height: 87 },
      { x: GAME_WIDTH / 2 - 28, y: GAME_HEIGHT - 205, width: 57, height: 87 },
      { x: GAME_WIDTH - 115, y: GAME_HEIGHT - 195, width: 57, height: 87 },
      { x: GAME_WIDTH - 58, y: GAME_HEIGHT - 180, width: 57, height: 87 },
    ],
  ];
  
  return positions5Tight[levelMod].map((pos, i) => ({
    ...pos,
    spriteKey: shuffledSprites[i % shuffledSprites.length],
  }));
};

export default function ShootoutSimulator() {
  const params = useLocalSearchParams();
  const shootoutId = params.shootoutId as string;
  const shootoutName = params.shootoutName as string || 'Shootout';
  const difficulty = parseInt(params.difficulty as string) || 1;
  const isStandalone = params.standalone === 'true';
  
  const levelConfig = getLevelConfig(difficulty);
  
  const { playerId, refreshPlayer } = useGameStore();
  const { invalidateCooldowns, invalidatePlayer } = useInvalidateMapQueries();
  
  const [gameId, setGameId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [gameStarted, setGameStarted] = useState(false);
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [gameRewards, setGameRewards] = useState<GameRewards | null>(null);
  
  // Game state
  const [shotsRemaining, setShotsRemaining] = useState(TOTAL_SHOTS);
  const [hits, setHits] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(levelConfig.timeLimit);
  const [isGameOver, setIsGameOver] = useState(false);
  const [gangMembers, setGangMembers] = useState<GangMember[]>([]);
  
  // Crosshair position
  const crosshairX = useRef(new Animated.Value(GAME_WIDTH / 2 - CROSSHAIR_SIZE / 2)).current;
  const crosshairY = useRef(new Animated.Value(GAME_HEIGHT / 2 - CROSSHAIR_SIZE / 2)).current;
  const crosshairPosRef = useRef({ x: GAME_WIDTH / 2, y: GAME_HEIGHT / 2 });
  const crosshairDirRef = useRef({ dx: 1, dy: 1 });
  const frameCountRef = useRef(0);
  
  const gameLoopRef = useRef<number | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  const rewardAnimValues = useRef({
    cash: new Animated.Value(0),
    xp: new Animated.Value(0),
    rep: new Animated.Value(0),
  }).current;

  // Initialize game
  useEffect(() => {
    initializeGame();
    return () => {
      cleanup();
    };
  }, []);

  const cleanup = () => {
    if (gameLoopRef.current) {
      cancelAnimationFrame(gameLoopRef.current);
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const initializeGame = async () => {
    if (isStandalone) {
      setGameId('standalone');
      setLoading(false);
      return;
    }
    
    if (!playerId || !shootoutId) {
      setLoading(false);
      return;
    }
    
    try {
      const result = await startShootout(shootoutId, playerId);
      setGameId(result.game_id);
    } catch (error: any) {
      showGameToast({
        type: 'error',
        title: 'Error',
        message: error?.response?.data?.detail || 'Failed to start shootout',
        duration: 2000,
      });
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const initializeGangMembers = () => {
    const positionConfig = getPositionConfig(difficulty, levelConfig.characterCount);
    
    const members: GangMember[] = positionConfig.map((config, i) => ({
      id: i,
      x: config.x,
      y: config.y,
      spriteKey: config.spriteKey,
      isHit: false,
      hitAnim: new Animated.Value(0),
      width: config.width,
      height: config.height,
    }));
    
    setGangMembers(members);
  };

  const startGame = () => {
    cleanup();
    setGameStarted(true);
    setShowResultsModal(false);
    setGameRewards(null);
    setShotsRemaining(TOTAL_SHOTS);
    setHits(0);
    setTimeRemaining(levelConfig.timeLimit);
    setIsGameOver(false);
    
    // Reset crosshair
    crosshairPosRef.current = { x: GAME_WIDTH / 2, y: GAME_HEIGHT / 2 };
    crosshairX.setValue(GAME_WIDTH / 2 - CROSSHAIR_SIZE / 2);
    crosshairY.setValue(GAME_HEIGHT / 2 - CROSSHAIR_SIZE / 2);
    crosshairDirRef.current = { dx: Math.random() > 0.5 ? 1 : -1, dy: Math.random() > 0.5 ? 1 : -1 };
    frameCountRef.current = 0;
    
    // Reset animations
    rewardAnimValues.cash.setValue(0);
    rewardAnimValues.xp.setValue(0);
    rewardAnimValues.rep.setValue(0);
    
    initializeGangMembers();
    runGameLoop();
    startTimer();
  };

  const startTimer = () => {
    timerRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          endGame();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const runGameLoop = () => {
    const loop = () => {
      frameCountRef.current++;
      
      // Move crosshair
      let { x, y } = crosshairPosRef.current;
      let { dx, dy } = crosshairDirRef.current;
      
      // Random direction change based on erratic-ness
      if (frameCountRef.current % Math.floor(levelConfig.crosshairErratic) === 0) {
        const angleChange = (Math.random() - 0.5) * Math.PI;
        const currentAngle = Math.atan2(dy, dx);
        const newAngle = currentAngle + angleChange;
        dx = Math.cos(newAngle);
        dy = Math.sin(newAngle);
        crosshairDirRef.current = { dx, dy };
      }
      
      // Move crosshair
      x += dx * levelConfig.crosshairSpeed;
      y += dy * levelConfig.crosshairSpeed;
      
      // Bounce off walls
      const padding = CROSSHAIR_SIZE / 2;
      if (x < padding || x > GAME_WIDTH - padding) {
        dx = -dx;
        x = Math.max(padding, Math.min(GAME_WIDTH - padding, x));
        crosshairDirRef.current.dx = dx;
      }
      if (y < padding || y > GAME_HEIGHT - padding) {
        dy = -dy;
        y = Math.max(padding, Math.min(GAME_HEIGHT - padding, y));
        crosshairDirRef.current.dy = dy;
      }
      
      crosshairPosRef.current = { x, y };
      crosshairX.setValue(x - CROSSHAIR_SIZE / 2);
      crosshairY.setValue(y - CROSSHAIR_SIZE / 2);
      
      gameLoopRef.current = requestAnimationFrame(loop);
    };
    
    gameLoopRef.current = requestAnimationFrame(loop);
  };

  const handleShoot = useCallback(() => {
    if (isGameOver || shotsRemaining <= 0) return;
    
    const newShotsRemaining = shotsRemaining - 1;
    setShotsRemaining(newShotsRemaining);
    
    // Check if crosshair is over any gang member
    const crosshairCenter = crosshairPosRef.current;
    let hitMember: GangMember | null = null;
    
    for (const member of gangMembers) {
      const hitTolerance = 15;
      if (
        crosshairCenter.x > member.x - hitTolerance &&
        crosshairCenter.x < member.x + member.width + hitTolerance &&
        crosshairCenter.y > member.y - hitTolerance &&
        crosshairCenter.y < member.y + member.height + hitTolerance
      ) {
        hitMember = member;
        break;
      }
    }
    
    if (hitMember) {
      setHits(prev => prev + 1);
      
      // Play hit animation
      Animated.sequence([
        Animated.timing(hitMember.hitAnim, {
          toValue: 1,
          duration: 100,
          useNativeDriver: true,
        }),
        Animated.timing(hitMember.hitAnim, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
    }
    
    if (newShotsRemaining <= 0) {
      endGame();
    }
  }, [isGameOver, shotsRemaining, gangMembers]);

  const endGame = useCallback(() => {
    if (isGameOver) return;
    
    setIsGameOver(true);
    cleanup();
    
    const rewards = calculateRewards(hits, difficulty);
    setGameRewards(rewards);
    setShowResultsModal(true);
    
    if (hits > 0) {
      Animated.sequence([
        Animated.timing(rewardAnimValues.cash, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(rewardAnimValues.xp, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(rewardAnimValues.rep, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    }
    
    submitResults(hits);
  }, [isGameOver, hits, difficulty]);

  useEffect(() => {
    if (gameStarted && !isGameOver) {
      if (shotsRemaining <= 0 || timeRemaining <= 0) {
        endGame();
      }
    }
  }, [shotsRemaining, timeRemaining, gameStarted, isGameOver, endGame]);

  const submitResults = async (finalHits: number) => {
    if (!gameId) return;
    
    try {
      const result = await completeShootout(gameId, finalHits, isStandalone);
      
      if (result.hits > 0) {
        const rewardMessage = isStandalone
          ? `${result.hits} hits! +$${result.rewards?.cash || 0} (Practice Mode: 50% rewards)`
          : `${result.hits} hits! +$${result.rewards?.cash || 0}`;
        showGameToast({
          type: 'success',
          title: 'SHOOTOUT COMPLETE!',
          message: rewardMessage,
          duration: 2000,
        });
        
        if (refreshPlayer) refreshPlayer();
      }
      
      if (playerId && !isStandalone) {
        invalidateCooldowns(playerId);
        invalidatePlayer(playerId);
      } else if (playerId) {
        invalidatePlayer(playerId);
      }
    } catch (error) {
      console.error('Failed to complete shootout:', error);
    }
  };

  const handleGoBack = () => {
    cleanup();
    router.back();
  };

  // Render street background
  const renderBackground = () => (
    <View style={styles.background}>
      <View style={styles.sky} />
      <View style={styles.buildingsContainer}>
        <View style={[styles.building, { left: 0, width: 60, height: 150 }]}>
          <View style={styles.window} />
          <View style={[styles.window, { marginTop: 15 }]} />
        </View>
        <View style={[styles.building, { left: 70, width: 80, height: 180 }]}>
          <View style={styles.window} />
          <View style={[styles.window, { marginTop: 15 }]} />
          <View style={[styles.window, { marginTop: 15 }]} />
        </View>
        <View style={[styles.building, { right: 70, width: 80, height: 170 }]}>
          <View style={styles.window} />
          <View style={[styles.window, { marginTop: 15 }]} />
        </View>
        <View style={[styles.building, { right: 0, width: 60, height: 140 }]}>
          <View style={styles.window} />
          <View style={[styles.window, { marginTop: 15 }]} />
        </View>
      </View>
      <View style={styles.street}>
        <View style={styles.streetLine} />
      </View>
    </View>
  );

  // Render gang members with custom sprites
  const renderGangMembers = () => {
    return gangMembers.map(member => {
      const hitScale = member.hitAnim.interpolate({
        inputRange: [0, 1],
        outputRange: [1, 0.8],
      });
      const hitRotate = member.hitAnim.interpolate({
        inputRange: [0, 1],
        outputRange: ['0deg', '-15deg'],
      });
      const hitOpacity = member.hitAnim.interpolate({
        inputRange: [0, 0.5, 1],
        outputRange: [1, 0.5, 1],
      });
      
      const spriteUrl = getSpriteUrl(member.spriteKey);
      
      return (
        <Animated.View
          key={member.id}
          style={[
            styles.gangMember,
            {
              left: member.x,
              top: member.y,
              width: member.width,
              height: member.height,
              transform: [
                { scale: hitScale },
                { rotate: hitRotate },
              ],
              opacity: hitOpacity,
            },
          ]}
        >
          <Image
            source={{ uri: spriteUrl }}
            style={styles.gangMemberSprite}
            resizeMode="contain"
          />
        </Animated.View>
      );
    });
  };

  // Render crosshair
  const renderCrosshair = () => (
    <Animated.View
      style={[
        styles.crosshair,
        {
          left: crosshairX,
          top: crosshairY,
        },
      ]}
    >
      <View style={styles.crosshairGlow} />
      <View style={styles.crosshairCenter} />
      <View style={[styles.crosshairLine, styles.crosshairLineH]} />
      <View style={[styles.crosshairLine, styles.crosshairLineV]} />
      <View style={styles.crosshairCircle} />
    </Animated.View>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading Shootout...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={handleGoBack}>
          <Ionicons name="close" size={24} color="#fff" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>{shootoutName}</Text>
          <Text style={styles.headerSubtitle}>Level {difficulty} {'⭐'.repeat(Math.min(5, Math.ceil(difficulty / 4)))} • {levelConfig.characterCount} targets</Text>
        </View>
      </View>

      {/* Stats Bar */}
      {gameStarted && (
        <View style={styles.statsBar}>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>SHOTS</Text>
            <Text style={styles.statValue}>{shotsRemaining}/{TOTAL_SHOTS}</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>HITS</Text>
            <Text style={[styles.statValue, { color: '#27ae60' }]}>{hits}</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>TIME</Text>
            <Text style={[styles.statValue, { color: timeRemaining <= 10 ? '#e74c3c' : '#fff' }]}>
              {timeRemaining}s
            </Text>
          </View>
        </View>
      )}

      {/* Game Area */}
      <View style={styles.gameContainer}>
        {!gameStarted ? (
          <View style={styles.startScreen}>
            <Text style={styles.startEmoji}>🔫🎯</Text>
            <Text style={styles.startTitle}>SHOOTOUT</Text>
            
            <View style={styles.instructionsCard}>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>🎯</Text>
                <Text style={styles.instructionText}>Crosshair moves automatically</Text>
              </View>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>👆</Text>
                <Text style={styles.instructionText}>Tap anywhere to shoot</Text>
              </View>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>🧍</Text>
                <Text style={styles.instructionText}>Hit gang members for points</Text>
              </View>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>⏱️</Text>
                <Text style={styles.instructionText}>Score before time runs out!</Text>
              </View>
            </View>
            
            <View style={styles.statsHint}>
              <Text style={styles.statsHintText}>🔫 {TOTAL_SHOTS} shots • ⏱️ {Math.floor(levelConfig.timeLimit)}s • 🧍 {levelConfig.characterCount} targets</Text>
            </View>
            
            <TouchableOpacity style={styles.startButton} onPress={startGame} activeOpacity={0.8}>
              <Ionicons name="flash" size={24} color="#fff" />
              <Text style={styles.startButtonText}>START SHOOTOUT</Text>
              <Ionicons name="arrow-forward" size={22} color="#fff" />
            </TouchableOpacity>
          </View>
        ) : (
          <TouchableWithoutFeedback onPress={handleShoot}>
            <View style={[styles.gameArea, { width: GAME_WIDTH, height: GAME_HEIGHT }]}>
              {renderBackground()}
              {renderGangMembers()}
              {renderCrosshair()}
              
              {isGameOver && (
                <View style={styles.gameOverOverlay}>
                  <Text style={styles.gameOverEmoji}>
                    {hits > 0 ? '🎯' : '💨'}
                  </Text>
                  <Text style={[styles.gameOverText, { color: hits > 0 ? '#27ae60' : '#e74c3c' }]}>
                    {hits > 0 ? `${hits} HITS!` : 'NO HITS'}
                  </Text>
                </View>
              )}
            </View>
          </TouchableWithoutFeedback>
        )}
      </View>

      {/* Shoot instruction */}
      {gameStarted && !isGameOver && (
        <View style={styles.shootHint}>
          <Ionicons name="hand-left" size={24} color="#888" />
          <Text style={styles.shootHintText}>TAP TO SHOOT</Text>
        </View>
      )}

      {/* Results Modal */}
      <Modal
        visible={showResultsModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowResultsModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.resultsModal}>
            {hits > 0 ? (
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>🎯🔫</Text>
                  <Text style={styles.resultTitle}>SHOOTOUT COMPLETE!</Text>
                  <Text style={styles.resultSubtitle}>Nice shooting!</Text>
                </View>
                
                <View style={styles.hitsCard}>
                  <Text style={styles.hitsLabel}>Total Hits</Text>
                  <Text style={styles.hitsValue}>{hits}</Text>
                  <Text style={styles.hitsAccuracy}>
                    {Math.round((hits / TOTAL_SHOTS) * 100)}% accuracy
                  </Text>
                </View>
                
                <View style={styles.rewardsContainer}>
                  <Text style={styles.rewardsTitle}>🎁 REWARDS</Text>
                  
                  <Animated.View style={[styles.rewardRow, {
                    opacity: rewardAnimValues.cash,
                    transform: [{
                      translateX: rewardAnimValues.cash.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-50, 0],
                      }),
                    }],
                  }]}>
                    <View style={styles.rewardIcon}>
                      <Text style={styles.rewardIconText}>💰</Text>
                    </View>
                    <View style={styles.rewardDetails}>
                      <Text style={styles.rewardLabel}>Cash</Text>
                      <Text style={styles.rewardValue}>+${gameRewards?.totalCash || 0}</Text>
                    </View>
                  </Animated.View>
                  
                  <Animated.View style={[styles.rewardRow, {
                    opacity: rewardAnimValues.xp,
                    transform: [{
                      translateX: rewardAnimValues.xp.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-50, 0],
                      }),
                    }],
                  }]}>
                    <View style={[styles.rewardIcon, { backgroundColor: '#2196f320' }]}>
                      <Text style={styles.rewardIconText}>⭐</Text>
                    </View>
                    <View style={styles.rewardDetails}>
                      <Text style={styles.rewardLabel}>Experience</Text>
                      <Text style={[styles.rewardValue, { color: '#2196f3' }]}>+{gameRewards?.totalXP || 0} XP</Text>
                    </View>
                  </Animated.View>
                  
                  <Animated.View style={[styles.rewardRow, {
                    opacity: rewardAnimValues.rep,
                    transform: [{
                      translateX: rewardAnimValues.rep.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-50, 0],
                      }),
                    }],
                  }]}>
                    <View style={[styles.rewardIcon, { backgroundColor: '#9c27b020' }]}>
                      <Text style={styles.rewardIconText}>👑</Text>
                    </View>
                    <View style={styles.rewardDetails}>
                      <Text style={styles.rewardLabel}>Reputation</Text>
                      <Text style={[styles.rewardValue, { color: '#9c27b0' }]}>+{gameRewards?.reputation || 0}</Text>
                    </View>
                  </Animated.View>
                </View>
                
                <TouchableOpacity style={styles.collectButton} onPress={handleGoBack}>
                  <Ionicons name="checkmark-circle" size={24} color="#fff" />
                  <Text style={styles.collectButtonText}>COLLECT REWARDS</Text>
                </TouchableOpacity>
                
                <TouchableOpacity style={styles.playAgainButton} onPress={startGame}>
                  <Text style={styles.playAgainText}>Play Again</Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>💨🔫</Text>
                  <Text style={[styles.resultTitle, { color: '#e74c3c' }]}>NO HITS!</Text>
                  <Text style={styles.resultSubtitle}>Better luck next time</Text>
                </View>
                
                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statRowLabel}>Shots Fired:</Text>
                    <Text style={styles.statRowValue}>{TOTAL_SHOTS - shotsRemaining}</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statRowLabel}>Hits:</Text>
                    <Text style={[styles.statRowValue, { color: '#e74c3c' }]}>0</Text>
                  </View>
                </View>
                
                <View style={styles.noRewardsBox}>
                  <Ionicons name="close-circle" size={40} color="#e74c3c" />
                  <Text style={styles.noRewardsText}>No Rewards</Text>
                  <Text style={styles.noRewardsSubtext}>Score at least 1 hit to earn rewards!</Text>
                </View>
                
                <TouchableOpacity style={styles.retryButtonLarge} onPress={startGame}>
                  <Ionicons name="refresh" size={24} color="#fff" />
                  <Text style={styles.retryButtonLargeText}>TRY AGAIN</Text>
                </TouchableOpacity>
                
                <TouchableOpacity style={styles.exitButtonLarge} onPress={handleGoBack}>
                  <Text style={styles.exitButtonLargeText}>Exit</Text>
                </TouchableOpacity>
              </>
            )}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#333',
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerInfo: {
    flex: 1,
    marginLeft: 12,
  },
  headerTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: '#e74c3c',
    fontSize: 12,
    marginTop: 2,
  },
  statsBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 10,
    backgroundColor: '#111',
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  statBox: {
    alignItems: 'center',
  },
  statLabel: {
    color: '#666',
    fontSize: 10,
    fontWeight: 'bold',
  },
  statValue: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
  },
  gameContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  startScreen: {
    alignItems: 'center',
    padding: 24,
  },
  startEmoji: {
    fontSize: 56,
    marginBottom: 12,
  },
  startTitle: {
    color: '#fff',
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  instructionsCard: {
    backgroundColor: '#252525',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333',
    width: '100%',
    maxWidth: 320,
  },
  instructionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  instructionIcon: {
    fontSize: 20,
    width: 40,
    textAlign: 'center',
  },
  instructionText: {
    color: '#e0e0e0',
    fontSize: 13,
    fontWeight: '500',
    flex: 1,
    marginLeft: 8,
  },
  statsHint: {
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.3)',
  },
  statsHintText: {
    color: '#e74c3c',
    fontSize: 14,
    fontWeight: '700',
  },
  startButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    backgroundColor: '#c0392b',
    paddingHorizontal: 32,
    paddingVertical: 18,
    borderRadius: 16,
    borderWidth: 3,
    borderColor: '#e74c3c',
    shadowColor: '#c0392b',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  startButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1,
  },
  gameArea: {
    backgroundColor: COLORS.background,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  background: {
    ...StyleSheet.absoluteFillObject,
  },
  sky: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '40%',
    backgroundColor: '#1a1a2e',
  },
  buildingsContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '70%',
  },
  building: {
    position: 'absolute',
    bottom: 0,
    backgroundColor: COLORS.building,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
    padding: 8,
  },
  window: {
    width: 20,
    height: 15,
    backgroundColor: '#ffeaa7',
    opacity: 0.7,
    alignSelf: 'center',
    borderRadius: 2,
  },
  street: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 60,
    backgroundColor: COLORS.street,
    justifyContent: 'center',
    alignItems: 'center',
  },
  streetLine: {
    width: '80%',
    height: 4,
    backgroundColor: '#f1c40f',
  },
  gangMember: {
    position: 'absolute',
    zIndex: 5,
  },
  gangMemberSprite: {
    width: '100%',
    height: '100%',
  },
  crosshair: {
    position: 'absolute',
    width: CROSSHAIR_SIZE,
    height: CROSSHAIR_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  crosshairGlow: {
    position: 'absolute',
    width: CROSSHAIR_SIZE + 10,
    height: CROSSHAIR_SIZE + 10,
    borderRadius: (CROSSHAIR_SIZE + 10) / 2,
    backgroundColor: COLORS.crosshairGlow,
  },
  crosshairCenter: {
    position: 'absolute',
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: COLORS.crosshair,
  },
  crosshairLine: {
    position: 'absolute',
    backgroundColor: COLORS.crosshair,
  },
  crosshairLineH: {
    width: CROSSHAIR_SIZE - 10,
    height: 2,
  },
  crosshairLineV: {
    width: 2,
    height: CROSSHAIR_SIZE - 10,
  },
  crosshairCircle: {
    position: 'absolute',
    width: CROSSHAIR_SIZE - 20,
    height: CROSSHAIR_SIZE - 20,
    borderRadius: (CROSSHAIR_SIZE - 20) / 2,
    borderWidth: 2,
    borderColor: COLORS.crosshair,
  },
  gameOverOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 20,
  },
  gameOverEmoji: {
    fontSize: 64,
    marginBottom: 16,
  },
  gameOverText: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  shootHint: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: 16,
    backgroundColor: '#111',
  },
  shootHintText: {
    color: '#888',
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  resultsModal: {
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#333',
  },
  resultHeader: {
    alignItems: 'center',
    marginBottom: 20,
  },
  resultEmoji: {
    fontSize: 56,
    marginBottom: 8,
  },
  resultTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#27ae60',
    marginBottom: 4,
  },
  resultSubtitle: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
  },
  hitsCard: {
    backgroundColor: 'rgba(39, 174, 96, 0.15)',
    borderRadius: 14,
    padding: 20,
    marginBottom: 16,
    alignItems: 'center',
    width: '100%',
    borderWidth: 1,
    borderColor: 'rgba(39, 174, 96, 0.3)',
  },
  hitsLabel: {
    color: '#888',
    fontSize: 12,
    marginBottom: 8,
  },
  hitsValue: {
    fontSize: 48,
    fontWeight: '900',
    color: '#27ae60',
  },
  hitsAccuracy: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
  statsContainer: {
    width: '100%',
    backgroundColor: '#0f0f1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  statRowLabel: {
    fontSize: 14,
    color: '#888',
  },
  statRowValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  rewardsContainer: {
    width: '100%',
    backgroundColor: '#0a2a0a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#4caf5040',
  },
  rewardsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#27ae60',
    textAlign: 'center',
    marginBottom: 16,
  },
  rewardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  rewardIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: '#4caf5020',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  rewardIconText: {
    fontSize: 22,
  },
  rewardDetails: {
    flex: 1,
  },
  rewardLabel: {
    fontSize: 11,
    color: '#888',
    marginBottom: 2,
  },
  rewardValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#27ae60',
  },
  collectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#27ae60',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: '100%',
    gap: 8,
  },
  collectButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  playAgainButton: {
    marginTop: 12,
    paddingVertical: 12,
  },
  playAgainText: {
    color: '#888',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
  noRewardsBox: {
    width: '100%',
    backgroundColor: '#2a0a0a',
    borderRadius: 12,
    padding: 24,
    marginBottom: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e74c3c40',
  },
  noRewardsText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#e74c3c',
    marginTop: 8,
  },
  noRewardsSubtext: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
    textAlign: 'center',
  },
  retryButtonLarge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f39c12',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: '100%',
    gap: 8,
  },
  retryButtonLargeText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  exitButtonLarge: {
    marginTop: 12,
    paddingVertical: 12,
  },
  exitButtonLargeText: {
    color: '#888',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
});
