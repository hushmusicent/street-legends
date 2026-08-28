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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Game constants
const WORLD_WIDTH = 1200;
const WORLD_HEIGHT = 500;
const VIEWPORT_WIDTH = SCREEN_WIDTH;
const VIEWPORT_HEIGHT = 400;
const GROUND_Y = WORLD_HEIGHT - 60;
const GRAVITY = 0.4;
const INITIAL_VELOCITY = 22;

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

interface Block {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  destroyed: boolean;
  velocityX: number;
  velocityY: number;
  falling: boolean;
  rotation: number;
  type: 'wood' | 'ice' | 'stone'; // Block material type
  shape: 'square' | 'plank_h' | 'plank_v' | 'pillar'; // Block shape
  mass: number; // Higher mass = harder to move
  friction: number; // Higher friction = resists sliding
  hitCount: number; // Track number of hits before breaking
}

interface Enemy {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  eliminated: boolean;
  velocityX: number;
  velocityY: number;
  falling: boolean;
}

interface Cannonball {
  x: number;
  y: number;
  velocityX: number;
  velocityY: number;
  active: boolean;
  trail: { x: number; y: number }[];
}

export default function CastleLevelsScreen() {
  const [currentLevel, setCurrentLevel] = useState(1);
  const [unlockedLevel, setUnlockedLevel] = useState(1);
  const [showLevelSelect, setShowLevelSelect] = useState(true);
  const [showResults, setShowResults] = useState(false);
  const [won, setWon] = useState(false);
  
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

  // Generate level layout - Angry Birds style structures
  const generateLevel = useCallback((levelNum: number) => {
    const config = LEVELS[levelNum - 1];
    const newBlocks: Block[] = [];
    const newEnemies: Enemy[] = [];
    
    const fortX = 350;
    
    // Material properties - VERY HIGH mass and friction to prevent chain reactions
    // Only direct hits should move blocks, minimal force transfer
    const materialProps = {
      wood: { mass: 15.0, friction: 0.95, hitsToBreak: 1 },
      ice: { mass: 8.0, friction: 0.85, hitsToBreak: 1 },
      stone: { mass: 30.0, friction: 0.98, hitsToBreak: 2 },
    };
    
    // Helper to create blocks
    const addBlock = (x: number, y: number, type: 'wood' | 'ice' | 'stone', shape: 'square' | 'plank_h' | 'plank_v' | 'pillar') => {
      let width = 40, height = 40;
      if (shape === 'plank_h') { width = 80; height = 20; }
      if (shape === 'plank_v') { width = 20; height = 80; }
      if (shape === 'pillar') { width = 15; height = 100; }
      
      const props = materialProps[type];
      
      newBlocks.push({
        id: `block-${newBlocks.length}`,
        x, y: GROUND_Y - y,
        width, height,
        destroyed: false,
        velocityX: 0, velocityY: 0,
        falling: false, rotation: 0,
        type, shape,
        mass: props.mass,
        friction: props.friction,
        hitCount: 0,
      });
    };
    
    // Helper to add enemy (pig)
    const addPig = (x: number, y: number) => {
      newEnemies.push({
        id: `pig-${newEnemies.length}`,
        x, y: GROUND_Y - y,
        width: 40, height: 40,
        eliminated: false,
        velocityX: 0, velocityY: 0,
        falling: false,
      });
    };
    
    // Level-specific designs inspired by Angry Birds
    switch (levelNum) {
      case 1: // Simple tower - Training Ground
        addBlock(fortX, 100, 'stone', 'pillar');
        addBlock(fortX + 60, 100, 'stone', 'pillar');
        addBlock(fortX - 10, 110, 'wood', 'plank_h');
        addPig(fortX + 10, 140);
        break;
        
      case 2: // Two pillars with pigs - Small Outpost
        addBlock(fortX, 100, 'stone', 'pillar');
        addBlock(fortX + 100, 100, 'stone', 'pillar');
        addBlock(fortX - 10, 110, 'wood', 'plank_h');
        addBlock(fortX + 90, 110, 'wood', 'plank_h');
        addPig(fortX + 10, 140);
        addPig(fortX + 110, 140);
        break;
        
      case 3: // Tall wooden tower - Guard Tower
        addBlock(fortX, 40, 'wood', 'square');
        addBlock(fortX + 45, 40, 'wood', 'square');
        addBlock(fortX, 85, 'wood', 'plank_v');
        addBlock(fortX + 65, 85, 'wood', 'plank_v');
        addBlock(fortX - 10, 135, 'wood', 'plank_h');
        addBlock(fortX, 175, 'wood', 'plank_v');
        addBlock(fortX + 65, 175, 'wood', 'plank_v');
        addBlock(fortX - 10, 225, 'wood', 'plank_h');
        addPig(fortX + 20, 130);
        addPig(fortX + 20, 255);
        break;
        
      case 4: // Ice structure - Watchtower
        addBlock(fortX, 100, 'stone', 'pillar');
        addBlock(fortX + 80, 100, 'stone', 'pillar');
        addBlock(fortX - 10, 110, 'ice', 'plank_h');
        addBlock(fortX, 130, 'ice', 'square');
        addBlock(fortX + 45, 130, 'ice', 'square');
        addBlock(fortX, 175, 'ice', 'square');
        addBlock(fortX + 45, 175, 'ice', 'square');
        addBlock(fortX + 90, 175, 'ice', 'square');
        addBlock(fortX - 10, 220, 'ice', 'plank_h');
        addPig(fortX + 20, 115);
        addPig(fortX + 20, 250);
        addPig(fortX + 100, 220);
        break;
        
      case 5: // Multi-tower - Fort Minor
        // Left tower
        addBlock(fortX - 50, 100, 'stone', 'pillar');
        addBlock(fortX + 30, 100, 'stone', 'pillar');
        addBlock(fortX - 60, 110, 'wood', 'plank_h');
        addPig(fortX - 30, 145);
        // Right tower
        addBlock(fortX + 100, 100, 'stone', 'pillar');
        addBlock(fortX + 180, 100, 'stone', 'pillar');
        addBlock(fortX + 90, 110, 'wood', 'plank_h');
        addBlock(fortX + 90, 130, 'ice', 'square');
        addBlock(fortX + 135, 130, 'ice', 'square');
        addBlock(fortX + 90, 180, 'ice', 'plank_h');
        addPig(fortX + 120, 115);
        addPig(fortX + 120, 215);
        break;
        
      case 6: // House structure - Stone Keep
        // Foundation
        addBlock(fortX, 40, 'stone', 'square');
        addBlock(fortX + 45, 40, 'stone', 'square');
        addBlock(fortX + 90, 40, 'stone', 'square');
        // Walls
        addBlock(fortX, 130, 'wood', 'plank_v');
        addBlock(fortX + 115, 130, 'wood', 'plank_v');
        // Roof frame (ice)
        addBlock(fortX - 20, 180, 'ice', 'plank_v');
        addBlock(fortX + 135, 180, 'ice', 'plank_v');
        addBlock(fortX + 20, 250, 'ice', 'plank_h');
        addBlock(fortX + 60, 280, 'ice', 'square');
        // Interior
        addBlock(fortX + 30, 85, 'wood', 'plank_h');
        addPig(fortX + 50, 50);
        addPig(fortX + 50, 120);
        addPig(fortX + 50, 200);
        addPig(fortX - 30, 50);
        break;
        
      case 7: // Complex fortress - Battle Fortress
        // Base pillars
        addBlock(fortX - 30, 100, 'stone', 'pillar');
        addBlock(fortX + 50, 100, 'stone', 'pillar');
        addBlock(fortX + 130, 100, 'stone', 'pillar');
        addBlock(fortX + 210, 100, 'stone', 'pillar');
        // First floor
        addBlock(fortX - 40, 110, 'wood', 'plank_h');
        addBlock(fortX + 40, 110, 'wood', 'plank_h');
        addBlock(fortX + 120, 110, 'wood', 'plank_h');
        // Second floor pillars
        addBlock(fortX, 200, 'wood', 'plank_v');
        addBlock(fortX + 80, 200, 'wood', 'plank_v');
        addBlock(fortX + 160, 200, 'wood', 'plank_v');
        // Ice top
        addBlock(fortX - 10, 250, 'ice', 'plank_h');
        addBlock(fortX + 70, 250, 'ice', 'plank_h');
        addBlock(fortX + 40, 280, 'ice', 'square');
        addBlock(fortX + 120, 280, 'ice', 'square');
        addPig(fortX, 145);
        addPig(fortX + 80, 145);
        addPig(fortX + 160, 145);
        addPig(fortX + 80, 310);
        break;
        
      case 8: // War Castle
        // Ground level structures
        for (let i = 0; i < 4; i++) {
          addBlock(fortX + i * 70, 100, 'stone', 'pillar');
          addBlock(fortX + i * 70 - 10, 110, 'wood', 'plank_h');
        }
        // Middle layer - ice
        addBlock(fortX + 20, 150, 'ice', 'square');
        addBlock(fortX + 90, 150, 'ice', 'square');
        addBlock(fortX + 160, 150, 'ice', 'square');
        addBlock(fortX - 10, 200, 'ice', 'plank_h');
        addBlock(fortX + 70, 200, 'ice', 'plank_h');
        addBlock(fortX + 150, 200, 'ice', 'plank_h');
        // Top
        addBlock(fortX + 50, 250, 'wood', 'plank_v');
        addBlock(fortX + 130, 250, 'wood', 'plank_v');
        addBlock(fortX + 40, 300, 'wood', 'plank_h');
        addPig(fortX + 30, 145);
        addPig(fortX + 100, 145);
        addPig(fortX + 170, 145);
        addPig(fortX + 50, 235);
        addPig(fortX + 130, 235);
        break;
        
      case 9: // Imperial Stronghold
        // Multiple structures spread out
        // Structure 1 - Left
        addBlock(fortX - 100, 100, 'stone', 'pillar');
        addBlock(fortX - 20, 100, 'stone', 'pillar');
        addBlock(fortX - 110, 110, 'wood', 'plank_h');
        addBlock(fortX - 70, 150, 'ice', 'square');
        addBlock(fortX - 70, 200, 'ice', 'square');
        addPig(fortX - 60, 145);
        addPig(fortX - 60, 240);
        // Structure 2 - Center tower
        addBlock(fortX + 60, 100, 'stone', 'pillar');
        addBlock(fortX + 140, 100, 'stone', 'pillar');
        addBlock(fortX + 50, 110, 'wood', 'plank_h');
        addBlock(fortX + 50, 150, 'wood', 'square');
        addBlock(fortX + 95, 150, 'wood', 'square');
        addBlock(fortX + 70, 250, 'wood', 'plank_v');
        addBlock(fortX + 110, 250, 'wood', 'plank_v');
        addBlock(fortX + 60, 300, 'wood', 'plank_h');
        addPig(fortX + 70, 145);
        addPig(fortX + 90, 335);
        // Structure 3 - Right
        addBlock(fortX + 220, 100, 'stone', 'pillar');
        addBlock(fortX + 220, 45, 'ice', 'square');
        addPig(fortX + 215, 145);
        break;
        
      case 10: // Dragon Citadel - Epic final level
        // Grand castle structure
        // Base layer
        for (let i = 0; i < 5; i++) {
          addBlock(fortX - 50 + i * 60, 100, 'stone', 'pillar');
        }
        // First floor
        addBlock(fortX - 60, 110, 'wood', 'plank_h');
        addBlock(fortX + 20, 110, 'wood', 'plank_h');
        addBlock(fortX + 100, 110, 'wood', 'plank_h');
        addBlock(fortX + 180, 110, 'wood', 'plank_h');
        // Ice walls
        addBlock(fortX - 30, 200, 'ice', 'plank_v');
        addBlock(fortX + 50, 200, 'ice', 'plank_v');
        addBlock(fortX + 130, 200, 'ice', 'plank_v');
        addBlock(fortX + 210, 200, 'ice', 'plank_v');
        // Second platform
        addBlock(fortX - 40, 250, 'ice', 'plank_h');
        addBlock(fortX + 40, 250, 'ice', 'plank_h');
        addBlock(fortX + 120, 250, 'ice', 'plank_h');
        // Top tower
        addBlock(fortX + 40, 290, 'wood', 'square');
        addBlock(fortX + 85, 290, 'wood', 'square');
        addBlock(fortX + 130, 290, 'wood', 'square');
        addBlock(fortX + 50, 380, 'wood', 'plank_v');
        addBlock(fortX + 120, 380, 'wood', 'plank_v');
        addBlock(fortX + 40, 430, 'wood', 'plank_h');
        addBlock(fortX + 85, 460, 'ice', 'square');
        // Pigs everywhere
        addPig(fortX - 20, 145);
        addPig(fortX + 60, 145);
        addPig(fortX + 140, 145);
        addPig(fortX + 220, 145);
        addPig(fortX + 90, 285);
        addPig(fortX + 90, 465);
        break;
        
      default:
        // Fallback simple structure
        addBlock(fortX, 100, 'stone', 'pillar');
        addBlock(fortX + 60, 100, 'stone', 'pillar');
        addBlock(fortX - 10, 110, 'wood', 'plank_h');
        addPig(fortX + 10, 140);
    }
    
    setBlocks(newBlocks);
    setEnemies(newEnemies);
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

  // Collision detection
  const checkBallRectCollision = (ballX: number, ballY: number, rect: { x: number; y: number; width: number; height: number }) => {
    const ballRadius = 18;
    const closestX = Math.max(rect.x, Math.min(ballX, rect.x + rect.width));
    const closestY = Math.max(rect.y, Math.min(ballY, rect.y + rect.height));
    const distanceX = ballX - closestX;
    const distanceY = ballY - closestY;
    return (distanceX * distanceX + distanceY * distanceY) < (ballRadius * ballRadius);
  };

  const checkRectRectCollision = (r1: { x: number; y: number; width: number; height: number }, r2: { x: number; y: number; width: number; height: number }) => {
    return r1.x < r2.x + r2.width &&
           r1.x + r1.width > r2.x &&
           r1.y < r2.y + r2.height &&
           r1.y + r1.height > r2.y;
  };

  // Physics update
  const updatePhysics = useCallback(() => {
    const ball = cannonballRef.current;
    const currentBlocks = blocksRef.current;
    
    // Update cannonball
    if (ball && ball.active) {
      let newX = ball.x + ball.velocityX;
      let newY = ball.y + ball.velocityY;
      let newVelX = ball.velocityX;
      let newVelY = ball.velocityY + GRAVITY;
      let stillActive = true;
      
      const newTrail = [...ball.trail, { x: ball.x, y: ball.y }].slice(-20);
      
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
      
      const updatedBall = {
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

    // Update blocks - physics with material-based behavior
    setBlocks(prev => {
      // First pass: handle cannonball collisions and basic physics
      const updatedBlocks = prev.map(block => {
        if (block.destroyed && block.y >= GROUND_Y + 100) return block;
        
        const ballX = ballPositionRef.current.x;
        const ballY = ballPositionRef.current.y;
        const ballActive = ballPositionRef.current.active;
        const ball = cannonballRef.current;
        
        // Direct cannonball hits
        if (!block.destroyed && !block.falling && ballActive && ball) {
          if (checkBallRectCollision(ballX, ballY, block)) {
            const impactForce = Math.sqrt(ball.velocityX * ball.velocityX + ball.velocityY * ball.velocityY);
            const impactAngle = Math.atan2(ballY - (block.y + block.height/2), ballX - (block.x + block.width/2));
            
            // Mark structure as hit - now support checks can happen
            structureHitRef.current = true;
            
            // Direct cannonball hit - ONLY this specific block moves
            // Very LOW velocity transfer to prevent chain reactions
            const velocityMult = block.type === 'stone' ? 0.08 : (block.type === 'ice' ? 0.15 : 0.12);
            return {
              ...block,
              destroyed: true,
              falling: true,
              hitCount: block.hitCount + 1,
              // Minimal velocity - block moves slowly, doesn't fly
              velocityX: -Math.cos(impactAngle) * impactForce * velocityMult,
              velocityY: -Math.abs(Math.sin(impactAngle) * impactForce * velocityMult * 0.3) - 1,
            };
          }
        }
        
        // Physics for falling/destroyed blocks ONLY
        if (block.falling || block.destroyed) {
          let newX = block.x + block.velocityX;
          let newY = block.y + block.velocityY;
          // Slow falling, high drag
          let newVelY = block.velocityY + GRAVITY * 0.6;
          // Very high friction - blocks slow down fast
          let newVelX = block.velocityX * 0.85;
          let newRotation = block.rotation + block.velocityX * 0.5;
          
          // Ground collision - blocks stop quickly
          if (newY > GROUND_Y - 10) {
            newY = GROUND_Y - 10;
            newVelY = 0; // No bounce
            newVelX *= 0.2; // High ground friction
          }
          
          // Cap maximum velocity to prevent blocks flying too fast
          newVelX = Math.max(-3, Math.min(3, newVelX));
          newVelY = Math.max(-5, Math.min(8, newVelY));
          
          return {
            ...block,
            x: newX,
            y: newY,
            velocityX: newVelX,
            velocityY: newVelY,
            rotation: newRotation,
          };
        }
        
        // Stationary blocks stay stationary until hit
        return block;
      });
      
      // Second pass: block-to-block collisions - VERY restrictive
      // ONLY if structure has been hit at least once
      if (!structureHitRef.current) {
        return updatedBlocks;
      }
      
      return updatedBlocks.map(block => {
        if (block.destroyed || block.falling) return block;
        
        // Check if hit by falling/moving block
        for (const other of updatedBlocks) {
          if (other.id === block.id) continue;
          if (!other.falling && !other.destroyed) continue;
          
          // Calculate the momentum of the falling block
          const otherSpeed = Math.sqrt(other.velocityX * other.velocityX + other.velocityY * other.velocityY);
          const otherMomentum = otherSpeed * other.mass;
          
          if (!checkRectRectCollision(other, block)) continue;
          
          // VERY HIGH force thresholds - blocks barely affect each other
          // Only a fast, heavy block can move another block
          const forceNeeded = block.type === 'stone' ? 100 : (block.type === 'ice' ? 40 : 60);
          
          if (otherMomentum > forceNeeded) {
            // Very rare - only happens with very fast, heavy blocks
            // Even then, minimal velocity transfer
            const pushDirection = other.x < block.x ? 1 : -1;
            return {
              ...block,
              destroyed: true,
              falling: true,
              // Minimal velocity - block barely moves
              velocityX: pushDirection * 0.5,
              velocityY: -0.5,
            };
          }
        }
        
        // DISABLED support check - blocks don't fall just because support is removed
        // They only move when directly hit or pushed by a fast-moving block
        // This prevents the whole structure collapsing
        
        return block;
      });
    });

    // Update enemies (pigs) - can be hit by cannonball or falling blocks
    setEnemies(prev => {
      const currentBlocksNow = blocksRef.current;
      
      return prev.map(enemy => {
        if (enemy.eliminated && enemy.y >= GROUND_Y + 100) return enemy;
        
        const ballX = ballPositionRef.current.x;
        const ballY = ballPositionRef.current.y;
        const ballActive = ballPositionRef.current.active;
        const ball = cannonballRef.current;
        
        // Direct cannonball hit eliminates pig
        if (!enemy.eliminated && ballActive && ball) {
          if (checkBallRectCollision(ballX, ballY, enemy)) {
            return {
              ...enemy,
              eliminated: true,
              falling: true,
              velocityX: ball.velocityX * 0.4,
              velocityY: -8,
            };
          }
        }
        
        // Falling blocks can knock pigs - any block with enough momentum
        if (!enemy.eliminated && !enemy.falling) {
          for (const b of currentBlocksNow) {
            if (!b.falling && !b.destroyed) continue;
            if (!checkRectRectCollision(b, enemy)) continue;
            
            // Calculate block momentum (mass * velocity)
            const blockMomentum = b.mass * Math.sqrt(b.velocityX * b.velocityX + b.velocityY * b.velocityY);
            
            // Stone blocks need less speed because they're heavy
            // Wood blocks need more speed
            const momentumThreshold = b.type === 'stone' ? 3 : (b.type === 'ice' ? 2 : 4);
            
            if (blockMomentum > momentumThreshold) {
              const pushDir = b.x < enemy.x ? 1 : -1;
              return {
                ...enemy,
                eliminated: true,
                falling: true,
                velocityX: pushDir * 3 + b.velocityX * 0.3,
                velocityY: -6,
              };
            }
          }
        }
        
        // Pigs fall if their support is destroyed (only after structure hit)
        if (!enemy.falling && !enemy.eliminated && structureHitRef.current) {
          const supportBlock = currentBlocksNow.find(b => 
            !b.destroyed &&
            !b.falling &&
            enemy.x + enemy.width * 0.3 > b.x &&
            enemy.x + enemy.width * 0.7 < b.x + b.width &&
            Math.abs((enemy.y + enemy.height) - b.y) < 20
          );
          
          const isOnGround = enemy.y + enemy.height >= GROUND_Y - 25;
          
          if (!supportBlock && !isOnGround) {
            return {
              ...enemy,
              falling: true,
              velocityX: 0,
              velocityY: 0,
            };
          }
        }
        
        // Physics for falling pigs
        if (enemy.falling) {
          let newY = enemy.y + enemy.velocityY;
          let newVelY = enemy.velocityY + GRAVITY;
          
          // Hit ground = eliminated
          if (newY > GROUND_Y - 20) {
            return { ...enemy, eliminated: true, y: GROUND_Y - 20, velocityY: 0, falling: false };
          }
          
          return {
            ...enemy,
            x: enemy.x + enemy.velocityX,
            y: newY,
            velocityX: enemy.velocityX * 0.98,
            velocityY: newVelY,
          };
        }
        
        return enemy;
      });
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
        
        if (remainingEnemies === 0) {
          setWon(true);
          setGameOver(true);
          saveProgress(currentLevel);
          setShowResults(true);
        } else if (shotsRemaining <= 0) {
          setWon(false);
          setGameOver(true);
          setShowResults(true);
        }
      }, 1500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cannonball?.active, firing, enemies, shotsRemaining, currentLevel]);

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
        <TouchableOpacity style={styles.backButton} onPress={() => setShowLevelSelect(true)}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <View style={styles.gameHeaderCenter}>
          <Text style={styles.gameHeaderTitle}>Level {currentLevel}</Text>
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
          
          {/* Green Pigs */}
          {enemies.map(enemy => {
            if (enemy.y > GROUND_Y + 100) return null;
            
            return (
              <View
                key={enemy.id}
                style={[
                  styles.pig,
                  { left: enemy.x, top: enemy.y, opacity: enemy.eliminated ? 0.3 : 1 },
                ]}
              >
                {/* Pig body (green circle) */}
                <View style={styles.pigBody}>
                  {/* Ears */}
                  <View style={[styles.pigEar, { left: -3, top: 2 }]} />
                  <View style={[styles.pigEar, { right: -3, top: 2 }]} />
                  {/* Eyes */}
                  <View style={styles.pigEyeLeft}>
                    <View style={styles.pigPupil} />
                  </View>
                  <View style={styles.pigEyeRight}>
                    <View style={styles.pigPupil} />
                  </View>
                  {/* Snout */}
                  <View style={styles.pigSnout}>
                    <View style={styles.pigNostril} />
                    <View style={[styles.pigNostril, { left: 12 }]} />
                  </View>
                  {/* Eyebrows when hit */}
                  {enemy.eliminated && (
                    <>
                      <View style={[styles.pigBrow, { left: 6, transform: [{ rotate: '-20deg' }] }]} />
                      <View style={[styles.pigBrow, { right: 6, transform: [{ rotate: '20deg' }] }]} />
                    </>
                  )}
                </View>
              </View>
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
                  <Text style={styles.rewardValue}>+${config.cashReward}</Text>
                </View>
                <View style={styles.rewardRow}>
                  <Text style={styles.rewardIcon}>⭐</Text>
                  <Text style={styles.rewardValue}>+{config.xpReward} XP</Text>
                </View>
              </View>
            )}
            
            <View style={styles.resultsButtons}>
              {won && currentLevel < 10 && (
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
                  setShowResults(false);
                  setShowLevelSelect(true);
                }}
              >
                <Text style={styles.resultBtnText}>LEVEL SELECT</Text>
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
  // Pig styles (Angry Birds style green pigs)
  pig: { position: 'absolute', width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  pigBody: { width: 38, height: 38, borderRadius: 19, backgroundColor: '#7CB342', borderWidth: 3, borderColor: '#558B2F', position: 'relative', overflow: 'visible' },
  pigEar: { position: 'absolute', width: 10, height: 10, borderRadius: 5, backgroundColor: '#7CB342', borderWidth: 2, borderColor: '#558B2F' },
  pigEyeLeft: { position: 'absolute', top: 8, left: 5, width: 12, height: 12, borderRadius: 6, backgroundColor: '#fff', borderWidth: 1, borderColor: '#333' },
  pigEyeRight: { position: 'absolute', top: 8, right: 5, width: 12, height: 12, borderRadius: 6, backgroundColor: '#fff', borderWidth: 1, borderColor: '#333' },
  pigPupil: { position: 'absolute', top: 3, left: 4, width: 5, height: 5, borderRadius: 3, backgroundColor: '#333' },
  pigSnout: { position: 'absolute', bottom: 4, left: '50%', marginLeft: -10, width: 20, height: 12, borderRadius: 6, backgroundColor: '#8BC34A', borderWidth: 2, borderColor: '#558B2F' },
  pigNostril: { position: 'absolute', top: 3, left: 3, width: 4, height: 4, borderRadius: 2, backgroundColor: '#558B2F' },
  pigBrow: { position: 'absolute', top: 4, width: 8, height: 3, backgroundColor: '#333', borderRadius: 1 },
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
