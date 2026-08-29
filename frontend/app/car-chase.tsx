import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
  Animated,
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
    if (!gameId) return;
    
    if (isStandalone) {
      // Standalone mode - just show result
      if (gameState.won) {
        showGameToast({
          type: 'success',
          title: 'ESCAPED!',
          message: `You reached the county line! Distance: ${Math.floor(gameState.distance)}m`,
          duration: 3000,
        });
      } else {
        showGameToast({
          type: 'error',
          title: 'BUSTED!',
          message: `Caught at ${Math.floor(gameState.distance)}m`,
          duration: 3000,
        });
      }
      return;
    }
    
    try {
      const result = await completeCarChase(gameId, gameState.won, Math.floor(gameState.distance));
      
      if (result.won) {
        showGameToast({
          type: 'success',
          title: 'ESCAPED!',
          message: `+$${result.rewards.cash} | +${result.rewards.xp} XP`,
          duration: 3000,
        });
      } else {
        showGameToast({
          type: 'error',
          title: 'BUSTED!',
          message: result.message,
          duration: 3000,
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

            {/* Game Over Overlay */}
            {gameState.isGameOver && (
              <View style={styles.gameOverOverlay}>
                <Text style={styles.gameOverEmoji}>{gameState.won ? '🏁' : '🚔'}</Text>
                <Text style={[styles.gameOverText, { color: gameState.won ? '#4caf50' : '#e74c3c' }]}>
                  {gameState.won ? 'ESCAPED!' : 'BUSTED!'}
                </Text>
                <Text style={styles.gameOverDistance}>
                  Distance: {Math.floor(gameState.distance)}m
                </Text>
                <TouchableOpacity style={styles.retryButton} onPress={startGame}>
                  <Text style={styles.retryButtonText}>TRY AGAIN</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.exitButton} onPress={handleGoBack}>
                  <Text style={styles.exitButtonText}>EXIT</Text>
                </TouchableOpacity>
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
});
