import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Player, Monster, Mission, Battle, Guild, Position, NearbyPlayer } from '../types/game';

interface GameState {
  // Player state
  player: Player | null;
  playerId: string | null;
  isLoading: boolean;
  
  // Location state
  currentPosition: Position | null;
  
  // Game entities nearby
  nearbyMonsters: Monster[];
  nearbyMissions: Mission[];
  nearbyPlayers: NearbyPlayer[];
  
  // Current activity
  currentBattle: Battle | null;
  currentMission: Mission | null;
  
  // Guild
  playerGuild: Guild | null;
  
  // Profile pic (shared between character & map)
  profilePic: string | null;
  
  // Actions
  setPlayer: (player: Player) => void;
  setPlayerId: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setCurrentPosition: (position: Position) => void;
  setNearbyMonsters: (monsters: Monster[]) => void;
  setNearbyMissions: (missions: Mission[]) => void;
  setNearbyPlayers: (players: NearbyPlayer[]) => void;
  removeMonster: (monsterId: string) => void;
  removeMission: (missionId: string) => void;
  setCurrentBattle: (battle: Battle | null) => void;
  setCurrentMission: (mission: Mission | null) => void;
  setPlayerGuild: (guild: Guild | null) => void;
  setProfilePic: (pic: string | null) => void;
  clearPlayer: () => void;
  
  // Persistence
  loadStoredPlayerId: () => Promise<string | null>;
  savePlayerId: (id: string) => Promise<void>;
}

export const useGameStore = create<GameState>((set, get) => ({
  // Initial state
  player: null,
  playerId: null,
  isLoading: true,
  currentPosition: null,
  nearbyMonsters: [],
  nearbyMissions: [],
  nearbyPlayers: [],
  currentBattle: null,
  currentMission: null,
  playerGuild: null,
  profilePic: null,
  
  // Actions
  setPlayer: (player) => set({ player }),
  setPlayerId: (playerId) => set({ playerId }),
  setLoading: (isLoading) => set({ isLoading }),
  setCurrentPosition: (position) => set({ currentPosition: position }),
  setNearbyMonsters: (monsters) => set({ nearbyMonsters: monsters }),
  setNearbyMissions: (missions) => set({ nearbyMissions: missions }),
  setNearbyPlayers: (players) => set({ nearbyPlayers: players }),
  removeMonster: (monsterId) => set((state) => ({
    nearbyMonsters: state.nearbyMonsters.filter(m => m.id !== monsterId),
  })),
  removeMission: (missionId) => set((state) => ({
    nearbyMissions: state.nearbyMissions.filter(m => m.id !== missionId),
  })),
  setCurrentBattle: (battle) => set({ currentBattle: battle }),
  setCurrentMission: (mission) => set({ currentMission: mission }),
  setPlayerGuild: (guild) => set({ playerGuild: guild }),
  setProfilePic: (pic) => set({ profilePic: pic }),
  
  clearPlayer: () => set({
    player: null,
    playerId: null,
    nearbyMonsters: [],
    nearbyMissions: [],
    nearbyPlayers: [],
    currentBattle: null,
    currentMission: null,
    playerGuild: null,
    profilePic: null,
  }),
  
  // Persistence
  loadStoredPlayerId: async () => {
    try {
      const id = await AsyncStorage.getItem('playerId');
      if (id) {
        set({ playerId: id });
      }
      return id;
    } catch (error) {
      console.error('Error loading player ID:', error);
      return null;
    }
  },
  
  savePlayerId: async (id) => {
    try {
      await AsyncStorage.setItem('playerId', id);
      set({ playerId: id });
    } catch (error) {
      console.error('Error saving player ID:', error);
    }
  },
}));
