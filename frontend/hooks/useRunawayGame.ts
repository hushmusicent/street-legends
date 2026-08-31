import { useRef, useCallback, useState, useEffect } from 'react';
import { Dimensions } from 'react-native';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Game constants
export const GAME_WIDTH = Math.min(SCREEN_WIDTH - 32, 380);
export const GAME_HEIGHT = 280;
export const GROUND_Y = GAME_HEIGHT - 60;
export const PLAYER_WIDTH = 48;
export const PLAYER_HEIGHT = 64;
export const OBSTACLE_WIDTH = 44;
export const OBSTACLE_HEIGHT = 44;

// Player states
export type PlayerState = 'running' | 'jumping' | 'ducking';

// Obstacle types
export interface RunawayObstacle {
  id: number;
  x: number;
  type: 'low' | 'high'; // low = jump over, high = duck under
  passed: boolean;
}

// Level configuration - 20 difficulty levels
// NEW: Difficulty is based on DISTANCE, not speed
// Speed ramps up as player approaches hideout
export interface LevelConfig {
  level: number;
  baseScrollSpeed: number; // Starting speed
  maxScrollSpeed: number; // Speed near hideout
  minObstacleGap: number; // Minimum pixels between obstacles
  hideoutDistance: number; // pixels to win - THIS IS THE KEY DIFFICULTY FACTOR
  lowObstacleChance: number; // 0-1 chance of low vs high
  obstacleTypes: string[]; // visual variety
}

// Generate level config based on difficulty (1-20)
// NEW SYSTEM: Level determines DISTANCE, not speed
export const getLevelConfig = (difficulty: number): LevelConfig => {
  const level = Math.min(20, Math.max(1, difficulty));
  
  // Base distance for level 1, increases significantly with each level
  // Level 1: 1500m (short run)
  // Level 20: 8000m (marathon run)
  const baseDistance = 1500;
  const distancePerLevel = 350; // Each level adds 350 pixels
  const hideoutDistance = baseDistance + (level - 1) * distancePerLevel;
  
  // Speed is the SAME across all levels - it ramps up during the run
  const baseScrollSpeed = 3.0; // Comfortable starting speed
  const maxScrollSpeed = 6.5; // Fast but fair at the end
  
  // Obstacle spacing - GENEROUS gaps, especially at lower levels
  // Level 1: 280px minimum gap (very comfortable)
  // Level 20: 160px minimum gap (still readable and fair)
  const minGapBase = 280;
  const minGapReduction = (level - 1) * 6; // Reduce gap by 6px per level
  const minObstacleGap = Math.max(160, minGapBase - minGapReduction);
  
  return {
    level,
    baseScrollSpeed,
    maxScrollSpeed,
    minObstacleGap,
    hideoutDistance,
    lowObstacleChance: 0.5, // 50/50 low vs high
    obstacleTypes: getObstacleTypesForLevel(level),
  };
};

// Obstacle visual variety by level
const getObstacleTypesForLevel = (level: number): string[] => {
  const types = ['trash', 'barrier']; // Always available
  if (level >= 5) types.push('hydrant');
  if (level >= 10) types.push('car');
  if (level >= 15) types.push('dumpster');
  if (level >= 18) types.push('construction');
  return types;
};

// Calculate rewards based on level (higher level = more rewards)
export const getRunawayRewards = (level: number): { cash: number; xp: number; reputation: number } => {
  // Base rewards + scaling with level
  const baseCash = 60;
  const baseXP = 30;
  const baseRep = 2;
  
  // Exponential-ish scaling so higher levels feel very rewarding
  const levelMultiplier = 1 + (level - 1) * 0.2; // 1.0 at L1, 4.8 at L20
  
  return {
    cash: Math.floor(baseCash * levelMultiplier + level * 15),
    xp: Math.floor(baseXP * levelMultiplier + level * 10),
    reputation: Math.floor(baseRep + level / 2),
  };
};

export interface GameState {
  playerState: PlayerState;
  playerY: number;
  obstacles: RunawayObstacle[];
  distance: number;
  isGameOver: boolean;
  won: boolean;
  scrollOffset: number;
  currentSpeed: number; // Track current speed for display
}

export interface UseRunawayGameResult {
  gameState: GameState;
  levelConfig: LevelConfig;
  startGame: () => void;
  jump: () => void;
  duck: () => void;
  stopDucking: () => void;
  progressPercent: number;
}

export const useRunawayGame = (difficulty: number): UseRunawayGameResult => {
  const levelConfig = getLevelConfig(difficulty);
  
  const [gameState, setGameState] = useState<GameState>({
    playerState: 'running',
    playerY: GROUND_Y,
    obstacles: [],
    distance: 0,
    isGameOver: false,
    won: false,
    scrollOffset: 0,
    currentSpeed: levelConfig.baseScrollSpeed,
  });
  
  const gameLoopRef = useRef<number | null>(null);
  const obstacleIdRef = useRef(0);
  const lastObstacleXRef = useRef(-1000); // Track X position of last obstacle (not time)
  const jumpVelocityRef = useRef(0);
  const isJumpingRef = useRef(false);
  const isDuckingRef = useRef(false);
  const gameStartedRef = useRef(false);
  
  // Jump physics constants
  const JUMP_VELOCITY = -14;
  const GRAVITY = 0.8;
  const DUCK_HEIGHT_REDUCTION = 28;
  
  // Calculate current scroll speed based on progress
  // Speed ramps up as player approaches hideout
  const calculateCurrentSpeed = useCallback((distance: number): number => {
    const progress = distance / levelConfig.hideoutDistance; // 0 to 1
    
    // Use smooth easing curve - slow start, accelerates toward end
    // Quadratic easing: starts slow, ends fast
    const speedProgress = progress * progress; // Quadratic curve
    
    const speedRange = levelConfig.maxScrollSpeed - levelConfig.baseScrollSpeed;
    return levelConfig.baseScrollSpeed + speedRange * speedProgress;
  }, [levelConfig]);
  
  const startGame = useCallback(() => {
    gameStartedRef.current = true;
    isJumpingRef.current = false;
    isDuckingRef.current = false;
    jumpVelocityRef.current = 0;
    obstacleIdRef.current = 0;
    lastObstacleXRef.current = -1000; // Reset to allow immediate first obstacle
    
    setGameState({
      playerState: 'running',
      playerY: GROUND_Y,
      obstacles: [],
      distance: 0,
      isGameOver: false,
      won: false,
      scrollOffset: 0,
      currentSpeed: levelConfig.baseScrollSpeed,
    });
    
    runGameLoop();
  }, [levelConfig]);
  
  const jump = useCallback(() => {
    if (!gameStartedRef.current || isJumpingRef.current || isDuckingRef.current) return;
    
    isJumpingRef.current = true;
    jumpVelocityRef.current = JUMP_VELOCITY;
    
    setGameState(prev => ({
      ...prev,
      playerState: 'jumping',
    }));
  }, []);
  
  const duck = useCallback(() => {
    if (!gameStartedRef.current || isJumpingRef.current) return;
    
    isDuckingRef.current = true;
    setGameState(prev => ({
      ...prev,
      playerState: 'ducking',
    }));
  }, []);
  
  const stopDucking = useCallback(() => {
    if (!isDuckingRef.current) return;
    
    isDuckingRef.current = false;
    setGameState(prev => ({
      ...prev,
      playerState: 'running',
    }));
  }, []);
  
  // Spawn obstacle based on DISTANCE from last obstacle, not time
  const trySpawnObstacle = useCallback((currentScrollOffset: number): RunawayObstacle | null => {
    // Calculate distance since last obstacle
    const distanceSinceLastObstacle = currentScrollOffset - lastObstacleXRef.current;
    
    // Only spawn if we've traveled far enough
    if (distanceSinceLastObstacle < levelConfig.minObstacleGap) {
      return null;
    }
    
    // Add some randomness to spacing (±20% of min gap)
    const randomExtra = levelConfig.minObstacleGap * 0.2 * Math.random();
    if (distanceSinceLastObstacle < levelConfig.minObstacleGap + randomExtra) {
      return null;
    }
    
    // Update last obstacle position
    lastObstacleXRef.current = currentScrollOffset;
    
    // Determine obstacle type
    const isLow = Math.random() < levelConfig.lowObstacleChance;
    
    return {
      id: obstacleIdRef.current++,
      x: GAME_WIDTH + 50,
      type: isLow ? 'low' : 'high',
      passed: false,
    };
  }, [levelConfig]);
  
  const checkCollision = useCallback((playerY: number, playerState: PlayerState, obstacle: RunawayObstacle): boolean => {
    // Player hitbox
    const playerLeft = 50; // Fixed X position
    const playerRight = playerLeft + PLAYER_WIDTH - 10; // Slight forgiveness
    const playerTop = playerState === 'ducking' ? playerY + DUCK_HEIGHT_REDUCTION : playerY;
    const playerBottom = playerY + PLAYER_HEIGHT;
    
    // Obstacle hitbox - generous forgiveness
    const obsLeft = obstacle.x + 8; // More forgiveness
    const obsRight = obstacle.x + OBSTACLE_WIDTH - 8;
    
    // Check horizontal overlap first
    if (playerRight < obsLeft || playerLeft > obsRight) {
      return false;
    }
    
    if (obstacle.type === 'low') {
      // Low obstacle - player must jump over
      // Obstacle is on ground level
      const obsTop = GROUND_Y;
      
      // If player is on ground or below obstacle top, collision
      if (playerBottom > obsTop + 12) { // Extra forgiveness when landing
        return true;
      }
    } else {
      // High obstacle - player must duck under
      // Obstacle is floating at head height
      const obsTop = GROUND_Y - 30;
      const obsBottom = obsTop + OBSTACLE_HEIGHT - 12;
      
      // If player is standing (not ducking), head collides
      if (playerState !== 'ducking' && playerTop < obsBottom) {
        return true;
      }
    }
    
    return false;
  }, []);
  
  const runGameLoop = useCallback(() => {
    const loop = () => {
      setGameState(prev => {
        if (prev.isGameOver || !gameStartedRef.current) return prev;
        
        // Calculate current speed based on progress
        const currentSpeed = calculateCurrentSpeed(prev.distance);
        
        // Update distance
        const newDistance = prev.distance + currentSpeed;
        const newScrollOffset = prev.scrollOffset + currentSpeed;
        
        // Check win condition
        if (newDistance >= levelConfig.hideoutDistance) {
          gameStartedRef.current = false;
          return {
            ...prev,
            distance: newDistance,
            scrollOffset: newScrollOffset,
            currentSpeed,
            isGameOver: true,
            won: true,
          };
        }
        
        // Update player Y (jumping physics)
        let newPlayerY = prev.playerY;
        let newPlayerState = prev.playerState;
        
        if (isJumpingRef.current) {
          jumpVelocityRef.current += GRAVITY;
          newPlayerY = prev.playerY + jumpVelocityRef.current;
          
          // Land on ground
          if (newPlayerY >= GROUND_Y) {
            newPlayerY = GROUND_Y;
            isJumpingRef.current = false;
            jumpVelocityRef.current = 0;
            newPlayerState = isDuckingRef.current ? 'ducking' : 'running';
          }
        }
        
        // Move obstacles at current speed
        let newObstacles = prev.obstacles.map(obs => ({
          ...obs,
          x: obs.x - currentSpeed,
        })).filter(obs => obs.x > -OBSTACLE_WIDTH);
        
        // Try to spawn new obstacle
        const newObstacle = trySpawnObstacle(newScrollOffset);
        if (newObstacle) {
          newObstacles.push(newObstacle);
        }
        
        // Check collisions
        for (const obs of newObstacles) {
          if (!obs.passed && checkCollision(newPlayerY, newPlayerState, obs)) {
            gameStartedRef.current = false;
            return {
              ...prev,
              playerY: newPlayerY,
              playerState: newPlayerState,
              obstacles: newObstacles,
              distance: newDistance,
              scrollOffset: newScrollOffset,
              currentSpeed,
              isGameOver: true,
              won: false,
            };
          }
          
          // Mark as passed if player cleared it
          if (obs.x + OBSTACLE_WIDTH < 50) {
            obs.passed = true;
          }
        }
        
        return {
          ...prev,
          playerY: newPlayerY,
          playerState: newPlayerState,
          obstacles: newObstacles,
          distance: newDistance,
          scrollOffset: newScrollOffset,
          currentSpeed,
        };
      });
      
      if (gameStartedRef.current) {
        gameLoopRef.current = requestAnimationFrame(loop);
      }
    };
    
    gameLoopRef.current = requestAnimationFrame(loop);
  }, [levelConfig, calculateCurrentSpeed, trySpawnObstacle, checkCollision]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (gameLoopRef.current) {
        cancelAnimationFrame(gameLoopRef.current);
      }
      gameStartedRef.current = false;
    };
  }, []);
  
  const progressPercent = Math.min(100, (gameState.distance / levelConfig.hideoutDistance) * 100);
  
  return {
    gameState,
    levelConfig,
    startGame,
    jump,
    duck,
    stopDucking,
    progressPercent,
  };
};
