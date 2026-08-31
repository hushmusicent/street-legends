import axios from 'axios';
import { Player, Monster, Mission, Battle, Guild, Skill, CharacterClass, NearbyPlayer, LeaderboardEntry, ChatMessage, Position } from '../types/game';

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
  characterClass: string
): Promise<any> => {
  const response = await api.post('/auth/register', {
    username,
    password,
    name,
    character_class: characterClass,
  });
  return response.data;
};

export const loginAccount = async (username: string, password: string): Promise<any> => {
  const response = await api.post('/auth/login', { username, password });
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

export const completeCastleGame = async (gameId: string, membersEliminated: number, won: boolean) => {
  const response = await api.post(`/castles/game/${gameId}/complete?members_eliminated=${membersEliminated}&won=${won}`);
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

// Car Chase APIs
export const spawnCarChases = async (latitude: number, longitude: number, playerLevel: number = 1) => {
  const response = await api.get(`/car-chases/spawn?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const startCarChase = async (chaseId: string, playerId: string) => {
  const response = await api.post(`/car-chases/${chaseId}/start?player_id=${playerId}`);
  return response.data;
};

export const completeCarChase = async (gameId: string, won: boolean, distanceTraveled: number) => {
  const response = await api.post(`/car-chases/game/${gameId}/complete?won=${won}&distance_traveled=${distanceTraveled}`);
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

export const completeRunaway = async (gameId: string, won: boolean, distanceTraveled: number) => {
  const response = await api.post(`/runaways/game/${gameId}/complete?won=${won}&distance_traveled=${distanceTraveled}`);
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

export const completePackageGrab = async (gameId: string, won: boolean, boxesCollected: number, distanceTraveled: number) => {
  const response = await api.post(`/packagegrabs/game/${gameId}/complete?won=${won}&boxes_collected=${boxesCollected}&distance_traveled=${distanceTraveled}`);
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

export const completeShootout = async (gameId: string, hits: number) => {
  const response = await api.post(`/shootouts/game/${gameId}/complete?hits=${hits}`);
  return response.data;
};

export default api;
