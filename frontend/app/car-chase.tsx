import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
  Animated,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { startCarChase, completeCarChase } from '../services/api';
import { showGameToast } from '../components/GameToast';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Game constants
const GAME_WIDTH = Math.min(SCREEN_WIDTH - 40, 360);
const GAME_HEIGHT = SCREEN_HEIGHT - 200;
const LANE_COUNT = 3;
const LANE_WIDTH = GAME_WIDTH / LANE_COUNT;
const CAR_WIDTH = 50;
const CAR_HEIGHT = 80;
const OBSTACLE_SIZE = 50;
const POLICE_CAR_START_Y = -150;
const POLICE_CATCH_Y = GAME_HEIGHT - CAR_HEIGHT - 30;

// Balanced gameplay constants - challenging but fair
const INITIAL_SPEED = 2.5; // Start slow for reaction time
const MAX_SPEED = 8; // Cap max speed for manageability
const SPEED_INCREMENT = 0.0008; // Very gradual speed increase
const BASE_SPAWN_INTERVAL = 280; // More spacing between obstacles
const MIN_SPAWN_INTERVAL = 150; // Minimum gap even at high difficulty

// Obstacle types
const OBSTACLES = [
  { type: 'car', emoji: '🚗', color: '#e74c3c' },
  { type: 'car', emoji: '🚙', color: '#3498db' },
  { type: 'truck', emoji: '🚚', color: '#f39c12' },
  { type: 'barrier', emoji: '🚧', color: '#e67e22' },
  { type: 'cone', emoji: '🔶', color: '#ff6b35' },
];

interface Obstacle {
  id: number;
  lane: number;
  y: number;
  type: string;
  emoji: string;
  color: string;
}

interface GameState {
  playerLane: number;
  obstacles: Obstacle[];
  policeY: number;
  distance: number;
  speed: number;
  isGameOver: boolean;
  won: boolean;
}

// Reward calculation interface
interface GameRewards {
  baseCash: number;
  distanceBonus: number;
  timeBonus: number;
  difficultyBonus: number;
  totalCash: number;
  baseXP: number;
  totalXP: number;
  reputation: number;
}

// Calculate rewards based on performance
const calculateRewards = (
  distance: number,
  timeSeconds: number,
  difficulty: number,
  countyLineDistance: number,
  won: boolean
): GameRewards => {
  if (!won) {
    return {
      baseCash: 0,
      distanceBonus: 0,
      timeBonus: 0,
      difficultyBonus: 0,
      totalCash: 0,
      baseXP: 0,
      totalXP: 0,
      reputation: 0,
    };
  }
  
  // Base rewards for completing the chase
  const baseCash = 100 + (difficulty * 20);
  const baseXP = 50 + (difficulty * 10);
  
  // Distance bonus - reward for how far beyond minimum they traveled
  // (distance should be at least countyLineDistance to win)
  const distancePercent = Math.min(150, (distance / countyLineDistance) * 100);
  const distanceBonus = Math.floor(baseCash * (distancePercent - 100) / 100 * 0.5);
  
  // Time bonus - longer survival = more rewards (capped at 120 seconds)
  const effectiveTime = Math.min(120, timeSeconds);
  const timeBonus = Math.floor(effectiveTime * 2);
  
  // Difficulty multiplier bonus
  const difficultyMultiplier = 1 + (difficulty * 0.15);
  const difficultyBonus = Math.floor((baseCash + distanceBonus + timeBonus) * (difficultyMultiplier - 1));
  
  const totalCash = baseCash + Math.max(0, distanceBonus) + timeBonus + difficultyBonus;
  const totalXP = Math.floor(baseXP * difficultyMultiplier) + Math.floor(timeSeconds * 0.5);
  
  // Reputation scales with difficulty
  const reputation = Math.floor(5 + difficulty * 2);
  
  return {
    baseCash,
    distanceBonus: Math.max(0, distanceBonus),
    timeBonus,
    difficultyBonus,
    totalCash,
    baseXP,
    totalXP,
    reputation,
  };
};

export default function CarChaseGame() {
  const params = useLocalSearchParams();
  const chaseId = params.chaseId as string;
  const chaseName = params.chaseName as string || 'Car Chase';
  const difficulty = parseInt(params.difficulty as string) || 5;
  const countyLineDistance = parseInt(params.countyLineDistance as string) || 8000;
  const isStandalone = params.standalone === 'true';
  
  const { playerId } = useGameStore();
  
  const [gameId, setGameId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [gameStarted, setGameStarted] = useState(false);
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [gameRewards, setGameRewards] = useState<GameRewards | null>(null);
  const [gameState, setGameState] = useState<GameState>({
    playerLane: 1,
    obstacles: [],
    policeY: POLICE_CAR_START_Y,
    distance: 0,
    speed: INITIAL_SPEED,
    isGameOver: false,
    won: false,
  });
  
  const gameLoopRef = useRef<number | null>(null);
  const obstacleIdRef = useRef(0);
  const lastSpawnRef = useRef(0);
  const playerLaneAnim = useRef(new Animated.Value(1)).current;
  const gameStartTimeRef = useRef<number>(0);
  const rewardAnimValues = useRef({
    cash: new Animated.Value(0),
    xp: new Animated.Value(0),
    rep: new Animated.Value(0),
  }).current;

  // Initialize game
  useEffect(() => {
    initializeGame();
    return () => {
      if (gameLoopRef.current) {
        cancelAnimationFrame(gameLoopRef.current);
      }
    };
  }, []);

  const initializeGame = async () => {
    if (isStandalone) {
      // Standalone mode - no API call needed
      setGameId('standalone');
      setLoading(false);
      return;
    }
    
    if (!playerId || !chaseId) {
      setLoading(false);
      return;
    }
    
    try {
      const result = await startCarChase(chaseId, playerId);
      setGameId(result.game_id);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to start car chase');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const startGame = () => {
    setGameStarted(true);
    setShowResultsModal(false);
    setGameRewards(null);
    gameStartTimeRef.current = Date.now();
    setGameState({
      playerLane: 1,
      obstacles: [],
      policeY: POLICE_CAR_START_Y,
      distance: 0,
      speed: INITIAL_SPEED + (difficulty * 0.2), // Slight difficulty adjustment
      isGameOver: false,
      won: false,
    });
    lastSpawnRef.current = 0;
    obstacleIdRef.current = 0;
    playerLaneAnim.setValue(1);
    // Reset animation values
    rewardAnimValues.cash.setValue(0);
    rewardAnimValues.xp.setValue(0);
    rewardAnimValues.rep.setValue(0);
    runGameLoop();
  };

  const runGameLoop = () => {
    const loop = () => {
      setGameState(prev => {
        if (prev.isGameOver) return prev;

        const newDistance = prev.distance + prev.speed;
        // Gradual speed increase - slow ramp up for fair gameplay
        const newSpeed = Math.min(MAX_SPEED, prev.speed + SPEED_INCREMENT);
        
        // Spawn obstacles with more spacing
        let newObstacles = [...prev.obstacles];
        // Larger spawn interval = more gaps between obstacles
        const spawnInterval = Math.max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL - (difficulty * 10));
        
        if (newDistance - lastSpawnRef.current > spawnInterval) {
          lastSpawnRef.current = newDistance;
          
          // Much lower chance of spawning 2 obstacles at once (only at high difficulty)
          // Difficulty 1-5: always 1 obstacle
          // Difficulty 6-10: 10-30% chance of 2 obstacles
          const spawnCount = (difficulty >= 6 && Math.random() < (difficulty - 5) * 0.06) ? 2 : 1;
          const usedLanes: number[] = [];
          
          for (let i = 0; i < spawnCount; i++) {
            let lane = Math.floor(Math.random() * LANE_COUNT);
            // Avoid spawning in same lane
            let attempts = 0;
            while (usedLanes.includes(lane) && attempts < 10) {
              lane = Math.floor(Math.random() * LANE_COUNT);
              attempts++;
            }
            usedLanes.push(lane);
            
            const obsType = OBSTACLES[Math.floor(Math.random() * OBSTACLES.length)];
            newObstacles.push({
              id: obstacleIdRef.current++,
              lane,
              y: -OBSTACLE_SIZE,
              type: obsType.type,
              emoji: obsType.emoji,
              color: obsType.color,
            });
          }
        }
        
        // Move obstacles at current speed
        newObstacles = newObstacles
          .map(obs => ({ ...obs, y: obs.y + newSpeed }))
          .filter(obs => obs.y < GAME_HEIGHT + OBSTACLE_SIZE);
        
        // Check collisions
        const playerX = prev.playerLane * LANE_WIDTH + LANE_WIDTH / 2 - CAR_WIDTH / 2;
        const playerY = GAME_HEIGHT - CAR_HEIGHT - 20;
        
        for (const obs of newObstacles) {
          const obsX = obs.lane * LANE_WIDTH + LANE_WIDTH / 2 - OBSTACLE_SIZE / 2;
          const obsY = obs.y;
          
          // Simple box collision with slight forgiveness (smaller hitbox)
          const hitboxPadding = 5;
          if (
            playerX + hitboxPadding < obsX + OBSTACLE_SIZE - hitboxPadding &&
            playerX + CAR_WIDTH - hitboxPadding > obsX + hitboxPadding &&
            playerY + hitboxPadding < obsY + OBSTACLE_SIZE - hitboxPadding &&
            playerY + CAR_HEIGHT - hitboxPadding > obsY + hitboxPadding
          ) {
            // Collision detected!
            return {
              ...prev,
              obstacles: newObstacles,
              distance: newDistance,
              isGameOver: true,
              won: false,
            };
          }
        }
        
        // Police car pursues more slowly - gives player more time
        const policeSpeed = 0.02 + (difficulty * 0.005);
        const newPoliceY = Math.min(POLICE_CATCH_Y, prev.policeY + policeSpeed);
        
        // Check if police caught player
        if (newPoliceY >= POLICE_CATCH_Y) {
          return {
            ...prev,
            obstacles: newObstacles,
            policeY: newPoliceY,
            distance: newDistance,
            isGameOver: true,
            won: false,
          };
        }
        
        // Check win condition
        if (newDistance >= countyLineDistance) {
          return {
            ...prev,
            obstacles: newObstacles,
            policeY: newPoliceY,
            distance: newDistance,
            speed: newSpeed,
            isGameOver: true,
            won: true,
          };
        }
        
        return {
          ...prev,
          obstacles: newObstacles,
          policeY: newPoliceY,
          distance: newDistance,
          speed: newSpeed,
        };
      });
      
      gameLoopRef.current = requestAnimationFrame(loop);
    };
    
    gameLoopRef.current = requestAnimationFrame(loop);
  };

  // Stop game loop when game is over
  useEffect(() => {
    if (gameState.isGameOver && gameLoopRef.current) {
      cancelAnimationFrame(gameLoopRef.current);
      handleGameOver();
    }
  }, [gameState.isGameOver]);

  const handleGameOver = async () => {
    // Calculate time played
    const timePlayedSeconds = (Date.now() - gameStartTimeRef.current) / 1000;
    
    // Calculate rewards based on performance
    const rewards = calculateRewards(
      gameState.distance,
      timePlayedSeconds,
      difficulty,
      countyLineDistance,
      gameState.won
    );
    
    setGameRewards(rewards);
    setShowResultsModal(true);
    
    // Animate reward values if won
    if (gameState.won) {
      Animated.sequence([
        Animated.timing(rewardAnimValues.cash, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(rewardAnimValues.xp, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(rewardAnimValues.rep, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
      ]).start();
    }
    
    if (!gameId) return;
    
    if (isStandalone) {
      // Standalone mode - rewards are visual only
      return;
    }
    
    try {
      const result = await completeCarChase(gameId, gameState.won, Math.floor(gameState.distance));
      
      if (result.won) {
        showGameToast({
          type: 'success',
          title: 'REWARDS COLLECTED!',
          message: `+$${result.rewards?.cash || rewards.totalCash} | +${result.rewards?.xp || rewards.totalXP} XP`,
          duration: 2000,
        });
      }
    } catch (error) {
      console.error('Failed to complete car chase:', error);
    }
  };

  const changeLane = useCallback((direction: 'left' | 'right') => {
    if (gameState.isGameOver) return;
    
    setGameState(prev => {
      const newLane = direction === 'left' 
        ? Math.max(0, prev.playerLane - 1)
        : Math.min(LANE_COUNT - 1, prev.playerLane + 1);
      
      Animated.spring(playerLaneAnim, {
        toValue: newLane,
        useNativeDriver: false,
        tension: 100,
        friction: 10,
      }).start();
      
      return { ...prev, playerLane: newLane };
    });
  }, [gameState.isGameOver]);

  const handleGoBack = () => {
    if (gameLoopRef.current) {
      cancelAnimationFrame(gameLoopRef.current);
    }
    router.back();
  };

  const progressPercent = Math.min(100, (gameState.distance / countyLineDistance) * 100);
  const policeDistancePercent = Math.max(0, 100 - ((gameState.policeY - POLICE_CAR_START_Y) / (POLICE_CATCH_Y - POLICE_CAR_START_Y)) * 100);

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Starting Chase...</Text>
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
          <Text style={styles.headerTitle}>{chaseName}</Text>
          <Text style={styles.headerSubtitle}>Difficulty: {'⭐'.repeat(Math.min(5, Math.ceil(difficulty / 2)))}</Text>
        </View>
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progressPercent}%` }]} />
        </View>
        <View style={styles.progressLabels}>
          <Text style={styles.progressText}>🚗 START</Text>
          <Text style={styles.progressText}>COUNTY LINE 🏁</Text>
        </View>
        <Text style={styles.distanceText}>{Math.floor(gameState.distance)}m / {countyLineDistance}m</Text>
      </View>

      {/* Police Warning */}
      <View style={styles.policeWarning}>
        <Text style={styles.policeText}>🚔 Police: {Math.floor(policeDistancePercent)}% behind</Text>
        <View style={styles.policeBar}>
          <View style={[styles.policeFill, { width: `${100 - policeDistancePercent}%` }]} />
        </View>
      </View>

      {/* Game Area */}
      <View style={styles.gameContainer}>
        {!gameStarted ? (
          <View style={styles.startScreen}>
            <Text style={styles.startEmoji}>🚗💨</Text>
            <Text style={styles.startTitle}>CAR CHASE</Text>
            <Text style={styles.startInstructions}>
              Tap LEFT or RIGHT to change lanes{'\n'}
              Avoid traffic and obstacles{'\n'}
              Reach the county line to escape!
            </Text>
            <TouchableOpacity style={styles.startButton} onPress={startGame}>
              <Text style={styles.startButtonText}>START CHASE</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={[styles.gameArea, { width: GAME_WIDTH, height: GAME_HEIGHT }]}>
            {/* Road Background */}
            <View style={styles.road}>
              {/* Lane dividers */}
              {[1, 2].map(i => (
                <View key={i} style={[styles.laneDivider, { left: i * LANE_WIDTH - 2 }]} />
              ))}
            </View>

            {/* Obstacles */}
            {gameState.obstacles.map(obs => (
              <View
                key={obs.id}
                style={[
                  styles.obstacle,
                  {
                    left: obs.lane * LANE_WIDTH + LANE_WIDTH / 2 - OBSTACLE_SIZE / 2,
                    top: obs.y,
                    width: OBSTACLE_SIZE,
                    height: OBSTACLE_SIZE,
                  },
                ]}
              >
                <Text style={styles.obstacleEmoji}>{obs.emoji}</Text>
              </View>
            ))}

            {/* Police Car */}
            <View
              style={[
                styles.policeCar,
                {
                  left: gameState.playerLane * LANE_WIDTH + LANE_WIDTH / 2 - CAR_WIDTH / 2,
                  top: gameState.policeY,
                },
              ]}
            >
              <Text style={styles.carEmoji}>🚔</Text>
            </View>

            {/* Player Car */}
            <Animated.View
              style={[
                styles.playerCar,
                {
                  left: playerLaneAnim.interpolate({
                    inputRange: [0, 1, 2],
                    outputRange: [
                      LANE_WIDTH / 2 - CAR_WIDTH / 2,
                      LANE_WIDTH * 1.5 - CAR_WIDTH / 2,
                      LANE_WIDTH * 2.5 - CAR_WIDTH / 2,
                    ],
                  }),
                  bottom: 20,
                },
              ]}
            >
              <Text style={styles.carEmoji}>🚘</Text>
            </Animated.View>

            {/* Simple Overlay when game is over (full results shown in modal) */}
            {gameState.isGameOver && (
              <View style={styles.gameOverOverlay}>
                <Text style={styles.gameOverEmoji}>{gameState.won ? '🏁' : '💥'}</Text>
                <Text style={[styles.gameOverText, { color: gameState.won ? '#4caf50' : '#e74c3c' }]}>
                  {gameState.won ? 'ESCAPED!' : 'CRASHED!'}
                </Text>
              </View>
            )}
          </View>
        )}
      </View>

      {/* Controls */}
      {gameStarted && !gameState.isGameOver && (
        <View style={styles.controls}>
          <TouchableOpacity
            style={styles.controlButton}
            onPress={() => changeLane('left')}
            activeOpacity={0.7}
          >
            <Ionicons name="chevron-back" size={40} color="#fff" />
            <Text style={styles.controlText}>LEFT</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.controlButton}
            onPress={() => changeLane('right')}
            activeOpacity={0.7}
          >
            <Ionicons name="chevron-forward" size={40} color="#fff" />
            <Text style={styles.controlText}>RIGHT</Text>
          </TouchableOpacity>
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
            {gameState.won ? (
              // WIN SCREEN - Show rewards
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>🏁</Text>
                  <Text style={styles.resultTitle}>ESCAPED!</Text>
                  <Text style={styles.resultSubtitle}>You reached the county line!</Text>
                </View>

                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Distance:</Text>
                    <Text style={styles.statValue}>{Math.floor(gameState.distance)}m</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Time:</Text>
                    <Text style={styles.statValue}>
                      {Math.floor((Date.now() - gameStartTimeRef.current) / 1000)}s
                    </Text>
                  </View>
                </View>

                <View style={styles.rewardsContainer}>
                  <Text style={styles.rewardsTitle}>🎁 REWARDS</Text>
                  
                  <Animated.View style={[styles.rewardRow, { 
                    opacity: rewardAnimValues.cash,
                    transform: [{ 
                      translateX: rewardAnimValues.cash.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-50, 0]
                      })
                    }]
                  }]}>
                    <View style={styles.rewardIcon}>
                      <Text style={styles.rewardIconText}>💰</Text>
                    </View>
                    <View style={styles.rewardDetails}>
                      <Text style={styles.rewardLabel}>Cash</Text>
                      <Text style={styles.rewardValue}>+${gameRewards?.totalCash || 0}</Text>
                      {gameRewards && gameRewards.distanceBonus > 0 && (
                        <Text style={styles.rewardBonus}>
                          (Base ${gameRewards.baseCash} + ${gameRewards.timeBonus} time + ${gameRewards.difficultyBonus} difficulty)
                        </Text>
                      )}
                    </View>
                  </Animated.View>

                  <Animated.View style={[styles.rewardRow, { 
                    opacity: rewardAnimValues.xp,
                    transform: [{ 
                      translateX: rewardAnimValues.xp.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-50, 0]
                      })
                    }]
                  }]}>
                    <View style={[styles.rewardIcon, { backgroundColor: '#2196f320' }]}>
                      <Text style={styles.rewardIconText}>⭐</Text>
                    </View>
                    <View style={styles.rewardDetails}>
                      <Text style={styles.rewardLabel}>Experience</Text>
                      <Text style={[styles.rewardValue, { color: '#2196f3' }]}>
                        +{gameRewards?.totalXP || 0} XP
                      </Text>
                    </View>
                  </Animated.View>

                  <Animated.View style={[styles.rewardRow, { 
                    opacity: rewardAnimValues.rep,
                    transform: [{ 
                      translateX: rewardAnimValues.rep.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-50, 0]
                      })
                    }]
                  }]}>
                    <View style={[styles.rewardIcon, { backgroundColor: '#9c27b020' }]}>
                      <Text style={styles.rewardIconText}>👑</Text>
                    </View>
                    <View style={styles.rewardDetails}>
                      <Text style={styles.rewardLabel}>Reputation</Text>
                      <Text style={[styles.rewardValue, { color: '#9c27b0' }]}>
                        +{gameRewards?.reputation || 0}
                      </Text>
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
              // LOSE SCREEN - No rewards
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>🚔</Text>
                  <Text style={[styles.resultTitle, { color: '#e74c3c' }]}>BUSTED!</Text>
                  <Text style={styles.resultSubtitle}>
                    {gameState.policeY >= POLICE_CATCH_Y - 10 
                      ? 'The police caught up with you!' 
                      : 'You crashed into an obstacle!'}
                  </Text>
                </View>

                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Distance Reached:</Text>
                    <Text style={styles.statValue}>{Math.floor(gameState.distance)}m</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Progress:</Text>
                    <Text style={styles.statValue}>
                      {Math.floor((gameState.distance / countyLineDistance) * 100)}%
                    </Text>
                  </View>
                </View>

                <View style={styles.noRewardsBox}>
                  <Ionicons name="close-circle" size={40} color="#e74c3c" />
                  <Text style={styles.noRewardsText}>No Rewards</Text>
                  <Text style={styles.noRewardsSubtext}>
                    Reach the county line to earn rewards!
                  </Text>
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
    padding: 16,
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
    color: '#f39c12',
    fontSize: 12,
    marginTop: 2,
  },
  progressContainer: {
    padding: 12,
    backgroundColor: '#111',
  },
  progressBar: {
    height: 12,
    backgroundColor: '#333',
    borderRadius: 6,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4caf50',
    borderRadius: 6,
  },
  progressLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  progressText: {
    color: '#888',
    fontSize: 10,
    fontWeight: 'bold',
  },
  distanceText: {
    color: '#4caf50',
    fontSize: 14,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 4,
  },
  policeWarning: {
    paddingHorizontal: 12,
    paddingBottom: 8,
  },
  policeText: {
    color: '#e74c3c',
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  policeBar: {
    height: 6,
    backgroundColor: '#333',
    borderRadius: 3,
    overflow: 'hidden',
  },
  policeFill: {
    height: '100%',
    backgroundColor: '#e74c3c',
    borderRadius: 3,
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
    fontSize: 64,
    marginBottom: 16,
  },
  startTitle: {
    color: '#fff',
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  startInstructions: {
    color: '#888',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  startButton: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 40,
    paddingVertical: 16,
    borderRadius: 12,
  },
  startButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  gameArea: {
    backgroundColor: '#2d2d2d',
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  road: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#3d3d3d',
  },
  laneDivider: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 4,
    backgroundColor: '#f39c12',
    opacity: 0.5,
  },
  obstacle: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  obstacleEmoji: {
    fontSize: 36,
  },
  policeCar: {
    position: 'absolute',
    width: CAR_WIDTH,
    height: CAR_HEIGHT,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playerCar: {
    position: 'absolute',
    width: CAR_WIDTH,
    height: CAR_HEIGHT,
    justifyContent: 'center',
    alignItems: 'center',
  },
  carEmoji: {
    fontSize: 48,
  },
  gameOverOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  gameOverEmoji: {
    fontSize: 64,
    marginBottom: 16,
  },
  gameOverText: {
    fontSize: 36,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  gameOverDistance: {
    color: '#888',
    fontSize: 16,
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#4caf50',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 10,
    marginBottom: 12,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  exitButton: {
    backgroundColor: '#333',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 10,
  },
  exitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 16,
    backgroundColor: '#111',
  },
  controlButton: {
    width: 120,
    height: 80,
    backgroundColor: '#333',
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#444',
  },
  controlText: {
    color: '#888',
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 4,
  },
  // Results Modal Styles
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
    fontSize: 64,
    marginBottom: 8,
  },
  resultTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#4caf50',
    marginBottom: 4,
  },
  resultSubtitle: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
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
  statLabel: {
    fontSize: 14,
    color: '#888',
  },
  statValue: {
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
    color: '#4caf50',
    textAlign: 'center',
    marginBottom: 16,
  },
  rewardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  rewardIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#4caf5020',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  rewardIconText: {
    fontSize: 24,
  },
  rewardDetails: {
    flex: 1,
  },
  rewardLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 2,
  },
  rewardValue: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#4caf50',
  },
  rewardBonus: {
    fontSize: 10,
    color: '#666',
    marginTop: 2,
  },
  collectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4caf50',
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
