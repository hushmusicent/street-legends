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
  
  // Audio
  isMuted: boolean;
  
  // Mini-game levels (selected in options)
  runawayLevel: number; // 1-20, selected level for Runaway Simulator
  packageGrabLevel: number; // 1-20, selected level for Package Grab
  shootoutLevel: number; // 1-20, selected level for Shootout Simulator
  
  // Data refresh triggers
  missionRefreshTrigger: number;
  
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
  setMuted: (muted: boolean) => void;
  setRunawayLevel: (level: number) => void;
  setPackageGrabLevel: (level: number) => void;
  setShootoutLevel: (level: number) => void;
  triggerMissionRefresh: () => void;
  clearPlayer: () => void;
  
  // Persistence
  loadStoredPlayerId: () => Promise<string | null>;
  savePlayerId: (id: string) => Promise<void>;
  loadRunawayLevel: () => Promise<number>;
  saveRunawayLevel: (level: number) => Promise<void>;
  loadPackageGrabLevel: () => Promise<number>;
  savePackageGrabLevel: (level: number) => Promise<void>;
  loadShootoutLevel: () => Promise<number>;
  saveShootoutLevel: (level: number) => Promise<void>;
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
  isMuted: false,
  runawayLevel: 1, // Default to level 1
  packageGrabLevel: 1, // Default to level 1
  shootoutLevel: 1, // Default to level 1
  missionRefreshTrigger: 0,
  
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
  setMuted: (muted) => set({ isMuted: muted }),
  setRunawayLevel: (level) => set({ runawayLevel: Math.min(20, Math.max(1, level)) }),
  setPackageGrabLevel: (level) => set({ packageGrabLevel: Math.min(20, Math.max(1, level)) }),
  setShootoutLevel: (level) => set({ shootoutLevel: Math.min(20, Math.max(1, level)) }),
  triggerMissionRefresh: () => set((state) => ({ missionRefreshTrigger: state.missionRefreshTrigger + 1 })),
  
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
  
  loadRunawayLevel: async () => {
    try {
      const level = await AsyncStorage.getItem('runawayLevel');
      const parsedLevel = level ? parseInt(level, 10) : 1;
      const validLevel = Math.min(20, Math.max(1, parsedLevel || 1));
      set({ runawayLevel: validLevel });
      return validLevel;
    } catch (error) {
      console.error('Error loading runaway level:', error);
      return 1;
    }
  },
  
  saveRunawayLevel: async (level) => {
    try {
      const validLevel = Math.min(20, Math.max(1, level));
      await AsyncStorage.setItem('runawayLevel', validLevel.toString());
      set({ runawayLevel: validLevel });
    } catch (error) {
      console.error('Error saving runaway level:', error);
    }
  },
  
  loadPackageGrabLevel: async () => {
    try {
      const level = await AsyncStorage.getItem('packageGrabLevel');
      const parsedLevel = level ? parseInt(level, 10) : 1;
      const validLevel = Math.min(20, Math.max(1, parsedLevel || 1));
      set({ packageGrabLevel: validLevel });
      return validLevel;
    } catch (error) {
      console.error('Error loading package grab level:', error);
      return 1;
    }
  },
  
  savePackageGrabLevel: async (level) => {
    try {
      const validLevel = Math.min(20, Math.max(1, level));
      await AsyncStorage.setItem('packageGrabLevel', validLevel.toString());
      set({ packageGrabLevel: validLevel });
    } catch (error) {
      console.error('Error saving package grab level:', error);
    }
  },
  
  loadShootoutLevel: async () => {
    try {
      const level = await AsyncStorage.getItem('shootoutLevel');
      const parsedLevel = level ? parseInt(level, 10) : 1;
      const validLevel = Math.min(20, Math.max(1, parsedLevel || 1));
      set({ shootoutLevel: validLevel });
      return validLevel;
    } catch (error) {
      console.error('Error loading shootout level:', error);
      return 1;
    }
  },
  
  saveShootoutLevel: async (level) => {
    try {
      const validLevel = Math.min(20, Math.max(1, level));
      await AsyncStorage.setItem('shootoutLevel', validLevel.toString());
      set({ shootoutLevel: validLevel });
    } catch (error) {
      console.error('Error saving shootout level:', error);
    }
  },
}));
