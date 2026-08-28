import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  PanResponder,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { completeCastleGame } from '../services/api';
import { showGameToast } from '../components/GameToast';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Game world is much larger than screen - camera will pan
const WORLD_WIDTH = 1200;
const WORLD_HEIGHT = 500;
const VIEWPORT_WIDTH = SCREEN_WIDTH;
const VIEWPORT_HEIGHT = 450;
const GROUND_Y = WORLD_HEIGHT - 60;
const GRAVITY = 0.4;
const INITIAL_VELOCITY = 22;

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
  type: 'wood' | 'ice' | 'stone';
  shape: 'square' | 'plank_h' | 'plank_v' | 'pillar';
  mass: number;
  friction: number;
  hitCount: number;
}

interface GangMember {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  eliminated: boolean;
  fort_index: number;
  velocityX: number;
  velocityY: number;
  falling: boolean;
}

interface Fort {
  id: string;
  x: number;
  blocks: Block[];
  height: number;
  width: number;
}

interface GameLayout {
  forts: Fort[];
  gang_members: GangMember[];
  total_members: number;
  difficulty: number;
}

interface Cannonball {
  x: number;
  y: number;
  velocityX: number;
  velocityY: number;
  active: boolean;
  trail: { x: number; y: number }[];
}

export default function CastleMinigameScreen() {
  const params = useLocalSearchParams();
  const gameData = params.gameData ? JSON.parse(params.gameData as string) : null;
  
  const [angle, setAngle] = useState(45);
  const [power, setPower] = useState(100);
  const [shotsRemaining, setShotsRemaining] = useState(3);
  const [cannonball, setCannonball] = useState<Cannonball | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [gangMembers, setGangMembers] = useState<GangMember[]>([]);
  const [gameOver, setGameOver] = useState(false);
  const [won, setWon] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [firing, setFiring] = useState(false);
  const [cameraX, setCameraX] = useState(0);
  const [showTrajectory, setShowTrajectory] = useState(true);
  const animationRef = useRef<number | null>(null);
  const cameraAnim = useRef(new Animated.Value(0)).current;
  const ballPositionRef = useRef({ x: 0, y: 0, active: false });
  const cannonballRef = useRef<Cannonball | null>(null);
  const structureHitRef = useRef(false); // Track if any block has been hit
  
  // Initialize game state from gameData
  useEffect(() => {
    if (gameData?.layout) {
      const layout: GameLayout = gameData.layout;
      
      // Scale server coordinates to world coordinates
      // Server uses x: 400-900, y: 0-400
      // World uses x: 0-1200, y: 0-500
      // Shift forts farther right for longer cannonball arc
      const scaleX = (x: number) => 500 + ((x - 300) / 600) * 700;
      const scaleY = (y: number) => (y / 400) * (GROUND_Y - 50);
      
      // Material properties - VERY HIGH mass and friction to prevent chain reactions
      const materialProps = {
        wood: { mass: 15.0, friction: 0.95, hitsToBreak: 1 },
        ice: { mass: 8.0, friction: 0.85, hitsToBreak: 1 },
        stone: { mass: 30.0, friction: 0.98, hitsToBreak: 2 },
      };
      
      // Block type assignment based on difficulty and position
      const getBlockType = (blockIndex: number, _fortIndex: number): { type: 'wood' | 'ice' | 'stone', shape: 'square' | 'plank_h' | 'plank_v' | 'pillar' } => {
        const difficulty = gameData.difficulty || 1;
        // More variety as difficulty increases
        // Base blocks are often stone pillars, middle wood, top ice
        const heightFactor = (blockIndex % 4);
        if (heightFactor === 0) return { type: 'stone', shape: 'pillar' };
        if (heightFactor === 1) return { type: 'wood', shape: difficulty > 2 ? 'plank_h' : 'square' };
        if (heightFactor === 2) return { type: difficulty > 1 ? 'ice' : 'wood', shape: 'square' };
        return { type: 'wood', shape: 'plank_v' };
      };
      
      // Initialize blocks with types and physics properties
      const allBlocks: Block[] = [];
      layout.forts.forEach((fort, fortIndex) => {
        fort.blocks.forEach((block, blockIndex) => {
          const { type, shape } = getBlockType(blockIndex, fortIndex);
          const props = materialProps[type];
          let width = 45, height = 45;
          if (shape === 'plank_h') { width = 80; height = 20; }
          if (shape === 'plank_v') { width = 20; height = 80; }
          if (shape === 'pillar') { width = 15; height = 100; }
          
          allBlocks.push({
            ...block,
            x: scaleX(block.x),
            y: scaleY(block.y),
            width,
            height,
            velocityX: 0,
            velocityY: 0,
            falling: false,
            rotation: 0,
            type,
            shape,
            mass: props.mass,
            friction: props.friction,
            hitCount: 0,
          });
        });
      });
      setBlocks(allBlocks);
      
      // Initialize gang members
      const members: GangMember[] = layout.gang_members.map(m => ({
        ...m,
        x: scaleX(m.x),
        y: scaleY(m.y) - 10,
        width: 35,
        height: 40,
        velocityX: 0,
        velocityY: 0,
        falling: false,
      }));
      setGangMembers(members);
      structureHitRef.current = false; // Reset - no blocks hit yet
    }
  }, [gameData]);

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

  // Calculate trajectory preview
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

  // Check collision between ball and rectangle
  const checkBallRectCollision = (ballX: number, ballY: number, rect: { x: number; y: number; width: number; height: number }) => {
    const ballRadius = 18; // Slightly larger for better hit detection
    const closestX = Math.max(rect.x, Math.min(ballX, rect.x + rect.width));
    const closestY = Math.max(rect.y, Math.min(ballY, rect.y + rect.height));
    const distanceX = ballX - closestX;
    const distanceY = ballY - closestY;
    return (distanceX * distanceX + distanceY * distanceY) < (ballRadius * ballRadius);
  };

  // Check collision between two rectangles (for block-to-block)
  const checkRectRectCollision = (r1: { x: number; y: number; width: number; height: number }, r2: { x: number; y: number; width: number; height: number }) => {
    return r1.x < r2.x + r2.width &&
           r1.x + r1.width > r2.x &&
           r1.y < r2.y + r2.height &&
           r1.y + r1.height > r2.y;
  };

  // Refs to track current state for collision in physics loop
  const blocksRef = useRef<Block[]>([]);
  const gangMembersRef = useRef<GangMember[]>([]);

  // Keep refs in sync with state
  useEffect(() => {
    blocksRef.current = blocks;
  }, [blocks]);

  useEffect(() => {
    gangMembersRef.current = gangMembers;
  }, [gangMembers]);

  // Physics update loop - completely rewritten for proper collision
  const updatePhysics = useCallback(() => {
    // Get current ball position from ref
    const ball = cannonballRef.current;
    const currentBlocks = blocksRef.current;
    
    // Update cannonball position
    if (ball && ball.active) {
      let newX = ball.x + ball.velocityX;
      let newY = ball.y + ball.velocityY;
      let newVelX = ball.velocityX;
      let newVelY = ball.velocityY + GRAVITY;
      let stillActive = true;
      
      // Add trail point
      const newTrail = [...ball.trail, { x: ball.x, y: ball.y }].slice(-20);
      
      // Check collision with blocks BEFORE updating position
      let hitSomething = false;
      currentBlocks.forEach(block => {
        if (!block.destroyed && !hitSomething) {
          if (checkBallRectCollision(newX, newY, block)) {
            hitSomething = true;
            // Reduce ball velocity on impact but keep it going
            newVelX *= 0.6;
            newVelY *= 0.6;
          }
        }
      });
      
      // Check if out of bounds or hit ground
      if (newX > WORLD_WIDTH + 50 || newY > GROUND_Y || newX < -50) {
        stillActive = false;
      }
      
      // Update ball ref and state
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

    // Camera follows ball using ref
    if (ballPositionRef.current.active) {
      const ballX = ballPositionRef.current.x;
      const targetCameraX = Math.max(0, Math.min(WORLD_WIDTH - VIEWPORT_WIDTH, ballX - VIEWPORT_WIDTH / 3));
      setCameraX(prev => prev + (targetCameraX - prev) * 0.15);
    }

    // Update blocks physics - material-based behavior
    setBlocks(prev => {
      // First pass: handle cannonball collisions and basic physics
      const updatedBlocks = prev.map(block => {
        if (block.destroyed && block.y >= GROUND_Y + 100) return block;
        
        const ball = cannonballRef.current;
        const ballX = ballPositionRef.current.x;
        const ballY = ballPositionRef.current.y;
        const ballActive = ballPositionRef.current.active;
        
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
          
          // Cap maximum velocity
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
        
        for (const other of updatedBlocks) {
          if (other.id === block.id) continue;
          if (!other.falling && !other.destroyed) continue;
          
          const otherSpeed = Math.sqrt(other.velocityX * other.velocityX + other.velocityY * other.velocityY);
          const otherMomentum = otherSpeed * other.mass;
          
          if (!checkRectRectCollision(other, block)) continue;
          
          // VERY HIGH force thresholds
          const forceNeeded = block.type === 'stone' ? 100 : (block.type === 'ice' ? 40 : 60);
          
          if (otherMomentum > forceNeeded) {
            const pushDirection = other.x < block.x ? 1 : -1;
            return {
              ...block,
              destroyed: true,
              falling: true,
              velocityX: pushDirection * 0.5,
              velocityY: -0.5,
            };
          }
        }
        
        // DISABLED support check - blocks don't fall just because support is removed
        
        return block;
      });
    });

    // Update gang members physics - can be hit by blocks
    setGangMembers(prev => {
      const currentBlocksNow = blocksRef.current;
      
      return prev.map(member => {
        if (member.eliminated && member.y >= GROUND_Y + 100) return member;
        
        const ballX = ballPositionRef.current.x;
        const ballY = ballPositionRef.current.y;
        const ballActive = ballPositionRef.current.active;
        const ball = cannonballRef.current;
        
        // Direct cannonball hit
        if (!member.eliminated && ballActive && ball) {
          if (checkBallRectCollision(ballX, ballY, member)) {
            return {
              ...member,
              eliminated: true,
              falling: true,
              velocityX: ball.velocityX * 0.4,
              velocityY: -8,
            };
          }
        }
        
        // Falling blocks can knock members
        if (!member.eliminated && !member.falling) {
          for (const b of currentBlocksNow) {
            if (!b.falling && !b.destroyed) continue;
            if (!checkRectRectCollision(b, member)) continue;
            
            const blockMomentum = b.mass * Math.sqrt(b.velocityX * b.velocityX + b.velocityY * b.velocityY);
            const momentumThreshold = b.type === 'stone' ? 3 : (b.type === 'ice' ? 2 : 4);
            
            if (blockMomentum > momentumThreshold) {
              const pushDir = b.x < member.x ? 1 : -1;
              return {
                ...member,
                eliminated: true,
                falling: true,
                velocityX: pushDir * 3 + b.velocityX * 0.3,
                velocityY: -6,
              };
            }
          }
        }
        
        // Members fall if support is destroyed (only after structure hit)
        if (!member.falling && !member.eliminated && structureHitRef.current) {
          const supportBlock = currentBlocksNow.find(b => 
            !b.destroyed &&
            !b.falling &&
            member.x + member.width * 0.3 > b.x &&
            member.x + member.width * 0.7 < b.x + b.width &&
            Math.abs((member.y + member.height) - b.y) < 20
          );
          
          const isOnGround = member.y + member.height >= GROUND_Y - 25;
          
          if (!supportBlock && !isOnGround) {
            return {
              ...member,
              falling: true,
              velocityX: 0,
              velocityY: 0,
            };
          }
        }
        
        // Physics for falling members
        if (member.falling) {
          let newY = member.y + member.velocityY;
          let newVelY = member.velocityY + GRAVITY;
          
          if (newY > GROUND_Y - 20) {
            return { ...member, eliminated: true, y: GROUND_Y - 20, velocityY: 0, falling: false };
          }
          
          return {
            ...member,
            x: member.x + member.velocityX,
            y: newY,
            velocityX: member.velocityX * 0.98,
            velocityY: newVelY,
          };
        }
        
        return member;
      });
    });

    // Check if we should continue animating
    const ballActive = ballPositionRef.current.active;
    const hasAnimatingBlocks = blocksRef.current.some(b => b.falling && (Math.abs(b.velocityY) > 0.5 || Math.abs(b.velocityX) > 0.5));
    const hasAnimatingMembers = gangMembersRef.current.some(m => m.falling);
    
    if (ballActive || hasAnimatingBlocks || hasAnimatingMembers) {
      animationRef.current = requestAnimationFrame(updatePhysics);
    } else {
      animationRef.current = null;
    }
  }, []);

  // Animation loop cleanup only - loop is started by fireCannon
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, []);

  // Check win/lose after ball stops
  useEffect(() => {
    if (cannonball && !cannonball.active && firing) {
      // Wait for physics to settle
      setTimeout(() => {
        setFiring(false);
        setShowTrajectory(true);
        
        // Pan camera back to cannon
        Animated.timing(cameraAnim, {
          toValue: 0,
          duration: 800,
          useNativeDriver: false,
        }).start();
        setCameraX(0);
        
        const remainingMembers = gangMembers.filter(m => !m.eliminated).length;
        
        if (remainingMembers === 0) {
          setWon(true);
          setGameOver(true);
          handleGameComplete(true);
        } else if (shotsRemaining <= 1) {
          setWon(false);
          setGameOver(true);
          handleGameComplete(false);
        }
      }, 1500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cannonball?.active, firing]);

  const handleGameComplete = async (didWin: boolean) => {
    if (!gameData?.id) return;
    
    const eliminated = gangMembers.filter(m => m.eliminated).length;
    
    try {
      const result = await completeCastleGame(gameData.id, eliminated, didWin);
      setResults(result);
      setShowResults(true);
      
      if (didWin && result.rewards) {
        showGameToast(`🏰 Victory! +$${result.rewards.cash} +${result.rewards.xp}XP`, 'success');
      }
    } catch {
      setShowResults(true);
      setResults({ won: didWin, message: didWin ? 'Victory!' : 'Defeated!' });
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
    
    // Update refs immediately before setting state
    cannonballRef.current = newBall;
    ballPositionRef.current = { x: newBall.x, y: newBall.y, active: true };
    
    setCannonball(newBall);
    
    // Start animation loop immediately
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    animationRef.current = requestAnimationFrame(updatePhysics);
  };

  const handleClose = () => {
    router.back();
  };

  const trajectoryPoints = showTrajectory ? getTrajectoryPoints() : [];

  const renderWorld = () => (
    <View style={[styles.world, { transform: [{ translateX: -cameraX }] }]}>
      {/* Sky gradient layers */}
      <View style={styles.skyGradient1} />
      <View style={styles.skyGradient2} />
      
      {/* Clouds */}
      <View style={[styles.cloud, { left: 200, top: 40 }]} />
      <View style={[styles.cloud, { left: 500, top: 80 }]} />
      <View style={[styles.cloud, { left: 800, top: 30 }]} />
      <View style={[styles.cloud, { left: 1000, top: 60 }]} />
      
      {/* Ground */}
      <View style={[styles.ground, { top: GROUND_Y }]}>
        <View style={styles.groundGrass} />
        <View style={styles.groundDirt} />
      </View>
      
      {/* Trajectory preview */}
      {showTrajectory && trajectoryPoints.map((point, i) => (
        <View
          key={`traj-${i}`}
          style={[
            styles.trajectoryDot,
            {
              left: point.x - 4,
              top: point.y - 4,
              opacity: 1 - i / trajectoryPoints.length,
            },
          ]}
        />
      ))}
      
      {/* Cannon */}
      <View style={styles.cannonPlatform}>
        <View style={styles.cannonWheelLeft} />
        <View style={styles.cannonWheelRight} />
        <View style={styles.cannonBody}>
          <View
            style={[
              styles.cannonBarrel,
              { transform: [{ rotate: `-${angle}deg` }] },
            ]}
          >
            <View style={styles.cannonBarrelEnd} />
          </View>
        </View>
      </View>
      
      {/* Cannonball trail */}
      {cannonball?.trail.map((point, i) => (
        <View
          key={`trail-${i}`}
          style={[
            styles.trailDot,
            {
              left: point.x - 5,
              top: point.y - 5,
              opacity: i / cannonball.trail.length,
              transform: [{ scale: 0.5 + (i / cannonball.trail.length) * 0.5 }],
            },
          ]}
        />
      ))}
      
      {/* Cannonball */}
      {cannonball?.active && (
        <View
          style={[
            styles.cannonball,
            {
              left: cannonball.x - 15,
              top: cannonball.y - 15,
            },
          ]}
        >
          <View style={styles.cannonballHighlight} />
        </View>
      )}
      
      {/* Fort blocks - Angry Birds style */}
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
      
      {/* Green Pigs - Angry Birds style */}
      {gangMembers.map(member => {
        if (member.y > GROUND_Y + 100) return null;
        
        return (
          <View
            key={member.id}
            style={[
              styles.pig,
              {
                left: member.x,
                top: member.y,
                opacity: member.eliminated ? 0.3 : 1,
              },
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
              {member.eliminated && (
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
  );

  const renderResultsModal = () => (
    <Modal visible={showResults} transparent animationType="fade">
      <View style={styles.resultsOverlay}>
        <View style={styles.resultsContainer}>
          <Text style={[styles.resultsTitle, { color: won ? '#4ade80' : '#ef4444' }]}>
            {won ? '🏰 VICTORY!' : '💥 DEFEATED!'}
          </Text>
          
          <Text style={styles.resultsSubtitle}>
            {results?.castle_name || gameData?.castle_name}
          </Text>
          
          <View style={styles.resultsStat}>
            <Text style={styles.resultsStatLabel}>Gang Members Eliminated:</Text>
            <Text style={styles.resultsStatValue}>
              {gangMembers.filter(m => m.eliminated).length} / {gangMembers.length}
            </Text>
          </View>
          
          {won && results?.rewards && (
            <View style={styles.rewardsContainer}>
              <Text style={styles.rewardsTitle}>REWARDS</Text>
              <View style={styles.rewardRow}>
                <Text style={styles.rewardIcon}>💰</Text>
                <Text style={styles.rewardText}>+${results.rewards.cash}</Text>
              </View>
              <View style={styles.rewardRow}>
                <Text style={styles.rewardIcon}>⭐</Text>
                <Text style={styles.rewardText}>+{results.rewards.xp} XP</Text>
              </View>
              <View style={styles.rewardRow}>
                <Text style={styles.rewardIcon}>👑</Text>
                <Text style={styles.rewardText}>+{results.rewards.reputation} Rep</Text>
              </View>
            </View>
          )}
          
          {!won && (
            <Text style={styles.tryAgainText}>
              The gang held their ground! Come back in 30 minutes.
            </Text>
          )}
          
          <TouchableOpacity style={styles.resultsButton} onPress={handleClose}>
            <Text style={styles.resultsButtonText}>
              {won ? 'COLLECT REWARDS' : 'RETREAT'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  if (!gameData) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>Game data not found</Text>
        <TouchableOpacity onPress={handleClose}>
          <Text style={styles.backText}>Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.closeButton} onPress={handleClose}>
          <Ionicons name="close" size={28} color="#fff" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>{gameData.castle_name}</Text>
          <Text style={styles.headerSubtitle}>
            {'⚔️'.repeat(gameData.difficulty)} Level {gameData.difficulty}
          </Text>
        </View>
        <View style={styles.shotsContainer}>
          <Text style={styles.shotsLabel}>SHOTS</Text>
          <View style={styles.shotsIndicator}>
            {[1, 2, 3].map(i => (
              <View
                key={i}
                style={[
                  styles.shotDot,
                  { backgroundColor: i <= shotsRemaining ? '#FFD700' : '#333' },
                ]}
              />
            ))}
          </View>
        </View>
      </View>

      {/* Game Viewport */}
      <View style={styles.viewport} {...panResponder.panHandlers}>
        {renderWorld()}
        
        {/* Aiming HUD */}
        {!firing && !gameOver && (
          <View style={styles.aimHUD}>
            <Text style={styles.aimText}>Angle: {Math.round(angle)}°</Text>
            <Text style={styles.aimText}>Power: {Math.round(power)}%</Text>
          </View>
        )}
      </View>

      {/* Bottom Controls */}
      <View style={styles.controls}>
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Ionicons name="skull-outline" size={20} color="#e74c3c" />
            <Text style={styles.statValue}>
              {gangMembers.filter(m => !m.eliminated).length}
            </Text>
            <Text style={styles.statLabel}>LEFT</Text>
          </View>
          <View style={styles.statBox}>
            <Ionicons name="checkmark-circle-outline" size={20} color="#4ade80" />
            <Text style={[styles.statValue, { color: '#4ade80' }]}>
              {gangMembers.filter(m => m.eliminated).length}
            </Text>
            <Text style={styles.statLabel}>DOWN</Text>
          </View>
        </View>
        
        <TouchableOpacity
          style={[
            styles.fireButton,
            (firing || shotsRemaining <= 0 || gameOver) && styles.fireButtonDisabled,
          ]}
          onPress={fireCannon}
          disabled={firing || shotsRemaining <= 0 || gameOver}
        >
          <Text style={styles.fireButtonText}>
            {firing ? '💨 FIRING...' : gameOver ? (won ? '🏆 VICTORY' : '💀 GAME OVER') : '🔥 FIRE!'}
          </Text>
        </TouchableOpacity>
        
        {!firing && !gameOver && (
          <Text style={styles.hintText}>☝️ Drag to aim • Release & tap FIRE</Text>
        )}
      </View>

      {renderResultsModal()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#0f0f1a',
    borderBottomWidth: 2,
    borderBottomColor: '#8B4513',
  },
  closeButton: {
    padding: 6,
  },
  headerCenter: {
    alignItems: 'center',
    flex: 1,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#CD853F',
  },
  headerSubtitle: {
    fontSize: 11,
    color: '#888',
    marginTop: 2,
  },
  shotsContainer: {
    alignItems: 'center',
  },
  shotsLabel: {
    fontSize: 9,
    color: '#666',
    fontWeight: '700',
  },
  shotsIndicator: {
    flexDirection: 'row',
    gap: 4,
    marginTop: 4,
  },
  shotDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: '#FFD700',
  },
  viewport: {
    width: VIEWPORT_WIDTH,
    height: VIEWPORT_HEIGHT,
    overflow: 'hidden',
    backgroundColor: '#87CEEB',
  },
  world: {
    width: WORLD_WIDTH,
    height: WORLD_HEIGHT,
    position: 'relative',
  },
  skyGradient1: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 200,
    backgroundColor: '#4a90d9',
  },
  skyGradient2: {
    position: 'absolute',
    top: 200,
    left: 0,
    right: 0,
    height: 200,
    backgroundColor: '#6ba3e3',
  },
  cloud: {
    position: 'absolute',
    width: 80,
    height: 35,
    backgroundColor: 'rgba(255,255,255,0.8)',
    borderRadius: 20,
  },
  ground: {
    position: 'absolute',
    left: 0,
    width: WORLD_WIDTH,
    height: 100,
  },
  groundGrass: {
    height: 15,
    backgroundColor: '#4a7c23',
  },
  groundDirt: {
    height: 85,
    backgroundColor: '#5c3d2e',
  },
  cannonPlatform: {
    position: 'absolute',
    left: 50,
    bottom: 60,
    width: 100,
    height: 80,
  },
  cannonBody: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    width: 60,
    height: 50,
    backgroundColor: '#2a2a2a',
    borderRadius: 10,
    borderWidth: 3,
    borderColor: '#444',
  },
  cannonBarrel: {
    position: 'absolute',
    bottom: 20,
    left: 35,
    width: 70,
    height: 25,
    backgroundColor: '#3a3a3a',
    borderRadius: 5,
    transformOrigin: 'left center',
  },
  cannonBarrelEnd: {
    position: 'absolute',
    right: -5,
    top: 2,
    width: 10,
    height: 21,
    backgroundColor: '#222',
    borderRadius: 3,
  },
  cannonWheelLeft: {
    position: 'absolute',
    bottom: 0,
    left: 15,
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#4a3a2a',
    borderWidth: 4,
    borderColor: '#2a2a2a',
  },
  cannonWheelRight: {
    position: 'absolute',
    bottom: 0,
    left: 55,
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#4a3a2a',
    borderWidth: 4,
    borderColor: '#2a2a2a',
  },
  trajectoryDot: {
    position: 'absolute',
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FFD700',
  },
  trailDot: {
    position: 'absolute',
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#666',
  },
  cannonball: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#1a1a1a',
    borderWidth: 3,
    borderColor: '#333',
  },
  cannonballHighlight: {
    position: 'absolute',
    top: 5,
    left: 5,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  block: {
    position: 'absolute',
    backgroundColor: '#8B4513',
    borderRadius: 4,
    borderWidth: 3,
    borderColor: '#5D3A1A',
  },
  blockInner: {
    flex: 1,
    overflow: 'hidden',
  },
  blockHighlight: {
    position: 'absolute',
    top: 2,
    left: 2,
    right: 10,
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 2,
  },
  blockShadow: {
    position: 'absolute',
    bottom: 2,
    left: 10,
    right: 2,
    height: 8,
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 2,
  },
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
  aimHUD: {
    position: 'absolute',
    top: 10,
    left: 10,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  aimText: {
    color: '#FFD700',
    fontSize: 12,
    fontWeight: '700',
  },
  controls: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    padding: 12,
    justifyContent: 'space-between',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 30,
  },
  statBox: {
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#333',
    flexDirection: 'row',
    gap: 8,
  },
  statValue: {
    fontSize: 20,
    fontWeight: '900',
    color: '#fff',
  },
  statLabel: {
    fontSize: 10,
    color: '#666',
    fontWeight: '600',
  },
  fireButton: {
    backgroundColor: '#e74c3c',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#c0392b',
  },
  fireButtonDisabled: {
    backgroundColor: '#4a2020',
    borderColor: '#3a1a1a',
  },
  fireButtonText: {
    fontSize: 20,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 2,
  },
  hintText: {
    textAlign: 'center',
    color: '#666',
    fontSize: 11,
    marginTop: 8,
  },
  resultsOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  resultsContainer: {
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#8B4513',
  },
  resultsTitle: {
    fontSize: 32,
    fontWeight: '900',
    marginBottom: 8,
  },
  resultsSubtitle: {
    fontSize: 16,
    color: '#CD853F',
    marginBottom: 20,
  },
  resultsStat: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  resultsStatLabel: {
    fontSize: 14,
    color: '#888',
  },
  resultsStatValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#fff',
  },
  rewardsContainer: {
    width: '100%',
    backgroundColor: '#0f0f1a',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
  },
  rewardsTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#FFD700',
    textAlign: 'center',
    marginBottom: 12,
  },
  rewardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 12,
  },
  rewardIcon: {
    fontSize: 20,
  },
  rewardText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4ade80',
  },
  tryAgainText: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    marginTop: 16,
  },
  resultsButton: {
    backgroundColor: '#8B4513',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 12,
    marginTop: 20,
    borderWidth: 2,
    borderColor: '#CD853F',
  },
  resultsButtonText: {
    fontSize: 16,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: 1,
  },
  errorText: {
    color: '#fff',
    fontSize: 18,
    textAlign: 'center',
    marginTop: 100,
  },
  backText: {
    color: '#f59e0b',
    fontSize: 16,
    textAlign: 'center',
    marginTop: 20,
  },
});
