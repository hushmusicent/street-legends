import axios from 'axios';
import { Player, Monster, Mission, Battle, Guild, Skill, CharacterClass, NearbyPlayer, LeaderboardEntry, ChatMessage, Position } from '../types/game';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

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
export const generateMissions = async (latitude: number, longitude: number, playerLevel: number): Promise<Mission[]> => {
  const response = await api.get(`/missions/generate?latitude=${latitude}&longitude=${longitude}&player_level=${playerLevel}`);
  return response.data;
};

export const completeMission = async (missionId: string, playerId: string): Promise<{ message: string; rewards: any; level_up: boolean }> => {
  const response = await api.post(`/missions/${missionId}/complete?player_id=${playerId}`);
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

// Chat APIs
export const sendChatMessage = async (channel: string, playerId: string, message: string): Promise<ChatMessage> => {
  const response = await api.post(`/chat?channel=${channel}&player_id=${playerId}&message=${encodeURIComponent(message)}`);
  return response.data;
};

export const getChatMessages = async (channel: string, limit: number = 50): Promise<ChatMessage[]> => {
  const response = await api.get(`/chat/${channel}?limit=${limit}`);
  return response.data;
};

export default api;
