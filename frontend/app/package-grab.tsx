import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { startPackageGrab, completePackageGrab } from '../services/api';
import { showGameToast } from '../components/GameToast';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Game constants
const GAME_WIDTH = Math.min(SCREEN_WIDTH - 40, 360);
const GAME_HEIGHT = SCREEN_HEIGHT - 220;
const LANE_COUNT = 3;
const LANE_WIDTH = GAME_WIDTH / LANE_COUNT;
const TRUCK_WIDTH = 55;
const TRUCK_HEIGHT = 85;
const ITEM_SIZE = 45;

// 24-bit pixel art colors
const COLORS = {
  road: '#2c2c2c',
  roadLine: '#f1c40f',
  grass: '#27ae60',
  truck: '#e67e22',
  truckAccent: '#d35400',
  truckCargo: '#8b4513',
  box: '#daa520',
  boxHighlight: '#ffd700',
  obstacle: '#e74c3c',
  barrier: '#ff6b35',
};

// Level configuration - 20 levels based on distance
interface LevelConfig {
  level: number;
  baseSpeed: number;
  maxSpeed: number;
  finishDistance: number;
  obstacleInterval: number;
  boxInterval: number;
  obstacleChance: number; // Chance per spawn to be obstacle vs box
}

const getLevelConfig = (level: number): LevelConfig => {
  const clampedLevel = Math.min(20, Math.max(1, level));
  
  // Distance scales with level - Level 1: 2000, Level 20: 9000
  const baseDistance = 2000;
  const distancePerLevel = 370;
  const finishDistance = baseDistance + (clampedLevel - 1) * distancePerLevel;
  
  // Speed starts same for all, ramps during gameplay
  const baseSpeed = 2.8;
  const maxSpeed = 7.0;
  
  // Spawn intervals - more frequent at higher levels
  const obstacleInterval = Math.max(200, 350 - clampedLevel * 7);
  const boxInterval = Math.max(150, 280 - clampedLevel * 6);
  
  // Obstacle chance increases with level (30% at L1, 55% at L20)
  const obstacleChance = 0.30 + (clampedLevel - 1) * 0.013;
  
  return {
    level: clampedLevel,
    baseSpeed,
    maxSpeed,
    finishDistance,
    obstacleInterval,
    boxInterval,
    obstacleChance,
  };
};

// Reward calculation based on boxes collected
interface GameRewards {
  boxBonus: number;
  levelBonus: number;
  totalCash: number;
  totalXP: number;
  reputation: number;
}

const calculateRewards = (
  boxesCollected: number,
  level: number,
  won: boolean
): GameRewards => {
  if (!won) {
    return {
      boxBonus: 0,
      levelBonus: 0,
      totalCash: 0,
      totalXP: 0,
      reputation: 0,
    };
  }
  
  // Base reward for finishing (small)
  const baseFinishReward = 20;
  
  // Box bonus - each box is worth more at higher levels
  const perBoxValue = 8 + level * 2;
  const boxBonus = boxesCollected * perBoxValue;
  
  // Level multiplier
  const levelMultiplier = 1 + (level - 1) * 0.12;
  const levelBonus = Math.floor((baseFinishReward + boxBonus) * (levelMultiplier - 1));
  
  const totalCash = baseFinishReward + boxBonus + levelBonus;
  
  // XP based on boxes collected
  const baseXP = 15 + boxesCollected * 3;
  const totalXP = Math.floor(baseXP * levelMultiplier);
  
  // Reputation - minimum 1, more with more boxes
  const reputation = Math.max(1, Math.floor(boxesCollected / 5) + Math.floor(level / 4));
  
  return {
    boxBonus,
    levelBonus,
    totalCash,
    totalXP,
    reputation,
  };
};

// Obstacle types
const OBSTACLES = [
  { type: 'barrier', emoji: '🚧', color: COLORS.barrier },
  { type: 'cone', emoji: '🔶', color: '#ff6b35' },
  { type: 'car', emoji: '🚗', color: '#e74c3c' },
  { type: 'truck', emoji: '🚙', color: '#3498db' },
];

interface GameItem {
  id: number;
  lane: number;
  y: number;
  type: 'box' | 'obstacle';
  emoji: string;
  color: string;
  collected?: boolean;
}

interface GameState {
  playerLane: number;
  items: GameItem[];
  distance: number;
  speed: number;
  boxesCollected: number;
  isGameOver: boolean;
  won: boolean;
}

export default function PackageGrabGame() {
  const params = useLocalSearchParams();
  const grabId = params.grabId as string;
  const grabName = params.grabName as string || 'Package Grab';
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
  const [gameState, setGameState] = useState<GameState>({
    playerLane: 1,
    items: [],
    distance: 0,
    speed: levelConfig.baseSpeed,
    boxesCollected: 0,
    isGameOver: false,
    won: false,
  });
  
  const gameLoopRef = useRef<number | null>(null);
  const itemIdRef = useRef(0);
  const lastObstacleSpawnRef = useRef(0);
  const lastBoxSpawnRef = useRef(0);
  const playerLaneAnim = useRef(new Animated.Value(1)).current;
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
      setGameId('standalone');
      setLoading(false);
      return;
    }
    
    if (!playerId || !grabId) {
      setLoading(false);
      return;
    }
    
    try {
      const result = await startPackageGrab(grabId, playerId);
      setGameId(result.game_id);
    } catch (error: any) {
      showGameToast({
        type: 'error',
        title: 'Error',
        message: error?.response?.data?.detail || 'Failed to start package grab',
        duration: 2000,
      });
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const startGame = () => {
    setGameStarted(true);
    setShowResultsModal(false);
    setGameRewards(null);
    setGameState({
      playerLane: 1,
      items: [],
      distance: 0,
      speed: levelConfig.baseSpeed,
      boxesCollected: 0,
      isGameOver: false,
      won: false,
    });
    lastObstacleSpawnRef.current = 0;
    lastBoxSpawnRef.current = 0;
    itemIdRef.current = 0;
    playerLaneAnim.setValue(1);
    rewardAnimValues.cash.setValue(0);
    rewardAnimValues.xp.setValue(0);
    rewardAnimValues.rep.setValue(0);
    runGameLoop();
  };

  // Calculate current speed - ramps up as player approaches finish
  const calculateCurrentSpeed = (distance: number): number => {
    const progress = distance / levelConfig.finishDistance;
    const speedProgress = progress * progress; // Quadratic curve
    const speedRange = levelConfig.maxSpeed - levelConfig.baseSpeed;
    return levelConfig.baseSpeed + speedRange * speedProgress;
  };

  const runGameLoop = () => {
    const loop = () => {
      setGameState(prev => {
        if (prev.isGameOver) return prev;

        const currentSpeed = calculateCurrentSpeed(prev.distance);
        const newDistance = prev.distance + currentSpeed;
        
        let newItems = [...prev.items];
        let newBoxesCollected = prev.boxesCollected;
        
        // Spawn obstacles
        if (newDistance - lastObstacleSpawnRef.current > levelConfig.obstacleInterval) {
          if (Math.random() < levelConfig.obstacleChance) {
            lastObstacleSpawnRef.current = newDistance;
            const lane = Math.floor(Math.random() * LANE_COUNT);
            const obsType = OBSTACLES[Math.floor(Math.random() * OBSTACLES.length)];
            newItems.push({
              id: itemIdRef.current++,
              lane,
              y: -ITEM_SIZE,
              type: 'obstacle',
              emoji: obsType.emoji,
              color: obsType.color,
            });
          }
        }
        
        // Spawn boxes
        if (newDistance - lastBoxSpawnRef.current > levelConfig.boxInterval) {
          lastBoxSpawnRef.current = newDistance;
          const lane = Math.floor(Math.random() * LANE_COUNT);
          // Don't spawn box on top of obstacle in same lane
          const hasObstacleInLane = newItems.some(
            item => item.type === 'obstacle' && item.lane === lane && item.y < 100
          );
          if (!hasObstacleInLane) {
            newItems.push({
              id: itemIdRef.current++,
              lane,
              y: -ITEM_SIZE,
              type: 'box',
              emoji: '📦',
              color: COLORS.box,
            });
          }
        }
        
        // Move items
        newItems = newItems
          .map(item => ({ ...item, y: item.y + currentSpeed }))
          .filter(item => item.y < GAME_HEIGHT + ITEM_SIZE && !item.collected);
        
        // Check collisions
        const playerX = prev.playerLane * LANE_WIDTH + LANE_WIDTH / 2 - TRUCK_WIDTH / 2;
        const playerY = GAME_HEIGHT - TRUCK_HEIGHT - 20;
        
        for (const item of newItems) {
          if (item.collected) continue;
          
          const itemX = item.lane * LANE_WIDTH + LANE_WIDTH / 2 - ITEM_SIZE / 2;
          const itemY = item.y;
          
          // Collision check with some forgiveness
          const hitboxPadding = 8;
          const collides = 
            playerX + hitboxPadding < itemX + ITEM_SIZE - hitboxPadding &&
            playerX + TRUCK_WIDTH - hitboxPadding > itemX + hitboxPadding &&
            playerY + hitboxPadding < itemY + ITEM_SIZE - hitboxPadding &&
            playerY + TRUCK_HEIGHT - hitboxPadding > itemY + hitboxPadding;
          
          if (collides) {
            if (item.type === 'obstacle') {
              // Hit obstacle - game over!
              return {
                ...prev,
                items: newItems,
                distance: newDistance,
                speed: currentSpeed,
                isGameOver: true,
                won: false,
              };
            } else if (item.type === 'box') {
              // Collect box!
              item.collected = true;
              newBoxesCollected++;
            }
          }
        }
        
        // Check win condition
        if (newDistance >= levelConfig.finishDistance) {
          return {
            ...prev,
            items: newItems,
            distance: newDistance,
            speed: currentSpeed,
            boxesCollected: newBoxesCollected,
            isGameOver: true,
            won: true,
          };
        }
        
        return {
          ...prev,
          items: newItems,
          distance: newDistance,
          speed: currentSpeed,
          boxesCollected: newBoxesCollected,
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
    const rewards = calculateRewards(
      gameState.boxesCollected,
      difficulty,
      gameState.won
    );
    
    setGameRewards(rewards);
    setShowResultsModal(true);
    
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
    
    try {
      const result = await completePackageGrab(
        gameId,
        gameState.won,
        gameState.boxesCollected,
        Math.floor(gameState.distance),
        isStandalone
      );
      
      if (result.won) {
        const rewardMessage = isStandalone
          ? `+$${result.rewards?.cash || 0} | +${result.rewards?.xp || 0} XP (Practice Mode: 50% rewards)`
          : `+$${result.rewards?.cash || rewards.totalCash} | +${result.rewards?.xp || rewards.totalXP} XP`;
        showGameToast({
          type: 'success',
          title: 'DELIVERY COMPLETE!',
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
      console.error('Failed to complete package grab:', error);
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

  const progressPercent = Math.min(100, (gameState.distance / levelConfig.finishDistance) * 100);

  // Render road markings
  const renderRoadMarkings = () => {
    const markings = [];
    const markingSpacing = 80;
    const numMarkings = Math.ceil(GAME_HEIGHT / markingSpacing) + 2;
    const offset = (gameState.distance * 2) % markingSpacing;
    
    for (let i = 0; i < numMarkings; i++) {
      const y = i * markingSpacing - offset;
      markings.push(
        <View
          key={`marking-${i}`}
          style={[
            styles.roadMarking,
            {
              top: y,
              left: LANE_WIDTH - 3,
            },
          ]}
        />,
        <View
          key={`marking2-${i}`}
          style={[
            styles.roadMarking,
            {
              top: y,
              left: LANE_WIDTH * 2 - 3,
            },
          ]}
        />
      );
    }
    return markings;
  };

  // Render truck (top-down cargo truck)
  const renderTruck = () => {
    const truckX = playerLaneAnim.interpolate({
      inputRange: [0, 1, 2],
      outputRange: [
        LANE_WIDTH / 2 - TRUCK_WIDTH / 2,
        LANE_WIDTH * 1.5 - TRUCK_WIDTH / 2,
        LANE_WIDTH * 2.5 - TRUCK_WIDTH / 2,
      ],
    });
    
    return (
      <Animated.View
        style={[
          styles.truck,
          {
            left: truckX,
            bottom: 20,
          },
        ]}
      >
        {/* Truck cab (front) */}
        <View style={styles.truckCab}>
          <View style={styles.truckWindshield} />
        </View>
        {/* Cargo area */}
        <View style={styles.truckCargo}>
          <Text style={styles.truckCargoText}>📦</Text>
        </View>
        {/* Wheels */}
        <View style={[styles.truckWheel, { top: 5, left: -4 }]} />
        <View style={[styles.truckWheel, { top: 5, right: -4 }]} />
        <View style={[styles.truckWheel, { bottom: 10, left: -4 }]} />
        <View style={[styles.truckWheel, { bottom: 10, right: -4 }]} />
      </Animated.View>
    );
  };

  // Render items (boxes and obstacles)
  const renderItems = () => {
    return gameState.items.filter(item => !item.collected).map(item => {
      const itemX = item.lane * LANE_WIDTH + LANE_WIDTH / 2 - ITEM_SIZE / 2;
      
      if (item.type === 'box') {
        return (
          <View
            key={item.id}
            style={[
              styles.boxItem,
              {
                left: itemX,
                top: item.y,
              },
            ]}
          >
            <Text style={styles.boxEmoji}>📦</Text>
            <View style={styles.boxGlow} />
          </View>
        );
      } else {
        return (
          <View
            key={item.id}
            style={[
              styles.obstacleItem,
              {
                left: itemX,
                top: item.y,
                backgroundColor: item.color,
              },
            ]}
          >
            <Text style={styles.obstacleEmoji}>{item.emoji}</Text>
          </View>
        );
      }
    });
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading Delivery...</Text>
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
          <Text style={styles.headerTitle}>{grabName}</Text>
          <Text style={styles.headerSubtitle}>Level {difficulty} {'⭐'.repeat(Math.min(5, Math.ceil(difficulty / 4)))}</Text>
        </View>
        <View style={styles.boxCounter}>
          <Text style={styles.boxCounterEmoji}>📦</Text>
          <Text style={styles.boxCounterText}>{gameState.boxesCollected}</Text>
        </View>
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progressPercent}%` }]} />
        </View>
        <View style={styles.progressLabels}>
          <Text style={styles.progressText}>🚚 START</Text>
          <Text style={styles.progressText}>FINISH 🏁</Text>
        </View>
        <Text style={styles.distanceText}>{Math.floor(gameState.distance)}m / {levelConfig.finishDistance}m</Text>
      </View>

      {/* Game Area */}
      <View style={styles.gameContainer}>
        {!gameStarted ? (
          <View style={styles.startScreen}>
            <Text style={styles.startEmoji}>📦🚚</Text>
            <Text style={styles.startTitle}>PACKAGE GRAB</Text>
            
            <View style={styles.instructionsCard}>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>⬅️➡️</Text>
                <Text style={styles.instructionText}>Move left/right to collect boxes</Text>
              </View>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>📦</Text>
                <Text style={styles.instructionText}>Collect wooden boxes for rewards</Text>
              </View>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>🚧</Text>
                <Text style={styles.instructionText}>Avoid obstacles or you will crash!</Text>
              </View>
              <View style={styles.instructionRow}>
                <Text style={styles.instructionIcon}>🏁</Text>
                <Text style={styles.instructionText}>Reach the finish to complete delivery</Text>
              </View>
            </View>
            
            <View style={styles.rewardHint}>
              <Text style={styles.rewardHintText}>💰 More boxes = More rewards!</Text>
            </View>
            
            <TouchableOpacity style={styles.startButton} onPress={startGame} activeOpacity={0.8}>
              <Ionicons name="car" size={24} color="#fff" />
              <Text style={styles.startButtonText}>START DELIVERY</Text>
              <Ionicons name="arrow-forward" size={22} color="#fff" />
            </TouchableOpacity>
          </View>
        ) : (
          <View style={[styles.gameArea, { width: GAME_WIDTH, height: GAME_HEIGHT }]}>
            {/* Road background */}
            <View style={styles.road}>
              {/* Grass sides */}
              <View style={[styles.grass, { left: -20 }]} />
              <View style={[styles.grass, { right: -20 }]} />
              
              {/* Road markings */}
              {renderRoadMarkings()}
              
              {/* Lane dividers */}
              <View style={[styles.laneDivider, { left: LANE_WIDTH }]} />
              <View style={[styles.laneDivider, { left: LANE_WIDTH * 2 }]} />
            </View>
            
            {/* Items */}
            {renderItems()}
            
            {/* Truck */}
            {renderTruck()}
            
            {/* Game Over Overlay */}
            {gameState.isGameOver && (
              <View style={styles.gameOverOverlay}>
                <Text style={styles.gameOverEmoji}>
                  {gameState.won ? '🎉' : '💥'}
                </Text>
                <Text style={[styles.gameOverText, { color: gameState.won ? '#27ae60' : '#e74c3c' }]}>
                  {gameState.won ? 'DELIVERED!' : 'CRASHED!'}
                </Text>
                {gameState.won && (
                  <Text style={styles.gameOverBoxes}>📦 x {gameState.boxesCollected}</Text>
                )}
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
            <Ionicons name="arrow-back" size={40} color="#fff" />
            <Text style={styles.controlText}>LEFT</Text>
          </TouchableOpacity>
          <View style={styles.speedIndicator}>
            <Text style={styles.speedText}>
              {Math.floor(gameState.speed * 10)} km/h
            </Text>
          </View>
          <TouchableOpacity
            style={styles.controlButton}
            onPress={() => changeLane('right')}
            activeOpacity={0.7}
          >
            <Ionicons name="arrow-forward" size={40} color="#fff" />
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
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>🚚✅</Text>
                  <Text style={styles.resultTitle}>DELIVERY COMPLETE!</Text>
                  <Text style={styles.resultSubtitle}>You made it to the finish line!</Text>
                </View>
                
                <View style={styles.boxesCollectedCard}>
                  <Text style={styles.boxesCollectedLabel}>Boxes Collected</Text>
                  <View style={styles.boxesCollectedValue}>
                    <Text style={styles.boxesCollectedEmoji}>📦</Text>
                    <Text style={styles.boxesCollectedNumber}>{gameState.boxesCollected}</Text>
                  </View>
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
                  <Text style={styles.resultEmoji}>💥🚚</Text>
                  <Text style={[styles.resultTitle, { color: '#e74c3c' }]}>CRASHED!</Text>
                  <Text style={styles.resultSubtitle}>You hit an obstacle!</Text>
                </View>
                
                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Distance:</Text>
                    <Text style={styles.statValue}>{Math.floor(gameState.distance)}m</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Boxes Lost:</Text>
                    <Text style={[styles.statValue, { color: '#e74c3c' }]}>📦 x {gameState.boxesCollected}</Text>
                  </View>
                </View>
                
                <View style={styles.noRewardsBox}>
                  <Ionicons name="close-circle" size={40} color="#e74c3c" />
                  <Text style={styles.noRewardsText}>No Rewards</Text>
                  <Text style={styles.noRewardsSubtext}>Complete the delivery to earn rewards!</Text>
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
    color: '#e67e22',
    fontSize: 12,
    marginTop: 2,
  },
  boxCounter: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(218, 165, 32, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 2,
    borderColor: COLORS.box,
  },
  boxCounterEmoji: {
    fontSize: 18,
    marginRight: 6,
  },
  boxCounterText: {
    color: COLORS.boxHighlight,
    fontSize: 18,
    fontWeight: '900',
  },
  progressContainer: {
    padding: 10,
    backgroundColor: '#111',
  },
  progressBar: {
    height: 10,
    backgroundColor: '#333',
    borderRadius: 5,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#e67e22',
    borderRadius: 5,
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
    color: '#e67e22',
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 2,
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
  rewardHint: {
    backgroundColor: 'rgba(218, 165, 32, 0.15)',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(218, 165, 32, 0.3)',
  },
  rewardHintText: {
    color: COLORS.boxHighlight,
    fontSize: 14,
    fontWeight: '700',
  },
  startButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    backgroundColor: '#e67e22',
    paddingHorizontal: 32,
    paddingVertical: 18,
    borderRadius: 16,
    borderWidth: 3,
    borderColor: '#f39c12',
    shadowColor: '#e67e22',
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
    backgroundColor: COLORS.road,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  road: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: COLORS.road,
  },
  grass: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 20,
    backgroundColor: COLORS.grass,
  },
  roadMarking: {
    position: 'absolute',
    width: 6,
    height: 40,
    backgroundColor: COLORS.roadLine,
    borderRadius: 2,
  },
  laneDivider: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  truck: {
    position: 'absolute',
    width: TRUCK_WIDTH,
    height: TRUCK_HEIGHT,
    zIndex: 10,
  },
  truckCab: {
    width: TRUCK_WIDTH - 10,
    height: 30,
    backgroundColor: COLORS.truck,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    marginLeft: 5,
    borderWidth: 2,
    borderColor: COLORS.truckAccent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  truckWindshield: {
    width: 30,
    height: 12,
    backgroundColor: '#87CEEB',
    borderRadius: 3,
    marginTop: 4,
  },
  truckCargo: {
    width: TRUCK_WIDTH - 6,
    height: 50,
    backgroundColor: COLORS.truckCargo,
    marginLeft: 3,
    borderWidth: 2,
    borderColor: '#6b3510',
    borderBottomLeftRadius: 4,
    borderBottomRightRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  truckCargoText: {
    fontSize: 24,
  },
  truckWheel: {
    position: 'absolute',
    width: 12,
    height: 18,
    backgroundColor: '#1a1a1a',
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#333',
  },
  boxItem: {
    position: 'absolute',
    width: ITEM_SIZE,
    height: ITEM_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 5,
  },
  boxEmoji: {
    fontSize: 36,
  },
  boxGlow: {
    position: 'absolute',
    width: ITEM_SIZE + 10,
    height: ITEM_SIZE + 10,
    borderRadius: (ITEM_SIZE + 10) / 2,
    backgroundColor: 'rgba(255, 215, 0, 0.3)',
    zIndex: -1,
  },
  obstacleItem: {
    position: 'absolute',
    width: ITEM_SIZE,
    height: ITEM_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#fff',
    zIndex: 5,
  },
  obstacleEmoji: {
    fontSize: 28,
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
  gameOverBoxes: {
    fontSize: 24,
    color: COLORS.boxHighlight,
    marginTop: 12,
    fontWeight: '700',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#111',
  },
  controlButton: {
    width: 100,
    height: 70,
    backgroundColor: '#333',
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#444',
  },
  controlText: {
    color: '#888',
    fontSize: 11,
    fontWeight: 'bold',
    marginTop: 2,
  },
  speedIndicator: {
    backgroundColor: 'rgba(230, 126, 34, 0.2)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e67e22',
  },
  speedText: {
    color: '#e67e22',
    fontSize: 14,
    fontWeight: 'bold',
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
  boxesCollectedCard: {
    backgroundColor: 'rgba(218, 165, 32, 0.15)',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    alignItems: 'center',
    width: '100%',
    borderWidth: 1,
    borderColor: 'rgba(218, 165, 32, 0.3)',
  },
  boxesCollectedLabel: {
    color: '#888',
    fontSize: 12,
    marginBottom: 8,
  },
  boxesCollectedValue: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  boxesCollectedEmoji: {
    fontSize: 32,
    marginRight: 10,
  },
  boxesCollectedNumber: {
    fontSize: 42,
    fontWeight: '900',
    color: COLORS.boxHighlight,
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
