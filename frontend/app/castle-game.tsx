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
import { useGameStore } from '../stores/gameStore';
import { showGameToast } from '../components/GameToast';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
// Force mobile-like dimensions for consistent game layout
const GAME_WIDTH = 390; // Fixed width for game consistency
const GAME_HEIGHT = 450; // Fixed height for game area
const GROUND_Y = GAME_HEIGHT - 50;
const GRAVITY = 0.5;
const INITIAL_VELOCITY = 18;

interface Block {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  destroyed: boolean;
  velocityX?: number;
  velocityY?: number;
  falling?: boolean;
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
  velocityX?: number;
  velocityY?: number;
  falling?: boolean;
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
}

export default function CastleMinigameScreen() {
  const params = useLocalSearchParams();
  const gameData = params.gameData ? JSON.parse(params.gameData as string) : null;
  
  const { playerId: _playerId } = useGameStore();
  const [angle, setAngle] = useState(45);
  const [shotsRemaining, setShotsRemaining] = useState(3);
  const [cannonball, setCannonball] = useState<Cannonball | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [gangMembers, setGangMembers] = useState<GangMember[]>([]);
  const [gameOver, setGameOver] = useState(false);
  const [won, setWon] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [firing, setFiring] = useState(false);
  const animationRef = useRef<number | null>(null);
  const angleAnim = useRef(new Animated.Value(45)).current;
  
  // Initialize game state from gameData
  useEffect(() => {
    if (gameData?.layout) {
      const layout: GameLayout = gameData.layout;
      
      // Scale positions to fit fixed game area
      const scaleX = (x: number) => {
        return 80 + ((x - 300) / 600) * (GAME_WIDTH - 100);
      };
      const scaleY = (y: number) => {
        return (y / 400) * GROUND_Y;
      };
      const scaleW = (w: number) => Math.max(w * 0.6, 25);
      const scaleH = (h: number) => Math.max(h * 0.6, 25);
      
      // Initialize blocks from all forts
      const allBlocks: Block[] = [];
      layout.forts.forEach(fort => {
        fort.blocks.forEach(block => {
          allBlocks.push({
            ...block,
            x: scaleX(block.x),
            y: scaleY(block.y),
            width: scaleW(block.width),
            height: scaleH(block.height),
            velocityX: 0,
            velocityY: 0,
            falling: false,
          });
        });
      });
      setBlocks(allBlocks);
      
      // Initialize gang members
      const members: GangMember[] = layout.gang_members.map(m => ({
        ...m,
        x: scaleX(m.x),
        y: scaleY(m.y),
        width: scaleW(m.width),
        height: scaleH(m.height),
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
        // Map vertical drag to angle (0-90 degrees)
        const newAngle = Math.max(10, Math.min(80, 45 - gestureState.dy / 5));
        setAngle(newAngle);
        angleAnim.setValue(newAngle);
      },
    })
  ).current;

  // Check collision between cannonball and a rectangle
  const checkCollision = (ball: Cannonball, rect: { x: number; y: number; width: number; height: number }) => {
    const ballRadius = 12;
    const closestX = Math.max(rect.x, Math.min(ball.x, rect.x + rect.width));
    const closestY = Math.max(rect.y, Math.min(ball.y, rect.y + rect.height));
    const distanceX = ball.x - closestX;
    const distanceY = ball.y - closestY;
    return (distanceX * distanceX + distanceY * distanceY) < (ballRadius * ballRadius);
  };

  // Physics update loop
  const updatePhysics = useCallback(() => {
    if (!cannonball?.active) return;

    setCannonball(prev => {
      if (!prev || !prev.active) return prev;
      
      let newX = prev.x + prev.velocityX;
      let newY = prev.y + prev.velocityY;
      let newVelY = prev.velocityY + GRAVITY;
      
      // Check if out of bounds
      if (newX > GAME_WIDTH + 50 || newY > GROUND_Y + 50 || newX < -50) {
        return { ...prev, active: false };
      }
      
      return {
        ...prev,
        x: newX,
        y: newY,
        velocityY: newVelY,
      };
    });

    // Check collisions with blocks
    setBlocks(prev => {
      if (!cannonball) return prev;
      
      return prev.map(block => {
        if (block.destroyed) return block;
        
        if (checkCollision(cannonball, block)) {
          // Block is hit - destroy it and apply physics
          return {
            ...block,
            destroyed: true,
            falling: true,
            velocityX: (Math.random() - 0.5) * 8,
            velocityY: -5,
          };
        }
        
        // Apply gravity to falling blocks
        if (block.falling) {
          const newY = block.y + (block.velocityY || 0);
          const newVelY = (block.velocityY || 0) + GRAVITY * 0.5;
          
          if (newY > GROUND_Y) {
            return { ...block, y: GROUND_Y, velocityY: 0, falling: false };
          }
          
          return {
            ...block,
            x: block.x + (block.velocityX || 0),
            y: newY,
            velocityY: newVelY,
            velocityX: (block.velocityX || 0) * 0.98,
          };
        }
        
        return block;
      });
    });

    // Check collisions with gang members and apply physics
    setGangMembers(prev => {
      if (!cannonball) return prev;
      
      return prev.map(member => {
        if (member.eliminated) return member;
        
        // Direct hit by cannonball
        if (checkCollision(cannonball, member)) {
          return {
            ...member,
            eliminated: true,
            falling: true,
            velocityX: cannonball.velocityX * 0.3,
            velocityY: -8,
          };
        }
        
        // Check if standing block is destroyed
        const standingBlock = blocks.find(b => 
          !b.destroyed &&
          member.x + member.width > b.x &&
          member.x < b.x + b.width &&
          Math.abs((member.y + member.height) - b.y) < 10
        );
        
        if (!standingBlock && !member.falling && member.y < GROUND_Y - 20) {
          // No support - start falling
          return {
            ...member,
            falling: true,
            velocityX: (Math.random() - 0.5) * 4,
            velocityY: 0,
          };
        }
        
        // Apply gravity to falling members
        if (member.falling) {
          const newY = member.y + (member.velocityY || 0);
          const newVelY = (member.velocityY || 0) + GRAVITY * 0.7;
          
          // Eliminated if falls to ground
          if (newY > GROUND_Y - 10) {
            return { ...member, eliminated: true, y: GROUND_Y, velocityY: 0 };
          }
          
          return {
            ...member,
            x: member.x + (member.velocityX || 0),
            y: newY,
            velocityY: newVelY,
            velocityX: (member.velocityX || 0) * 0.98,
          };
        }
        
        return member;
      });
    });

    animationRef.current = requestAnimationFrame(updatePhysics);
  }, [cannonball, blocks]);

  // Start/stop animation loop
  useEffect(() => {
    if (cannonball?.active) {
      animationRef.current = requestAnimationFrame(updatePhysics);
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [cannonball?.active, updatePhysics]);

  // Check for cannonball stopping
  useEffect(() => {
    if (cannonball && !cannonball.active && firing) {
      setFiring(false);
      
      // Check win condition
      const remainingMembers = gangMembers.filter(m => !m.eliminated).length;
      
      if (remainingMembers === 0) {
        // Won!
        setWon(true);
        setGameOver(true);
        handleGameComplete(true);
      } else if (shotsRemaining <= 1) {
        // Out of shots - lost
        setWon(false);
        setGameOver(true);
        handleGameComplete(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cannonball?.active, firing, gangMembers, shotsRemaining]);

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
    } catch (error: any) {
      console.error('Failed to complete game:', error);
      setShowResults(true);
      setResults({ won: didWin, message: didWin ? 'Victory!' : 'Defeated!' });
    }
  };

  const fireCannon = () => {
    if (firing || shotsRemaining <= 0 || gameOver) return;
    
    setFiring(true);
    setShotsRemaining(prev => prev - 1);
    
    const angleRad = (angle * Math.PI) / 180;
    const velocityX = Math.cos(angleRad) * INITIAL_VELOCITY;
    const velocityY = -Math.sin(angleRad) * INITIAL_VELOCITY;
    
    setCannonball({
      x: 80,
      y: GROUND_Y - 60 - Math.sin(angleRad) * 40,
      velocityX,
      velocityY,
      active: true,
    });
  };

  const handleClose = () => {
    router.back();
  };

  const renderCannon = () => {
    return (
      <View style={styles.cannonContainer}>
        {/* Cannon base */}
        <View style={styles.cannonBase} />
        {/* Cannon barrel */}
        <View
          style={[
            styles.cannonBarrel,
            {
              transform: [{ rotate: `-${angle}deg` }],
            },
          ]}
        />
        {/* Angle indicator */}
        <Text style={styles.angleText}>{Math.round(angle)}°</Text>
      </View>
    );
  };

  const renderBlocks = () => {
    return blocks.map(block => {
      if (block.destroyed && block.y >= GROUND_Y) return null;
      
      return (
        <View
          key={block.id}
          style={[
            styles.block,
            {
              left: block.x,
              top: block.y,
              width: Math.max(block.width, 20),
              height: Math.max(block.height, 20),
              opacity: block.destroyed ? 0.5 : 1,
            },
          ]}
        />
      );
    });
  };

  const renderGangMembers = () => {
    return gangMembers.map(member => {
      if (member.eliminated && member.y >= GROUND_Y) return null;
      
      return (
        <View
          key={member.id}
          style={[
            styles.gangMember,
            {
              left: member.x,
              top: member.y,
              width: Math.max(member.width, 20),
              height: Math.max(member.height, 20),
              opacity: member.eliminated ? 0.3 : 1,
            },
          ]}
        >
          <Text style={styles.gangMemberEmoji}>👤</Text>
        </View>
      );
    });
  };

  const renderCannonball = () => {
    if (!cannonball?.active) return null;
    
    return (
      <View
        style={[
          styles.cannonball,
          {
            left: cannonball.x - 12,
            top: cannonball.y - 12,
          },
        ]}
      />
    );
  };

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
          <Text style={styles.headerSubtitle}>Difficulty: {'⚔️'.repeat(gameData.difficulty)}</Text>
        </View>
        <View style={styles.shotsContainer}>
          <Text style={styles.shotsLabel}>SHOTS</Text>
          <Text style={styles.shotsCount}>{shotsRemaining}/3</Text>
        </View>
      </View>

      {/* Game Area */}
      <View style={styles.gameArea} {...panResponder.panHandlers}>
        {/* Sky gradient */}
        <View style={styles.sky} />
        
        {/* Ground */}
        <View style={[styles.ground, { top: GROUND_Y }]} />
        
        {/* Cannon */}
        {renderCannon()}
        
        {/* Fort blocks */}
        {renderBlocks()}
        
        {/* Gang members */}
        {renderGangMembers()}
        
        {/* Cannonball */}
        {renderCannonball()}
        
        {/* Aim guide */}
        {!firing && !gameOver && (
          <View style={styles.aimGuide}>
            <Text style={styles.aimGuideText}>☝️ Drag up/down to aim</Text>
          </View>
        )}
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>TARGETS</Text>
            <Text style={styles.statValue}>
              {gangMembers.filter(m => !m.eliminated).length} left
            </Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>ELIMINATED</Text>
            <Text style={[styles.statValue, { color: '#4ade80' }]}>
              {gangMembers.filter(m => m.eliminated).length}
            </Text>
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
      </View>

      {/* Results Modal */}
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
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#0f0f1a',
    borderBottomWidth: 2,
    borderBottomColor: '#8B4513',
  },
  closeButton: {
    padding: 8,
  },
  headerCenter: {
    alignItems: 'center',
    flex: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#CD853F',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  shotsContainer: {
    alignItems: 'center',
    backgroundColor: '#2a1a0a',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#8B4513',
  },
  shotsLabel: {
    fontSize: 10,
    color: '#888',
    fontWeight: '600',
  },
  shotsCount: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFD700',
  },
  gameArea: {
    width: GAME_WIDTH,
    height: GAME_HEIGHT,
    backgroundColor: '#87CEEB',
    position: 'relative',
    overflow: 'hidden',
  },
  sky: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 100,
    backgroundColor: '#4a90d9',
  },
  ground: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 60,
    backgroundColor: '#3d2817',
    borderTopWidth: 4,
    borderTopColor: '#5c3d2e',
  },
  cannonContainer: {
    position: 'absolute',
    left: 20,
    bottom: 80,
    alignItems: 'center',
  },
  cannonBase: {
    width: 60,
    height: 40,
    backgroundColor: '#4a4a4a',
    borderRadius: 8,
    borderWidth: 3,
    borderColor: '#2a2a2a',
  },
  cannonBarrel: {
    position: 'absolute',
    bottom: 25,
    left: 30,
    width: 50,
    height: 20,
    backgroundColor: '#333',
    borderRadius: 4,
    borderWidth: 2,
    borderColor: '#222',
    transformOrigin: 'left center',
  },
  angleText: {
    position: 'absolute',
    bottom: -25,
    fontSize: 14,
    fontWeight: '700',
    color: '#FFD700',
  },
  block: {
    position: 'absolute',
    backgroundColor: '#D2691E',
    borderWidth: 3,
    borderColor: '#8B4513',
    borderRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 3,
    elevation: 5,
  },
  gangMember: {
    position: 'absolute',
    backgroundColor: '#FF4444',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#CC0000',
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 3,
    elevation: 6,
  },
  gangMemberEmoji: {
    fontSize: 16,
  },
  cannonball: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#333',
    borderWidth: 3,
    borderColor: '#555',
  },
  aimGuide: {
    position: 'absolute',
    top: 20,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  aimGuideText: {
    fontSize: 14,
    color: '#fff',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  controls: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    padding: 16,
    justifyContent: 'space-between',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
  },
  statBox: {
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#333',
  },
  statLabel: {
    fontSize: 11,
    color: '#666',
    fontWeight: '600',
  },
  statValue: {
    fontSize: 22,
    fontWeight: '900',
    color: '#fff',
    marginTop: 4,
  },
  fireButton: {
    backgroundColor: '#e74c3c',
    paddingVertical: 18,
    borderRadius: 16,
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
    fontSize: 22,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 2,
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
