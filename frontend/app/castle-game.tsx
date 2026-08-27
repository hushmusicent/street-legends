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
  
  // Initialize game state from gameData
  useEffect(() => {
    if (gameData?.layout) {
      const layout: GameLayout = gameData.layout;
      
      // Scale server coordinates to world coordinates
      // Server uses x: 400-900, y: 0-400
      // World uses x: 0-1200, y: 0-500
      const scaleX = (x: number) => 300 + ((x - 300) / 600) * 800;
      const scaleY = (y: number) => (y / 400) * (GROUND_Y - 50);
      
      // Initialize blocks
      const allBlocks: Block[] = [];
      layout.forts.forEach(fort => {
        fort.blocks.forEach(block => {
          allBlocks.push({
            ...block,
            x: scaleX(block.x),
            y: scaleY(block.y),
            width: 45,
            height: 45,
            velocityX: 0,
            velocityY: 0,
            falling: false,
            rotation: 0,
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

  // Check collision
  const checkCollision = (ball: Cannonball, rect: { x: number; y: number; width: number; height: number }) => {
    const ballRadius = 15;
    const closestX = Math.max(rect.x, Math.min(ball.x, rect.x + rect.width));
    const closestY = Math.max(rect.y, Math.min(ball.y, rect.y + rect.height));
    const distanceX = ball.x - closestX;
    const distanceY = ball.y - closestY;
    return (distanceX * distanceX + distanceY * distanceY) < (ballRadius * ballRadius);
  };

  // Physics update loop
  const updatePhysics = useCallback(() => {
    let ballActive = false;
    let ballX = 0;

    setCannonball(prev => {
      if (!prev || !prev.active) return prev;
      
      let newX = prev.x + prev.velocityX;
      let newY = prev.y + prev.velocityY;
      let newVelY = prev.velocityY + GRAVITY;
      
      // Add trail point
      const newTrail = [...prev.trail, { x: prev.x, y: prev.y }].slice(-20);
      
      // Check if out of bounds or hit ground
      if (newX > WORLD_WIDTH + 50 || newY > GROUND_Y || newX < -50) {
        return { ...prev, active: false, trail: newTrail };
      }
      
      ballActive = true;
      ballX = newX;
      
      return {
        ...prev,
        x: newX,
        y: newY,
        velocityY: newVelY,
        trail: newTrail,
      };
    });

    // Camera follows ball
    if (ballActive) {
      const targetCameraX = Math.max(0, Math.min(WORLD_WIDTH - VIEWPORT_WIDTH, ballX - VIEWPORT_WIDTH / 3));
      setCameraX(prev => prev + (targetCameraX - prev) * 0.1);
    }

    // Update blocks physics
    setBlocks(prev => {
      return prev.map(block => {
        if (block.destroyed && block.y >= GROUND_Y + 100) return block;
        
        // Check cannonball collision
        if (!block.destroyed && cannonball?.active && checkCollision(cannonball, block)) {
          return {
            ...block,
            destroyed: true,
            falling: true,
            velocityX: cannonball.velocityX * 0.4 + (Math.random() - 0.5) * 5,
            velocityY: -8 - Math.random() * 5,
          };
        }
        
        // Physics for falling blocks
        if (block.falling || block.destroyed) {
          let newY = block.y + block.velocityY;
          let newVelY = block.velocityY + GRAVITY * 0.8;
          let newVelX = block.velocityX * 0.98;
          let newRotation = block.rotation + block.velocityX * 2;
          
          // Hit ground
          if (newY > GROUND_Y - 10) {
            newY = GROUND_Y - 10;
            newVelY = -newVelY * 0.3;
            newVelX *= 0.7;
            if (Math.abs(newVelY) < 1) {
              newVelY = 0;
            }
          }
          
          return {
            ...block,
            x: block.x + newVelX,
            y: newY,
            velocityX: newVelX,
            velocityY: newVelY,
            rotation: newRotation,
          };
        }
        
        return block;
      });
    });

    // Update gang members physics
    setGangMembers(prev => {
      return prev.map(member => {
        if (member.eliminated && member.y >= GROUND_Y + 100) return member;
        
        // Direct hit by cannonball
        if (!member.eliminated && cannonball?.active && checkCollision(cannonball, member)) {
          return {
            ...member,
            eliminated: true,
            falling: true,
            velocityX: cannonball.velocityX * 0.5 + (Math.random() - 0.5) * 3,
            velocityY: -12,
          };
        }
        
        // Check if support block is destroyed
        if (!member.falling && !member.eliminated) {
          const hasSupport = blocks.some(b => 
            !b.destroyed &&
            !b.falling &&
            member.x + member.width > b.x &&
            member.x < b.x + b.width &&
            Math.abs((member.y + member.height) - b.y) < 15
          );
          
          if (!hasSupport) {
            return {
              ...member,
              falling: true,
              velocityX: (Math.random() - 0.5) * 3,
              velocityY: 0,
            };
          }
        }
        
        // Physics for falling members
        if (member.falling) {
          let newY = member.y + member.velocityY;
          let newVelY = member.velocityY + GRAVITY;
          
          // Hit ground = eliminated
          if (newY > GROUND_Y - 20) {
            return { ...member, eliminated: true, y: GROUND_Y - 20, velocityY: 0 };
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

    animationRef.current = requestAnimationFrame(updatePhysics);
  }, [cannonball, blocks]);

  // Animation loop control
  useEffect(() => {
    if (cannonball?.active || blocks.some(b => b.falling) || gangMembers.some(m => m.falling)) {
      animationRef.current = requestAnimationFrame(updatePhysics);
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [cannonball?.active, updatePhysics]);

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
    } catch (error) {
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
    
    setCannonball({
      x: 120,
      y: GROUND_Y - 80,
      velocityX: Math.cos(angleRad) * velocity,
      velocityY: -Math.sin(angleRad) * velocity,
      active: true,
      trail: [],
    });
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
      
      {/* Fort blocks */}
      {blocks.map(block => {
        if (block.y > GROUND_Y + 100) return null;
        
        return (
          <View
            key={block.id}
            style={[
              styles.block,
              {
                left: block.x,
                top: block.y,
                width: block.width,
                height: block.height,
                opacity: block.destroyed ? 0.7 : 1,
                transform: [{ rotate: `${block.rotation}deg` }],
              },
            ]}
          >
            <View style={styles.blockInner}>
              <View style={styles.blockHighlight} />
              <View style={styles.blockShadow} />
            </View>
          </View>
        );
      })}
      
      {/* Gang members */}
      {gangMembers.map(member => {
        if (member.y > GROUND_Y + 100) return null;
        
        return (
          <View
            key={member.id}
            style={[
              styles.gangMember,
              {
                left: member.x,
                top: member.y,
                opacity: member.eliminated ? 0.4 : 1,
              },
            ]}
          >
            <View style={styles.gangMemberHead}>
              <View style={styles.gangMemberEye} />
              <View style={[styles.gangMemberEye, { left: 18 }]} />
              {!member.eliminated && <View style={styles.gangMemberMouth} />}
              {member.eliminated && <View style={styles.gangMemberMouthDead} />}
            </View>
            <View style={styles.gangMemberBody} />
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
  gangMember: {
    position: 'absolute',
    width: 35,
    height: 50,
    alignItems: 'center',
  },
  gangMemberHead: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#ffcc99',
    borderWidth: 2,
    borderColor: '#cc9966',
  },
  gangMemberEye: {
    position: 'absolute',
    top: 10,
    left: 6,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#333',
  },
  gangMemberMouth: {
    position: 'absolute',
    bottom: 6,
    left: 10,
    width: 10,
    height: 4,
    backgroundColor: '#c0392b',
    borderRadius: 2,
  },
  gangMemberMouthDead: {
    position: 'absolute',
    bottom: 8,
    left: 8,
    width: 14,
    height: 2,
    backgroundColor: '#666',
  },
  gangMemberBody: {
    width: 25,
    height: 20,
    backgroundColor: '#e74c3c',
    borderRadius: 4,
    marginTop: -2,
    borderWidth: 2,
    borderColor: '#c0392b',
  },
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
