import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Modal,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { startRunaway, completeRunaway } from '../services/api';
import { showGameToast } from '../components/GameToast';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';
import {
  useRunawayGame,
  GAME_WIDTH,
  GAME_HEIGHT,
  GROUND_Y,
  PLAYER_WIDTH,
  PLAYER_HEIGHT,
  OBSTACLE_WIDTH,
  OBSTACLE_HEIGHT,
  getRunawayRewards,
} from '../hooks/useRunawayGame';

const COLORS = {
  sky: '#1a1a2e',
  skyGradient: '#16213e',
  ground: '#2d3436',
  groundLine: '#636e72',
  building1: '#2d3436',
  building2: '#353b48',
  building3: '#4a4a5a',
  player: '#00b894',
  playerOutline: '#00cec9',
  obstacleLow: '#e17055',
  obstacleHigh: '#fdcb6e',
  hideout: '#6c5ce7',
  progress: '#00b894',
  danger: '#d63031',
};

// Obstacle visuals
const OBSTACLE_VISUALS = {
  low: [
    { name: 'Trash Can', color: '#636e72', accent: '#b2bec3' },
    { name: 'Barrier', color: '#e17055', accent: '#fab1a0' },
    { name: 'Hydrant', color: '#d63031', accent: '#ff7675' },
  ],
  high: [
    { name: 'Sign', color: '#fdcb6e', accent: '#ffeaa7' },
    { name: 'Awning', color: '#74b9ff', accent: '#a29bfe' },
    { name: 'Branch', color: '#55a3a3', accent: '#81ecec' },
  ],
};

// Reward calculation - use the hook's function
interface GameRewards {
  cash: number;
  xp: number;
  reputation: number;
}

const calculateRewards = (difficulty: number, won: boolean): GameRewards => {
  if (!won) {
    return { cash: 0, xp: 0, reputation: 0 };
  }
  
  // Use centralized reward calculation from hook
  return getRunawayRewards(difficulty);
};

export default function RunawaySimulator() {
  const params = useLocalSearchParams();
  const runawayId = params.runawayId as string;
  const runawayName = params.runawayName as string || 'Runaway';
  const difficulty = parseInt(params.difficulty as string) || 1;
  const isStandalone = params.standalone === 'true';
  
  const { playerId, refreshPlayer } = useGameStore();
  const { invalidateCooldowns, invalidatePlayer } = useInvalidateMapQueries();
  
  const [gameId, setGameId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [gameStarted, setGameStarted] = useState(false);
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [gameRewards, setGameRewards] = useState<GameRewards | null>(null);
  
  const { gameState, levelConfig, startGame, jump, duck, stopDucking, progressPercent } = useRunawayGame(difficulty);
  
  const rewardAnimValues = useRef({
    cash: new Animated.Value(0),
    xp: new Animated.Value(0),
    rep: new Animated.Value(0),
  }).current;
  
  // Building animation for parallax - track scroll offset
  const scrollOffsetRef = useRef(0);
  
  useEffect(() => {
    initializeGame();
  }, []);
  
  const initializeGame = async () => {
    if (isStandalone) {
      setGameId('standalone');
      setLoading(false);
      return;
    }
    
    if (!playerId || !runawayId) {
      setLoading(false);
      return;
    }
    
    try {
      const result = await startRunaway(runawayId, playerId);
      setGameId(result.game_id);
    } catch (error: any) {
      showGameToast({
        type: 'error',
        title: 'Error',
        message: error?.response?.data?.detail || 'Failed to start runaway',
        duration: 2000,
      });
      router.back();
    } finally {
      setLoading(false);
    }
  };
  
  const handleStartGame = () => {
    setGameStarted(true);
    setShowResultsModal(false);
    setGameRewards(null);
    rewardAnimValues.cash.setValue(0);
    rewardAnimValues.xp.setValue(0);
    rewardAnimValues.rep.setValue(0);
    startGame();
  };
  
  // Handle game over
  useEffect(() => {
    if (gameState.isGameOver && gameStarted) {
      handleGameOver();
    }
  }, [gameState.isGameOver]);
  
  const handleGameOver = async () => {
    const rewards = calculateRewards(difficulty, gameState.won);
    setGameRewards(rewards);
    setShowResultsModal(true);
    
    // Animate rewards if won
    if (gameState.won) {
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
    
    if (!gameId || isStandalone) return;
    
    try {
      const result = await completeRunaway(
        gameId,
        gameState.won,
        Math.floor(gameState.distance)
      );
      
      if (result.won) {
        showGameToast({
          type: 'success',
          title: 'ESCAPED!',
          message: `+$${result.rewards?.cash || rewards.cash} | +${result.rewards?.xp || rewards.xp} XP`,
          duration: 2000,
        });
        
        if (refreshPlayer) refreshPlayer();
      }
      
      if (playerId) {
        invalidateCooldowns(playerId);
        invalidatePlayer(playerId);
      }
    } catch (error) {
      console.error('Failed to complete runaway:', error);
    }
  };
  
  const handleGoBack = () => {
    router.back();
  };
  
  // Render building silhouettes (parallax background)
  const renderBuildings = () => {
    const buildings = [];
    const buildingWidth = 60;
    const numBuildings = Math.ceil(GAME_WIDTH / buildingWidth) + 2;
    const offset = (gameState.scrollOffset * 0.3) % buildingWidth;
    
    for (let i = 0; i < numBuildings; i++) {
      const height = 40 + (i % 4) * 25;
      const x = i * buildingWidth - offset;
      const color = i % 3 === 0 ? COLORS.building1 : i % 3 === 1 ? COLORS.building2 : COLORS.building3;
      
      buildings.push(
        <View
          key={`building-${i}`}
          style={[
            styles.building,
            {
              left: x,
              height,
              width: buildingWidth - 4,
              backgroundColor: color,
              bottom: GAME_HEIGHT - GROUND_Y,
            },
          ]}
        >
          {/* Windows */}
          {Array.from({ length: Math.floor(height / 20) }).map((_, wi) => (
            <View key={wi} style={styles.windowRow}>
              <View style={[styles.window, { opacity: (i + wi) % 3 === 0 ? 1 : 0.3 }]} />
              <View style={[styles.window, { opacity: (i + wi) % 2 === 0 ? 1 : 0.3 }]} />
            </View>
          ))}
        </View>
      );
    }
    
    return buildings;
  };
  
  // Render ground details
  const renderGround = () => {
    const lines = [];
    const lineSpacing = 80;
    const numLines = Math.ceil(GAME_WIDTH / lineSpacing) + 2;
    const offset = (gameState.scrollOffset * 1) % lineSpacing;
    
    for (let i = 0; i < numLines; i++) {
      const x = i * lineSpacing - offset;
      lines.push(
        <View
          key={`line-${i}`}
          style={[
            styles.groundLine,
            { left: x },
          ]}
        />
      );
    }
    
    return lines;
  };
  
  // Render player character
  const renderPlayer = () => {
    const isDucking = gameState.playerState === 'ducking';
    const isJumping = gameState.playerState === 'jumping';
    
    const playerHeight = isDucking ? PLAYER_HEIGHT - 28 : PLAYER_HEIGHT;
    const playerTop = isDucking ? gameState.playerY + 28 : gameState.playerY;
    
    return (
      <View
        style={[
          styles.player,
          {
            left: 50,
            top: playerTop,
            width: PLAYER_WIDTH,
            height: playerHeight,
          },
        ]}
      >
        {/* Player body - geometric pixel art style */}
        <View style={styles.playerBody}>
          {/* Head */}
          {!isDucking && (
            <View style={styles.playerHead}>
              <View style={styles.playerEye} />
            </View>
          )}
          {/* Body */}
          <View style={[styles.playerTorso, isDucking && styles.playerTorsoDucking]} />
          {/* Legs */}
          <View style={styles.playerLegs}>
            <View style={[styles.playerLeg, isJumping && styles.playerLegJumping]} />
            <View style={[styles.playerLeg, styles.playerLegBack, isJumping && styles.playerLegJumping]} />
          </View>
        </View>
      </View>
    );
  };
  
  // Render obstacles
  const renderObstacles = () => {
    return gameState.obstacles.map((obs, idx) => {
      const isLow = obs.type === 'low';
      const visuals = isLow ? OBSTACLE_VISUALS.low : OBSTACLE_VISUALS.high;
      const visual = visuals[obs.id % visuals.length];
      
      const obsY = isLow ? GROUND_Y : GROUND_Y - 30;
      
      return (
        <View
          key={obs.id}
          style={[
            styles.obstacle,
            {
              left: obs.x,
              top: obsY,
              width: OBSTACLE_WIDTH,
              height: OBSTACLE_HEIGHT,
            },
          ]}
        >
          <View style={[styles.obstacleInner, { backgroundColor: visual.color }]}>
            <View style={[styles.obstacleAccent, { backgroundColor: visual.accent }]} />
            {isLow ? (
              <Text style={styles.obstacleIcon}>🗑️</Text>
            ) : (
              <Text style={styles.obstacleIcon}>⚠️</Text>
            )}
          </View>
        </View>
      );
    });
  };
  
  // Render hideout indicator
  const renderHideout = () => {
    const hideoutProgress = progressPercent / 100;
    if (hideoutProgress < 0.7) return null; // Only show when close
    
    const hideoutX = GAME_WIDTH - 60 + (1 - hideoutProgress) * 200;
    
    return (
      <View
        style={[
          styles.hideout,
          { left: Math.max(GAME_WIDTH - 80, hideoutX) },
        ]}
      >
        <View style={styles.hideoutDoor} />
        <Text style={styles.hideoutIcon}>🏠</Text>
      </View>
    );
  };
  
  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Getting Ready...</Text>
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
          <Text style={styles.headerTitle}>{runawayName}</Text>
          <Text style={styles.headerSubtitle}>Level {difficulty} {'⭐'.repeat(Math.min(5, Math.ceil(difficulty / 4)))}</Text>
        </View>
      </View>
      
      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progressPercent}%` }]} />
          <View style={styles.progressHideout}>
            <Text style={styles.progressHideoutIcon}>🏠</Text>
          </View>
        </View>
        <View style={styles.progressLabels}>
          <Text style={styles.progressText}>🏃 START</Text>
          <Text style={styles.progressText}>HIDEOUT 🏠</Text>
        </View>
        <Text style={styles.distanceText}>
          {Math.floor(gameState.distance)}m / {levelConfig.hideoutDistance}m
        </Text>
      </View>
      
      {/* Game Area */}
      <View style={styles.gameContainer}>
        {!gameStarted ? (
          <View style={styles.startScreen}>
            <Text style={styles.startEmoji}>🏃💨</Text>
            <Text style={styles.startTitle}>RUNAWAY</Text>
            <Text style={styles.startInstructions}>
              Tap ⬆️ to JUMP over low obstacles{"\n"}
              Hold ⬇️ to DUCK under high obstacles{"\n"}
              Reach the hideout to escape!
            </Text>
            <View style={styles.obstacleHint}>
              <View style={styles.hintRow}>
                <Text style={styles.hintIcon}>🗑️</Text>
                <Text style={styles.hintText}>Low → JUMP</Text>
              </View>
              <View style={styles.hintRow}>
                <Text style={styles.hintIcon}>⚠️</Text>
                <Text style={styles.hintText}>High → DUCK</Text>
              </View>
            </View>
            <TouchableOpacity style={styles.startButton} onPress={handleStartGame}>
              <Text style={styles.startButtonText}>START RUNNING</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={[styles.gameArea, { width: GAME_WIDTH, height: GAME_HEIGHT }]}>
            {/* Sky */}
            <View style={styles.sky} />
            
            {/* Buildings (parallax) */}
            {renderBuildings()}
            
            {/* Ground */}
            <View style={[styles.ground, { top: GROUND_Y }]}>
              {renderGround()}
            </View>
            
            {/* Hideout */}
            {renderHideout()}
            
            {/* Obstacles */}
            {renderObstacles()}
            
            {/* Player */}
            {renderPlayer()}
            
            {/* Game Over Overlay */}
            {gameState.isGameOver && (
              <View style={styles.gameOverOverlay}>
                <Text style={styles.gameOverEmoji}>{gameState.won ? '🏠' : '🚔'}</Text>
                <Text style={[styles.gameOverText, { color: gameState.won ? COLORS.progress : COLORS.danger }]}>
                  {gameState.won ? 'SAFE!' : 'CAUGHT!'}
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
            onPress={jump}
            activeOpacity={0.7}
          >
            <Ionicons name="arrow-up" size={40} color="#fff" />
            <Text style={styles.controlText}>JUMP</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.controlButton}
            onPressIn={duck}
            onPressOut={stopDucking}
            activeOpacity={0.7}
          >
            <Ionicons name="arrow-down" size={40} color="#fff" />
            <Text style={styles.controlText}>DUCK</Text>
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
              // WIN SCREEN
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>🏠</Text>
                  <Text style={styles.resultTitle}>ESCAPED!</Text>
                  <Text style={styles.resultSubtitle}>You made it to the hideout!</Text>
                </View>
                
                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Distance:</Text>
                    <Text style={styles.statValue}>{Math.floor(gameState.distance)}m</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Level:</Text>
                    <Text style={styles.statValue}>{difficulty}</Text>
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
                      <Text style={styles.rewardValue}>+${gameRewards?.cash || 0}</Text>
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
                      <Text style={[styles.rewardValue, { color: '#2196f3' }]}>+{gameRewards?.xp || 0} XP</Text>
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
                
                <TouchableOpacity style={styles.playAgainButton} onPress={handleStartGame}>
                  <Text style={styles.playAgainText}>Play Again</Text>
                </TouchableOpacity>
              </>
            ) : (
              // LOSE SCREEN
              <>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultEmoji}>🚔</Text>
                  <Text style={[styles.resultTitle, { color: COLORS.danger }]}>BUSTED!</Text>
                  <Text style={styles.resultSubtitle}>You got caught by the cops!</Text>
                </View>
                
                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Distance:</Text>
                    <Text style={styles.statValue}>{Math.floor(gameState.distance)}m</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>Progress:</Text>
                    <Text style={styles.statValue}>{Math.floor(progressPercent)}%</Text>
                  </View>
                </View>
                
                <View style={styles.noRewardsBox}>
                  <Ionicons name="close-circle" size={40} color={COLORS.danger} />
                  <Text style={styles.noRewardsText}>No Rewards</Text>
                  <Text style={styles.noRewardsSubtext}>Reach the hideout to earn rewards!</Text>
                </View>
                
                <TouchableOpacity style={styles.retryButtonLarge} onPress={handleStartGame}>
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
    color: COLORS.progress,
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
    position: 'relative',
  },
  progressFill: {
    height: '100%',
    backgroundColor: COLORS.progress,
    borderRadius: 6,
  },
  progressHideout: {
    position: 'absolute',
    right: 4,
    top: -2,
  },
  progressHideoutIcon: {
    fontSize: 14,
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
    color: COLORS.progress,
    fontSize: 14,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 4,
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
    marginBottom: 16,
  },
  obstacleHint: {
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  hintRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  hintIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  hintText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  startButton: {
    backgroundColor: COLORS.progress,
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
    backgroundColor: COLORS.sky,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  sky: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: COLORS.sky,
  },
  building: {
    position: 'absolute',
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  windowRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 6,
  },
  window: {
    width: 10,
    height: 10,
    backgroundColor: '#ffeaa7',
    borderRadius: 1,
  },
  ground: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: 60,
    backgroundColor: COLORS.ground,
  },
  groundLine: {
    position: 'absolute',
    top: 10,
    width: 40,
    height: 4,
    backgroundColor: COLORS.groundLine,
    borderRadius: 2,
  },
  player: {
    position: 'absolute',
    zIndex: 10,
  },
  playerBody: {
    flex: 1,
    alignItems: 'center',
  },
  playerHead: {
    width: 24,
    height: 24,
    backgroundColor: COLORS.player,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: COLORS.playerOutline,
    marginBottom: 2,
    justifyContent: 'center',
    alignItems: 'flex-end',
    paddingRight: 4,
  },
  playerEye: {
    width: 4,
    height: 4,
    backgroundColor: '#fff',
    borderRadius: 2,
  },
  playerTorso: {
    width: 20,
    height: 24,
    backgroundColor: COLORS.player,
    borderWidth: 2,
    borderColor: COLORS.playerOutline,
    borderRadius: 4,
  },
  playerTorsoDucking: {
    height: 16,
    width: 28,
  },
  playerLegs: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 4,
  },
  playerLeg: {
    width: 8,
    height: 14,
    backgroundColor: COLORS.player,
    borderWidth: 2,
    borderColor: COLORS.playerOutline,
    borderRadius: 4,
  },
  playerLegBack: {
    marginLeft: -4,
  },
  playerLegJumping: {
    transform: [{ rotate: '15deg' }],
  },
  obstacle: {
    position: 'absolute',
    zIndex: 5,
  },
  obstacleInner: {
    flex: 1,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  obstacleAccent: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '40%',
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  obstacleIcon: {
    fontSize: 20,
  },
  hideout: {
    position: 'absolute',
    bottom: 60,
    width: 60,
    height: 80,
    backgroundColor: COLORS.hideout,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingBottom: 8,
    borderWidth: 2,
    borderColor: '#a29bfe',
    borderBottomWidth: 0,
  },
  hideoutDoor: {
    position: 'absolute',
    bottom: 0,
    width: 24,
    height: 40,
    backgroundColor: '#2d3436',
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
  },
  hideoutIcon: {
    fontSize: 28,
    position: 'absolute',
    top: 8,
  },
  gameOverOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  gameOverEmoji: {
    fontSize: 64,
    marginBottom: 16,
  },
  gameOverText: {
    fontSize: 36,
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
    fontSize: 64,
    marginBottom: 8,
  },
  resultTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.progress,
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
    color: COLORS.progress,
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
    color: COLORS.progress,
  },
  collectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.progress,
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
    color: COLORS.danger,
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
