/**
 * Shared Castle Mini-game Physics Engine
 * Used by both castle-game.tsx (map version) and castle-levels.tsx (options panel version)
 * This ensures identical physics behavior across both entry points.
 */

// Physics constants
export const PHYSICS_CONSTANTS = {
  WORLD_WIDTH: 1200,
  WORLD_HEIGHT: 500,
  GROUND_Y: 440, // WORLD_HEIGHT - 60
  GRAVITY: 0.4,
  INITIAL_VELOCITY: 22,
  BALL_RADIUS: 12,
};

// Material properties - determines how blocks behave when hit
export const MATERIAL_PROPERTIES = {
  wood: { mass: 15.0, friction: 0.95, hitsToBreak: 1 },
  ice: { mass: 8.0, friction: 0.85, hitsToBreak: 1 },
  stone: { mass: 30.0, friction: 0.98, hitsToBreak: 2 },
};

// Visual colors for each material type
export const MATERIAL_COLORS = {
  wood: { bg: '#8B4513', border: '#5D3A1A', highlight: '#A0522D', texture: '#6B3410' },
  ice: { bg: '#87CEEB', border: '#4682B4', highlight: '#B0E0E6', texture: '#5F9EA0' },
  stone: { bg: '#808080', border: '#505050', highlight: '#A9A9A9', texture: '#696969' },
};

// Block interface
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
  type: 'wood' | 'ice' | 'stone';
  shape: 'square' | 'plank_h' | 'plank_v' | 'pillar';
  mass: number;
  friction: number;
  hitCount: number;
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
 */
export function createBlock(
  id: string,
  x: number,
  y: number,
  type: 'wood' | 'ice' | 'stone',
  shape: 'square' | 'plank_h' | 'plank_v' | 'pillar'
): Block {
  const props = MATERIAL_PROPERTIES[type];
  
  let width = 40, height = 40;
  if (shape === 'plank_h') { width = 80; height = 20; }
  if (shape === 'plank_v') { width = 20; height = 80; }
  if (shape === 'pillar') { width = 15; height = 100; }
  
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
 */
export function updateBlocksPhysics(
  blocks: Block[],
  ballX: number,
  ballY: number,
  ballActive: boolean,
  ball: Cannonball | null,
  structureHit: boolean,
  onStructureHit: () => void
): Block[] {
  const { GRAVITY, GROUND_Y } = PHYSICS_CONSTANTS;
  
  // First pass: handle cannonball collisions and basic physics
  const updatedBlocks = blocks.map(block => {
    if (block.destroyed && block.y >= GROUND_Y + 100) return block;
    
    // Direct cannonball hits
    if (!block.destroyed && !block.falling && ballActive && ball) {
      if (checkBallRectCollision(ballX, ballY, block)) {
        const impactForce = Math.sqrt(ball.velocityX * ball.velocityX + ball.velocityY * ball.velocityY);
        const impactAngle = Math.atan2(ballY - (block.y + block.height/2), ballX - (block.x + block.width/2));
        
        // Mark structure as hit - now support checks can happen
        onStructureHit();
        
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
}

/**
 * Update enemy (pig) physics - handles cannonball hits and falling block collisions
 */
export function updateEnemiesPhysics(
  enemies: Enemy[],
  blocks: Block[],
  ballX: number,
  ballY: number,
  ballActive: boolean,
  ball: Cannonball | null,
  structureHit: boolean
): Enemy[] {
  const { GRAVITY, GROUND_Y } = PHYSICS_CONSTANTS;
  
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
    
    // Falling blocks can knock pigs - any block with enough momentum
    if (!enemy.eliminated && !enemy.falling) {
      for (const b of blocks) {
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
 * Generate Angry Birds-style level structure based on difficulty
 * Returns blocks and enemies for the level
 */
export function generateLevelStructure(
  difficulty: number,
  enemyNames: string[] = ['Thug', 'Goon', 'Boss']
): { blocks: Block[]; enemies: Enemy[] } {
  const blocks: Block[] = [];
  const enemies: Enemy[] = [];
  
  // Fort position - farther from cannon for longer cannonball arc
  const fortX = 650;
  let blockIdCounter = 0;
  let enemyIdCounter = 0;
  let nameIndex = 0;
  
  const addBlock = (x: number, y: number, type: 'wood' | 'ice' | 'stone', shape: 'square' | 'plank_h' | 'plank_v' | 'pillar') => {
    blocks.push(createBlock(`block-${blockIdCounter++}`, x, y, type, shape));
  };
  
  const addPig = (x: number, y: number, fortIndex: number = 0) => {
    const name = enemyNames[nameIndex++ % enemyNames.length];
    enemies.push(createEnemy(`pig-${enemyIdCounter++}`, name, x, y, fortIndex));
  };
  
  // Generate structure based on difficulty (1-10 scale)
  if (difficulty <= 1) {
    // Simple tower - Training Ground style
    addBlock(fortX, 100, 'stone', 'pillar');
    addBlock(fortX + 60, 100, 'stone', 'pillar');
    addBlock(fortX - 10, 110, 'wood', 'plank_h');
    addPig(fortX + 10, 140, 0);
  } else if (difficulty === 2) {
    // Two pillars with pigs - Small Outpost style
    addBlock(fortX, 100, 'stone', 'pillar');
    addBlock(fortX + 100, 100, 'stone', 'pillar');
    addBlock(fortX - 10, 110, 'wood', 'plank_h');
    addBlock(fortX + 90, 110, 'wood', 'plank_h');
    addPig(fortX + 10, 140, 0);
    addPig(fortX + 110, 140, 1);
  } else if (difficulty === 3) {
    // Tall wooden tower - Guard Tower style
    addBlock(fortX, 40, 'wood', 'square');
    addBlock(fortX + 45, 40, 'wood', 'square');
    addBlock(fortX, 85, 'wood', 'plank_v');
    addBlock(fortX + 65, 85, 'wood', 'plank_v');
    addBlock(fortX - 10, 135, 'wood', 'plank_h');
    addBlock(fortX, 175, 'wood', 'plank_v');
    addBlock(fortX + 65, 175, 'wood', 'plank_v');
    addBlock(fortX - 10, 225, 'wood', 'plank_h');
    addPig(fortX + 20, 130, 0);
    addPig(fortX + 20, 255, 0);
  } else if (difficulty === 4) {
    // Ice structure - Watchtower style
    addBlock(fortX, 100, 'stone', 'pillar');
    addBlock(fortX + 80, 100, 'stone', 'pillar');
    addBlock(fortX - 10, 110, 'ice', 'plank_h');
    addBlock(fortX, 130, 'ice', 'square');
    addBlock(fortX + 45, 130, 'ice', 'square');
    addBlock(fortX, 175, 'ice', 'square');
    addBlock(fortX + 45, 175, 'ice', 'square');
    addBlock(fortX + 90, 175, 'ice', 'square');
    addBlock(fortX - 10, 220, 'ice', 'plank_h');
    addPig(fortX + 20, 115, 0);
    addPig(fortX + 20, 250, 0);
    addPig(fortX + 100, 220, 0);
  } else if (difficulty === 5) {
    // Multi-tower - Fort Minor style
    // Left tower
    addBlock(fortX - 50, 100, 'stone', 'pillar');
    addBlock(fortX + 30, 100, 'stone', 'pillar');
    addBlock(fortX - 60, 110, 'wood', 'plank_h');
    addPig(fortX - 30, 145, 0);
    // Right tower
    addBlock(fortX + 100, 100, 'stone', 'pillar');
    addBlock(fortX + 180, 100, 'stone', 'pillar');
    addBlock(fortX + 90, 110, 'wood', 'plank_h');
    addBlock(fortX + 90, 130, 'ice', 'square');
    addBlock(fortX + 135, 130, 'ice', 'square');
    addBlock(fortX + 90, 180, 'ice', 'plank_h');
    addPig(fortX + 120, 115, 1);
    addPig(fortX + 120, 215, 1);
  } else if (difficulty === 6) {
    // House structure - Stone Keep style
    addBlock(fortX, 40, 'stone', 'square');
    addBlock(fortX + 45, 40, 'stone', 'square');
    addBlock(fortX + 90, 40, 'stone', 'square');
    addBlock(fortX, 130, 'wood', 'plank_v');
    addBlock(fortX + 115, 130, 'wood', 'plank_v');
    addBlock(fortX - 20, 180, 'ice', 'plank_v');
    addBlock(fortX + 135, 180, 'ice', 'plank_v');
    addBlock(fortX + 20, 250, 'ice', 'plank_h');
    addBlock(fortX + 60, 280, 'ice', 'square');
    addBlock(fortX + 30, 85, 'wood', 'plank_h');
    addPig(fortX + 50, 50, 0);
    addPig(fortX + 50, 120, 0);
    addPig(fortX + 50, 200, 0);
    addPig(fortX - 30, 50, 0);
  } else if (difficulty === 7) {
    // Complex fortress - Battle Fortress style
    addBlock(fortX - 30, 100, 'stone', 'pillar');
    addBlock(fortX + 50, 100, 'stone', 'pillar');
    addBlock(fortX + 130, 100, 'stone', 'pillar');
    addBlock(fortX + 210, 100, 'stone', 'pillar');
    addBlock(fortX - 40, 110, 'wood', 'plank_h');
    addBlock(fortX + 40, 110, 'wood', 'plank_h');
    addBlock(fortX + 120, 110, 'wood', 'plank_h');
    addBlock(fortX, 200, 'wood', 'plank_v');
    addBlock(fortX + 80, 200, 'wood', 'plank_v');
    addBlock(fortX + 160, 200, 'wood', 'plank_v');
    addBlock(fortX - 10, 250, 'ice', 'plank_h');
    addBlock(fortX + 70, 250, 'ice', 'plank_h');
    addBlock(fortX + 40, 280, 'ice', 'square');
    addBlock(fortX + 120, 280, 'ice', 'square');
    addPig(fortX, 145, 0);
    addPig(fortX + 80, 145, 0);
    addPig(fortX + 160, 145, 0);
    addPig(fortX + 80, 310, 0);
  } else if (difficulty === 8) {
    // War Castle style
    for (let i = 0; i < 4; i++) {
      addBlock(fortX + i * 70, 100, 'stone', 'pillar');
      addBlock(fortX + i * 70 - 10, 110, 'wood', 'plank_h');
    }
    addBlock(fortX + 20, 150, 'ice', 'square');
    addBlock(fortX + 90, 150, 'ice', 'square');
    addBlock(fortX + 160, 150, 'ice', 'square');
    addBlock(fortX - 10, 200, 'ice', 'plank_h');
    addBlock(fortX + 70, 200, 'ice', 'plank_h');
    addBlock(fortX + 150, 200, 'ice', 'plank_h');
    addBlock(fortX + 50, 250, 'wood', 'plank_v');
    addBlock(fortX + 130, 250, 'wood', 'plank_v');
    addBlock(fortX + 40, 300, 'wood', 'plank_h');
    addPig(fortX + 30, 145, 0);
    addPig(fortX + 100, 145, 0);
    addPig(fortX + 170, 145, 0);
    addPig(fortX + 50, 235, 0);
    addPig(fortX + 130, 235, 0);
  } else if (difficulty === 9) {
    // Imperial Stronghold style
    // Structure 1 - Left
    addBlock(fortX - 100, 100, 'stone', 'pillar');
    addBlock(fortX - 20, 100, 'stone', 'pillar');
    addBlock(fortX - 110, 110, 'wood', 'plank_h');
    addBlock(fortX - 70, 150, 'ice', 'square');
    addBlock(fortX - 70, 200, 'ice', 'square');
    addPig(fortX - 60, 145, 0);
    addPig(fortX - 60, 240, 0);
    // Structure 2 - Center tower
    addBlock(fortX + 60, 100, 'stone', 'pillar');
    addBlock(fortX + 140, 100, 'stone', 'pillar');
    addBlock(fortX + 50, 110, 'wood', 'plank_h');
    addBlock(fortX + 50, 150, 'wood', 'square');
    addBlock(fortX + 95, 150, 'wood', 'square');
    addBlock(fortX + 70, 250, 'wood', 'plank_v');
    addBlock(fortX + 110, 250, 'wood', 'plank_v');
    addBlock(fortX + 60, 300, 'wood', 'plank_h');
    addPig(fortX + 70, 145, 1);
    addPig(fortX + 90, 335, 1);
    // Structure 3 - Right
    addBlock(fortX + 220, 100, 'stone', 'pillar');
    addBlock(fortX + 300, 100, 'stone', 'pillar');
    addBlock(fortX + 210, 110, 'ice', 'plank_h');
    addPig(fortX + 240, 145, 2);
  } else {
    // Dragon Citadel style (difficulty 10+)
    // Grand central structure
    for (let i = 0; i < 5; i++) {
      addBlock(fortX - 50 + i * 60, 100, 'stone', 'pillar');
    }
    addBlock(fortX - 60, 110, 'stone', 'plank_h');
    addBlock(fortX + 20, 110, 'stone', 'plank_h');
    addBlock(fortX + 100, 110, 'stone', 'plank_h');
    addBlock(fortX + 180, 110, 'stone', 'plank_h');
    // Second level
    addBlock(fortX - 30, 200, 'wood', 'plank_v');
    addBlock(fortX + 50, 200, 'wood', 'plank_v');
    addBlock(fortX + 130, 200, 'wood', 'plank_v');
    addBlock(fortX + 210, 200, 'wood', 'plank_v');
    addBlock(fortX - 40, 250, 'ice', 'plank_h');
    addBlock(fortX + 40, 250, 'ice', 'plank_h');
    addBlock(fortX + 120, 250, 'ice', 'plank_h');
    // Top tower
    addBlock(fortX + 60, 320, 'ice', 'plank_v');
    addBlock(fortX + 100, 320, 'ice', 'plank_v');
    addBlock(fortX + 50, 370, 'ice', 'plank_h');
    addBlock(fortX + 80, 400, 'stone', 'square');
    // Pigs spread throughout
    addPig(fortX - 40, 145, 0);
    addPig(fortX + 40, 145, 0);
    addPig(fortX + 120, 145, 0);
    addPig(fortX + 200, 145, 0);
    addPig(fortX + 80, 285, 0);
    addPig(fortX + 80, 405, 0);
  }
  
  return { blocks, enemies };
}
