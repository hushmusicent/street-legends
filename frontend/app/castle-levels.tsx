import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
  Dimensions,
  PanResponder,
  Image,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_URL, startRandomCastleGame, completeCastleGame } from '../services/api';
import { useGameStore } from '../stores/gameStore';
import { showGameToast } from '../components/GameToast';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';
import {
  PHYSICS_CONSTANTS,
  Block,
  Enemy,
  Cannonball,
  checkBallRectCollision,
  updateBlocksPhysics,
  updateEnemiesPhysics,
  generateLevelStructure,
} from '../hooks/useCastlePhysics';

// Pixel art gangster character sprite URL (transparent PNG served from backend)
const GANGSTER_SPRITE_URL = `${API_URL}/static/gangster_sprite.png`;

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Use constants from shared physics module
const WORLD_WIDTH = PHYSICS_CONSTANTS.WORLD_WIDTH;
const WORLD_HEIGHT = PHYSICS_CONSTANTS.WORLD_HEIGHT;
const VIEWPORT_WIDTH = SCREEN_WIDTH;
const VIEWPORT_HEIGHT = 400;
const GROUND_Y = PHYSICS_CONSTANTS.GROUND_Y;
const GRAVITY = PHYSICS_CONSTANTS.GRAVITY;
const INITIAL_VELOCITY = PHYSICS_CONSTANTS.INITIAL_VELOCITY;

// Level configurations (rewards scaled to 25% for mini-game balance)
const LEVELS = [
  { level: 1, name: 'Training Ground', blocks: 4, enemies: 1, shots: 3, xpReward: 12, cashReward: 25 },
  { level: 2, name: 'Small Outpost', blocks: 6, enemies: 2, shots: 3, xpReward: 18, cashReward: 35 },
  { level: 3, name: 'Guard Tower', blocks: 8, enemies: 2, shots: 3, xpReward: 25, cashReward: 50 },
  { level: 4, name: 'Watchtower', blocks: 10, enemies: 3, shots: 4, xpReward: 35, cashReward: 75 },
  { level: 5, name: 'Fort Minor', blocks: 12, enemies: 3, shots: 4, xpReward: 50, cashReward: 100 },
  { level: 6, name: 'Stone Keep', blocks: 15, enemies: 4, shots: 4, xpReward: 75, cashReward: 125 },
  { level: 7, name: 'Battle Fortress', blocks: 18, enemies: 4, shots: 5, xpReward: 100, cashReward: 175 },
  { level: 8, name: 'War Castle', blocks: 20, enemies: 5, shots: 5, xpReward: 125, cashReward: 225 },
  { level: 9, name: 'Imperial Stronghold', blocks: 24, enemies: 5, shots: 5, xpReward: 185, cashReward: 300 },
  { level: 10, name: 'Dragon Citadel', blocks: 30, enemies: 6, shots: 6, xpReward: 250, cashReward: 500 },
];

// Note: Block, Enemy, and Cannonball interfaces are imported from useCastlePhysics

export default function CastleLevelsScreen() {
  // Get route params - if randomLevel is true, skip level selection and pick a random level
  const params = useLocalSearchParams<{ randomLevel?: string; castleId?: string }>();
  const isRandomMode = params.randomLevel === 'true';
  const mapCastleId = params.castleId;
  
  // Get player ID from store
  const { playerId, refreshPlayer } = useGameStore();
  const { invalidateCooldowns, invalidatePlayer } = useInvalidateMapQueries();
  
  const [currentLevel, setCurrentLevel] = useState(1);
  const [unlockedLevel, setUnlockedLevel] = useState(1);
  const [showLevelSelect, setShowLevelSelect] = useState(!isRandomMode); // Skip level select in random mode
  const [showResults, setShowResults] = useState(false);
  const [won, setWon] = useState(false);
  const isFromMap = isRandomMode; // Track if launched from map (read-only)
  
  // Game session state for map-based games
  const [gameSessionId, setGameSessionId] = useState<string | null>(null);
  const [gameRewards, setGameRewards] = useState<{ cash: number; xp: number; reputation: number } | null>(null);
  const [isSubmittingResult, setIsSubmittingResult] = useState(false);
  
  // Game state
  const [angle, setAngle] = useState(45);
  const [power, setPower] = useState(100);
  const [shotsRemaining, setShotsRemaining] = useState(3);
  const [cannonball, setCannonball] = useState<Cannonball | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [enemies, setEnemies] = useState<Enemy[]>([]);
  const [gameOver, setGameOver] = useState(false);
  const [firing, setFiring] = useState(false);
  const [cameraX, setCameraX] = useState(0);
  const [showTrajectory, setShowTrajectory] = useState(true);
  
  const animationRef = useRef<number | null>(null);
  const ballPositionRef = useRef({ x: 0, y: 0, active: false });
  const cannonballRef = useRef<Cannonball | null>(null);
  const blocksRef = useRef<Block[]>([]);
  const enemiesRef = useRef<Enemy[]>([]);
  const structureHitRef = useRef(false); // Track if any block has been hit

  // Load progress on mount
  useEffect(() => {
    loadProgress();
  }, []);

  // Auto-start random level when launched from map (random mode)
  useEffect(() => {
    if (isRandomMode && playerId) {
      startMapGame();
    }
  }, [isRandomMode, playerId]);
  
  // Start a game session when coming from the map
  const startMapGame = async () => {
    if (!playerId) return;
    
    try {
      const session = await startRandomCastleGame(playerId, mapCastleId || undefined);
      setGameSessionId(session.id);
      
      // Use the random level from the backend
      const randomLevelNum = session.random_level || Math.floor(Math.random() * 10) + 1;
      setCurrentLevel(randomLevelNum);
      
      // Generate the level
      setTimeout(() => {
        generateLevel(randomLevelNum);
      }, 100);
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Failed to start game';
      showGameToast({
        type: 'error',
        title: 'Cannot Start',
        message: errorMsg,
        duration: 3000,
      });
      // Go back to map
      router.back();
    }
  };

  // Keep refs in sync
  useEffect(() => {
    blocksRef.current = blocks;
  }, [blocks]);

  useEffect(() => {
    enemiesRef.current = enemies;
  }, [enemies]);

  const loadProgress = async () => {
    try {
      const saved = await AsyncStorage.getItem('castleLevelProgress');
      if (saved) {
        const progress = JSON.parse(saved);
        setUnlockedLevel(progress.unlockedLevel || 1);
      }
    } catch {
      console.log('Failed to load progress');
    }
  };

  const saveProgress = async (level: number) => {
    try {
      const newUnlocked = Math.max(unlockedLevel, level + 1);
      setUnlockedLevel(newUnlocked);
      await AsyncStorage.setItem('castleLevelProgress', JSON.stringify({ unlockedLevel: newUnlocked }));
    } catch {
      console.log('Failed to save progress');
    }
  };

  // Generate level layout - uses shared physics module for identical structures as castle-game.tsx
  const generateLevel = useCallback((levelNum: number) => {
    const config = LEVELS[levelNum - 1];
    
    // Use shared level structure generator - ensures identical structures as castle-game.tsx
    const { blocks: generatedBlocks, enemies: generatedEnemies } = generateLevelStructure(levelNum);
    
    setBlocks(generatedBlocks);
    setEnemies(generatedEnemies);
    setShotsRemaining(config.shots);
    setGameOver(false);
    setWon(false);
    setFiring(false);
    setCannonball(null);
    setCameraX(0);
    setShowTrajectory(true);
    structureHitRef.current = false; // Reset - no blocks hit yet
  }, []);

  const startLevel = (level: number) => {
    setCurrentLevel(level);
    generateLevel(level);
    setShowLevelSelect(false);
    structureHitRef.current = false; // Ensure reset on level start
  };

  // Pan responder for aiming
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => !firing && !gameOver,
      onMoveShouldSetPanResponder: () => !firing && !gameOver,
      onPanResponderMove: (_, gestureState) => {
        const newAngle = Math.max(10, Math.min(75, 45 - gestureState.dy / 4));
        const newPower = Math.max(50, Math.min(100, 100 + gestureState.dx / 3));
        setAngle(newAngle);
        setPower(newPower);
      },
    })
  ).current;

  // Trajectory preview
  const getTrajectoryPoints = useCallback(() => {
    const points: { x: number; y: number }[] = [];
    const angleRad = (angle * Math.PI) / 180;
    const velocity = INITIAL_VELOCITY * (power / 100);
    let x = 120;
    let y = GROUND_Y - 80;
    let vx = Math.cos(angleRad) * velocity;
    let vy = -Math.sin(angleRad) * velocity;
    
    for (let i = 0; i < 30; i++) {
      points.push({ x, y });
      x += vx * 3;
      y += vy * 3;
      vy += GRAVITY * 3;
      if (y > GROUND_Y) break;
    }
    return points;
  }, [angle, power]);

  // Note: Collision detection functions (checkBallRectCollision, checkRectRectCollision) 
  // are imported from useCastlePhysics

  // Physics update - uses shared physics module for identical behavior as castle-game.tsx
  const updatePhysics = useCallback(() => {
    const ball = cannonballRef.current;
    const currentBlocks = blocksRef.current;
    
    // Update cannonball position (local calculation for real-time updates)
    if (ball && ball.active) {
      let newX = ball.x + ball.velocityX;
      let newY = ball.y + ball.velocityY;
      let newVelX = ball.velocityX;
      let newVelY = ball.velocityY + GRAVITY;
      let stillActive = true;
      
      const newTrail = [...ball.trail, { x: ball.x, y: ball.y }].slice(-20);
      
      // Check collision with blocks using shared function
      currentBlocks.forEach(block => {
        if (!block.destroyed) {
          if (checkBallRectCollision(newX, newY, block)) {
            newVelX *= 0.6;
            newVelY *= 0.6;
          }
        }
      });
      
      if (newX > WORLD_WIDTH + 50 || newY > GROUND_Y || newX < -50) {
        stillActive = false;
      }
      
      const updatedBall: Cannonball = {
        ...ball,
        x: newX,
        y: newY,
        velocityX: newVelX,
        velocityY: newVelY,
        active: stillActive,
        trail: newTrail,
      };
      cannonballRef.current = updatedBall;
      ballPositionRef.current = { x: newX, y: newY, active: stillActive };
      setCannonball(updatedBall);
    }

    // Camera follows ball
    if (ballPositionRef.current.active) {
      const ballX = ballPositionRef.current.x;
      const targetCameraX = Math.max(0, Math.min(WORLD_WIDTH - VIEWPORT_WIDTH, ballX - VIEWPORT_WIDTH / 3));
      setCameraX(prev => prev + (targetCameraX - prev) * 0.15);
    }

    // Update blocks using SHARED physics function - identical to castle-game.tsx
    setBlocks(prev => {
      const ball = cannonballRef.current;
      const ballX = ballPositionRef.current.x;
      const ballY = ballPositionRef.current.y;
      const ballActive = ballPositionRef.current.active;
      
      return updateBlocksPhysics(
        prev,
        ballX,
        ballY,
        ballActive,
        ball,
        structureHitRef.current,
        () => { structureHitRef.current = true; }
      );
    });

    // Update enemies using SHARED physics function - identical to castle-game.tsx
    setEnemies(prev => {
      const currentBlocksNow = blocksRef.current;
      const ball = cannonballRef.current;
      const ballX = ballPositionRef.current.x;
      const ballY = ballPositionRef.current.y;
      const ballActive = ballPositionRef.current.active;
      
      return updateEnemiesPhysics(
        prev,
        currentBlocksNow,
        ballX,
        ballY,
        ballActive,
        ball,
        structureHitRef.current
      );
    });

    const ballActive = ballPositionRef.current.active;
    const hasAnimatingBlocks = blocksRef.current.some(b => b.falling && (Math.abs(b.velocityY) > 0.5 || Math.abs(b.velocityX) > 0.5));
    const hasAnimatingEnemies = enemiesRef.current.some(e => e.falling);
    
    if (ballActive || hasAnimatingBlocks || hasAnimatingEnemies) {
      animationRef.current = requestAnimationFrame(updatePhysics);
    } else {
      animationRef.current = null;
    }
  }, []);

  // Cleanup
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, []);

  // Check win/lose
  useEffect(() => {
    if (cannonball && !cannonball.active && firing) {
      setTimeout(() => {
        setFiring(false);
        setShowTrajectory(true);
        setCameraX(0);
        
        const remainingEnemies = enemies.filter(e => !e.eliminated).length;
        const eliminatedCount = enemies.length - remainingEnemies;
        
        if (remainingEnemies === 0) {
          setWon(true);
          setGameOver(true);
          saveProgress(currentLevel);
          
          // If from map, submit result to backend for rewards
          if (isFromMap && gameSessionId) {
            submitGameResult(true, eliminatedCount);
          } else {
            setShowResults(true);
          }
        } else if (shotsRemaining <= 0) {
          setWon(false);
          setGameOver(true);
          
          // If from map, submit result to backend (cooldown still applies)
          if (isFromMap && gameSessionId) {
            submitGameResult(false, eliminatedCount);
          } else {
            setShowResults(true);
          }
        }
      }, 1500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cannonball?.active, firing, enemies, shotsRemaining, currentLevel, isFromMap, gameSessionId]);
  
  // Submit game result to backend for map-based games
  const submitGameResult = async (didWin: boolean, eliminatedCount: number) => {
    if (!gameSessionId || isSubmittingResult) return;
    
    setIsSubmittingResult(true);
    
    try {
      const result = await completeCastleGame(gameSessionId, eliminatedCount, didWin);
      
      if (didWin && result.rewards) {
        setGameRewards(result.rewards);
        showGameToast({
          type: 'success',
          title: '🏰 VICTORY!',
          message: `+$${result.rewards.cash} | +${result.rewards.xp} XP | +${result.rewards.reputation} Rep`,
          duration: 3000,
        });
        // Refresh player stats
        if (refreshPlayer) refreshPlayer();
      }
      
      // Refresh cooldowns so the map shows the timer
      if (playerId) {
        invalidateCooldowns(playerId);
        invalidatePlayer(playerId);
      }
      
      setShowResults(true);
    } catch (error) {
      console.error('Failed to submit castle game result:', error);
      setShowResults(true);
    } finally {
      setIsSubmittingResult(false);
    }
  };

  const fireCannon = () => {
    if (firing || shotsRemaining <= 0 || gameOver) return;
    
    setFiring(true);
    setShowTrajectory(false);
    setShotsRemaining(prev => prev - 1);
    
    const angleRad = (angle * Math.PI) / 180;
    const velocity = INITIAL_VELOCITY * (power / 100);
    
    const newBall = {
      x: 120,
      y: GROUND_Y - 80,
      velocityX: Math.cos(angleRad) * velocity,
      velocityY: -Math.sin(angleRad) * velocity,
      active: true,
      trail: [],
    };
    
    cannonballRef.current = newBall;
    ballPositionRef.current = { x: newBall.x, y: newBall.y, active: true };
    setCannonball(newBall);
    
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    animationRef.current = requestAnimationFrame(updatePhysics);
  };

  const trajectoryPoints = showTrajectory ? getTrajectoryPoints() : [];
  const config = LEVELS[currentLevel - 1];

  // Level Select Screen
  if (showLevelSelect) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>CASTLE ASSAULT</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView contentContainerStyle={styles.levelGrid}>
          <Text style={styles.selectTitle}>Select Level</Text>
          
          {LEVELS.map((level) => {
            const isLocked = level.level > unlockedLevel;
            const isCompleted = level.level < unlockedLevel;
            
            return (
              <TouchableOpacity
                key={level.level}
                style={[
                  styles.levelCard,
                  isLocked && styles.levelCardLocked,
                  isCompleted && styles.levelCardCompleted,
                ]}
                onPress={() => !isLocked && startLevel(level.level)}
                disabled={isLocked}
              >
                <View style={styles.levelNumber}>
                  {isLocked ? (
                    <Ionicons name="lock-closed" size={24} color="#666" />
                  ) : isCompleted ? (
                    <Ionicons name="checkmark-circle" size={28} color="#4ade80" />
                  ) : (
                    <Text style={styles.levelNumberText}>{level.level}</Text>
                  )}
                </View>
                <View style={styles.levelInfo}>
                  <Text style={[styles.levelName, isLocked && styles.lockedText]}>
                    {level.name}
                  </Text>
                  <View style={styles.levelStats}>
                    <Text style={styles.levelStatText}>
                      👥 {level.enemies} • 🧱 {level.blocks} • 💣 {level.shots}
                    </Text>
                  </View>
                </View>
                <View style={styles.levelRewards}>
                  <Text style={styles.rewardText}>💰 ${level.cashReward}</Text>
                  <Text style={styles.rewardText}>⭐ {level.xpReward} XP</Text>
                </View>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </SafeAreaView>
    );
  }

  // Game Screen
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.gameHeader}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={() => {
            if (isFromMap) {
              // Go back to map directly
              router.back();
            } else {
              // Show level selection
              setShowLevelSelect(true);
            }
          }}
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <View style={styles.gameHeaderCenter}>
          <Text style={styles.gameHeaderTitle}>
            {isFromMap ? '🎲 Random ' : ''}Level {currentLevel}
          </Text>
          <Text style={styles.gameHeaderSubtitle}>{config.name}</Text>
        </View>
        <View style={styles.shotsContainer}>
          <Text style={styles.shotsLabel}>SHOTS</Text>
          <View style={styles.shotsIndicator}>
            {Array.from({ length: config.shots }).map((_, i) => (
              <View
                key={i}
                style={[
                  styles.shotDot,
                  { backgroundColor: i < shotsRemaining ? '#FFD700' : '#333' },
                ]}
              />
            ))}
          </View>
        </View>
      </View>

      <View style={styles.viewport} {...panResponder.panHandlers}>
        <View style={[styles.world, { transform: [{ translateX: -cameraX }] }]}>
          <View style={styles.skyGradient1} />
          <View style={styles.skyGradient2} />
          
          <View style={[styles.cloud, { left: 200, top: 40 }]} />
          <View style={[styles.cloud, { left: 500, top: 80 }]} />
          <View style={[styles.cloud, { left: 800, top: 30 }]} />
          
          <View style={[styles.ground, { top: GROUND_Y }]}>
            <View style={styles.groundGrass} />
            <View style={styles.groundDirt} />
          </View>
          
          {showTrajectory && trajectoryPoints.map((point, i) => (
            <View
              key={`traj-${i}`}
              style={[
                styles.trajectoryDot,
                { left: point.x - 4, top: point.y - 4, opacity: 1 - i / trajectoryPoints.length },
              ]}
            />
          ))}
          
          <View style={styles.cannonPlatform}>
            <View style={styles.cannonWheelLeft} />
            <View style={styles.cannonWheelRight} />
            <View style={styles.cannonBody}>
              <View style={[styles.cannonBarrel, { transform: [{ rotate: `-${angle}deg` }] }]}>
                <View style={styles.cannonBarrelEnd} />
              </View>
            </View>
          </View>
          
          {cannonball?.trail.map((point, i) => (
            <View
              key={`trail-${i}`}
              style={[
                styles.trailDot,
                { left: point.x - 5, top: point.y - 5, opacity: i / cannonball.trail.length },
              ]}
            />
          ))}
          
          {cannonball?.active && (
            <View style={[styles.cannonball, { left: cannonball.x - 15, top: cannonball.y - 15 }]}>
              <View style={styles.cannonballHighlight} />
            </View>
          )}
          
          {blocks.map(block => {
            if (block.y > GROUND_Y + 100) return null;
            
            // Block colors based on type
            const blockColors = {
              wood: { bg: '#D2691E', border: '#8B4513', highlight: '#DEB887' },
              ice: { bg: '#87CEEB', border: '#4682B4', highlight: '#B0E0E6' },
              stone: { bg: '#808080', border: '#505050', highlight: '#A9A9A9' },
            };
            const colors = blockColors[block.type] || blockColors.wood;
            
            return (
              <View
                key={block.id}
                style={[
                  {
                    position: 'absolute',
                    left: block.x,
                    top: block.y,
                    width: block.width,
                    height: block.height,
                    backgroundColor: colors.bg,
                    borderWidth: 3,
                    borderColor: colors.border,
                    borderRadius: block.type === 'ice' ? 2 : 4,
                    opacity: block.destroyed ? 0.6 : 1,
                    transform: [{ rotate: `${block.rotation}deg` }],
                    overflow: 'hidden',
                  },
                ]}
              >
                {/* Wood grain lines */}
                {block.type === 'wood' && (
                  <>
                    <View style={{ position: 'absolute', top: '30%', left: 0, right: 0, height: 2, backgroundColor: colors.border, opacity: 0.4 }} />
                    <View style={{ position: 'absolute', top: '60%', left: 0, right: 0, height: 2, backgroundColor: colors.border, opacity: 0.4 }} />
                  </>
                )}
                {/* Ice shine */}
                {block.type === 'ice' && (
                  <View style={{ position: 'absolute', top: 3, left: 3, width: '40%', height: '30%', backgroundColor: 'rgba(255,255,255,0.5)', borderRadius: 2 }} />
                )}
                {/* Stone texture */}
                {block.type === 'stone' && (
                  <>
                    <View style={{ position: 'absolute', top: 5, left: 5, width: 4, height: 4, backgroundColor: colors.highlight, borderRadius: 2 }} />
                    <View style={{ position: 'absolute', bottom: 5, right: 5, width: 4, height: 4, backgroundColor: colors.border, borderRadius: 2 }} />
                  </>
                )}
              </View>
            );
          })}
          
          {/* Gangster Enemies - Pixel art gangster characters */}
          {enemies.map(enemy => {
            // Don't render if fallen far below ground
            if (enemy.y > GROUND_Y + 100) return null;
            
            // When eliminated and falling, apply fade out animation
            const isDisappearing = enemy.eliminated && enemy.falling;
            
            return (
              <Animated.View
                key={enemy.id}
                style={[
                  styles.gangsterContainer,
                  {
                    left: enemy.x - 5, // Center the sprite
                    top: enemy.y - 10, // Adjust for taller sprite
                    opacity: isDisappearing ? 0.2 : (enemy.eliminated ? 0 : 1),
                    transform: [
                      { rotate: enemy.falling ? `${(enemy.velocityX || 0) * 5}deg` : '0deg' }
                    ],
                  },
                ]}
              >
                <Image
                  source={{ uri: GANGSTER_SPRITE_URL }}
                  style={styles.gangsterSprite}
                  resizeMode="contain"
                />
                {/* Health indicator when not eliminated */}
                {!enemy.eliminated && (
                  <View style={styles.gangsterHealthBar}>
                    <View style={styles.gangsterHealthFill} />
                  </View>
                )}
              </Animated.View>
            );
          })}
        </View>
        
        {!firing && !gameOver && (
          <View style={styles.aimHUD}>
            <Text style={styles.aimText}>Angle: {Math.round(angle)}°</Text>
            <Text style={styles.aimText}>Power: {Math.round(power)}%</Text>
          </View>
        )}
      </View>

      <View style={styles.controls}>
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Ionicons name="skull-outline" size={20} color="#e74c3c" />
            <Text style={styles.statValue}>{enemies.filter(e => !e.eliminated).length}</Text>
            <Text style={styles.statLabel}>LEFT</Text>
          </View>
          <View style={styles.statBox}>
            <Ionicons name="checkmark-circle-outline" size={20} color="#4ade80" />
            <Text style={[styles.statValue, { color: '#4ade80' }]}>{enemies.filter(e => e.eliminated).length}</Text>
            <Text style={styles.statLabel}>DOWN</Text>
          </View>
        </View>
        
        <TouchableOpacity
          style={[styles.fireButton, (firing || shotsRemaining <= 0 || gameOver) && styles.fireButtonDisabled]}
          onPress={fireCannon}
          disabled={firing || shotsRemaining <= 0 || gameOver}
        >
          <Text style={styles.fireButtonText}>
            {firing ? '💨 FIRING...' : gameOver ? (won ? '🏆 VICTORY' : '💀 FAILED') : '🔥 FIRE!'}
          </Text>
        </TouchableOpacity>
        
        {!firing && !gameOver && (
          <Text style={styles.hintText}>☝️ Drag to aim • Release & tap FIRE</Text>
        )}
      </View>

      {/* Results Modal */}
      <Modal visible={showResults} transparent animationType="fade">
        <View style={styles.resultsOverlay}>
          <View style={styles.resultsContainer}>
            <Text style={[styles.resultsTitle, { color: won ? '#4ade80' : '#ef4444' }]}>
              {won ? '🏆 LEVEL COMPLETE!' : '💀 LEVEL FAILED'}
            </Text>
            
            <Text style={styles.resultsSubtitle}>Level {currentLevel}: {config.name}</Text>
            
            {won && (
              <View style={styles.rewardsContainer}>
                <Text style={styles.rewardsTitle}>REWARDS</Text>
                <View style={styles.rewardRow}>
                  <Text style={styles.rewardIcon}>💰</Text>
                  <Text style={styles.rewardValue}>
                    +${isFromMap && gameRewards ? gameRewards.cash : config.cashReward}
                  </Text>
                </View>
                <View style={styles.rewardRow}>
                  <Text style={styles.rewardIcon}>⭐</Text>
                  <Text style={styles.rewardValue}>
                    +{isFromMap && gameRewards ? gameRewards.xp : config.xpReward} XP
                  </Text>
                </View>
                {isFromMap && gameRewards && (
                  <View style={styles.rewardRow}>
                    <Text style={styles.rewardIcon}>👑</Text>
                    <Text style={styles.rewardValue}>+{gameRewards.reputation} Rep</Text>
                  </View>
                )}
              </View>
            )}
            
            <View style={styles.resultsButtons}>
              {won && currentLevel < 10 && !isFromMap && (
                <TouchableOpacity
                  style={[styles.resultBtn, { backgroundColor: '#4ade80' }]}
                  onPress={() => {
                    setShowResults(false);
                    startLevel(currentLevel + 1);
                  }}
                >
                  <Text style={styles.resultBtnText}>NEXT LEVEL →</Text>
                </TouchableOpacity>
              )}
              
              {/* In random/map mode, allow playing another random level */}
              {isFromMap && (
                <TouchableOpacity
                  style={[styles.resultBtn, { backgroundColor: '#4ade80' }]}
                  onPress={() => {
                    setShowResults(false);
                    // Pick a new random level
                    const newRandomLevel = Math.floor(Math.random() * 10) + 1;
                    setCurrentLevel(newRandomLevel);
                    generateLevel(newRandomLevel);
                  }}
                >
                  <Text style={styles.resultBtnText}>🎲 RANDOM LEVEL</Text>
                </TouchableOpacity>
              )}
              
              <TouchableOpacity
                style={[styles.resultBtn, { backgroundColor: won ? '#666' : '#f39c12' }]}
                onPress={() => {
                  setShowResults(false);
                  startLevel(currentLevel);
                }}
              >
                <Text style={styles.resultBtnText}>{won ? 'REPLAY' : 'TRY AGAIN'}</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[styles.resultBtn, { backgroundColor: '#333' }]}
                onPress={() => {
                  if (isFromMap) {
                    // Go back to map
                    router.back();
                  } else {
                    // Show level selection
                    setShowResults(false);
                    setShowLevelSelect(true);
                  }
                }}
              >
                <Text style={styles.resultBtnText}>{isFromMap ? 'EXIT TO MAP' : 'LEVEL SELECT'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderBottomWidth: 1, borderBottomColor: '#222' },
  backButton: { padding: 8 },
  headerTitle: { fontSize: 20, fontWeight: '900', color: '#CD853F', letterSpacing: 2 },
  selectTitle: { fontSize: 16, color: '#888', marginBottom: 16, textAlign: 'center' },
  levelGrid: { padding: 16 },
  levelCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 2, borderColor: '#8B4513' },
  levelCardLocked: { borderColor: '#333', opacity: 0.6 },
  levelCardCompleted: { borderColor: '#4ade80' },
  levelNumber: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#222', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  levelNumberText: { fontSize: 24, fontWeight: '900', color: '#FFD700' },
  levelInfo: { flex: 1 },
  levelName: { fontSize: 16, fontWeight: '700', color: '#fff' },
  lockedText: { color: '#666' },
  levelStats: { marginTop: 4 },
  levelStatText: { fontSize: 12, color: '#888' },
  levelRewards: { alignItems: 'flex-end' },
  rewardText: { fontSize: 12, color: '#f39c12', fontWeight: '600' },
  
  // Game styles
  gameHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 12, backgroundColor: '#0f0f1a', borderBottomWidth: 2, borderBottomColor: '#8B4513' },
  gameHeaderCenter: { alignItems: 'center', flex: 1 },
  gameHeaderTitle: { fontSize: 16, fontWeight: '800', color: '#CD853F' },
  gameHeaderSubtitle: { fontSize: 11, color: '#888', marginTop: 2 },
  shotsContainer: { alignItems: 'center' },
  shotsLabel: { fontSize: 9, color: '#666', fontWeight: '700' },
  shotsIndicator: { flexDirection: 'row', gap: 4, marginTop: 4 },
  shotDot: { width: 12, height: 12, borderRadius: 6, borderWidth: 2, borderColor: '#FFD700' },
  viewport: { width: VIEWPORT_WIDTH, height: VIEWPORT_HEIGHT, overflow: 'hidden', backgroundColor: '#87CEEB' },
  world: { width: WORLD_WIDTH, height: WORLD_HEIGHT, position: 'relative' },
  skyGradient1: { position: 'absolute', top: 0, left: 0, right: 0, height: 200, backgroundColor: '#4a90d9' },
  skyGradient2: { position: 'absolute', top: 200, left: 0, right: 0, height: 200, backgroundColor: '#6ba3e3' },
  cloud: { position: 'absolute', width: 80, height: 35, backgroundColor: 'rgba(255,255,255,0.8)', borderRadius: 20 },
  ground: { position: 'absolute', left: 0, width: WORLD_WIDTH, height: 100 },
  groundGrass: { height: 15, backgroundColor: '#4a7c23' },
  groundDirt: { height: 85, backgroundColor: '#5c3d2e' },
  cannonPlatform: { position: 'absolute', left: 50, bottom: 60, width: 100, height: 80 },
  cannonBody: { position: 'absolute', bottom: 20, left: 20, width: 60, height: 50, backgroundColor: '#2a2a2a', borderRadius: 10, borderWidth: 3, borderColor: '#444' },
  cannonBarrel: { position: 'absolute', bottom: 20, left: 35, width: 70, height: 25, backgroundColor: '#3a3a3a', borderRadius: 5 },
  cannonBarrelEnd: { position: 'absolute', right: -5, top: 2, width: 10, height: 21, backgroundColor: '#222', borderRadius: 3 },
  cannonWheelLeft: { position: 'absolute', bottom: 0, left: 15, width: 30, height: 30, borderRadius: 15, backgroundColor: '#4a3a2a', borderWidth: 4, borderColor: '#2a2a2a' },
  cannonWheelRight: { position: 'absolute', bottom: 0, left: 55, width: 30, height: 30, borderRadius: 15, backgroundColor: '#4a3a2a', borderWidth: 4, borderColor: '#2a2a2a' },
  trajectoryDot: { position: 'absolute', width: 8, height: 8, borderRadius: 4, backgroundColor: '#FFD700' },
  trailDot: { position: 'absolute', width: 10, height: 10, borderRadius: 5, backgroundColor: '#666' },
  cannonball: { position: 'absolute', width: 30, height: 30, borderRadius: 15, backgroundColor: '#1a1a1a', borderWidth: 3, borderColor: '#333' },
  cannonballHighlight: { position: 'absolute', top: 5, left: 5, width: 10, height: 10, borderRadius: 5, backgroundColor: 'rgba(255,255,255,0.3)' },
  // Gangster sprite styles (pixel art gangster characters)
  gangsterContainer: { 
    position: 'absolute', 
    width: 50, 
    height: 60, 
    alignItems: 'center', 
    justifyContent: 'flex-end' 
  },
  gangsterSprite: { 
    width: 48, 
    height: 56, 
  },
  gangsterHealthBar: {
    position: 'absolute',
    bottom: -6,
    width: 36,
    height: 4,
    backgroundColor: '#333',
    borderRadius: 2,
    overflow: 'hidden',
  },
  gangsterHealthFill: {
    width: '100%',
    height: '100%',
    backgroundColor: '#e74c3c',
  },
  aimHUD: { position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  aimText: { color: '#FFD700', fontSize: 12, fontWeight: '700' },
  controls: { flex: 1, backgroundColor: '#0f0f1a', padding: 12, justifyContent: 'space-between' },
  statsRow: { flexDirection: 'row', justifyContent: 'center', gap: 30 },
  statBox: { alignItems: 'center', backgroundColor: '#1a1a2e', paddingHorizontal: 20, paddingVertical: 8, borderRadius: 10, borderWidth: 2, borderColor: '#333', flexDirection: 'row', gap: 8 },
  statValue: { fontSize: 20, fontWeight: '900', color: '#fff' },
  statLabel: { fontSize: 10, color: '#666', fontWeight: '600' },
  fireButton: { backgroundColor: '#e74c3c', paddingVertical: 14, borderRadius: 12, alignItems: 'center', justifyContent: 'center', borderWidth: 3, borderColor: '#c0392b' },
  fireButtonDisabled: { backgroundColor: '#4a2020', borderColor: '#3a1a1a' },
  fireButtonText: { fontSize: 20, fontWeight: '900', color: '#fff', letterSpacing: 2 },
  hintText: { textAlign: 'center', color: '#666', fontSize: 11, marginTop: 8 },
  resultsOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  resultsContainer: { backgroundColor: '#1a1a2e', borderRadius: 20, padding: 24, width: '100%', maxWidth: 340, alignItems: 'center', borderWidth: 3, borderColor: '#8B4513' },
  resultsTitle: { fontSize: 28, fontWeight: '900', marginBottom: 8 },
  resultsSubtitle: { fontSize: 16, color: '#CD853F', marginBottom: 20 },
  rewardsContainer: { width: '100%', backgroundColor: '#0f0f1a', borderRadius: 12, padding: 16, marginBottom: 16 },
  rewardsTitle: { fontSize: 14, fontWeight: '800', color: '#FFD700', textAlign: 'center', marginBottom: 12 },
  rewardRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 12 },
  rewardIcon: { fontSize: 20 },
  rewardValue: { fontSize: 18, fontWeight: '700', color: '#4ade80' },
  resultsButtons: { width: '100%', gap: 10 },
  resultBtn: { paddingVertical: 14, borderRadius: 12, alignItems: 'center' },
  resultBtnText: { fontSize: 14, fontWeight: '800', color: '#fff', letterSpacing: 1 },
});
