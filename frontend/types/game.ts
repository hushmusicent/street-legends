export interface Position {
  latitude: number;
  longitude: number;
}

export interface PlayerStats {
  health: number;
  max_health: number;
  attack: number;
  defense: number;
  speed: number;
  luck: number;
  energy: number;
  max_energy: number;
}

export interface Player {
  id: string;
  name: string;
  character_class: string;
  level: number;
  xp: number;
  xp_to_next: number;
  stats: PlayerStats;
  position: Position | null;
  cash: number;
  reputation: number;
  guild_id: string | null;
  equipment: {
    weapon: string | null;
    armor: string | null;
    accessory: string | null;
    vehicle: string | null;
  };
  inventory: InventoryItem[];
  skills: string[];
  wins: number;
  losses: number;
  missions_completed: number;
  created_at: string;
  last_active: string;
}

export interface InventoryItem {
  item_id: string;
  durability: number;
  max_durability: number;
}

export interface Monster {
  id: string;
  name: string;
  description: string;
  monster_type: string;
  level: number;
  stats: {
    health: number;
    attack: number;
    defense: number;
  };
  position: Position;
  loot_cash: number;
  loot_xp: number;
  loot_items: string[];
  spawn_time: string;
  expires_at: string;
}

export interface Mission {
  id: string;
  title: string;
  description: string;
  dialogue: string;
  objectives: string[];
  mission_type: string;
  difficulty: string;
  level_requirement: number;
  position: Position;
  rewards: {
    cash: number;
    xp: number;
    reputation?: number;
  };
  time_limit_minutes: number;
  expires_at: string;
  created_at: string;
}

export interface Battle {
  id: string;
  player_id: string;
  enemy_type: string;
  enemy_id: string;
  enemy_name: string;
  player_health: number;
  enemy_health: number;
  player_max_health: number;
  enemy_max_health: number;
  player_energy: number;
  turn: number;
  status: 'active' | 'won' | 'lost' | 'fled';
  combat_log: string[];
  rewards?: {
    cash: number;
    xp: number;
    items: string[];
  };
  created_at: string;
}

export interface Guild {
  id: string;
  name: string;
  tag: string;
  description: string;
  leader_id: string;
  officers: string[];
  members: string[];
  level: number;
  xp: number;
  territory_count: number;
  total_wins: number;
  created_at: string;
  member_details?: {
    id: string;
    name: string;
    level: number;
    character_class: string;
  }[];
}

export interface Skill {
  id: string;
  name: string;
  damage_mult?: number;
  defense_buff?: number;
  heal_percent?: number;
  crit_chance?: number;
  cost: number;
  unlock_level: number;
  unlocked?: boolean;
}

export interface CharacterClass {
  name: string;
  description: string;
  base_stats: {
    health: number;
    attack: number;
    defense: number;
    speed: number;
    luck: number;
  };
}

export interface NearbyPlayer {
  id: string;
  name: string;
  level: number;
  character_class: string;
  position: Position;
  distance: number;
  guild_id: string | null;
}

export interface LeaderboardEntry {
  rank: number;
  id: string;
  name: string;
  level: number;
  reputation: number;
  wins: number;
  character_class: string;
  profile_pic?: string | null;
}

export interface ChatMessage {
  id: string;
  channel: string;
  player_id: string;
  player_name: string;
  message: string;
  timestamp: string;
}
