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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { startShootout, completeShootout } from '../services/api';
import { showGameToast } from '../components/GameToast';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Game constants
const GAME_WIDTH = Math.min(SCREEN_WIDTH - 20, 380);
const GAME_HEIGHT = Math.min(SCREEN_HEIGHT - 280, 420);
const CROSSHAIR_SIZE = 60;
const GANG_MEMBER_WIDTH = 50;
const GANG_MEMBER_HEIGHT = 80;
const TOTAL_SHOTS = 12;

// 24-bit pixel art colors
const COLORS = {
  background: '#1a1a2e',
  street: '#2d2d2d',
  building: '#3d3d4d',
  buildingAccent: '#4a4a5a',
  crosshair: '#ff3333',
  crosshairGlow: 'rgba(255, 51, 51, 0.3)',
  hitFlash: '#ffff00',
  gangMember1: '#e74c3c',
  gangMember2: '#9b59b6',
  gangMember3: '#3498db',
  gangMember4: '#27ae60',
};

// Level configuration - 20 levels
interface LevelConfig {
  level: number;
  timeLimit: number; // seconds
  crosshairSpeed: number; // pixels per frame
  crosshairErratic: number; // direction change frequency (lower = more erratic)
  hitReward: number; // cash per hit
  xpPerHit: number;
}

const getLevelConfig = (level: number): LevelConfig => {
  const clampedLevel = Math.min(20, Math.max(1, level));
  
  // Time decreases with level: L1 = 45s, L20 = 15s
  const timeLimit = Math.max(15, 45 - (clampedLevel - 1) * 1.5);
  
  // Speed increases: L1 = 2, L20 = 8
  const crosshairSpeed = 2 + (clampedLevel - 1) * 0.32;
  
  // Erratic-ness: L1 = 60 frames between direction changes, L20 = 10 frames
  const crosshairErratic = Math.max(10, 60 - (clampedLevel - 1) * 2.6);
  
  // Rewards scale with level
  const hitReward = 5 + clampedLevel * 2;
  const xpPerHit = 2 + Math.floor(clampedLevel / 2);
  
  return {
    level: clampedLevel,
    timeLimit,
    crosshairSpeed,
    crosshairErratic,
    hitReward,
    xpPerHit,
  };
};

// Gang member data
interface GangMember {
  id: number;
  x: number;
  y: number;
  color: string;
  isHit: boolean;
  hitAnim: Animated.Value;
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
    // Create 5 gang members at fixed positions
    const members: GangMember[] = [];
    const positions = [
      { x: 30, y: GAME_HEIGHT - 180 },
      { x: 90, y: GAME_HEIGHT - 200 },
      { x: GAME_WIDTH / 2 - GANG_MEMBER_WIDTH / 2, y: GAME_HEIGHT - 220 },
      { x: GAME_WIDTH - 140, y: GAME_HEIGHT - 200 },
      { x: GAME_WIDTH - 80, y: GAME_HEIGHT - 180 },
    ];
    const colors = [COLORS.gangMember1, COLORS.gangMember2, COLORS.gangMember3, COLORS.gangMember4, COLORS.gangMember1];
    
    positions.forEach((pos, i) => {
      members.push({
        id: i,
        x: pos.x,
        y: pos.y,
        color: colors[i],
        isHit: false,
        hitAnim: new Animated.Value(0),
      });
    });
    
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
        // Add random angle change
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
      const memberCenterX = member.x + GANG_MEMBER_WIDTH / 2;
      const memberCenterY = member.y + GANG_MEMBER_HEIGHT / 2;
      
      // Check if crosshair center is within member bounds (with some tolerance)
      const hitTolerance = 15;
      if (
        crosshairCenter.x > member.x - hitTolerance &&
        crosshairCenter.x < member.x + GANG_MEMBER_WIDTH + hitTolerance &&
        crosshairCenter.y > member.y - hitTolerance &&
        crosshairCenter.y < member.y + GANG_MEMBER_HEIGHT + hitTolerance
      ) {
        hitMember = member;
        break;
      }
    }
    
    if (hitMember) {
      // Hit!
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
    
    // Check if out of shots
    if (newShotsRemaining <= 0) {
      endGame();
    }
  }, [isGameOver, shotsRemaining, gangMembers]);

  const endGame = useCallback(() => {
    if (isGameOver) return;
    
    setIsGameOver(true);
    cleanup();
    
    // Calculate final rewards
    const rewards = calculateRewards(hits, difficulty);
    setGameRewards(rewards);
    setShowResultsModal(true);
    
    // Animate rewards
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
    
    // Submit to backend
    submitResults(hits);
  }, [isGameOver, hits, difficulty]);

  // Watch for game over conditions
  useEffect(() => {
    if (gameStarted && !isGameOver) {
      if (shotsRemaining <= 0 || timeRemaining <= 0) {
        endGame();
      }
    }
  }, [shotsRemaining, timeRemaining, gameStarted, isGameOver, endGame]);

  const submitResults = async (finalHits: number) => {
    if (!gameId || isStandalone) return;
    
    try {
      const result = await completeShootout(gameId, finalHits);
      
      if (result.hits > 0) {
        showGameToast({
          type: 'success',
          title: 'SHOOTOUT COMPLETE!',
          message: `${result.hits} hits! +$${result.rewards?.cash || 0}`,
          duration: 2000,
        });
        
        if (refreshPlayer) refreshPlayer();
      }
      
      if (playerId) {
        invalidateCooldowns(playerId);
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
      {/* Sky */}
      <View style={styles.sky} />
      
      {/* Buildings */}
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
      
      {/* Street */}
      <View style={styles.street}>
        <View style={styles.streetLine} />
      </View>
    </View>
  );

  // Render gang members
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
      const hitColor = member.hitAnim.interpolate({
        inputRange: [0, 0.5, 1],
        outputRange: [member.color, COLORS.hitFlash, member.color],
      });
      
      return (
        <Animated.View
          key={member.id}
          style={[
            styles.gangMember,
            {
              left: member.x,
              top: member.y,
              transform: [
                { scale: hitScale },
                { rotate: hitRotate },
              ],
            },
          ]}
        >
          {/* Body */}
          <Animated.View style={[styles.gangMemberBody, { backgroundColor: hitColor as any }]}>
            {/* Head */}
            <View style={styles.gangMemberHead}>
              <View style={styles.gangMemberEye} />
              <View style={[styles.gangMemberEye, { right: 8 }]} />
            </View>
            {/* Torso */}
            <View style={styles.gangMemberTorso} />
            {/* Arms */}
            <View style={[styles.gangMemberArm, { left: -8 }]} />
            <View style={[styles.gangMemberArm, { right: -8 }]} />
            {/* Legs */}
            <View style={styles.gangMemberLegs}>
              <View style={styles.gangMemberLeg} />
              <View style={styles.gangMemberLeg} />
            </View>
          </Animated.View>
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
          <Text style={styles.headerSubtitle}>Level {difficulty} {'⭐'.repeat(Math.min(5, Math.ceil(difficulty / 4)))}</Text>
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
              <Text style={styles.statsHintText}>🔫 {TOTAL_SHOTS} shots • ⏱️ {Math.floor(levelConfig.timeLimit)}s</Text>
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
              
              {/* Muzzle flash on shoot */}
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
    width: GANG_MEMBER_WIDTH,
    height: GANG_MEMBER_HEIGHT,
    zIndex: 5,
  },
  gangMemberBody: {
    flex: 1,
    alignItems: 'center',
    borderRadius: 4,
  },
  gangMemberHead: {
    width: 24,
    height: 24,
    backgroundColor: '#f5d5a3',
    borderRadius: 12,
    marginTop: 4,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  gangMemberEye: {
    position: 'absolute',
    width: 4,
    height: 4,
    backgroundColor: '#000',
    borderRadius: 2,
    top: 8,
    left: 8,
  },
  gangMemberTorso: {
    width: 30,
    height: 25,
    backgroundColor: 'inherit',
    marginTop: 2,
    borderRadius: 4,
  },
  gangMemberArm: {
    position: 'absolute',
    top: 32,
    width: 10,
    height: 20,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 4,
  },
  gangMemberLegs: {
    flexDirection: 'row',
    gap: 4,
    marginTop: 2,
  },
  gangMemberLeg: {
    width: 12,
    height: 20,
    backgroundColor: '#2c3e50',
    borderRadius: 4,
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
