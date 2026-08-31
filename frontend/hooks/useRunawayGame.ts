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
export interface LevelConfig {
  level: number;
  scrollSpeed: number;
  obstacleInterval: number; // ms between obstacles
  hideoutDistance: number; // pixels to win
  lowObstacleChance: number; // 0-1 chance of low vs high
  comboChance: number; // chance of double obstacles
  obstacleTypes: string[]; // visual variety
}

// Generate level config based on difficulty (1-20)
export const getLevelConfig = (difficulty: number): LevelConfig => {
  const level = Math.min(20, Math.max(1, difficulty));
  
  // Base values
  const baseSpeed = 3.5;
  const baseInterval = 1800;
  const baseDistance = 2500;
  
  // Scaling factors - every 10 levels introduces bigger changes
  const speedBoost = level <= 10 ? level * 0.25 : 2.5 + (level - 10) * 0.35;
  const intervalReduction = level <= 10 ? level * 80 : 800 + (level - 10) * 60;
  const distanceBoost = level * 200;
  
  return {
    level,
    scrollSpeed: baseSpeed + speedBoost,
    obstacleInterval: Math.max(700, baseInterval - intervalReduction),
    hideoutDistance: baseDistance + distanceBoost,
    lowObstacleChance: level <= 10 ? 0.5 : 0.45, // Slightly more high obstacles at higher levels
    comboChance: level <= 5 ? 0 : Math.min(0.3, (level - 5) * 0.04), // Combos start at level 6
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

export interface GameState {
  playerState: PlayerState;
  playerY: number;
  obstacles: RunawayObstacle[];
  distance: number;
  isGameOver: boolean;
  won: boolean;
  scrollOffset: number;
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
  });
  
  const gameLoopRef = useRef<number | null>(null);
  const obstacleIdRef = useRef(0);
  const lastObstacleTimeRef = useRef(0);
  const jumpVelocityRef = useRef(0);
  const isJumpingRef = useRef(false);
  const isDuckingRef = useRef(false);
  const gameStartedRef = useRef(false);
  
  // Jump physics constants
  const JUMP_VELOCITY = -14;
  const GRAVITY = 0.8;
  const DUCK_HEIGHT_REDUCTION = 28;
  
  const startGame = useCallback(() => {
    gameStartedRef.current = true;
    isJumpingRef.current = false;
    isDuckingRef.current = false;
    jumpVelocityRef.current = 0;
    obstacleIdRef.current = 0;
    lastObstacleTimeRef.current = Date.now();
    
    setGameState({
      playerState: 'running',
      playerY: GROUND_Y,
      obstacles: [],
      distance: 0,
      isGameOver: false,
      won: false,
      scrollOffset: 0,
    });
    
    runGameLoop();
  }, []);
  
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
  
  const spawnObstacle = useCallback((): RunawayObstacle | null => {
    const now = Date.now();
    if (now - lastObstacleTimeRef.current < levelConfig.obstacleInterval) {
      return null;
    }
    
    lastObstacleTimeRef.current = now;
    
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
    
    // Obstacle hitbox
    const obsLeft = obstacle.x + 5; // Forgiveness
    const obsRight = obstacle.x + OBSTACLE_WIDTH - 5;
    
    // Check horizontal overlap first
    if (playerRight < obsLeft || playerLeft > obsRight) {
      return false;
    }
    
    if (obstacle.type === 'low') {
      // Low obstacle - player must jump over
      // Obstacle is on ground level
      const obsTop = GROUND_Y;
      const obsBottom = GROUND_Y + OBSTACLE_HEIGHT;
      
      // If player is on ground or below obstacle top, collision
      if (playerBottom > obsTop + 10) { // +10 for slight forgiveness when landing
        return true;
      }
    } else {
      // High obstacle - player must duck under
      // Obstacle is floating at head height
      const obsTop = GROUND_Y - 30;
      const obsBottom = obsTop + OBSTACLE_HEIGHT - 10;
      
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
        
        // Update distance
        const newDistance = prev.distance + levelConfig.scrollSpeed;
        const newScrollOffset = prev.scrollOffset + levelConfig.scrollSpeed;
        
        // Check win condition
        if (newDistance >= levelConfig.hideoutDistance) {
          gameStartedRef.current = false;
          return {
            ...prev,
            distance: newDistance,
            scrollOffset: newScrollOffset,
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
        
        // Move obstacles
        let newObstacles = prev.obstacles.map(obs => ({
          ...obs,
          x: obs.x - levelConfig.scrollSpeed,
        })).filter(obs => obs.x > -OBSTACLE_WIDTH);
        
        // Spawn new obstacle
        const newObstacle = spawnObstacle();
        if (newObstacle) {
          newObstacles.push(newObstacle);
          
          // Combo chance - spawn second obstacle
          if (Math.random() < levelConfig.comboChance) {
            const comboType = newObstacle.type === 'low' ? 'high' : 'low';
            newObstacles.push({
              id: obstacleIdRef.current++,
              x: GAME_WIDTH + 50 + 100, // Slightly behind first
              type: comboType,
              passed: false,
            });
          }
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
        };
      });
      
      if (gameStartedRef.current) {
        gameLoopRef.current = requestAnimationFrame(loop);
      }
    };
    
    gameLoopRef.current = requestAnimationFrame(loop);
  }, [levelConfig, spawnObstacle, checkCollision]);
  
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
