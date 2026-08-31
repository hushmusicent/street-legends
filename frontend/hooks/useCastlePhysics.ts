/**
 * Shared Castle Mini-game Physics Engine
 * Used by both castle-game.tsx (map version) and castle-levels.tsx (options panel version)
 * This ensures identical physics behavior across both entry points.
 * 
 * Supports advanced block types: TNT (explosives), Boulders (rolling), Wheels, Triangles
 */

// Import level configurations
import { getLevelConfig } from './castleLevelsData';

// Physics constants
export const PHYSICS_CONSTANTS = {
  WORLD_WIDTH: 1200,
  WORLD_HEIGHT: 500,
  GROUND_Y: 440, // WORLD_HEIGHT - 60
  GRAVITY: 0.4,
  INITIAL_VELOCITY: 22,
  BALL_RADIUS: 12,
  TNT_EXPLOSION_RADIUS: 120, // Radius of TNT explosion
  TNT_EXPLOSION_FORCE: 15, // Force applied to nearby objects
  BOULDER_ROLL_SPEED: 0.15, // How fast boulders accelerate when rolling
  BOULDER_CRUSH_THRESHOLD: 3, // Minimum speed for boulder to crush
};

// Material properties - determines how blocks behave when hit
export const MATERIAL_PROPERTIES: Record<string, { mass: number; friction: number; hitsToBreak: number; explosive?: boolean; rolling?: boolean }> = {
  wood: { mass: 15.0, friction: 0.95, hitsToBreak: 1 },
  ice: { mass: 8.0, friction: 0.85, hitsToBreak: 1 },
  stone: { mass: 30.0, friction: 0.98, hitsToBreak: 2 },
  tnt: { mass: 12.0, friction: 0.9, hitsToBreak: 1, explosive: true },
  boulder: { mass: 50.0, friction: 0.7, hitsToBreak: 3, rolling: true },
  wheel: { mass: 20.0, friction: 0.6, hitsToBreak: 2, rolling: true },
  glass: { mass: 5.0, friction: 0.8, hitsToBreak: 1 }, // Very fragile
  triangle: { mass: 18.0, friction: 0.92, hitsToBreak: 2 }, // Angled blocks
};

// Visual colors for each material type
export const MATERIAL_COLORS: Record<string, { bg: string; border: string; highlight: string; texture: string }> = {
  wood: { bg: '#8B4513', border: '#5D3A1A', highlight: '#A0522D', texture: '#6B3410' },
  ice: { bg: '#87CEEB', border: '#4682B4', highlight: '#B0E0E6', texture: '#5F9EA0' },
  stone: { bg: '#808080', border: '#505050', highlight: '#A9A9A9', texture: '#696969' },
  tnt: { bg: '#FF4444', border: '#AA0000', highlight: '#FF6666', texture: '#CC0000' },
  boulder: { bg: '#6B5B4F', border: '#3D3D3D', highlight: '#8B7B6B', texture: '#5A4A3E' },
  wheel: { bg: '#4A3A2A', border: '#2A2A2A', highlight: '#6A5A4A', texture: '#3A2A1A' },
  glass: { bg: 'rgba(200,230,255,0.7)', border: '#88AACC', highlight: 'rgba(255,255,255,0.8)', texture: '#99BBDD' },
  triangle: { bg: '#9B8B7B', border: '#6B5B4B', highlight: '#AB9B8B', texture: '#7B6B5B' },
};

// Block type definitions for shapes
export type BlockType = 'wood' | 'ice' | 'stone' | 'tnt' | 'boulder' | 'wheel' | 'glass' | 'triangle';
export type BlockShape = 'square' | 'plank_h' | 'plank_v' | 'pillar' | 'circle' | 'triangle_left' | 'triangle_right';

// Block interface - supports all block types including TNT, boulders, etc.
export interface Block {
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
  type: BlockType;
  shape: BlockShape;
  mass: number;
  friction: number;
  hitCount: number;
  exploded?: boolean; // For TNT blocks
  rolling?: boolean; // For boulders/wheels
}

// Enemy (pig) interface
export interface Enemy {
  id: string;
  name?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  eliminated: boolean;
  velocityX: number;
  velocityY: number;
  falling: boolean;
  fort_index?: number;
}

// Cannonball interface
export interface Cannonball {
  x: number;
  y: number;
  velocityX: number;
  velocityY: number;
  active: boolean;
  trail: { x: number; y: number }[];
}

/**
 * Check collision between ball and rectangle
 */
export function checkBallRectCollision(
  ballX: number, 
  ballY: number, 
  rect: { x: number; y: number; width: number; height: number }
): boolean {
  const ballRadius = PHYSICS_CONSTANTS.BALL_RADIUS;
  const closestX = Math.max(rect.x, Math.min(ballX, rect.x + rect.width));
  const closestY = Math.max(rect.y, Math.min(ballY, rect.y + rect.height));
  const distX = ballX - closestX;
  const distY = ballY - closestY;
  return (distX * distX + distY * distY) < (ballRadius * ballRadius);
}

/**
 * Check collision between two rectangles
 */
export function checkRectRectCollision(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number }
): boolean {
  return a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y;
}

/**
 * Create a block with proper physics properties
 * Supports all block types: wood, ice, stone, tnt, boulder, wheel, glass, triangle
 */
export function createBlock(
  id: string,
  x: number,
  y: number,
  type: BlockType,
  shape: BlockShape
): Block {
  const props = MATERIAL_PROPERTIES[type] || MATERIAL_PROPERTIES.wood;
  
  let width = 40, height = 40;
  if (shape === 'plank_h') { width = 80; height = 20; }
  if (shape === 'plank_v') { width = 20; height = 80; }
  if (shape === 'pillar') { width = 15; height = 100; }
  if (shape === 'circle') { width = 50; height = 50; } // For boulders
  if (shape === 'triangle_left' || shape === 'triangle_right') { width = 40; height = 40; }
  
  return {
    id,
    x,
    y: PHYSICS_CONSTANTS.GROUND_Y - y, // Convert from bottom-up to top-down coordinates
    width,
    height,
    destroyed: false,
    velocityX: 0,
    velocityY: 0,
    falling: false,
    rotation: 0,
    type,
    shape,
    mass: props.mass,
    friction: props.friction,
    hitCount: 0,
    exploded: false,
    rolling: props.rolling || false,
  };
}

/**
 * Create an enemy (pig) with proper physics properties
 */
export function createEnemy(
  id: string,
  name: string,
  x: number,
  y: number,
  fortIndex: number = 0
): Enemy {
  return {
    id,
    name,
    x,
    y: PHYSICS_CONSTANTS.GROUND_Y - y, // Convert from bottom-up
    width: 40,
    height: 40,
    eliminated: false,
    velocityX: 0,
    velocityY: 0,
    falling: false,
    fort_index: fortIndex,
  };
}

/**
 * Update cannonball physics
 * Returns the updated cannonball state
 */
export function updateCannonballPhysics(
  ball: Cannonball | null,
  blocks: Block[]
): Cannonball | null {
  if (!ball || !ball.active) return ball;
  
  const { GRAVITY, WORLD_WIDTH, GROUND_Y } = PHYSICS_CONSTANTS;
  
  let newX = ball.x + ball.velocityX;
  let newY = ball.y + ball.velocityY;
  let newVelX = ball.velocityX;
  let newVelY = ball.velocityY + GRAVITY;
  let stillActive = true;
  
  const newTrail = [...ball.trail, { x: ball.x, y: ball.y }].slice(-20);
  
  // Check collision with blocks (slow down ball)
  blocks.forEach(block => {
    if (!block.destroyed) {
      if (checkBallRectCollision(newX, newY, block)) {
        newVelX *= 0.6;
        newVelY *= 0.6;
      }
    }
  });
  
  // Check bounds
  if (newX > WORLD_WIDTH + 50 || newY > GROUND_Y || newX < -50) {
    stillActive = false;
  }
  
  return {
    ...ball,
    x: newX,
    y: newY,
    velocityX: newVelX,
    velocityY: newVelY,
    active: stillActive,
    trail: newTrail,
  };
}

/**
 * Update block physics - handles collisions, falling, and material-based behavior
 * This is the core physics engine that MUST be identical in both game versions
 * Now supports TNT explosions and boulder rolling mechanics
 */
export function updateBlocksPhysics(
  blocks: Block[],
  ballX: number,
  ballY: number,
  ballActive: boolean,
  ball: Cannonball | null,
  structureHit: boolean,
  onStructureHit: () => void,
  onTntExplode?: (x: number, y: number) => void
): Block[] {
  const { GRAVITY, GROUND_Y, TNT_EXPLOSION_RADIUS, TNT_EXPLOSION_FORCE } = PHYSICS_CONSTANTS;
  
  // Track TNT blocks that need to explode
  const tntToExplode: { x: number; y: number; id: string }[] = [];
  
  // First pass: handle cannonball collisions and basic physics
  let updatedBlocks = blocks.map(block => {
    if (block.destroyed && block.y >= GROUND_Y + 100) return block;
    
    // Direct cannonball hits
    if (!block.destroyed && !block.falling && ballActive && ball) {
      if (checkBallRectCollision(ballX, ballY, block)) {
        const impactForce = Math.sqrt(ball.velocityX * ball.velocityX + ball.velocityY * ball.velocityY);
        const impactAngle = Math.atan2(ballY - (block.y + block.height/2), ballX - (block.x + block.width/2));
        
        // Mark structure as hit - now support checks can happen
        onStructureHit();
        
        // TNT blocks explode when hit!
        if (block.type === 'tnt' && !block.exploded) {
          tntToExplode.push({ 
            x: block.x + block.width / 2, 
            y: block.y + block.height / 2,
            id: block.id 
          });
          return {
            ...block,
            destroyed: true,
            exploded: true,
            falling: false,
          };
        }
        
        // Boulder/wheel blocks start rolling when hit
        if (block.type === 'boulder' || block.type === 'wheel') {
          const rollDirection = ball.velocityX > 0 ? 1 : -1;
          return {
            ...block,
            destroyed: true,
            falling: true,
            rolling: true,
            hitCount: block.hitCount + 1,
            velocityX: rollDirection * 4, // Roll in direction of impact
            velocityY: -2,
          };
        }
        
        // Direct cannonball hit - ONLY this specific block moves
        // Very LOW velocity transfer to prevent chain reactions
        const velocityMult = block.type === 'stone' ? 0.08 : (block.type === 'ice' || block.type === 'glass' ? 0.15 : 0.12);
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
      // Very high friction - blocks slow down fast (but boulders roll!)
      let newVelX = block.velocityX * (block.rolling ? 0.98 : 0.85);
      let newRotation = block.rotation + block.velocityX * (block.rolling ? 2 : 0.5);
      
      // Boulder rolling on ground - maintain momentum
      if (block.rolling && newY >= GROUND_Y - 30) {
        newY = GROUND_Y - 30;
        newVelY = 0;
        // Boulders keep rolling on ground with slight deceleration
        newVelX *= 0.99;
        // Add slight acceleration if on a slope (simulate)
        if (Math.abs(newVelX) > 0.5) {
          newVelX += (newVelX > 0 ? PHYSICS_CONSTANTS.BOULDER_ROLL_SPEED : -PHYSICS_CONSTANTS.BOULDER_ROLL_SPEED);
        }
      }
      
      // Ground collision - blocks stop quickly
      if (newY > GROUND_Y - 10 && !block.rolling) {
        newY = GROUND_Y - 10;
        newVelY = 0; // No bounce
        newVelX *= 0.2; // High ground friction
      }
      
      // Cap maximum velocity to prevent blocks flying too fast
      newVelX = Math.max(-8, Math.min(8, newVelX));
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
  
  // Process TNT explosions - destroy nearby blocks
  for (const tnt of tntToExplode) {
    if (onTntExplode) onTntExplode(tnt.x, tnt.y);
    
    updatedBlocks = updatedBlocks.map(block => {
      if (block.id === tnt.id) return block; // Skip the TNT itself
      if (block.destroyed) return block;
      
      // Calculate distance from TNT center
      const blockCenterX = block.x + block.width / 2;
      const blockCenterY = block.y + block.height / 2;
      const dx = blockCenterX - tnt.x;
      const dy = blockCenterY - tnt.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      // If within explosion radius, apply damage
      if (distance < TNT_EXPLOSION_RADIUS) {
        const force = TNT_EXPLOSION_FORCE * (1 - distance / TNT_EXPLOSION_RADIUS);
        const angle = Math.atan2(dy, dx);
        
        // Chain reaction - nearby TNT also explodes!
        if (block.type === 'tnt' && !block.exploded) {
          tntToExplode.push({
            x: block.x + block.width / 2,
            y: block.y + block.height / 2,
            id: block.id
          });
          return {
            ...block,
            destroyed: true,
            exploded: true,
          };
        }
        
        // Glass/ice instantly destroyed by explosion
        if (block.type === 'glass' || block.type === 'ice') {
          return {
            ...block,
            destroyed: true,
            falling: true,
            velocityX: Math.cos(angle) * force,
            velocityY: Math.sin(angle) * force - 5,
          };
        }
        
        // Other blocks get pushed
        return {
          ...block,
          destroyed: true,
          falling: true,
          velocityX: Math.cos(angle) * force * 0.5,
          velocityY: Math.sin(angle) * force * 0.5 - 3,
        };
      }
      
      return block;
    });
  }
  
  // Second pass: block-to-block collisions - VERY restrictive
  // ONLY if structure has been hit at least once
  if (!structureHit) {
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
      
      // Rolling boulders crush everything in their path!
      if (other.rolling && otherSpeed > PHYSICS_CONSTANTS.BOULDER_CRUSH_THRESHOLD) {
        // TNT hit by boulder - explode!
        if (block.type === 'tnt' && !block.exploded) {
          tntToExplode.push({
            x: block.x + block.width / 2,
            y: block.y + block.height / 2,
            id: block.id
          });
          return {
            ...block,
            destroyed: true,
            exploded: true,
          };
        }
        
        const pushDirection = other.x < block.x ? 1 : -1;
        return {
          ...block,
          destroyed: true,
          falling: true,
          velocityX: pushDirection * 3,
          velocityY: -4,
        };
      }
      
      // VERY HIGH force thresholds - blocks barely affect each other
      // Only a fast, heavy block can move another block
      const forceNeeded = block.type === 'stone' ? 100 : (block.type === 'ice' || block.type === 'glass' ? 40 : 60);
      
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
}

/**
 * Update enemy (pig) physics - handles cannonball hits, falling block collisions,
 * TNT explosion damage, and boulder crushing
 */
export function updateEnemiesPhysics(
  enemies: Enemy[],
  blocks: Block[],
  ballX: number,
  ballY: number,
  ballActive: boolean,
  ball: Cannonball | null,
  structureHit: boolean,
  tntExplosions?: { x: number; y: number }[]
): Enemy[] {
  const { GRAVITY, GROUND_Y, TNT_EXPLOSION_RADIUS, BOULDER_CRUSH_THRESHOLD } = PHYSICS_CONSTANTS;
  
  return enemies.map(enemy => {
    if (enemy.eliminated && enemy.y >= GROUND_Y + 100) return enemy;
    
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
    
    // TNT explosion damage - enemies within radius are eliminated
    if (!enemy.eliminated && tntExplosions && tntExplosions.length > 0) {
      for (const explosion of tntExplosions) {
        const enemyCenterX = enemy.x + enemy.width / 2;
        const enemyCenterY = enemy.y + enemy.height / 2;
        const dx = enemyCenterX - explosion.x;
        const dy = enemyCenterY - explosion.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < TNT_EXPLOSION_RADIUS) {
          const force = 10 * (1 - distance / TNT_EXPLOSION_RADIUS);
          const angle = Math.atan2(dy, dx);
          return {
            ...enemy,
            eliminated: true,
            falling: true,
            velocityX: Math.cos(angle) * force,
            velocityY: Math.sin(angle) * force - 8,
          };
        }
      }
    }
    
    // Falling blocks and rolling boulders can knock pigs
    if (!enemy.eliminated && !enemy.falling) {
      for (const b of blocks) {
        if (!b.falling && !b.destroyed) continue;
        if (!checkRectRectCollision(b, enemy)) continue;
        
        // Rolling boulders instantly crush enemies!
        if (b.rolling) {
          const boulderSpeed = Math.sqrt(b.velocityX * b.velocityX + b.velocityY * b.velocityY);
          if (boulderSpeed > BOULDER_CRUSH_THRESHOLD) {
            const pushDir = b.x < enemy.x ? 1 : -1;
            return {
              ...enemy,
              eliminated: true,
              falling: true,
              velocityX: pushDir * 5 + b.velocityX * 0.5,
              velocityY: -10,
            };
          }
        }
        
        // Calculate block momentum (mass * velocity)
        const blockMomentum = b.mass * Math.sqrt(b.velocityX * b.velocityX + b.velocityY * b.velocityY);
        
        // Stone blocks need less speed because they're heavy
        // Wood blocks need more speed
        const momentumThreshold = b.type === 'stone' || b.type === 'boulder' ? 3 : (b.type === 'ice' || b.type === 'glass' ? 2 : 4);
        
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
    if (!enemy.falling && !enemy.eliminated && structureHit) {
      const supportBlock = blocks.find(b => 
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
        y: newY,
        velocityY: newVelY,
      };
    }
    
    return enemy;
  });
}

/**
 * Generate Angry Birds-style level structure based on level number
 * Returns blocks and enemies for the level
 * Now supports all 68 levels with TNT, boulders, wheels, glass, and triangles
 */
export function generateLevelStructure(
  levelNumber: number,
  enemyNames: string[] = ['Thug', 'Goon', 'Boss']
): { blocks: Block[]; enemies: Enemy[] } {
  const levelConfig = getLevelConfig(levelNumber);
  
  if (!levelConfig) {
    // Fallback to basic level if config not found
    return generateBasicLevel(levelNumber, enemyNames);
  }
  
  const blocks: Block[] = [];
  const enemies: Enemy[] = [];
  let blockIdCounter = 0;
  let enemyIdCounter = 0;
  let nameIndex = 0;
  
  // Create blocks from config
  for (const blockConfig of levelConfig.blocks) {
    blocks.push(createBlock(
      `block-${blockIdCounter++}`,
      blockConfig.x,
      blockConfig.y,
      blockConfig.type,
      blockConfig.shape
    ));
  }
  
  // Create enemies from config
  for (const enemyConfig of levelConfig.enemies) {
    const name = enemyConfig.name || enemyNames[nameIndex++ % enemyNames.length];
    enemies.push(createEnemy(
      `pig-${enemyIdCounter++}`,
      name,
      enemyConfig.x,
      enemyConfig.y,
      0
    ));
  }
  
  return { blocks, enemies };
}

/**
 * Fallback level generator for levels without custom config
 */
function generateBasicLevel(
  difficulty: number,
  enemyNames: string[]
): { blocks: Block[]; enemies: Enemy[] } {
  const blocks: Block[] = [];
  const enemies: Enemy[] = [];
  
  const fortX = 650;
  let blockIdCounter = 0;
  let enemyIdCounter = 0;
  let nameIndex = 0;
  
  const addBlock = (x: number, y: number, type: BlockType, shape: BlockShape) => {
    blocks.push(createBlock(`block-${blockIdCounter++}`, x, y, type, shape));
  };
  
  const addPig = (x: number, y: number, fortIndex: number = 0) => {
    const name = enemyNames[nameIndex++ % enemyNames.length];
    enemies.push(createEnemy(`pig-${enemyIdCounter++}`, name, x, y, fortIndex));
  };
  
  // Basic procedural generation based on difficulty
  const numEnemies = Math.min(1 + Math.floor(difficulty / 2), 8);
  
  // Create a basic tower structure
  for (let i = 0; i < Math.min(difficulty, 5); i++) {
    addBlock(fortX + i * 45, 100, 'stone', 'pillar');
    addBlock(fortX + i * 45 - 10, 110, 'wood', 'plank_h');
  }
  
  // Add some ice blocks
  for (let i = 0; i < Math.min(difficulty - 2, 4); i++) {
    addBlock(fortX + 20 + i * 50, 150, 'ice', 'square');
  }
  
  // Add enemies
  for (let i = 0; i < numEnemies; i++) {
    addPig(fortX + 20 + i * 60, 145 + (i % 2) * 50, i);
  }
  
  // Add TNT for higher difficulties
  if (difficulty >= 14) {
    addBlock(fortX + 80, 200, 'tnt', 'square');
  }
  
  // Add boulders for very high difficulties
  if (difficulty >= 16) {
    addBlock(fortX + 60, 350, 'boulder', 'circle');
  }
  
  return { blocks, enemies };
}
