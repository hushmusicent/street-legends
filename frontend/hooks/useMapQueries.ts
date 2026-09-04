import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  spawnMonsters,
  generateMissions,
  getNearbyPlayers,
  spawnShops,
  getNearbyTerritories,
  spawnRestaurants,
  spawnNightclubs,
  spawnBanks,
  spawnCasinos,
  spawnCastles,
  spawnCarChases,
  spawnRunaways,
  spawnPackageGrabs,
  spawnShootouts,
  getPlayer,
  updatePlayerPosition,
  getMinigameCooldowns,
} from '../services/api';
import { Monster, Mission, NearbyPlayer, Player } from '../types/game';

// Round position to ~50m grid for cache key stability
const roundPosition = (lat: number, lng: number) => ({
  lat: Math.round(lat * 200) / 200, // ~500m grid
  lng: Math.round(lng * 200) / 200,
});

// Query keys factory for consistency
export const mapQueryKeys = {
  all: ['map'] as const,
  player: (playerId: string) => ['player', playerId] as const,
  cooldowns: (playerId: string) => ['cooldowns', playerId] as const,
  entities: (lat: number, lng: number, level: number) => {
    const rounded = roundPosition(lat, lng);
    return ['entities', rounded.lat, rounded.lng, level] as const;
  },
};

export interface MapEntitiesData {
  monsters: Monster[];
  missions: Mission[];
  players: NearbyPlayer[];
  shops: any[];
  territories: any[];
  restaurants: any[];
  nightclubs: any[];
  banks: any[];
  casinos: any[];
  castles: any[];
  carChases: any[];
  runaways: any[];
  packageGrabs: any[];
  shootouts: any[];
}

interface UseMapEntitiesOptions {
  latitude: number;
  longitude: number;
  playerLevel: number;
  playerId: string;
  enabled?: boolean;
}

/**
 * Hook to fetch all map entities using TanStack Query
 * Replaces the manual setInterval polling with smart caching
 */
export const useMapEntities = ({
  latitude,
  longitude,
  playerLevel,
  playerId,
  enabled = true,
}: UseMapEntitiesOptions) => {
  return useQuery<MapEntitiesData>({
    queryKey: mapQueryKeys.entities(latitude, longitude, playerLevel),
    queryFn: async () => {
      // Update position first
      await updatePlayerPosition(playerId, { latitude, longitude }).catch(() => {});

      // Fetch all entities in parallel
      const results = await Promise.allSettled([
        spawnMonsters(latitude, longitude, playerLevel),
        generateMissions(latitude, longitude, playerLevel, playerId),
        getNearbyPlayers(playerId, 500),
        spawnShops(latitude, longitude, playerLevel),
        getNearbyTerritories(latitude, longitude, playerLevel),
        spawnRestaurants(latitude, longitude, playerLevel),
        spawnNightclubs(latitude, longitude, playerLevel),
        spawnBanks(latitude, longitude, playerLevel),
        spawnCasinos(latitude, longitude, playerLevel),
        spawnCastles(latitude, longitude, playerLevel),
        spawnCarChases(latitude, longitude, playerLevel),
        spawnRunaways(latitude, longitude, playerLevel),
        spawnPackageGrabs(latitude, longitude, playerLevel),
        spawnShootouts(latitude, longitude, playerLevel),
      ]);

      return {
        monsters: results[0].status === 'fulfilled' ? results[0].value : [],
        missions: results[1].status === 'fulfilled' ? results[1].value : [],
        players: results[2].status === 'fulfilled' ? results[2].value : [],
        shops: results[3].status === 'fulfilled' ? results[3].value : [],
        territories: results[4].status === 'fulfilled' ? results[4].value : [],
        restaurants: results[5].status === 'fulfilled' ? results[5].value : [],
        nightclubs: results[6].status === 'fulfilled' ? results[6].value : [],
        banks: results[7].status === 'fulfilled' ? results[7].value : [],
        casinos: results[8].status === 'fulfilled' ? results[8].value : [],
        castles: results[9].status === 'fulfilled' ? results[9].value : [],
        carChases: results[10].status === 'fulfilled' ? results[10].value : [],
        runaways: results[11].status === 'fulfilled' ? results[11].value : [],
        packageGrabs: results[12].status === 'fulfilled' ? results[12].value : [],
        shootouts: results[13].status === 'fulfilled' ? results[13].value : [],
      };
    },
    enabled: enabled && !!playerId && !!latitude && !!longitude,
    staleTime: 30 * 1000, // 30 seconds - matches previous cache TTL
    gcTime: 5 * 60 * 1000, // 5 minutes garbage collection
    refetchInterval: 5 * 60 * 1000, // 5 minutes - matches previous interval
    refetchIntervalInBackground: false, // Don't refetch when app is backgrounded
    refetchOnWindowFocus: true, // Refetch when app returns to foreground
    refetchOnReconnect: true, // Refetch on network reconnect
    retry: 2,
  });
};

interface UsePlayerDataOptions {
  playerId: string;
  enabled?: boolean;
}

/**
 * Hook to fetch player data with automatic refetching
 * Triggers HP/energy regen calculation on backend
 */
export const usePlayerData = ({ playerId, enabled = true }: UsePlayerDataOptions) => {
  return useQuery<Player>({
    queryKey: mapQueryKeys.player(playerId),
    queryFn: () => getPlayer(playerId),
    enabled: enabled && !!playerId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes - for HP/energy regen
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    retry: 2,
  });
};

// Cooldown data structure from backend
export interface MinigameCooldown {
  type: 'castle' | 'carchase' | 'runaway' | 'packagegrab' | 'shootout';
  marker_id: string;
  remaining_seconds: number;
  expires_at: string;
}

export interface CooldownsData {
  [key: string]: MinigameCooldown;
}

/**
 * Hook to fetch mini-game cooldowns (castles and car chases)
 * Updates every 10 seconds for accurate countdown timers
 */
export const useMinigameCooldowns = ({ playerId, enabled = true }: UsePlayerDataOptions) => {
  return useQuery<CooldownsData>({
    queryKey: mapQueryKeys.cooldowns(playerId),
    queryFn: () => getMinigameCooldowns(playerId),
    enabled: enabled && !!playerId,
    staleTime: 5 * 1000, // 5 seconds - cooldowns need frequent updates
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 1000, // 10 seconds - for timer accuracy
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    retry: 1,
  });
};

/**
 * Hook to invalidate map queries (for manual refresh)
 */
export const useInvalidateMapQueries = () => {
  const queryClient = useQueryClient();

  return {
    invalidateEntities: () => queryClient.invalidateQueries({ queryKey: ['entities'] }),
    invalidatePlayer: (playerId: string) =>
      queryClient.invalidateQueries({ queryKey: mapQueryKeys.player(playerId) }),
    invalidateCooldowns: (playerId: string) =>
      queryClient.invalidateQueries({ queryKey: mapQueryKeys.cooldowns(playerId) }),
    invalidateAll: () => queryClient.invalidateQueries({ queryKey: mapQueryKeys.all }),
  };
};
