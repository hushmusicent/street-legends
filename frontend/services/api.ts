import axios from 'axios';
import { Player, Monster, Mission, Battle, Guild, Skill, CharacterClass, NearbyPlayer, LeaderboardEntry, ChatMessage, Position, FriendInfo, PlayerSearchResult, RelationshipStatus, SocialStats } from '../types/game';

export const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Player APIs
export const getCharacterClasses = async (): Promise<Record<string, CharacterClass>> => {
  const response = await api.get('/classes');
  return response.data;
};

export const createPlayer = async (name: string, character_class: string): Promise<Player> => {
  const response = await api.post('/players', { name, character_class });
  return response.data;
};

export const getPlayer = async (playerId: string): Promise<Player> => {
  const response = await api.get(`/players/${playerId}`);
  return response.data;
};

export const updatePlayerPosition = async (playerId: string, position: Position): Promise<void> => {
  await api.put(`/players/${playerId}/position`, position);
};

export const getNearbyPlayers = async (playerId: string, radius: number = 500): Promise<NearbyPlayer[]> => {
  const response = await api.get(`/players/nearby/${playerId}?radius=${radius}`);
  return response.data;
};

export const getLeaderboard = async (limit: number = 20): Promise<LeaderboardEntry[]> => {
  const response = await api.get(`/leaderboard?limit=${limit}`);
  return response.data;
};

// Social / Friends APIs
export const searchPlayers = async (name: string, limit: number = 20): Promise<PlayerSearchResult[]> => {
  const response = await api.get(`/players/search?name=${encodeURIComponent(name)}&limit=${limit}`);
  return response.data;
};

export const getSocialStats = async (playerId: string): Promise<SocialStats> => {
  const response = await api.get(`/players/${playerId}/social-stats`);
  return response.data;
};

export const getFriendsList = async (playerId: string): Promise<FriendInfo[]> => {
  const response = await api.get(`/players/${playerId}/friends`);
  return response.data;
};

export const getFriendRequests = async (playerId: string): Promise<PlayerSearchResult[]> => {
  const response = await api.get(`/players/${playerId}/friend-requests`);
  return response.data;
};

export const getRelationshipStatus = async (playerId: string, targetId: string): Promise<RelationshipStatus> => {
  const response = await api.get(`/players/${playerId}/relationship/${targetId}`);
  return response.data;
};

export const followPlayer = async (playerId: string, targetId: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.post(`/players/${playerId}/follow/${targetId}`);
  return response.data;
};

export const unfollowPlayer = async (playerId: string, targetId: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.delete(`/players/${playerId}/unfollow/${targetId}`);
  return response.data;
};

export const sendFriendRequest = async (playerId: string, targetId: string): Promise<{ message: string; success: boolean; became_friends?: boolean }> => {
  const response = await api.post(`/players/${playerId}/friend-request/${targetId}`);
  return response.data;
};

export const acceptFriendRequest = async (playerId: string, targetId: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.post(`/players/${playerId}/accept-friend/${targetId}`);
  return response.data;
};

export const rejectFriendRequest = async (playerId: string, targetId: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.post(`/players/${playerId}/reject-friend/${targetId}`);
  return response.data;
};

export const removeFriend = async (playerId: string, targetId: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.delete(`/players/${playerId}/remove-friend/${targetId}`);
  return response.data;
};

// Monster APIs
export const spawnMonsters = async (latitude: number, longitude: number, playerLevel: number): Promise<Monster[]> => {
  const response = await api.get(`/monsters/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const getMonster = async (monsterId: string): Promise<Monster> => {
  const response = await api.get(`/monsters/${monsterId}`);
  return response.data;
};

// Battle APIs
export const startBattle = async (playerId: string, enemyType: string, enemyId: string): Promise<Battle> => {
  const response = await api.post(`/battles/start?player_id=${playerId}&enemy_type=${enemyType}&enemy_id=${enemyId}`);
  return response.data;
};

export const battleAction = async (battleId: string, action: string, skillId?: string): Promise<Battle> => {
  const response = await api.post(`/battles/${battleId}/action`, { action, skill_id: skillId });
  return response.data;
};

export const getBattle = async (battleId: string): Promise<Battle> => {
  const response = await api.get(`/battles/${battleId}`);
  return response.data;
};

// Mission APIs
export const generateMissions = async (latitude: number, longitude: number, playerLevel: number, playerId?: string): Promise<Mission[]> => {
  let url = `/missions/generate?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`;
  if (playerId) url += `&player_id=${playerId}`;
  const response = await api.get(url);
  return response.data;
};

export const completeMission = async (missionId: string, playerId: string): Promise<{ message: string; rewards: any; level_up: boolean }> => {
  const response = await api.post(`/missions/${missionId}/complete?player_id=${playerId}`);
  return response.data;
};

export const getActiveMissions = async (playerId: string): Promise<any[]> => {
  const response = await api.get(`/missions/active/${playerId}`);
  return response.data;
};

export const cancelMission = async (missionId: string, playerId: string): Promise<{ message: string }> => {
  const response = await api.post(`/missions/${missionId}/cancel?player_id=${playerId}`);
  return response.data;
};

export const collectTerritoryIncome = async (playerId: string): Promise<{ message: string; income: number; territories: number }> => {
  const response = await api.post(`/territories/collect-income/${playerId}`);
  return response.data;
};

export const getTerritoryIncomePreview = async (playerId: string): Promise<{ available_income: number; ready_territories: number; total_territories: number; next_collection_hours: number }> => {
  const response = await api.get(`/territories/income-preview/${playerId}`);
  return response.data;
};

// Guild APIs
export const createGuild = async (name: string, tag: string, description: string, leaderId: string): Promise<Guild> => {
  const response = await api.post(`/guilds?leader_id=${leaderId}`, { name, tag, description });
  return response.data;
};

export const getGuild = async (guildId: string): Promise<Guild> => {
  const response = await api.get(`/guilds/${guildId}`);
  return response.data;
};

export const joinGuild = async (guildId: string, playerId: string): Promise<{ message: string }> => {
  const response = await api.post(`/guilds/${guildId}/join?player_id=${playerId}`);
  return response.data;
};

export const leaveGuild = async (guildId: string, playerId: string): Promise<{ message: string }> => {
  const response = await api.post(`/guilds/${guildId}/leave?player_id=${playerId}`);
  return response.data;
};

export const listGuilds = async (limit: number = 20): Promise<Guild[]> => {
  const response = await api.get(`/guilds?limit=${limit}`);
  return response.data;
};

// Guild Chat APIs
export interface GuildChatMessage {
  id: string;
  guild_id: string;
  player_id: string;
  player_name: string;
  player_level: number;
  message: string;
  timestamp: string;
}

export const getGuildChat = async (guildId: string, playerId: string, limit: number = 50): Promise<GuildChatMessage[]> => {
  const response = await api.get(`/guilds/${guildId}/chat?player_id=${playerId}&limit=${limit}`);
  return response.data;
};

export const sendGuildMessage = async (guildId: string, playerId: string, message: string): Promise<GuildChatMessage> => {
  const response = await api.post(`/guilds/${guildId}/chat?player_id=${playerId}&message=${encodeURIComponent(message)}`);
  return response.data;
};

export const deleteGuildMessage = async (guildId: string, messageId: string, playerId: string): Promise<{ message: string }> => {
  const response = await api.delete(`/guilds/${guildId}/chat/${messageId}?player_id=${playerId}`);
  return response.data;
};

// Guild Battle APIs
export interface GuildBattleChallenge {
  id: string;
  challenger_guild_id: string;
  challenger_guild_name: string;
  challenger_guild_tag: string;
  target_guild_id: string;
  target_guild_name: string;
  target_guild_tag: string;
  format: string;
  challenger_player_id: string;
  challenger_player_name: string;
  status: string;
  created_at: string;
  expires_at: string;
}

export interface GuildBattleMatchup {
  id: string;
  match_number: number;
  challenger_player: {
    id: string;
    name: string;
    level: number;
    combat_power: number;
    stats: Record<string, number>;
    current_health: number;
    max_health: number;
    current_energy: number;
  };
  target_player: {
    id: string;
    name: string;
    level: number;
    combat_power: number;
    stats: Record<string, number>;
    current_health: number;
    max_health: number;
    current_energy: number;
  };
  status: string;
  combat_log: string[];
  turn: number;
}

export interface GuildBattle {
  id: string;
  challenge_id: string;
  challenger_guild_id: string;
  challenger_guild_name: string;
  challenger_guild_tag: string;
  target_guild_id: string;
  target_guild_name: string;
  target_guild_tag: string;
  format: string;
  matchups: GuildBattleMatchup[];
  challenger_wins: number;
  target_wins: number;
  current_matchup: number;
  status: string;
  winner_guild_id?: string;
  winner_guild_name?: string;
  top_performers?: any[];
  created_at: string;
  completed_at?: string;
}

export interface GuildBattleEligibility {
  guild_id: string;
  member_count: number;
  required_members: number;
  is_eligible: boolean;
  on_cooldown: boolean;
  cooldown_remaining_hours: number;
  message: string;
}

export const checkGuildBattleEligibility = async (guildId: string): Promise<GuildBattleEligibility> => {
  const response = await api.get(`/guilds/${guildId}/battle/eligibility`);
  return response.data;
};

export const createGuildBattleChallenge = async (
  guildId: string,
  targetGuildId: string,
  playerId: string,
  format: string = '3v3'
): Promise<GuildBattleChallenge> => {
  const response = await api.post(
    `/guilds/${guildId}/battle/challenge?target_guild_id=${targetGuildId}&player_id=${playerId}&format=${format}`
  );
  return response.data;
};

export const getGuildBattleChallenges = async (
  guildId: string,
  playerId: string
): Promise<{ incoming: GuildBattleChallenge[]; outgoing: GuildBattleChallenge[] }> => {
  const response = await api.get(`/guilds/${guildId}/battle/challenges?player_id=${playerId}`);
  return response.data;
};

export const acceptGuildBattleChallenge = async (
  guildId: string,
  challengeId: string,
  playerId: string
): Promise<GuildBattle> => {
  const response = await api.post(`/guilds/${guildId}/battle/accept/${challengeId}?player_id=${playerId}`);
  return response.data;
};

export const declineGuildBattleChallenge = async (
  guildId: string,
  challengeId: string,
  playerId: string
): Promise<{ message: string }> => {
  const response = await api.post(`/guilds/${guildId}/battle/decline/${challengeId}?player_id=${playerId}`);
  return response.data;
};

export const getGuildBattle = async (
  guildId: string,
  battleId: string,
  playerId: string
): Promise<GuildBattle> => {
  const response = await api.get(`/guilds/${guildId}/battle/${battleId}?player_id=${playerId}`);
  return response.data;
};

export const guildBattleAction = async (
  guildId: string,
  battleId: string,
  playerId: string,
  action: string = 'attack',
  skillId?: string
): Promise<GuildBattle> => {
  let url = `/guilds/${guildId}/battle/${battleId}/action?player_id=${playerId}&action=${action}`;
  if (skillId) url += `&skill_id=${skillId}`;
  const response = await api.post(url);
  return response.data;
};

export const getGuildBattleHistory = async (
  guildId: string,
  playerId: string,
  limit: number = 10
): Promise<GuildBattle[]> => {
  const response = await api.get(`/guilds/${guildId}/battle/history?player_id=${playerId}&limit=${limit}`);
  return response.data;
};

export const getActiveGuildBattle = async (
  guildId: string,
  playerId: string
): Promise<GuildBattle | null> => {
  const response = await api.get(`/guilds/${guildId}/battle/active?player_id=${playerId}`);
  return response.data;
};

// Guild Raid APIs
export interface GuildRaidParticipant {
  player_id: string;
  player_name: string;
  player_level: number;
  stats: Record<string, number>;
  current_health: number;
  max_health: number;
}

export interface GuildRaidEnemy {
  id: string;
  name: string;
  level: number;
  stats: {
    health: number;
    max_health: number;
    attack: number;
    defense: number;
  };
  is_boss: boolean;
}

export interface GuildRaid {
  id: string;
  guild_id: string;
  guild_name: string;
  leader_id: string;
  participants: GuildRaidParticipant[];
  current_level: number;
  current_enemy: GuildRaidEnemy | null;
  enemies_defeated: number;
  accumulated_rewards: {
    cash: number;
    xp: number;
    reputation: number;
  };
  combat_log: string[];
  status: 'waiting' | 'in_progress' | 'completed' | 'failed' | 'retreated' | 'cancelled';
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  final_rewards_per_player?: {
    cash: number;
    xp: number;
    reputation: number;
  };
}

export const startGuildRaid = async (guildId: string, playerId: string): Promise<GuildRaid> => {
  const response = await api.post(`/guilds/${guildId}/raid/start?player_id=${playerId}`);
  return response.data;
};

export const joinGuildRaid = async (guildId: string, raidId: string, playerId: string): Promise<GuildRaid> => {
  const response = await api.post(`/guilds/${guildId}/raid/${raidId}/join?player_id=${playerId}`);
  return response.data;
};

export const leaveGuildRaid = async (guildId: string, raidId: string, playerId: string): Promise<{ message: string }> => {
  const response = await api.post(`/guilds/${guildId}/raid/${raidId}/leave?player_id=${playerId}`);
  return response.data;
};

export const beginGuildRaid = async (guildId: string, raidId: string, playerId: string): Promise<GuildRaid> => {
  const response = await api.post(`/guilds/${guildId}/raid/${raidId}/begin?player_id=${playerId}`);
  return response.data;
};

export const getGuildRaid = async (guildId: string, raidId: string, playerId: string): Promise<GuildRaid> => {
  const response = await api.get(`/guilds/${guildId}/raid/${raidId}?player_id=${playerId}`);
  return response.data;
};

export const getActiveGuildRaid = async (guildId: string, playerId: string): Promise<GuildRaid | null> => {
  const response = await api.get(`/guilds/${guildId}/raid/active?player_id=${playerId}`);
  return response.data;
};

export const getAvailableGuildRaids = async (guildId: string, playerId: string): Promise<GuildRaid[]> => {
  const response = await api.get(`/guilds/${guildId}/raid/available?player_id=${playerId}`);
  return response.data;
};

export const guildRaidFight = async (
  guildId: string,
  raidId: string,
  playerId: string,
  action: string = 'attack'
): Promise<GuildRaid> => {
  const response = await api.post(`/guilds/${guildId}/raid/${raidId}/fight?player_id=${playerId}&action=${action}`);
  return response.data;
};

export const retreatGuildRaid = async (guildId: string, raidId: string, playerId: string): Promise<GuildRaid> => {
  const response = await api.post(`/guilds/${guildId}/raid/${raidId}/retreat?player_id=${playerId}`);
  return response.data;
};

export const getGuildRaidHistory = async (
  guildId: string,
  playerId: string,
  limit: number = 10
): Promise<GuildRaid[]> => {
  const response = await api.get(`/guilds/${guildId}/raid/history?player_id=${playerId}&limit=${limit}`);
  return response.data;
};

// Skills APIs
export const getAllSkills = async (): Promise<Record<string, Skill>> => {
  const response = await api.get('/skills');
  return response.data;
};

export const getPlayerSkills = async (playerId: string): Promise<Skill[]> => {
  const response = await api.get(`/players/${playerId}/skills`);
  return response.data;
};

// Inventory & Equipment APIs
export const getPlayerInventoryDetails = async (playerId: string): Promise<any[]> => {
  const response = await api.get(`/players/${playerId}/inventory-details`);
  return response.data;
};

export const getPlayerEquipmentDetails = async (playerId: string): Promise<Record<string, any>> => {
  const response = await api.get(`/players/${playerId}/equipment-details`);
  return response.data;
};

export const equipItem = async (playerId: string, equipmentId: string): Promise<{ message: string }> => {
  const response = await api.post(`/players/${playerId}/equip?equipment_id=${equipmentId}`);
  return response.data;
};

export const unequipItem = async (playerId: string, slot: string): Promise<{ message: string }> => {
  const response = await api.post(`/players/${playerId}/unequip?slot=${slot}`);
  return response.data;
};

export const getAllItems = async (): Promise<Record<string, any>> => {
  const response = await api.get('/items');
  return response.data;
};

// Shop APIs
export const spawnShops = async (latitude: number, longitude: number, playerLevel: number): Promise<any[]> => {
  const response = await api.get(`/shops/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const buyFromShop = async (playerId: string, itemId: string, shopPrice: number): Promise<any> => {
  const response = await api.post(`/shops/buy?player_id=${playerId}&item_id=${itemId}&shop_price=${shopPrice}`);
  return response.data;
};

// Skill Shop APIs
export const buySkill = async (playerId: string, skillId: string): Promise<any> => {
  const response = await api.post(`/shop/buy-skill?player_id=${playerId}&skill_id=${skillId}`);
  return response.data;
};

export const equipSkill = async (playerId: string, skillId: string): Promise<any> => {
  const response = await api.post(`/players/${playerId}/equip-skill?skill_id=${skillId}`);
  return response.data;
};

export const unequipSkill = async (playerId: string, skillId: string): Promise<any> => {
  const response = await api.post(`/players/${playerId}/unequip-skill?skill_id=${skillId}`);
  return response.data;
};

// Auth APIs
export const registerAccount = async (
  username: string,
  password: string,
  name: string,
  characterClass: string,
  email?: string
): Promise<any> => {
  const response = await api.post('/auth/register', {
    username,
    password,
    name,
    character_class: characterClass,
    email,
  });
  return response.data;
};

export const loginAccount = async (username: string, password: string): Promise<any> => {
  const response = await api.post('/auth/login', { username, password });
  return response.data;
};

// Password Reset APIs
export const forgotPassword = async (emailOrUsername: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.post('/auth/forgot-password', { email_or_username: emailOrUsername });
  return response.data;
};

export const resetPassword = async (token: string, newPassword: string): Promise<{ message: string; success: boolean }> => {
  const response = await api.post('/auth/reset-password', { token, new_password: newPassword });
  return response.data;
};

export const changePassword = async (
  playerId: string,
  currentPassword: string,
  newPassword: string
): Promise<{ message: string; success: boolean }> => {
  const response = await api.post(`/auth/change-password/${playerId}`, {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

// Profile pic APIs
export const uploadProfilePic = async (playerId: string, imageBase64: string): Promise<any> => {
  const response = await api.post(`/players/${playerId}/profile-pic`, { image: imageBase64 });
  return response.data;
};

export const getProfilePic = async (playerId: string): Promise<{ profile_pic: string | null }> => {
  const response = await api.get(`/players/${playerId}/profile-pic`);
  return response.data;
};

// Consumable Shop APIs
export const getConsumableShop = async (): Promise<any[]> => {
  const response = await api.get('/shop/consumables');
  return response.data;
};

export const buyConsumable = async (playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/shop/buy-consumable?player_id=${playerId}&item_id=${itemId}`);
  return response.data;
};

// Territory APIs
export const getNearbyTerritories = async (lat: number, lng: number, playerLevel: number = 1): Promise<any[]> => {
  const response = await api.get(`/territories/nearby?latitude=${lat}&longitude=${lng}&player_level=${playerLevel}`);
  return response.data;
};

export const captureTerritory = async (territoryId: string, playerId: string): Promise<any> => {
  const response = await api.post(`/territories/${territoryId}/capture?player_id=${playerId}`);
  return response.data;
};

export const getOwnedTerritories = async (playerId: string): Promise<any[]> => {
  const response = await api.get(`/territories/owned/${playerId}`);
  return response.data;
};

// Chat APIs
export const sendChatMessage = async (channel: string, playerId: string, message: string): Promise<ChatMessage> => {
  const response = await api.post(`/chat?channel=${channel}&player_id=${playerId}&message=${encodeURIComponent(message)}`);
  return response.data;
};

export const getChatMessages = async (channel: string, limit: number = 50): Promise<ChatMessage[]> => {
  const response = await api.get(`/chat/${channel}?limit=${limit}`);
  return response.data;
};

// Item Management APIs
export const deleteItem = async (playerId: string, itemId: string) => {
  const response = await api.delete(`/players/${playerId}/inventory/${itemId}`);
  return response.data;
};

export const sellItem = async (playerId: string, itemId: string) => {
  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);
  return response.data;
};

// Fitness APIs
export const getFitnessData = async (playerId: string) => {
  const response = await api.get(`/fitness/${playerId}`);
  return response.data;
};

export const updateSteps = async (playerId: string, steps: number) => {
  const response = await api.put(`/fitness/${playerId}/steps?steps=${steps}`);
  return response.data;
};

export const claimStepGoal = async (playerId: string, goalSteps: number) => {
  const response = await api.post(`/fitness/${playerId}/claim/${goalSteps}`);
  return response.data;
};

// ============== RESTAURANTS ==============
export const spawnRestaurants = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/restaurants/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const eatAtRestaurant = async (restaurantId: string, playerId: string) => {
  const response = await api.post(`/restaurants/${restaurantId}/eat?player_id=${playerId}`);
  return response.data;
};

// ============== NIGHTCLUBS ==============
export const spawnNightclubs = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/nightclubs/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const visitNightclub = async (nightclubId: string, playerId: string) => {
  const response = await api.post(`/nightclubs/${nightclubId}/visit?player_id=${playerId}`);
  return response.data;
};

// ============== BANKS ==============
export const spawnBanks = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/banks/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const robBank = async (bankId: string, playerId: string) => {
  const response = await api.post(`/banks/${bankId}/rob?player_id=${playerId}`);
  return response.data;
};

// ============== CASINOS ==============
export const spawnCasinos = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/casinos/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

// Castle Cannon Mini-game API
export const spawnCastles = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/castles/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const startCastleGame = async (castleId: string, playerId: string) => {
  const response = await api.post(`/castles/${castleId}/start?player_id=${playerId}`);
  return response.data;
};

// Start a random castle game from the map
export const startRandomCastleGame = async (playerId: string, castleId?: string) => {
  const params = new URLSearchParams({ player_id: playerId });
  if (castleId) params.append('castle_id', castleId);
  const response = await api.post(`/castles/start-random?${params.toString()}`);
  return response.data;
};

export const completeCastleGame = async (gameId: string, membersEliminated: number, won: boolean, standalone: boolean = false) => {
  const response = await api.post(`/castles/game/${gameId}/complete?members_eliminated=${membersEliminated}&won=${won}&standalone=${standalone}`);
  return response.data;
};

// Account Management APIs
export const deletePlayerAccount = async (playerId: string): Promise<{ status: string; message: string }> => {
  const response = await api.delete(`/players/${playerId}/account`);
  return response.data;
};

// Durability & Repair APIs
export interface RepairCostInfo {
  index: number;
  item_id: string;
  item_name: string;
  current_durability: number;
  max_durability: number;
  repair_cost: number;
  is_broken: boolean;
  needs_repair: boolean;
}

export const getRepairCosts = async (playerId: string): Promise<{ items: RepairCostInfo[] }> => {
  const response = await api.get(`/players/${playerId}/repair-costs`);
  return response.data;
};

export const repairItem = async (playerId: string, itemIndex: number): Promise<{
  message: string;
  repair_cost: number;
  item_name: string;
  new_durability: number;
  max_durability: number;
}> => {
  const response = await api.post(`/players/${playerId}/inventory/repair?item_index=${itemIndex}`);
  return response.data;
};

// Repair an equipped item by slot
export const repairEquippedItem = async (playerId: string, slot: string): Promise<{
  message: string;
  repair_cost: number;
  item_name: string;
  slot: string;
  new_durability: number;
  max_durability: number;
}> => {
  const response = await api.post(`/players/${playerId}/repair-equipped/${slot}`);
  return response.data;
};

// Car Chase APIs
export const spawnCarChases = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/car-chases/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const startCarChase = async (chaseId: string, playerId: string) => {
  const response = await api.post(`/car-chases/${chaseId}/start?player_id=${playerId}`);
  return response.data;
};

export const completeCarChase = async (gameId: string, won: boolean, distanceTraveled: number, standalone: boolean = false) => {
  const response = await api.post(`/car-chases/game/${gameId}/complete?won=${won}&distance_traveled=${distanceTraveled}&standalone=${standalone}`);
  return response.data;
};

// Get mini-game cooldowns for a player
export const getMinigameCooldowns = async (playerId: string) => {
  const response = await api.get(`/minigames/cooldowns/${playerId}`);
  return response.data;
};

// Runaway Simulator APIs
export const spawnRunaways = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/runaways/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const startRunaway = async (runawayId: string, playerId: string) => {
  const response = await api.post(`/runaways/${runawayId}/start?player_id=${playerId}`);
  return response.data;
};

export const completeRunaway = async (gameId: string, won: boolean, distanceTraveled: number, standalone: boolean = false) => {
  const response = await api.post(`/runaways/game/${gameId}/complete?won=${won}&distance_traveled=${distanceTraveled}&standalone=${standalone}`);
  return response.data;
};

// Package Grab APIs
export const spawnPackageGrabs = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/packagegrabs/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const startPackageGrab = async (grabId: string, playerId: string) => {
  const response = await api.post(`/packagegrabs/${grabId}/start?player_id=${playerId}`);
  return response.data;
};

export const completePackageGrab = async (gameId: string, won: boolean, boxesCollected: number, distanceTraveled: number, standalone: boolean = false) => {
  const response = await api.post(`/packagegrabs/game/${gameId}/complete?won=${won}&boxes_collected=${boxesCollected}&distance_traveled=${distanceTraveled}&standalone=${standalone}`);
  return response.data;
};

// Shootout Simulator APIs
export const spawnShootouts = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/shootouts/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const startShootout = async (shootoutId: string, playerId: string) => {
  const response = await api.post(`/shootouts/${shootoutId}/start?player_id=${playerId}`);
  return response.data;
};

export const completeShootout = async (gameId: string, hits: number, standalone: boolean = false) => {
  const response = await api.post(`/shootouts/game/${gameId}/complete?hits=${hits}&standalone=${standalone}`);
  return response.data;
};

// Image Upload APIs
import { Platform } from 'react-native';

export const uploadGuildIcon = async (guildId: string, playerId: string, uri: string, fileName: string): Promise<{ message: string; path: string }> => {
  const formData = new FormData();
  
  if (Platform.OS === 'web') {
    // Web: convert URI to blob
    const response = await fetch(uri);
    const blob = await response.blob();
    formData.append('file', blob, fileName);
  } else {
    // Native: use URI directly
    const fileType = fileName.split('.').pop()?.toLowerCase() || 'png';
    const mimeType = fileType === 'jpg' || fileType === 'jpeg' ? 'image/jpeg' : `image/${fileType}`;
    formData.append('file', {
      uri,
      name: fileName,
      type: mimeType,
    } as any);
  }
  
  const response = await axios.post(
    `${API_URL}/api/upload/guild-icon/${guildId}?player_id=${playerId}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }
  );
  return response.data;
};

export const uploadProfilePicture = async (playerId: string, uri: string, fileName: string): Promise<{ message: string; path: string }> => {
  const formData = new FormData();
  
  if (Platform.OS === 'web') {
    // Web: convert URI to blob
    const response = await fetch(uri);
    const blob = await response.blob();
    formData.append('file', blob, fileName);
  } else {
    // Native: use URI directly
    const fileType = fileName.split('.').pop()?.toLowerCase() || 'png';
    const mimeType = fileType === 'jpg' || fileType === 'jpeg' ? 'image/jpeg' : `image/${fileType}`;
    formData.append('file', {
      uri,
      name: fileName,
      type: mimeType,
    } as any);
  }
  
  const response = await axios.post(
    `${API_URL}/api/upload/profile-picture/${playerId}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }
  );
  return response.data;
};

export const getImageUrl = (path: string): string => {
  if (!path) return '';
  return `${API_URL}/api/images/${path}`;
};

// Player logout - removes character from game world
export const logoutPlayer = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/logout`);
  return response.data;
};

// Player login - makes character visible in game world
export const loginPlayer = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/login`);
  return response.data;
};


export default api;
