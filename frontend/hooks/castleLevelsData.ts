/**
 * Castle Mini-game Level Data
 * Contains all 68 levels (Levels 1-68) with block and enemy configurations
 * 
 * Block Types: wood, ice, stone, tnt, boulder, wheel, glass, triangle
 * Block Shapes: square, plank_h, plank_v, pillar, circle, triangle_left, triangle_right
 * 
 * Coordinate System:
 * - x: horizontal position (0 = left, 1200 = right)
 * - y: height from ground (0 = ground level, higher = taller)
 */

// Define types locally to avoid circular dependency with useCastlePhysics.ts
export type BlockType = 'wood' | 'ice' | 'stone' | 'tnt' | 'boulder' | 'wheel' | 'glass' | 'triangle';
export type BlockShape = 'square' | 'plank_h' | 'plank_v' | 'pillar' | 'circle' | 'triangle_left' | 'triangle_right';

export interface LevelBlockConfig {
  x: number;
  y: number;
  type: BlockType;
  shape: BlockShape;
}

export interface LevelEnemyConfig {
  x: number;
  y: number;
  name?: string;
}

export interface LevelConfig {
  blocks: LevelBlockConfig[];
  enemies: LevelEnemyConfig[];
}

// Helper to create block config quickly
const b = (x: number, y: number, type: BlockType, shape: BlockShape): LevelBlockConfig => ({ x, y, type, shape });
const e = (x: number, y: number, name?: string): LevelEnemyConfig => ({ x, y, name });

// All 68 levels
export const LEVEL_CONFIGS: Record<number, LevelConfig> = {
  // ==================== LEVELS 1-10 (Original) ====================
  
  // Level 1: Training Ground - Simple intro
  1: {
    blocks: [
      b(650, 100, 'stone', 'pillar'),
      b(710, 100, 'stone', 'pillar'),
      b(640, 110, 'wood', 'plank_h'),
    ],
    enemies: [e(660, 140)],
  },

  // Level 2: Small Outpost - Two towers
  2: {
    blocks: [
      b(600, 100, 'stone', 'pillar'),
      b(700, 100, 'stone', 'pillar'),
      b(590, 110, 'wood', 'plank_h'),
      b(690, 110, 'wood', 'plank_h'),
    ],
    enemies: [e(610, 140), e(710, 140)],
  },

  // Level 3: Guard Tower - Tall wooden structure
  3: {
    blocks: [
      b(650, 40, 'wood', 'square'),
      b(695, 40, 'wood', 'square'),
      b(650, 85, 'wood', 'plank_v'),
      b(715, 85, 'wood', 'plank_v'),
      b(640, 135, 'wood', 'plank_h'),
      b(650, 175, 'wood', 'plank_v'),
      b(715, 175, 'wood', 'plank_v'),
      b(640, 225, 'wood', 'plank_h'),
    ],
    enemies: [e(670, 130), e(670, 255)],
  },

  // Level 4: Watchtower - Ice and stone mix
  4: {
    blocks: [
      b(650, 100, 'stone', 'pillar'),
      b(730, 100, 'stone', 'pillar'),
      b(640, 110, 'ice', 'plank_h'),
      b(650, 130, 'ice', 'square'),
      b(695, 130, 'ice', 'square'),
      b(650, 175, 'ice', 'square'),
      b(695, 175, 'ice', 'square'),
      b(740, 175, 'ice', 'square'),
      b(640, 220, 'ice', 'plank_h'),
    ],
    enemies: [e(670, 115), e(670, 250), e(750, 220)],
  },

  // Level 5: Fort Minor - Multi-tower
  5: {
    blocks: [
      // Left tower
      b(600, 100, 'stone', 'pillar'),
      b(680, 100, 'stone', 'pillar'),
      b(590, 110, 'wood', 'plank_h'),
      // Right tower
      b(750, 100, 'stone', 'pillar'),
      b(830, 100, 'stone', 'pillar'),
      b(740, 110, 'wood', 'plank_h'),
      b(740, 130, 'ice', 'square'),
      b(785, 130, 'ice', 'square'),
      b(740, 180, 'ice', 'plank_h'),
    ],
    enemies: [e(620, 145), e(770, 115), e(770, 215)],
  },

  // Level 6: Stone Keep
  6: {
    blocks: [
      b(650, 40, 'stone', 'square'),
      b(695, 40, 'stone', 'square'),
      b(740, 40, 'stone', 'square'),
      b(650, 130, 'wood', 'plank_v'),
      b(765, 130, 'wood', 'plank_v'),
      b(630, 180, 'ice', 'plank_v'),
      b(785, 180, 'ice', 'plank_v'),
      b(670, 250, 'ice', 'plank_h'),
      b(710, 280, 'ice', 'square'),
      b(680, 85, 'wood', 'plank_h'),
    ],
    enemies: [e(700, 50), e(700, 120), e(700, 200), e(620, 50)],
  },

  // Level 7: Battle Fortress
  7: {
    blocks: [
      b(620, 100, 'stone', 'pillar'),
      b(700, 100, 'stone', 'pillar'),
      b(780, 100, 'stone', 'pillar'),
      b(860, 100, 'stone', 'pillar'),
      b(610, 110, 'wood', 'plank_h'),
      b(690, 110, 'wood', 'plank_h'),
      b(770, 110, 'wood', 'plank_h'),
      b(650, 200, 'wood', 'plank_v'),
      b(730, 200, 'wood', 'plank_v'),
      b(810, 200, 'wood', 'plank_v'),
      b(640, 250, 'ice', 'plank_h'),
      b(720, 250, 'ice', 'plank_h'),
      b(690, 280, 'ice', 'square'),
      b(770, 280, 'ice', 'square'),
    ],
    enemies: [e(650, 145), e(730, 145), e(810, 145), e(730, 310)],
  },

  // Level 8: War Castle
  8: {
    blocks: [
      b(600, 100, 'stone', 'pillar'),
      b(670, 100, 'stone', 'pillar'),
      b(740, 100, 'stone', 'pillar'),
      b(810, 100, 'stone', 'pillar'),
      b(590, 110, 'wood', 'plank_h'),
      b(660, 110, 'wood', 'plank_h'),
      b(730, 110, 'wood', 'plank_h'),
      b(800, 110, 'wood', 'plank_h'),
      b(620, 150, 'ice', 'square'),
      b(690, 150, 'ice', 'square'),
      b(760, 150, 'ice', 'square'),
      b(590, 200, 'ice', 'plank_h'),
      b(670, 200, 'ice', 'plank_h'),
      b(750, 200, 'ice', 'plank_h'),
      b(650, 250, 'wood', 'plank_v'),
      b(730, 250, 'wood', 'plank_v'),
      b(640, 300, 'wood', 'plank_h'),
    ],
    enemies: [e(630, 145), e(700, 145), e(770, 145), e(650, 235), e(730, 235)],
  },

  // Level 9: Imperial Stronghold
  9: {
    blocks: [
      // Structure 1 - Left
      b(550, 100, 'stone', 'pillar'),
      b(630, 100, 'stone', 'pillar'),
      b(540, 110, 'wood', 'plank_h'),
      b(580, 150, 'ice', 'square'),
      b(580, 200, 'ice', 'square'),
      // Structure 2 - Center
      b(710, 100, 'stone', 'pillar'),
      b(790, 100, 'stone', 'pillar'),
      b(700, 110, 'wood', 'plank_h'),
      b(700, 150, 'wood', 'square'),
      b(745, 150, 'wood', 'square'),
      b(720, 250, 'wood', 'plank_v'),
      b(760, 250, 'wood', 'plank_v'),
      b(710, 300, 'wood', 'plank_h'),
      // Structure 3 - Right
      b(870, 100, 'stone', 'pillar'),
      b(950, 100, 'stone', 'pillar'),
      b(860, 110, 'ice', 'plank_h'),
    ],
    enemies: [e(590, 145), e(590, 240), e(720, 145), e(740, 335), e(890, 145)],
  },

  // Level 10: Dragon Citadel
  10: {
    blocks: [
      b(600, 100, 'stone', 'pillar'),
      b(660, 100, 'stone', 'pillar'),
      b(720, 100, 'stone', 'pillar'),
      b(780, 100, 'stone', 'pillar'),
      b(840, 100, 'stone', 'pillar'),
      b(590, 110, 'stone', 'plank_h'),
      b(670, 110, 'stone', 'plank_h'),
      b(750, 110, 'stone', 'plank_h'),
      b(830, 110, 'stone', 'plank_h'),
      b(620, 200, 'wood', 'plank_v'),
      b(700, 200, 'wood', 'plank_v'),
      b(780, 200, 'wood', 'plank_v'),
      b(860, 200, 'wood', 'plank_v'),
      b(610, 250, 'ice', 'plank_h'),
      b(690, 250, 'ice', 'plank_h'),
      b(770, 250, 'ice', 'plank_h'),
      b(710, 320, 'ice', 'plank_v'),
      b(750, 320, 'ice', 'plank_v'),
      b(700, 370, 'ice', 'plank_h'),
      b(730, 400, 'stone', 'square'),
    ],
    enemies: [e(610, 145), e(690, 145), e(770, 145), e(850, 145), e(730, 285), e(730, 405)],
  },

  // ==================== LEVELS 11-20 (New) ====================

  // Level 11: Dual Tower Introduction - Two separate towers with ice bridges
  11: {
    blocks: [
      // Left tower
      b(550, 40, 'stone', 'square'),
      b(550, 85, 'wood', 'plank_v'),
      b(570, 85, 'wood', 'plank_v'),
      b(540, 165, 'wood', 'plank_h'),
      b(550, 205, 'ice', 'plank_v'),
      b(570, 205, 'ice', 'plank_v'),
      b(540, 285, 'ice', 'plank_h'),
      // Right tower
      b(750, 40, 'stone', 'square'),
      b(750, 85, 'wood', 'plank_v'),
      b(770, 85, 'wood', 'plank_v'),
      b(740, 165, 'wood', 'plank_h'),
      b(750, 205, 'ice', 'plank_v'),
      b(770, 205, 'ice', 'plank_v'),
      b(740, 285, 'ice', 'plank_h'),
      // Middle platform
      b(640, 100, 'wood', 'plank_h'),
      b(660, 100, 'wood', 'plank_h'),
    ],
    enemies: [e(555, 50), e(560, 290), e(755, 50), e(760, 290)],
  },

  // Level 12: Ice Tower - Tall ice structure
  12: {
    blocks: [
      b(680, 60, 'ice', 'square'),
      b(680, 105, 'ice', 'square'),
      b(640, 105, 'ice', 'square'),
      b(720, 105, 'ice', 'square'),
      b(640, 150, 'ice', 'plank_v'),
      b(720, 150, 'ice', 'plank_v'),
      b(630, 200, 'wood', 'plank_h'),
      b(720, 200, 'wood', 'plank_h'),
      b(640, 220, 'ice', 'square'),
      b(680, 220, 'ice', 'square'),
      b(720, 220, 'ice', 'square'),
      b(660, 265, 'wood', 'plank_h'),
    ],
    enemies: [e(690, 65), e(650, 205), e(730, 205)],
  },

  // Level 13: Stone Fortress - Heavy stone with ice accents
  13: {
    blocks: [
      b(600, 80, 'stone', 'square'),
      b(645, 80, 'stone', 'square'),
      b(690, 80, 'stone', 'square'),
      b(735, 80, 'stone', 'square'),
      b(620, 125, 'ice', 'plank_v'),
      b(710, 125, 'ice', 'plank_v'),
      b(610, 175, 'wood', 'plank_h'),
      b(700, 175, 'wood', 'plank_h'),
      b(640, 220, 'stone', 'square'),
      b(685, 220, 'stone', 'square'),
      b(660, 265, 'wood', 'plank_h'),
    ],
    enemies: [e(665, 90), e(665, 180), e(665, 270)],
  },

  // Level 14: TNT Introduction - First TNT level!
  14: {
    blocks: [
      b(650, 40, 'stone', 'pillar'),
      b(750, 40, 'stone', 'pillar'),
      b(640, 50, 'wood', 'plank_h'),
      b(700, 90, 'tnt', 'square'), // TNT!
      b(650, 150, 'wood', 'plank_v'),
      b(750, 150, 'wood', 'plank_v'),
      b(640, 200, 'wood', 'plank_h'),
      b(680, 240, 'ice', 'square'),
      b(720, 240, 'ice', 'square'),
    ],
    enemies: [e(670, 55), e(660, 205), e(740, 205)],
  },

  // Level 15: Glass House - Fragile glass structure
  15: {
    blocks: [
      b(620, 40, 'glass', 'square'),
      b(665, 40, 'glass', 'square'),
      b(710, 40, 'glass', 'square'),
      b(620, 85, 'glass', 'plank_v'),
      b(730, 85, 'glass', 'plank_v'),
      b(610, 135, 'glass', 'plank_h'),
      b(700, 135, 'glass', 'plank_h'),
      b(640, 175, 'wood', 'plank_v'),
      b(700, 175, 'wood', 'plank_v'),
      b(630, 225, 'wood', 'plank_h'),
      b(665, 265, 'stone', 'square'),
    ],
    enemies: [e(665, 50), e(665, 140), e(665, 230)],
  },

  // Level 16: Boulder Drop - First boulder level!
  16: {
    blocks: [
      b(700, 350, 'boulder', 'circle'), // Boulder on top!
      b(660, 40, 'stone', 'square'),
      b(705, 40, 'stone', 'square'),
      b(660, 85, 'wood', 'plank_v'),
      b(725, 85, 'wood', 'plank_v'),
      b(650, 165, 'wood', 'plank_h'),
      b(660, 200, 'ice', 'square'),
      b(705, 200, 'ice', 'square'),
      b(660, 245, 'wood', 'plank_v'),
      b(725, 245, 'wood', 'plank_v'),
      b(650, 325, 'wood', 'plank_h'),
    ],
    enemies: [e(680, 50), e(680, 170), e(680, 330)],
  },

  // Level 17: TNT Chain - Multiple TNT for chain reaction
  17: {
    blocks: [
      b(600, 40, 'wood', 'square'),
      b(650, 40, 'tnt', 'square'), // TNT
      b(700, 40, 'tnt', 'square'), // TNT
      b(750, 40, 'wood', 'square'),
      b(600, 85, 'wood', 'plank_v'),
      b(770, 85, 'wood', 'plank_v'),
      b(590, 165, 'wood', 'plank_h'),
      b(680, 165, 'wood', 'plank_h'),
      b(670, 120, 'ice', 'square'),
      b(715, 120, 'ice', 'square'),
    ],
    enemies: [e(610, 50), e(760, 50), e(680, 170)],
  },

  // Level 18: Wheel Cart - Wheels that roll
  18: {
    blocks: [
      b(580, 40, 'wheel', 'circle'), // Wheel
      b(620, 40, 'wood', 'plank_h'),
      b(720, 40, 'wheel', 'circle'), // Wheel
      b(650, 80, 'wood', 'plank_v'),
      b(700, 80, 'wood', 'plank_v'),
      b(640, 160, 'wood', 'plank_h'),
      b(660, 200, 'stone', 'square'),
      b(705, 200, 'stone', 'square'),
      b(660, 245, 'ice', 'plank_v'),
      b(725, 245, 'ice', 'plank_v'),
      b(650, 325, 'ice', 'plank_h'),
    ],
    enemies: [e(680, 85), e(680, 165), e(680, 330)],
  },

  // Level 19: Triangle Support - Triangle blocks for angled structures
  19: {
    blocks: [
      b(620, 40, 'triangle', 'triangle_left'),
      b(730, 40, 'triangle', 'triangle_right'),
      b(660, 80, 'wood', 'plank_h'),
      b(660, 120, 'ice', 'square'),
      b(705, 120, 'ice', 'square'),
      b(640, 165, 'stone', 'pillar'),
      b(720, 165, 'stone', 'pillar'),
      b(630, 175, 'wood', 'plank_h'),
      b(680, 220, 'wood', 'square'),
    ],
    enemies: [e(685, 85), e(685, 180), e(685, 225)],
  },

  // Level 20: Pitched Roof - Angled wooden structure
  20: {
    blocks: [
      // Left angled supports
      b(580, 180, 'wood', 'plank_v'),
      b(600, 220, 'wood', 'plank_v'),
      b(620, 260, 'wood', 'plank_v'),
      // Right angled supports
      b(760, 180, 'wood', 'plank_v'),
      b(740, 220, 'wood', 'plank_v'),
      b(720, 260, 'wood', 'plank_v'),
      // Center structure
      b(640, 40, 'wood', 'square'),
      b(685, 40, 'wood', 'square'),
      b(730, 40, 'wood', 'square'),
      b(640, 85, 'wood', 'plank_v'),
      b(750, 85, 'wood', 'plank_v'),
      b(630, 165, 'wood', 'plank_h'),
      // Ice fill
      b(660, 120, 'ice', 'square'),
      b(705, 120, 'ice', 'square'),
    ],
    enemies: [e(690, 50), e(690, 170)],
  },

  // ==================== LEVELS 21-30 ====================

  // Level 21: Boulder Pyramid - Boulder on pyramid
  21: {
    blocks: [
      b(680, 300, 'boulder', 'circle'), // Boulder on top
      // Pyramid structure
      b(620, 40, 'stone', 'square'),
      b(665, 40, 'stone', 'square'),
      b(710, 40, 'stone', 'square'),
      b(755, 40, 'stone', 'square'),
      b(640, 85, 'wood', 'square'),
      b(685, 85, 'wood', 'square'),
      b(730, 85, 'wood', 'square'),
      b(660, 130, 'wood', 'square'),
      b(705, 130, 'wood', 'square'),
      b(680, 175, 'wood', 'square'),
      b(660, 220, 'wood', 'plank_v'),
      b(700, 220, 'wood', 'plank_v'),
      b(650, 280, 'wood', 'plank_h'),
    ],
    enemies: [e(680, 50), e(680, 140), e(680, 285)],
  },

  // Level 22: Double TNT Tower
  22: {
    blocks: [
      // Left tower with TNT
      b(580, 40, 'wood', 'square'),
      b(580, 85, 'tnt', 'square'),
      b(580, 130, 'wood', 'plank_v'),
      b(600, 130, 'wood', 'plank_v'),
      b(570, 210, 'wood', 'plank_h'),
      // Right tower with TNT
      b(740, 40, 'wood', 'square'),
      b(740, 85, 'tnt', 'square'),
      b(740, 130, 'wood', 'plank_v'),
      b(760, 130, 'wood', 'plank_v'),
      b(730, 210, 'wood', 'plank_h'),
      // Center connection
      b(650, 100, 'ice', 'plank_h'),
    ],
    enemies: [e(590, 50), e(750, 50), e(660, 105), e(590, 215), e(750, 215)],
  },

  // Level 23: Glass Castle
  23: {
    blocks: [
      b(620, 40, 'glass', 'square'),
      b(665, 40, 'glass', 'square'),
      b(710, 40, 'glass', 'square'),
      b(755, 40, 'glass', 'square'),
      b(640, 85, 'glass', 'plank_v'),
      b(735, 85, 'glass', 'plank_v'),
      b(630, 165, 'glass', 'plank_h'),
      b(680, 165, 'glass', 'plank_h'),
      b(660, 205, 'glass', 'square'),
      b(705, 205, 'glass', 'square'),
      b(680, 250, 'stone', 'square'),
    ],
    enemies: [e(640, 50), e(730, 50), e(680, 170), e(680, 255)],
  },

  // Level 24: Mixed Fortress
  24: {
    blocks: [
      b(600, 40, 'stone', 'square'),
      b(700, 40, 'stone', 'square'),
      b(800, 40, 'stone', 'square'),
      b(600, 85, 'wood', 'plank_v'),
      b(700, 85, 'tnt', 'square'),
      b(820, 85, 'wood', 'plank_v'),
      b(590, 165, 'wood', 'plank_h'),
      b(710, 165, 'wood', 'plank_h'),
      b(620, 210, 'ice', 'square'),
      b(665, 210, 'ice', 'square'),
      b(750, 210, 'ice', 'square'),
      b(795, 210, 'ice', 'square'),
    ],
    enemies: [e(610, 50), e(710, 50), e(810, 50), e(670, 170)],
  },

  // Level 25: Wheel Wagon
  25: {
    blocks: [
      b(570, 40, 'wheel', 'circle'),
      b(750, 40, 'wheel', 'circle'),
      b(600, 80, 'wood', 'plank_h'),
      b(680, 80, 'wood', 'plank_h'),
      b(620, 120, 'wood', 'plank_v'),
      b(720, 120, 'wood', 'plank_v'),
      b(610, 200, 'wood', 'plank_h'),
      b(700, 200, 'wood', 'plank_h'),
      b(650, 240, 'ice', 'square'),
      b(695, 240, 'ice', 'square'),
    ],
    enemies: [e(660, 85), e(660, 205), e(675, 245)],
  },

  // Level 26: TNT Surprise
  26: {
    blocks: [
      b(650, 40, 'stone', 'square'),
      b(695, 40, 'stone', 'square'),
      b(650, 85, 'wood', 'plank_v'),
      b(715, 85, 'wood', 'plank_v'),
      b(670, 130, 'tnt', 'square'), // Hidden TNT
      b(640, 165, 'ice', 'plank_h'),
      b(660, 205, 'ice', 'square'),
      b(705, 205, 'ice', 'square'),
      b(660, 250, 'wood', 'plank_v'),
      b(725, 250, 'wood', 'plank_v'),
      b(650, 330, 'wood', 'plank_h'),
    ],
    enemies: [e(675, 50), e(675, 170), e(675, 335)],
  },

  // Level 27: Triple Tower
  27: {
    blocks: [
      // Tower 1
      b(520, 80, 'stone', 'pillar'),
      b(550, 80, 'stone', 'pillar'),
      b(510, 90, 'wood', 'plank_h'),
      // Tower 2
      b(670, 80, 'stone', 'pillar'),
      b(700, 80, 'stone', 'pillar'),
      b(660, 90, 'ice', 'plank_h'),
      b(680, 130, 'ice', 'square'),
      // Tower 3
      b(820, 80, 'stone', 'pillar'),
      b(850, 80, 'stone', 'pillar'),
      b(810, 90, 'wood', 'plank_h'),
    ],
    enemies: [e(535, 125), e(685, 95), e(685, 135), e(835, 125)],
  },

  // Level 28: Boulder Crusher
  28: {
    blocks: [
      b(650, 350, 'boulder', 'circle'),
      b(750, 350, 'boulder', 'circle'),
      b(620, 40, 'wood', 'square'),
      b(665, 40, 'wood', 'square'),
      b(710, 40, 'wood', 'square'),
      b(755, 40, 'wood', 'square'),
      b(640, 85, 'stone', 'plank_v'),
      b(735, 85, 'stone', 'plank_v'),
      b(630, 165, 'stone', 'plank_h'),
      b(720, 165, 'stone', 'plank_h'),
      b(680, 200, 'wood', 'square'),
      b(660, 250, 'wood', 'plank_v'),
      b(700, 250, 'wood', 'plank_v'),
      b(650, 330, 'wood', 'plank_h'),
    ],
    enemies: [e(690, 50), e(690, 170), e(690, 255), e(690, 335)],
  },

  // Level 29: Glass Menagerie
  29: {
    blocks: [
      b(600, 40, 'glass', 'square'),
      b(650, 40, 'glass', 'square'),
      b(700, 40, 'glass', 'square'),
      b(750, 40, 'glass', 'square'),
      b(800, 40, 'glass', 'square'),
      b(620, 85, 'glass', 'plank_v'),
      b(730, 85, 'glass', 'plank_v'),
      b(610, 165, 'glass', 'plank_h'),
      b(720, 165, 'glass', 'plank_h'),
      b(650, 210, 'stone', 'square'),
      b(700, 210, 'stone', 'square'),
      b(675, 255, 'tnt', 'square'),
    ],
    enemies: [e(625, 50), e(675, 50), e(725, 50), e(775, 50), e(675, 170)],
  },

  // Level 30: Fortified Base
  30: {
    blocks: [
      b(580, 40, 'stone', 'square'),
      b(625, 40, 'stone', 'square'),
      b(670, 40, 'stone', 'square'),
      b(715, 40, 'stone', 'square'),
      b(760, 40, 'stone', 'square'),
      b(600, 85, 'stone', 'plank_v'),
      b(740, 85, 'stone', 'plank_v'),
      b(590, 165, 'stone', 'plank_h'),
      b(680, 165, 'stone', 'plank_h'),
      b(640, 200, 'wood', 'square'),
      b(685, 200, 'wood', 'square'),
      b(660, 245, 'tnt', 'square'),
      b(640, 290, 'wood', 'plank_v'),
      b(680, 290, 'wood', 'plank_v'),
      b(630, 370, 'wood', 'plank_h'),
    ],
    enemies: [e(670, 50), e(670, 170), e(670, 250), e(670, 375)],
  },

  // ==================== LEVELS 31-40 ====================

  // Level 31: TNT Chain Reaction
  31: {
    blocks: [
      b(550, 40, 'tnt', 'square'),
      b(600, 40, 'wood', 'square'),
      b(650, 40, 'tnt', 'square'),
      b(700, 40, 'wood', 'square'),
      b(750, 40, 'tnt', 'square'),
      b(575, 85, 'wood', 'plank_h'),
      b(675, 85, 'wood', 'plank_h'),
      b(620, 130, 'ice', 'square'),
      b(680, 130, 'ice', 'square'),
      b(650, 175, 'stone', 'square'),
    ],
    enemies: [e(560, 50), e(660, 50), e(760, 50), e(650, 90), e(660, 180)],
  },

  // Level 32: Rolling Thunder
  32: {
    blocks: [
      b(550, 350, 'boulder', 'circle'),
      b(650, 350, 'boulder', 'circle'),
      b(750, 350, 'boulder', 'circle'),
      b(600, 40, 'wood', 'square'),
      b(650, 40, 'wood', 'square'),
      b(700, 40, 'wood', 'square'),
      b(600, 85, 'wood', 'plank_v'),
      b(720, 85, 'wood', 'plank_v'),
      b(590, 165, 'ice', 'plank_h'),
      b(660, 200, 'ice', 'square'),
      b(600, 250, 'wood', 'plank_v'),
      b(720, 250, 'wood', 'plank_v'),
      b(590, 330, 'wood', 'plank_h'),
    ],
    enemies: [e(660, 50), e(660, 170), e(660, 205), e(660, 335)],
  },

  // Level 33: Ice Palace
  33: {
    blocks: [
      b(580, 40, 'ice', 'square'),
      b(620, 40, 'ice', 'square'),
      b(660, 40, 'ice', 'square'),
      b(700, 40, 'ice', 'square'),
      b(740, 40, 'ice', 'square'),
      b(780, 40, 'ice', 'square'),
      b(600, 85, 'ice', 'plank_v'),
      b(700, 85, 'ice', 'plank_v'),
      b(760, 85, 'ice', 'plank_v'),
      b(590, 165, 'ice', 'plank_h'),
      b(690, 165, 'ice', 'plank_h'),
      b(640, 210, 'stone', 'square'),
      b(720, 210, 'stone', 'square'),
      b(680, 255, 'ice', 'plank_h'),
    ],
    enemies: [e(600, 50), e(680, 50), e(760, 50), e(660, 170), e(680, 260)],
  },

  // Level 34: Wheel Tower
  34: {
    blocks: [
      b(600, 40, 'wheel', 'circle'),
      b(750, 40, 'wheel', 'circle'),
      b(630, 80, 'wood', 'plank_h'),
      b(710, 80, 'wood', 'plank_h'),
      b(650, 120, 'stone', 'pillar'),
      b(720, 120, 'stone', 'pillar'),
      b(640, 130, 'wood', 'plank_h'),
      b(670, 170, 'ice', 'square'),
      b(700, 170, 'ice', 'square'),
      b(670, 215, 'wood', 'plank_v'),
      b(720, 215, 'wood', 'plank_v'),
      b(660, 295, 'wood', 'plank_h'),
    ],
    enemies: [e(670, 85), e(690, 175), e(690, 300)],
  },

  // Level 35: Triangle Mountain
  35: {
    blocks: [
      b(580, 40, 'triangle', 'triangle_left'),
      b(780, 40, 'triangle', 'triangle_right'),
      b(620, 80, 'stone', 'square'),
      b(665, 80, 'stone', 'square'),
      b(710, 80, 'stone', 'square'),
      b(640, 125, 'wood', 'square'),
      b(685, 125, 'wood', 'square'),
      b(660, 170, 'wood', 'square'),
      b(660, 215, 'tnt', 'square'),
      b(640, 260, 'ice', 'plank_v'),
      b(680, 260, 'ice', 'plank_v'),
      b(630, 340, 'ice', 'plank_h'),
    ],
    enemies: [e(670, 90), e(670, 175), e(670, 265), e(670, 345)],
  },

  // Level 36: Double Deck
  36: {
    blocks: [
      // Upper deck
      b(550, 200, 'stone', 'pillar'),
      b(630, 200, 'stone', 'pillar'),
      b(540, 210, 'wood', 'plank_h'),
      b(570, 250, 'ice', 'square'),
      b(600, 250, 'ice', 'square'),
      // Lower deck
      b(720, 80, 'stone', 'pillar'),
      b(800, 80, 'stone', 'pillar'),
      b(710, 90, 'wood', 'plank_h'),
      b(750, 130, 'ice', 'square'),
      b(780, 130, 'ice', 'square'),
    ],
    enemies: [e(580, 255), e(610, 255), e(760, 135), e(790, 135)],
  },

  // Level 37: TNT Bunker
  37: {
    blocks: [
      b(620, 40, 'stone', 'square'),
      b(665, 40, 'stone', 'square'),
      b(710, 40, 'stone', 'square'),
      b(620, 85, 'stone', 'plank_v'),
      b(730, 85, 'stone', 'plank_v'),
      b(665, 130, 'tnt', 'square'),
      b(610, 165, 'stone', 'plank_h'),
      b(700, 165, 'stone', 'plank_h'),
      b(640, 210, 'wood', 'square'),
      b(685, 210, 'wood', 'square'),
      b(660, 255, 'wood', 'plank_h'),
    ],
    enemies: [e(665, 50), e(665, 170), e(665, 260)],
  },

  // Level 38: Wheel Fortress
  38: {
    blocks: [
      b(540, 40, 'wheel', 'circle'),
      b(640, 40, 'wheel', 'circle'),
      b(740, 40, 'wheel', 'circle'),
      b(560, 80, 'wood', 'plank_h'),
      b(660, 80, 'wood', 'plank_h'),
      b(600, 120, 'stone', 'pillar'),
      b(700, 120, 'stone', 'pillar'),
      b(590, 130, 'wood', 'plank_h'),
      b(630, 170, 'ice', 'square'),
      b(670, 170, 'ice', 'square'),
      b(650, 215, 'tnt', 'square'),
    ],
    enemies: [e(610, 85), e(710, 85), e(650, 175), e(660, 220)],
  },

  // Level 39: Glass Towers
  39: {
    blocks: [
      // Tower 1
      b(550, 40, 'glass', 'square'),
      b(550, 85, 'glass', 'plank_v'),
      b(570, 85, 'glass', 'plank_v'),
      b(540, 165, 'glass', 'plank_h'),
      // Tower 2
      b(680, 40, 'glass', 'square'),
      b(680, 85, 'glass', 'plank_v'),
      b(700, 85, 'glass', 'plank_v'),
      b(670, 165, 'glass', 'plank_h'),
      // Tower 3
      b(810, 40, 'glass', 'square'),
      b(810, 85, 'glass', 'plank_v'),
      b(830, 85, 'glass', 'plank_v'),
      b(800, 165, 'glass', 'plank_h'),
    ],
    enemies: [e(560, 50), e(560, 170), e(690, 50), e(690, 170), e(820, 50), e(820, 170)],
  },

  // Level 40: Boulder Canyon
  40: {
    blocks: [
      b(500, 380, 'boulder', 'circle'),
      b(600, 380, 'boulder', 'circle'),
      b(700, 380, 'boulder', 'circle'),
      b(800, 380, 'boulder', 'circle'),
      // Canyon walls
      b(550, 40, 'stone', 'square'),
      b(750, 40, 'stone', 'square'),
      b(550, 85, 'stone', 'plank_v'),
      b(770, 85, 'stone', 'plank_v'),
      b(540, 165, 'wood', 'plank_h'),
      b(700, 165, 'wood', 'plank_h'),
      // Center
      b(630, 100, 'ice', 'square'),
      b(680, 100, 'ice', 'square'),
      b(655, 145, 'wood', 'plank_h'),
      b(650, 190, 'wood', 'plank_v'),
      b(680, 190, 'wood', 'plank_v'),
      b(640, 270, 'wood', 'plank_h'),
    ],
    enemies: [e(560, 50), e(760, 50), e(660, 150), e(665, 275)],
  },

  // ==================== LEVELS 41-50 ====================

  // Level 41: TNT Mountain
  41: {
    blocks: [
      b(620, 40, 'tnt', 'square'),
      b(680, 40, 'tnt', 'square'),
      b(740, 40, 'tnt', 'square'),
      b(650, 85, 'wood', 'square'),
      b(710, 85, 'wood', 'square'),
      b(680, 130, 'stone', 'square'),
      b(680, 175, 'wood', 'plank_v'),
      b(700, 175, 'wood', 'plank_v'),
      b(670, 255, 'wood', 'plank_h'),
      b(680, 300, 'stone', 'square'),
    ],
    enemies: [e(660, 90), e(720, 90), e(685, 260), e(690, 305)],
  },

  // Level 42: Wheel Madness
  42: {
    blocks: [
      b(520, 40, 'wheel', 'circle'),
      b(600, 40, 'wheel', 'circle'),
      b(680, 40, 'wheel', 'circle'),
      b(760, 40, 'wheel', 'circle'),
      b(560, 80, 'wood', 'plank_h'),
      b(640, 80, 'wood', 'plank_h'),
      b(720, 80, 'wood', 'plank_h'),
      b(600, 120, 'stone', 'pillar'),
      b(700, 120, 'stone', 'pillar'),
      b(590, 130, 'ice', 'plank_h'),
      b(650, 170, 'ice', 'square'),
      b(700, 170, 'ice', 'square'),
      b(675, 215, 'wood', 'plank_h'),
    ],
    enemies: [e(570, 85), e(650, 85), e(730, 85), e(675, 220)],
  },

  // Level 43: Stone Citadel
  43: {
    blocks: [
      b(580, 40, 'stone', 'square'),
      b(625, 40, 'stone', 'square'),
      b(670, 40, 'stone', 'square'),
      b(715, 40, 'stone', 'square'),
      b(760, 40, 'stone', 'square'),
      b(600, 85, 'stone', 'plank_v'),
      b(740, 85, 'stone', 'plank_v'),
      b(590, 165, 'stone', 'plank_h'),
      b(720, 165, 'stone', 'plank_h'),
      b(650, 200, 'ice', 'square'),
      b(695, 200, 'ice', 'square'),
      b(670, 245, 'tnt', 'square'),
      b(650, 290, 'wood', 'plank_v'),
      b(690, 290, 'wood', 'plank_v'),
      b(640, 370, 'wood', 'plank_h'),
    ],
    enemies: [e(670, 50), e(670, 170), e(670, 250), e(670, 375)],
  },

  // Level 44: Glass Palace
  44: {
    blocks: [
      b(560, 40, 'glass', 'square'),
      b(600, 40, 'glass', 'square'),
      b(640, 40, 'glass', 'square'),
      b(680, 40, 'glass', 'square'),
      b(720, 40, 'glass', 'square'),
      b(760, 40, 'glass', 'square'),
      b(580, 85, 'glass', 'plank_v'),
      b(680, 85, 'glass', 'plank_v'),
      b(740, 85, 'glass', 'plank_v'),
      b(570, 165, 'glass', 'plank_h'),
      b(670, 165, 'glass', 'plank_h'),
      b(620, 210, 'stone', 'square'),
      b(700, 210, 'stone', 'square'),
      b(660, 255, 'tnt', 'square'),
    ],
    enemies: [e(580, 50), e(660, 50), e(740, 50), e(640, 170), e(665, 260)],
  },

  // Level 45: Multi Boulder
  45: {
    blocks: [
      b(550, 400, 'boulder', 'circle'),
      b(650, 400, 'boulder', 'circle'),
      b(750, 400, 'boulder', 'circle'),
      b(600, 350, 'boulder', 'circle'),
      b(700, 350, 'boulder', 'circle'),
      b(600, 40, 'wood', 'square'),
      b(650, 40, 'wood', 'square'),
      b(700, 40, 'wood', 'square'),
      b(600, 85, 'wood', 'plank_v'),
      b(720, 85, 'wood', 'plank_v'),
      b(590, 165, 'wood', 'plank_h'),
      b(650, 200, 'ice', 'square'),
      b(700, 200, 'ice', 'square'),
      b(675, 245, 'stone', 'plank_h'),
      b(650, 290, 'stone', 'plank_v'),
      b(700, 290, 'stone', 'plank_v'),
    ],
    enemies: [e(660, 50), e(660, 170), e(675, 250)],
  },

  // Level 46: Triangle Fortress
  46: {
    blocks: [
      b(560, 40, 'triangle', 'triangle_left'),
      b(800, 40, 'triangle', 'triangle_right'),
      b(600, 80, 'stone', 'square'),
      b(650, 80, 'stone', 'square'),
      b(700, 80, 'stone', 'square'),
      b(750, 80, 'stone', 'square'),
      b(625, 125, 'wood', 'plank_v'),
      b(725, 125, 'wood', 'plank_v'),
      b(615, 205, 'wood', 'plank_h'),
      b(715, 205, 'wood', 'plank_h'),
      b(660, 250, 'tnt', 'square'),
      b(700, 250, 'tnt', 'square'),
    ],
    enemies: [e(630, 90), e(720, 90), e(660, 210), e(680, 255)],
  },

  // Level 47: Ice Kingdom
  47: {
    blocks: [
      b(540, 40, 'ice', 'square'),
      b(580, 40, 'ice', 'square'),
      b(620, 40, 'ice', 'square'),
      b(660, 40, 'ice', 'square'),
      b(700, 40, 'ice', 'square'),
      b(740, 40, 'ice', 'square'),
      b(780, 40, 'ice', 'square'),
      b(560, 85, 'ice', 'plank_v'),
      b(660, 85, 'ice', 'plank_v'),
      b(760, 85, 'ice', 'plank_v'),
      b(550, 165, 'ice', 'plank_h'),
      b(650, 165, 'ice', 'plank_h'),
      b(750, 165, 'ice', 'plank_h'),
      b(600, 210, 'stone', 'square'),
      b(660, 210, 'stone', 'square'),
      b(720, 210, 'stone', 'square'),
      b(660, 255, 'tnt', 'square'),
    ],
    enemies: [e(560, 50), e(660, 50), e(760, 50), e(620, 170), e(730, 170), e(665, 260)],
  },

  // Level 48: Wheel Castle
  48: {
    blocks: [
      b(500, 40, 'wheel', 'circle'),
      b(580, 40, 'wheel', 'circle'),
      b(700, 40, 'wheel', 'circle'),
      b(780, 40, 'wheel', 'circle'),
      b(540, 80, 'wood', 'plank_h'),
      b(640, 80, 'wood', 'plank_h'),
      b(740, 80, 'wood', 'plank_h'),
      b(580, 120, 'stone', 'pillar'),
      b(680, 120, 'stone', 'pillar'),
      b(570, 130, 'wood', 'plank_h'),
      b(620, 170, 'ice', 'square'),
      b(660, 170, 'ice', 'square'),
      b(640, 215, 'tnt', 'square'),
      b(620, 260, 'wood', 'plank_v'),
      b(660, 260, 'wood', 'plank_v'),
      b(610, 340, 'wood', 'plank_h'),
    ],
    enemies: [e(590, 85), e(690, 85), e(640, 175), e(640, 345)],
  },

  // Level 49: TNT Surprise Party
  49: {
    blocks: [
      b(560, 40, 'tnt', 'square'),
      b(620, 40, 'wood', 'square'),
      b(680, 40, 'tnt', 'square'),
      b(740, 40, 'wood', 'square'),
      b(800, 40, 'tnt', 'square'),
      b(590, 85, 'wood', 'plank_h'),
      b(710, 85, 'wood', 'plank_h'),
      b(650, 130, 'stone', 'square'),
      b(700, 130, 'stone', 'square'),
      b(675, 175, 'tnt', 'square'),
      b(650, 220, 'ice', 'plank_v'),
      b(700, 220, 'ice', 'plank_v'),
      b(640, 300, 'ice', 'plank_h'),
    ],
    enemies: [e(630, 50), e(750, 50), e(675, 180), e(675, 305)],
  },

  // Level 50: Grand Fortress
  50: {
    blocks: [
      b(500, 40, 'stone', 'square'),
      b(550, 40, 'stone', 'square'),
      b(600, 40, 'stone', 'square'),
      b(650, 40, 'stone', 'square'),
      b(700, 40, 'stone', 'square'),
      b(750, 40, 'stone', 'square'),
      b(800, 40, 'stone', 'square'),
      b(525, 85, 'stone', 'plank_v'),
      b(625, 85, 'stone', 'plank_v'),
      b(725, 85, 'stone', 'plank_v'),
      b(775, 85, 'stone', 'plank_v'),
      b(515, 165, 'wood', 'plank_h'),
      b(615, 165, 'wood', 'plank_h'),
      b(715, 165, 'wood', 'plank_h'),
      b(570, 210, 'ice', 'square'),
      b(620, 210, 'ice', 'square'),
      b(680, 210, 'ice', 'square'),
      b(730, 210, 'ice', 'square'),
      b(650, 255, 'tnt', 'square'),
      b(620, 300, 'wood', 'plank_v'),
      b(680, 300, 'wood', 'plank_v'),
      b(610, 380, 'wood', 'plank_h'),
    ],
    enemies: [e(525, 50), e(625, 50), e(725, 50), e(650, 170), e(650, 260), e(650, 385)],
  },

  // ==================== LEVELS 51-60 ====================

  // Level 51: Boulder Madness
  51: {
    blocks: [
      b(480, 400, 'boulder', 'circle'),
      b(560, 400, 'boulder', 'circle'),
      b(640, 400, 'boulder', 'circle'),
      b(720, 400, 'boulder', 'circle'),
      b(800, 400, 'boulder', 'circle'),
      b(520, 350, 'boulder', 'circle'),
      b(680, 350, 'boulder', 'circle'),
      b(600, 40, 'stone', 'square'),
      b(650, 40, 'stone', 'square'),
      b(700, 40, 'stone', 'square'),
      b(600, 85, 'stone', 'plank_v'),
      b(720, 85, 'stone', 'plank_v'),
      b(590, 165, 'stone', 'plank_h'),
      b(650, 200, 'wood', 'square'),
      b(700, 200, 'wood', 'square'),
      b(675, 245, 'ice', 'plank_h'),
    ],
    enemies: [e(660, 50), e(660, 170), e(675, 250)],
  },

  // Level 52: Glass Labyrinth
  52: {
    blocks: [
      b(520, 40, 'glass', 'square'),
      b(560, 40, 'glass', 'square'),
      b(600, 40, 'glass', 'square'),
      b(640, 40, 'glass', 'square'),
      b(680, 40, 'glass', 'square'),
      b(720, 40, 'glass', 'square'),
      b(760, 40, 'glass', 'square'),
      b(800, 40, 'glass', 'square'),
      b(540, 85, 'glass', 'plank_v'),
      b(620, 85, 'glass', 'plank_v'),
      b(700, 85, 'glass', 'plank_v'),
      b(780, 85, 'glass', 'plank_v'),
      b(530, 165, 'glass', 'plank_h'),
      b(610, 165, 'glass', 'plank_h'),
      b(690, 165, 'glass', 'plank_h'),
      b(770, 165, 'glass', 'plank_h'),
      b(580, 210, 'tnt', 'square'),
      b(660, 210, 'tnt', 'square'),
      b(740, 210, 'tnt', 'square'),
    ],
    enemies: [e(540, 50), e(620, 50), e(700, 50), e(780, 50), e(620, 170), e(700, 170)],
  },

  // Level 53: TNT Cascade
  53: {
    blocks: [
      b(580, 40, 'tnt', 'square'),
      b(640, 40, 'tnt', 'square'),
      b(700, 40, 'tnt', 'square'),
      b(760, 40, 'tnt', 'square'),
      b(610, 85, 'wood', 'plank_h'),
      b(730, 85, 'wood', 'plank_h'),
      b(670, 130, 'tnt', 'square'),
      b(640, 175, 'stone', 'plank_v'),
      b(700, 175, 'stone', 'plank_v'),
      b(630, 255, 'stone', 'plank_h'),
      b(670, 300, 'ice', 'square'),
    ],
    enemies: [e(590, 50), e(710, 50), e(670, 90), e(670, 260), e(680, 305)],
  },

  // Level 54: Wheel Highway
  54: {
    blocks: [
      b(480, 40, 'wheel', 'circle'),
      b(540, 40, 'wheel', 'circle'),
      b(600, 40, 'wheel', 'circle'),
      b(700, 40, 'wheel', 'circle'),
      b(760, 40, 'wheel', 'circle'),
      b(820, 40, 'wheel', 'circle'),
      b(510, 80, 'wood', 'plank_h'),
      b(590, 80, 'wood', 'plank_h'),
      b(730, 80, 'wood', 'plank_h'),
      b(810, 80, 'wood', 'plank_h'),
      b(560, 120, 'stone', 'pillar'),
      b(770, 120, 'stone', 'pillar'),
      b(550, 130, 'ice', 'plank_h'),
      b(760, 130, 'ice', 'plank_h'),
      b(660, 170, 'tnt', 'square'),
    ],
    enemies: [e(530, 85), e(650, 85), e(750, 85), e(665, 175)],
  },

  // Level 55: Triangle Symphony
  55: {
    blocks: [
      b(520, 40, 'triangle', 'triangle_left'),
      b(600, 40, 'triangle', 'triangle_right'),
      b(700, 40, 'triangle', 'triangle_left'),
      b(780, 40, 'triangle', 'triangle_right'),
      b(560, 80, 'stone', 'square'),
      b(640, 80, 'stone', 'square'),
      b(720, 80, 'stone', 'square'),
      b(600, 125, 'wood', 'plank_v'),
      b(700, 125, 'wood', 'plank_v'),
      b(590, 205, 'wood', 'plank_h'),
      b(690, 205, 'wood', 'plank_h'),
      b(640, 250, 'tnt', 'square'),
      b(700, 250, 'tnt', 'square'),
    ],
    enemies: [e(570, 90), e(650, 90), e(730, 90), e(660, 210), e(670, 255)],
  },

  // Level 56: Ice Fortress
  56: {
    blocks: [
      b(520, 40, 'ice', 'square'),
      b(560, 40, 'ice', 'square'),
      b(600, 40, 'ice', 'square'),
      b(640, 40, 'ice', 'square'),
      b(680, 40, 'ice', 'square'),
      b(720, 40, 'ice', 'square'),
      b(760, 40, 'ice', 'square'),
      b(800, 40, 'ice', 'square'),
      b(540, 85, 'stone', 'pillar'),
      b(620, 85, 'stone', 'pillar'),
      b(700, 85, 'stone', 'pillar'),
      b(780, 85, 'stone', 'pillar'),
      b(530, 95, 'ice', 'plank_h'),
      b(610, 95, 'ice', 'plank_h'),
      b(690, 95, 'ice', 'plank_h'),
      b(580, 140, 'ice', 'square'),
      b(660, 140, 'ice', 'square'),
      b(740, 140, 'ice', 'square'),
      b(620, 185, 'tnt', 'square'),
      b(700, 185, 'tnt', 'square'),
    ],
    enemies: [e(540, 50), e(660, 50), e(780, 50), e(620, 145), e(700, 145), e(660, 190)],
  },

  // Level 57: Boulder Valley
  57: {
    blocks: [
      b(450, 400, 'boulder', 'circle'),
      b(550, 400, 'boulder', 'circle'),
      b(650, 400, 'boulder', 'circle'),
      b(750, 400, 'boulder', 'circle'),
      b(850, 400, 'boulder', 'circle'),
      b(500, 350, 'boulder', 'circle'),
      b(600, 350, 'boulder', 'circle'),
      b(700, 350, 'boulder', 'circle'),
      b(800, 350, 'boulder', 'circle'),
      b(580, 40, 'stone', 'square'),
      b(640, 40, 'stone', 'square'),
      b(700, 40, 'stone', 'square'),
      b(760, 40, 'stone', 'square'),
      b(610, 85, 'wood', 'plank_v'),
      b(730, 85, 'wood', 'plank_v'),
      b(600, 165, 'wood', 'plank_h'),
      b(720, 165, 'wood', 'plank_h'),
      b(660, 210, 'tnt', 'square'),
    ],
    enemies: [e(610, 50), e(730, 50), e(660, 170), e(665, 215)],
  },

  // Level 58: Wheel Arena
  58: {
    blocks: [
      b(460, 40, 'wheel', 'circle'),
      b(540, 40, 'wheel', 'circle'),
      b(620, 40, 'wheel', 'circle'),
      b(700, 40, 'wheel', 'circle'),
      b(780, 40, 'wheel', 'circle'),
      b(860, 40, 'wheel', 'circle'),
      b(500, 80, 'wood', 'plank_h'),
      b(580, 80, 'wood', 'plank_h'),
      b(660, 80, 'wood', 'plank_h'),
      b(740, 80, 'wood', 'plank_h'),
      b(820, 80, 'wood', 'plank_h'),
      b(540, 120, 'stone', 'pillar'),
      b(620, 120, 'stone', 'pillar'),
      b(700, 120, 'stone', 'pillar'),
      b(780, 120, 'stone', 'pillar'),
      b(530, 130, 'ice', 'plank_h'),
      b(610, 130, 'ice', 'plank_h'),
      b(690, 130, 'ice', 'plank_h'),
      b(580, 175, 'tnt', 'square'),
      b(660, 175, 'tnt', 'square'),
      b(740, 175, 'tnt', 'square'),
    ],
    enemies: [e(510, 85), e(590, 85), e(670, 85), e(750, 85), e(830, 85), e(660, 180)],
  },

  // Level 59: TNT Volcano
  59: {
    blocks: [
      b(620, 40, 'tnt', 'square'),
      b(660, 40, 'tnt', 'square'),
      b(700, 40, 'tnt', 'square'),
      b(640, 85, 'tnt', 'square'),
      b(680, 85, 'tnt', 'square'),
      b(660, 130, 'stone', 'square'),
      b(660, 175, 'stone', 'plank_v'),
      b(680, 175, 'stone', 'plank_v'),
      b(650, 255, 'stone', 'plank_h'),
      b(660, 300, 'wood', 'square'),
      b(700, 300, 'wood', 'square'),
      b(680, 345, 'ice', 'plank_h'),
    ],
    enemies: [e(630, 50), e(710, 50), e(670, 260), e(680, 305), e(680, 350)],
  },

  // Level 60: Ultimate Challenge
  60: {
    blocks: [
      b(480, 40, 'stone', 'square'),
      b(530, 40, 'stone', 'square'),
      b(580, 40, 'stone', 'square'),
      b(630, 40, 'stone', 'square'),
      b(680, 40, 'stone', 'square'),
      b(730, 40, 'stone', 'square'),
      b(780, 40, 'stone', 'square'),
      b(830, 40, 'stone', 'square'),
      b(505, 85, 'stone', 'plank_v'),
      b(605, 85, 'stone', 'plank_v'),
      b(705, 85, 'stone', 'plank_v'),
      b(805, 85, 'stone', 'plank_v'),
      b(495, 165, 'wood', 'plank_h'),
      b(595, 165, 'wood', 'plank_h'),
      b(695, 165, 'wood', 'plank_h'),
      b(795, 165, 'wood', 'plank_h'),
      b(550, 210, 'ice', 'square'),
      b(600, 210, 'ice', 'square'),
      b(650, 210, 'ice', 'square'),
      b(700, 210, 'ice', 'square'),
      b(750, 210, 'ice', 'square'),
      b(600, 255, 'tnt', 'square'),
      b(700, 255, 'tnt', 'square'),
      b(650, 300, 'boulder', 'circle'),
      b(600, 350, 'wood', 'plank_v'),
      b(700, 350, 'wood', 'plank_v'),
      b(590, 430, 'wood', 'plank_h'),
    ],
    enemies: [e(505, 50), e(605, 50), e(705, 50), e(805, 50), e(620, 170), e(730, 170), e(650, 260), e(650, 435)],
  },

  // ==================== LEVELS 61-68 (Final) ====================

  // Level 61: Boulder Apocalypse
  61: {
    blocks: [
      b(400, 420, 'boulder', 'circle'),
      b(500, 420, 'boulder', 'circle'),
      b(600, 420, 'boulder', 'circle'),
      b(700, 420, 'boulder', 'circle'),
      b(800, 420, 'boulder', 'circle'),
      b(900, 420, 'boulder', 'circle'),
      b(450, 370, 'boulder', 'circle'),
      b(550, 370, 'boulder', 'circle'),
      b(650, 370, 'boulder', 'circle'),
      b(750, 370, 'boulder', 'circle'),
      b(850, 370, 'boulder', 'circle'),
      b(580, 40, 'stone', 'square'),
      b(640, 40, 'stone', 'square'),
      b(700, 40, 'stone', 'square'),
      b(760, 40, 'stone', 'square'),
      b(610, 85, 'stone', 'plank_v'),
      b(730, 85, 'stone', 'plank_v'),
      b(600, 165, 'stone', 'plank_h'),
      b(720, 165, 'stone', 'plank_h'),
      b(660, 210, 'tnt', 'square'),
    ],
    enemies: [e(610, 50), e(730, 50), e(660, 170), e(665, 215)],
  },

  // Level 62: Glass Kingdom
  62: {
    blocks: [
      b(480, 40, 'glass', 'square'),
      b(530, 40, 'glass', 'square'),
      b(580, 40, 'glass', 'square'),
      b(630, 40, 'glass', 'square'),
      b(680, 40, 'glass', 'square'),
      b(730, 40, 'glass', 'square'),
      b(780, 40, 'glass', 'square'),
      b(830, 40, 'glass', 'square'),
      b(505, 85, 'glass', 'plank_v'),
      b(605, 85, 'glass', 'plank_v'),
      b(705, 85, 'glass', 'plank_v'),
      b(805, 85, 'glass', 'plank_v'),
      b(495, 165, 'glass', 'plank_h'),
      b(595, 165, 'glass', 'plank_h'),
      b(695, 165, 'glass', 'plank_h'),
      b(795, 165, 'glass', 'plank_h'),
      b(550, 210, 'tnt', 'square'),
      b(650, 210, 'tnt', 'square'),
      b(750, 210, 'tnt', 'square'),
    ],
    enemies: [e(505, 50), e(605, 50), e(705, 50), e(805, 50), e(570, 170), e(670, 170), e(770, 170)],
  },

  // Level 63: Wheel Empire
  63: {
    blocks: [
      b(420, 40, 'wheel', 'circle'),
      b(500, 40, 'wheel', 'circle'),
      b(580, 40, 'wheel', 'circle'),
      b(660, 40, 'wheel', 'circle'),
      b(740, 40, 'wheel', 'circle'),
      b(820, 40, 'wheel', 'circle'),
      b(900, 40, 'wheel', 'circle'),
      b(460, 80, 'wood', 'plank_h'),
      b(540, 80, 'wood', 'plank_h'),
      b(620, 80, 'wood', 'plank_h'),
      b(700, 80, 'wood', 'plank_h'),
      b(780, 80, 'wood', 'plank_h'),
      b(860, 80, 'wood', 'plank_h'),
      b(500, 120, 'stone', 'pillar'),
      b(580, 120, 'stone', 'pillar'),
      b(660, 120, 'stone', 'pillar'),
      b(740, 120, 'stone', 'pillar'),
      b(820, 120, 'stone', 'pillar'),
      b(540, 170, 'tnt', 'square'),
      b(620, 170, 'tnt', 'square'),
      b(700, 170, 'tnt', 'square'),
      b(780, 170, 'tnt', 'square'),
    ],
    enemies: [e(480, 85), e(560, 85), e(640, 85), e(720, 85), e(800, 85), e(880, 85), e(660, 175)],
  },

  // Level 64: TNT Fortress
  64: {
    blocks: [
      b(520, 40, 'tnt', 'square'),
      b(580, 40, 'tnt', 'square'),
      b(640, 40, 'tnt', 'square'),
      b(700, 40, 'tnt', 'square'),
      b(760, 40, 'tnt', 'square'),
      b(820, 40, 'tnt', 'square'),
      b(550, 85, 'stone', 'plank_h'),
      b(670, 85, 'stone', 'plank_h'),
      b(790, 85, 'stone', 'plank_h'),
      b(610, 130, 'stone', 'square'),
      b(680, 130, 'stone', 'square'),
      b(750, 130, 'stone', 'square'),
      b(645, 175, 'tnt', 'square'),
      b(715, 175, 'tnt', 'square'),
      b(680, 220, 'ice', 'plank_h'),
    ],
    enemies: [e(535, 50), e(670, 50), e(805, 50), e(660, 135), e(730, 135), e(680, 225)],
  },

  // Level 65: Triangle Temple
  65: {
    blocks: [
      b(480, 40, 'triangle', 'triangle_left'),
      b(560, 40, 'triangle', 'triangle_right'),
      b(680, 40, 'triangle', 'triangle_left'),
      b(760, 40, 'triangle', 'triangle_right'),
      b(520, 80, 'stone', 'square'),
      b(600, 80, 'stone', 'square'),
      b(680, 80, 'stone', 'square'),
      b(760, 80, 'stone', 'square'),
      b(560, 125, 'wood', 'plank_v'),
      b(720, 125, 'wood', 'plank_v'),
      b(550, 205, 'wood', 'plank_h'),
      b(710, 205, 'wood', 'plank_h'),
      b(600, 250, 'tnt', 'square'),
      b(680, 250, 'tnt', 'square'),
      b(640, 295, 'boulder', 'circle'),
    ],
    enemies: [e(540, 90), e(680, 90), e(780, 90), e(580, 210), e(720, 210), e(645, 300)],
  },

  // Level 66: Ice Apocalypse
  66: {
    blocks: [
      b(460, 40, 'ice', 'square'),
      b(510, 40, 'ice', 'square'),
      b(560, 40, 'ice', 'square'),
      b(610, 40, 'ice', 'square'),
      b(660, 40, 'ice', 'square'),
      b(710, 40, 'ice', 'square'),
      b(760, 40, 'ice', 'square'),
      b(810, 40, 'ice', 'square'),
      b(860, 40, 'ice', 'square'),
      b(485, 85, 'ice', 'plank_v'),
      b(585, 85, 'ice', 'plank_v'),
      b(685, 85, 'ice', 'plank_v'),
      b(785, 85, 'ice', 'plank_v'),
      b(885, 85, 'ice', 'plank_v'),
      b(475, 165, 'ice', 'plank_h'),
      b(575, 165, 'ice', 'plank_h'),
      b(675, 165, 'ice', 'plank_h'),
      b(775, 165, 'ice', 'plank_h'),
      b(530, 210, 'tnt', 'square'),
      b(630, 210, 'tnt', 'square'),
      b(730, 210, 'tnt', 'square'),
      b(830, 210, 'tnt', 'square'),
    ],
    enemies: [e(485, 50), e(585, 50), e(685, 50), e(785, 50), e(885, 50), e(580, 170), e(680, 170), e(780, 170)],
  },

  // Level 67: Final Assault
  67: {
    blocks: [
      b(440, 40, 'stone', 'square'),
      b(490, 40, 'stone', 'square'),
      b(540, 40, 'stone', 'square'),
      b(590, 40, 'stone', 'square'),
      b(640, 40, 'stone', 'square'),
      b(690, 40, 'stone', 'square'),
      b(740, 40, 'stone', 'square'),
      b(790, 40, 'stone', 'square'),
      b(840, 40, 'stone', 'square'),
      b(890, 40, 'stone', 'square'),
      b(465, 85, 'stone', 'pillar'),
      b(565, 85, 'stone', 'pillar'),
      b(665, 85, 'stone', 'pillar'),
      b(765, 85, 'stone', 'pillar'),
      b(865, 85, 'stone', 'pillar'),
      b(455, 95, 'wood', 'plank_h'),
      b(555, 95, 'wood', 'plank_h'),
      b(655, 95, 'wood', 'plank_h'),
      b(755, 95, 'wood', 'plank_h'),
      b(855, 95, 'wood', 'plank_h'),
      b(510, 140, 'ice', 'square'),
      b(610, 140, 'ice', 'square'),
      b(710, 140, 'ice', 'square'),
      b(810, 140, 'ice', 'square'),
      b(560, 185, 'tnt', 'square'),
      b(660, 185, 'tnt', 'square'),
      b(760, 185, 'tnt', 'square'),
      b(610, 230, 'boulder', 'circle'),
      b(710, 230, 'boulder', 'circle'),
    ],
    enemies: [e(465, 50), e(565, 50), e(665, 50), e(765, 50), e(865, 50), e(560, 145), e(660, 145), e(760, 145), e(660, 235)],
  },

  // Level 68: Dragon's Lair (Final Boss Level)
  68: {
    blocks: [
      // Base fortress
      b(400, 40, 'stone', 'square'),
      b(450, 40, 'stone', 'square'),
      b(500, 40, 'stone', 'square'),
      b(550, 40, 'stone', 'square'),
      b(600, 40, 'stone', 'square'),
      b(650, 40, 'stone', 'square'),
      b(700, 40, 'stone', 'square'),
      b(750, 40, 'stone', 'square'),
      b(800, 40, 'stone', 'square'),
      b(850, 40, 'stone', 'square'),
      b(900, 40, 'stone', 'square'),
      // Second level
      b(425, 85, 'stone', 'pillar'),
      b(525, 85, 'stone', 'pillar'),
      b(625, 85, 'stone', 'pillar'),
      b(725, 85, 'stone', 'pillar'),
      b(825, 85, 'stone', 'pillar'),
      b(415, 95, 'ice', 'plank_h'),
      b(515, 95, 'ice', 'plank_h'),
      b(615, 95, 'ice', 'plank_h'),
      b(715, 95, 'ice', 'plank_h'),
      b(815, 95, 'ice', 'plank_h'),
      // Third level
      b(470, 140, 'ice', 'square'),
      b(570, 140, 'ice', 'square'),
      b(670, 140, 'ice', 'square'),
      b(770, 140, 'ice', 'square'),
      // TNT layer
      b(520, 185, 'tnt', 'square'),
      b(620, 185, 'tnt', 'square'),
      b(720, 185, 'tnt', 'square'),
      b(820, 185, 'tnt', 'square'),
      // Boulder layer
      b(470, 230, 'boulder', 'circle'),
      b(570, 230, 'boulder', 'circle'),
      b(670, 230, 'boulder', 'circle'),
      b(770, 230, 'boulder', 'circle'),
      b(870, 230, 'boulder', 'circle'),
      // Top tower
      b(620, 280, 'stone', 'plank_v'),
      b(680, 280, 'stone', 'plank_v'),
      b(610, 360, 'stone', 'plank_h'),
      b(650, 400, 'tnt', 'square'),
    ],
    enemies: [
      e(425, 50), e(525, 50), e(625, 50), e(725, 50), e(825, 50),
      e(520, 145), e(620, 145), e(720, 145),
      e(570, 190), e(670, 190), e(770, 190),
      e(650, 365), e(655, 405)
    ],
  },
};

/**
 * Get level configuration for a specific level number
 */
export function getLevelConfig(levelNum: number): LevelConfig | null {
  return LEVEL_CONFIGS[levelNum] || null;
}

/**
 * Get total number of available levels
 */
export function getTotalLevels(): number {
  return Object.keys(LEVEL_CONFIGS).length;
}
