import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  ScrollView,
  Modal,
  Pressable,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Location from 'expo-location';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../../stores/gameStore';
import { getEnemyBattleImage } from '../../assets/enemyImages';
import {
  getPlayer,
  updatePlayerPosition,
  startBattle,
  getProfilePic,
  captureTerritory,
  collectTerritoryIncome,
  eatAtRestaurant,
  visitNightclub,
  robBank,
  startCarChase,
  startRunaway,
  startPackageGrab,
  startShootout,
  getRelationshipStatus,
  followPlayer,
  unfollowPlayer,
  sendFriendRequest,
} from '../../services/api';
import { Monster, Mission, NearbyPlayer, RelationshipStatus } from '../../types/game';
import { GameMap } from '../../components/GameMap';
import { showGameToast } from '../../components/GameToast';
import { SFX } from '../../hooks/useSoundEffects';
import { useMapEntities, usePlayerData, useInvalidateMapQueries, useMinigameCooldowns } from '../../hooks/useMapQueries';

export default function MapScreen() {
  const {
    player,
    playerId,
    setPlayer,
    currentPosition,
    setCurrentPosition,
    setNearbyMonsters,
    setNearbyMissions,
    setNearbyPlayers,
    setCurrentBattle,
  } = useGameStore();

  const [loading, setLoading] = useState(true);
  const [selectedMarker, setSelectedMarker] = useState<{
    type: 'monster' | 'mission' | 'bounty' | 'player' | 'shop' | 'restaurant' | 'nightclub';
    data: any;
  } | null>(null);
  const [isTracking, setIsTracking] = useState(false);
  const [heading, setHeading] = useState<number>(0);
  const [selectedTerritory, setSelectedTerritory] = useState<any | null>(null);
  const [selectedBank, setSelectedBank] = useState<any | null>(null);
  const [selectedCastle, setSelectedCastle] = useState<any | null>(null);
  const [selectedCarChase, setSelectedCarChase] = useState<any | null>(null);
  const [selectedRunaway, setSelectedRunaway] = useState<any | null>(null);
  const [selectedPackageGrab, setSelectedPackageGrab] = useState<any | null>(null);
  const [selectedShootout, setSelectedShootout] = useState<any | null>(null);
  const [territoryBattleLog, setTerritoryBattleLog] = useState<string[]>([]);
  const [territoryFighting, setTerritoryFighting] = useState(false);
  const [robbingBank, setRobbingBank] = useState(false);
  const [startingCarChase, setStartingCarChase] = useState(false);
  const [startingRunaway, setStartingRunaway] = useState(false);
  const [startingPackageGrab, setStartingPackageGrab] = useState(false);
  const [startingShootout, setStartingShootout] = useState(false);
  const globalProfilePic = useGameStore(s => s.profilePic);
  const setGlobalProfilePic = useGameStore(s => s.setProfilePic);
  
  // Player popup social state
  const [playerRelationship, setPlayerRelationship] = useState<RelationshipStatus | null>(null);
  const [loadingFollow, setLoadingFollow] = useState(false);
  const [loadingFriendRequest, setLoadingFriendRequest] = useState(false);
  
  const locationSubscription = useRef<Location.LocationSubscription | null>(null);
  const headingSubscription = useRef<Location.LocationSubscription | null>(null);
  const lastServerUpdateTime = useRef<number>(0);

  // TanStack Query hooks - replaces setInterval polling
  const { invalidateEntities } = useInvalidateMapQueries();
  
  const { 
    data: entitiesData, 
    refetch: refetchEntities,
    isFetching: isRefreshing,
  } = useMapEntities({
    latitude: currentPosition?.latitude || 0,
    longitude: currentPosition?.longitude || 0,
    playerLevel: player?.level || 1,
    playerId: playerId || '',
    enabled: !!currentPosition && !!player && !!playerId,
  });

  const { data: playerData, refetch: refetchPlayer } = usePlayerData({
    playerId: playerId || '',
    enabled: !!playerId,
  });

  // Mini-game cooldowns query
  const { data: cooldownsData, refetch: refetchCooldowns } = useMinigameCooldowns({
    playerId: playerId || '',
    enabled: !!playerId,
  });

  // Local countdown state for smooth timer updates
  const [localCooldowns, setLocalCooldowns] = useState<{ [key: string]: number }>({});
  
  // Initialize local cooldowns from server data
  useEffect(() => {
    if (cooldownsData) {
      const newCooldowns: { [key: string]: number } = {};
      Object.entries(cooldownsData).forEach(([key, cooldown]) => {
        newCooldowns[key] = cooldown.remaining_seconds;
      });
      setLocalCooldowns(newCooldowns);
    }
  }, [cooldownsData]);
  
  // Countdown timer - updates every second
  useEffect(() => {
    const interval = setInterval(() => {
      setLocalCooldowns(prev => {
        const updated: { [key: string]: number } = {};
        let hasActiveCooldowns = false;
        Object.entries(prev).forEach(([key, secs]) => {
          if (secs > 0) {
            updated[key] = secs - 1;
            hasActiveCooldowns = true;
          }
        });
        return hasActiveCooldowns ? updated : prev;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Sync TanStack Query player data to global store
  useEffect(() => {
    if (playerData) {
      setPlayer(playerData);
    }
  }, [playerData, setPlayer]);

  // Memoized derived state from entities query
  const nearbyMonsters = useMemo(() => entitiesData?.monsters || [], [entitiesData?.monsters]);
  const nearbyMissions = useMemo(() => entitiesData?.missions || [], [entitiesData?.missions]);
  const nearbyPlayers = useMemo(() => entitiesData?.players || [], [entitiesData?.players]);
  const nearbyShops = useMemo(() => entitiesData?.shops || [], [entitiesData?.shops]);
  const territories = useMemo(() => entitiesData?.territories || [], [entitiesData?.territories]);
  const nearbyRestaurants = useMemo(() => entitiesData?.restaurants || [], [entitiesData?.restaurants]);
  const nearbyNightclubs = useMemo(() => entitiesData?.nightclubs || [], [entitiesData?.nightclubs]);
  const nearbyBanks = useMemo(() => entitiesData?.banks || [], [entitiesData?.banks]);
  const nearbyCastles = useMemo(() => entitiesData?.castles || [], [entitiesData?.castles]);
  const nearbyCarChases = useMemo(() => entitiesData?.carChases || [], [entitiesData?.carChases]);
  const nearbyRunaways = useMemo(() => entitiesData?.runaways || [], [entitiesData?.runaways]);
  const nearbyPackageGrabs = useMemo(() => entitiesData?.packageGrabs || [], [entitiesData?.packageGrabs]);
  const nearbyShootouts = useMemo(() => entitiesData?.shootouts || [], [entitiesData?.shootouts]);

  // Update global store when entities change
  useEffect(() => {
    if (entitiesData) {
      setNearbyMonsters(entitiesData.monsters);
      setNearbyMissions(entitiesData.missions);
      setNearbyPlayers(entitiesData.players);
    }
  }, [entitiesData, setNearbyMonsters, setNearbyMissions, setNearbyPlayers]);

  useEffect(() => {
    initializeLocation();
    return () => {
      if (locationSubscription.current) locationSubscription.current.remove();
      if (headingSubscription.current) headingSubscription.current.remove();
    };
  }, []);

  // Fetch profile pic for map avatar when playerId is available
  useEffect(() => {
    if (playerId && !globalProfilePic) {
      getProfilePic(playerId).then((res) => {
        if (res.profile_pic) {
          setGlobalProfilePic(res.profile_pic);
        }
      }).catch(() => {});
    }
  }, [playerId]);

  const initializeLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        // Use default location (New York) for demo when permission denied
        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
        setCurrentPosition(defaultPos);
        if (playerId) {
          updatePlayerPosition(playerId, defaultPos).catch(console.error);
          getPlayer(playerId).then(setPlayer).catch(console.error);
        }
        setLoading(false);
        startLocationTracking();
        return;
      }

      // Get initial position quickly with balanced accuracy
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      const position = {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      };

      setCurrentPosition(position);
      
      if (playerId) {
        // Update position on server and fetch player data
        updatePlayerPosition(playerId, position).catch(console.error);
        getPlayer(playerId).then(setPlayer).catch(console.error);
      }

      setLoading(false);
      startLocationTracking();
      
    } catch (error: any) {
      // Fallback to default location on error
      const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
      setCurrentPosition(defaultPos);
      setLoading(false);
    }
  };

  const startLocationTracking = async () => {
    try {
      if (locationSubscription.current) {
        locationSubscription.current.remove();
      }

      setIsTracking(true);
      
      // Track position - frequent local updates for smooth movement, server every 5s
      locationSubscription.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          timeInterval: 1000,
          distanceInterval: 1,
        },
        (loc) => {
          const newPos = {
            latitude: loc.coords.latitude,
            longitude: loc.coords.longitude,
          };
          setCurrentPosition(newPos);
          
          if (loc.coords.heading !== null && loc.coords.heading >= 0) {
            setHeading(loc.coords.heading);
          }
          
          // Throttle server updates to every 5 seconds
          const now = Date.now();
          if (playerId && now - lastServerUpdateTime.current > 5000) {
            lastServerUpdateTime.current = now;
            updatePlayerPosition(playerId, newPos).catch(console.error);
          }
        }
      );
      
      // Heading updates for compass direction
      try {
        headingSubscription.current = await Location.watchHeadingAsync((h) => {
          if (h.trueHeading >= 0) setHeading(h.trueHeading);
          else if (h.magHeading >= 0) setHeading(h.magHeading);
        });
      } catch {}
      
    } catch (error) {
      setIsTracking(false);
    }
  };

  // Manual refresh handler using TanStack Query
  const handleRefresh = useCallback(async () => {
    await Promise.all([
      refetchEntities(),
      refetchPlayer(),
    ]);
  }, [refetchEntities, refetchPlayer]);

  // Build territory data for the map
  const mapTerritories = useMemo(() => {
    return territories.map((t: any) => ({
      id: t.id,
      name: t.name,
      location: { latitude: t.location?.latitude || 0, longitude: t.location?.longitude || 0 },
      radius: t.radius || t.size || 200,
      size: t.size || t.radius || 200,
      bounds: t.bounds || null,
      color: t.color || '#e74c3c',
      owner_id: t.owner_id || null,
      owner_name: t.owner_name || null,
      owner_pic: t.owner_pic || null,
    }));
  }, [territories]);

  const handleTerritoryPress = useCallback((territory: any) => {
    // Find full territory data
    const fullTerritory = territories.find((t: any) => t.id === territory.id);
    if (fullTerritory) {
      setSelectedTerritory(fullTerritory);
      setTerritoryBattleLog([]);
    }
  }, [territories]);

  const handleTerritoryCapture = useCallback(async () => {
    if (!playerId || !selectedTerritory) return;
    try {
      setTerritoryFighting(true);
      const result = await captureTerritory(selectedTerritory.id, playerId);
      setTerritoryBattleLog(result.combat_log || []);
      
      // Update selected territory with new ownership
      if (result.territory) {
        setSelectedTerritory(result.territory);
      }
      
      // Invalidate queries to refresh data
      await Promise.all([
        invalidateEntities(),
        refetchPlayer(),
      ]);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to challenge territory');
    } finally {
      setTerritoryFighting(false);
    }
  }, [playerId, selectedTerritory, invalidateEntities, refetchPlayer]);

  const handleCollectIncome = useCallback(async () => {
    if (!playerId || !selectedTerritory) return;
    try {
      const result = await collectTerritoryIncome(playerId);
      Alert.alert('Income Collected!', result.message);
      await refetchPlayer();
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to collect income');
    }
  }, [playerId, selectedTerritory, refetchPlayer]);

  const handleStartBattle = useCallback(async (monster: Monster) => {
    if (!playerId) return;
    try {
      const battle = await startBattle(playerId, 'monster', monster.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start battle');
    }
  }, [playerId]);

  const handleStartMission = useCallback((mission: Mission) => {
    // Play different sound based on mission type
    if (mission.mission_type === 'bounty') {
      SFX.bountyMission();
    } else {
      SFX.phoneMission();
    }
    setSelectedMarker(null);
    router.push(`/mission/${mission.id}`);
  }, []);

  const handlePvPChallenge = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId) return;
    try {
      const battle = await startBattle(playerId, 'player', targetPlayer.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start PvP');
    }
  }, [playerId]);

  // Load relationship status when player popup opens
  const loadPlayerRelationship = useCallback(async (targetId: string) => {
    if (!playerId) return;
    try {
      const status = await getRelationshipStatus(playerId, targetId);
      setPlayerRelationship(status);
    } catch (error) {
      console.error('Failed to load relationship status:', error);
      setPlayerRelationship(null);
    }
  }, [playerId]);

  const handleFollowPlayer = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId || loadingFollow) return;
    setLoadingFollow(true);
    try {
      if (playerRelationship?.is_following) {
        await unfollowPlayer(playerId, targetPlayer.id);
        showGameToast({ type: 'info', title: 'Unfollowed', message: `Unfollowed ${targetPlayer.name}` });
      } else {
        await followPlayer(playerId, targetPlayer.id);
        showGameToast({ type: 'success', title: 'Following', message: `Now following ${targetPlayer.name}` });
      }
      // Refresh relationship status
      await loadPlayerRelationship(targetPlayer.id);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Action failed');
    } finally {
      setLoadingFollow(false);
    }
  }, [playerId, playerRelationship, loadingFollow, loadPlayerRelationship]);

  const handleAddFriend = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId || loadingFriendRequest) return;
    setLoadingFriendRequest(true);
    try {
      const result = await sendFriendRequest(playerId, targetPlayer.id);
      if (result.became_friends) {
        showGameToast({ type: 'success', title: 'Friends!', message: `You are now friends with ${targetPlayer.name}!` });
      } else {
        showGameToast({ type: 'info', title: 'Request Sent', message: `Friend request sent to ${targetPlayer.name}` });
      }
      // Refresh relationship status
      await loadPlayerRelationship(targetPlayer.id);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send friend request');
    } finally {
      setLoadingFriendRequest(false);
    }
  }, [playerId, loadingFriendRequest, loadPlayerRelationship]);

  const handleRobBank = useCallback(async () => {
    if (!playerId || !selectedBank || robbingBank) return;
    setRobbingBank(true);
    
    // Play bank mission sound when starting the robbery
    SFX.bankMission();
    
    try {
      const result = await robBank(selectedBank.id, playerId);
      
      if (result.success) {
        // Success! Show green toast
        showGameToast({
          type: 'success',
          title: 'HEIST SUCCESS!',
          message: result.message,
        });
      } else {
        // Busted! Show red toast
        showGameToast({
          type: 'error',
          title: 'BUSTED!',
          message: result.message,
        });
      }
      
      // Refresh player data using TanStack Query
      await refetchPlayer();
      setSelectedBank(null);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Bank robbery failed');
    } finally {
      setRobbingBank(false);
    }
  }, [playerId, selectedBank, robbingBank, refetchPlayer]);

  const handleStartCastleGame = useCallback(async () => {
    if (!playerId || !selectedCastle) return;
    
    // Check cooldown
    const cooldownKey = `castle_${selectedCastle.id}`;
    if (localCooldowns[cooldownKey] > 0) {
      Alert.alert('Cooldown Active', 'Wait for the cooldown to expire before attacking again.');
      return;
    }
    
    const castleId = selectedCastle.id;
    setSelectedCastle(null);
    
    // Navigate to castle-levels with randomLevel flag and castle ID
    router.push({
      pathname: '/castle-levels',
      params: { randomLevel: 'true', castleId: castleId },
    });
  }, [playerId, selectedCastle, localCooldowns]);

  const handleStartCarChase = useCallback(async () => {
    if (!playerId || !selectedCarChase || startingCarChase) return;
    setStartingCarChase(true);
    
    try {
      const gameData = await startCarChase(selectedCarChase.id, playerId);
      setSelectedCarChase(null);
      
      // Navigate to the car chase game screen
      router.push({
        pathname: '/car-chase',
        params: {
          chaseId: selectedCarChase.id,
          chaseName: selectedCarChase.name,
          difficulty: selectedCarChase.difficulty.toString(),
          countyLineDistance: selectedCarChase.county_line_distance.toString(),
          gameId: gameData.game_id,
        },
      });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Failed to start car chase';
      Alert.alert('Cannot Start Chase', errorMsg);
    } finally {
      setStartingCarChase(false);
    }
  }, [playerId, selectedCarChase, startingCarChase]);

  const handleStartRunaway = useCallback(async () => {
    if (!playerId || !selectedRunaway || startingRunaway) return;
    setStartingRunaway(true);
    
    try {
      const gameData = await startRunaway(selectedRunaway.id, playerId);
      setSelectedRunaway(null);
      
      // Get the selected runaway level from the store
      const { runawayLevel } = useGameStore.getState();
      
      // Navigate to the runaway simulator game screen
      // Use the selected level from options panel instead of map marker difficulty
      router.push({
        pathname: '/runaway-simulator',
        params: {
          runawayId: selectedRunaway.id,
          runawayName: selectedRunaway.name,
          difficulty: runawayLevel.toString(), // Use selected level from options
          gameId: gameData.game_id,
        },
      });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Failed to start runaway';
      Alert.alert('Cannot Start Runaway', errorMsg);
    } finally {
      setStartingRunaway(false);
    }
  }, [playerId, selectedRunaway, startingRunaway]);

  const handleStartPackageGrab = useCallback(async () => {
    if (!playerId || !selectedPackageGrab || startingPackageGrab) return;
    setStartingPackageGrab(true);
    
    try {
      const gameData = await startPackageGrab(selectedPackageGrab.id, playerId);
      setSelectedPackageGrab(null);
      
      // Get the selected package grab level from the store
      const { packageGrabLevel } = useGameStore.getState();
      
      // Navigate to the package grab game screen
      router.push({
        pathname: '/package-grab',
        params: {
          grabId: selectedPackageGrab.id,
          grabName: selectedPackageGrab.name,
          difficulty: packageGrabLevel.toString(),
          gameId: gameData.game_id,
        },
      });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Failed to start package grab';
      Alert.alert('Cannot Start Delivery', errorMsg);
    } finally {
      setStartingPackageGrab(false);
    }
  }, [playerId, selectedPackageGrab, startingPackageGrab]);

  const handleStartShootout = useCallback(async () => {
    if (!playerId || !selectedShootout || startingShootout) return;
    setStartingShootout(true);
    
    try {
      const gameData = await startShootout(selectedShootout.id, playerId);
      setSelectedShootout(null);
      
      // Get the selected shootout level from the store
      const { shootoutLevel } = useGameStore.getState();
      
      // Navigate to the shootout simulator game screen
      router.push({
        pathname: '/shootout-simulator',
        params: {
          shootoutId: selectedShootout.id,
          shootoutName: selectedShootout.name,
          difficulty: shootoutLevel.toString(),
          gameId: gameData.game_id,
        },
      });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Failed to start shootout';
      Alert.alert('Cannot Start Shootout', errorMsg);
    } finally {
      setStartingShootout(false);
    }
  }, [playerId, selectedShootout, startingShootout]);

  // Memoize markers to prevent re-renders
  const mapMarkers = useMemo(() => [
    ...nearbyMonsters.map((m) => ({
      id: m.id,
      coordinate: m.position,
      type: 'monster' as const,
      level: m.level,
      name: m.name,
      isBoss: m.is_boss || false,
    })),
    ...nearbyMissions.map((m) => ({
      id: m.id,
      coordinate: m.position,
      type: (m.mission_type === 'bounty' ? 'bounty' : 'mission') as 'mission' | 'bounty',
      name: m.title,
    })),
    ...nearbyPlayers.map((p) => ({
      id: p.id,
      coordinate: p.position,
      type: 'player' as const,
      level: p.level,
      name: p.name,
    })),
    ...nearbyShops.map((s) => ({
      id: s.id,
      coordinate: { latitude: s.latitude, longitude: s.longitude },
      type: 'shop' as const,
      name: s.name,
      level: s.level,
    })),
    ...nearbyRestaurants.map((r) => ({
      id: r.id,
      coordinate: { latitude: r.latitude, longitude: r.longitude },
      type: 'restaurant' as const,
      name: r.name,
      icon: r.icon,
    })),
    ...nearbyNightclubs.map((nc) => ({
      id: nc.id,
      coordinate: { latitude: nc.latitude, longitude: nc.longitude },
      type: 'nightclub' as const,
      name: nc.name,
      icon: nc.icon,
    })),
    ...nearbyBanks.map((b) => ({
      id: b.id,
      coordinate: { latitude: b.latitude, longitude: b.longitude },
      type: 'bank' as const,
      name: b.name,
      icon: '🏦',
    })),
    ...nearbyCastles.map((c) => {
      const cooldownKey = `castle_${c.id}`;
      const remainingSecs = localCooldowns[cooldownKey] || 0;
      return {
        id: c.id,
        coordinate: { latitude: c.latitude, longitude: c.longitude },
        type: 'castle' as const,
        name: c.name,
        level: c.difficulty,
        icon: '🏰',
        cooldownSeconds: remainingSecs,
      };
    }),
    ...nearbyCarChases.map((cc) => {
      const cooldownKey = `carchase_${cc.id}`;
      const remainingSecs = localCooldowns[cooldownKey] || 0;
      return {
        id: cc.id,
        coordinate: { latitude: cc.latitude, longitude: cc.longitude },
        type: 'carChase' as const,
        name: cc.name,
        level: cc.difficulty,
        icon: '🚗',
        cooldownSeconds: remainingSecs,
      };
    }),
    ...nearbyRunaways.map((r) => {
      const cooldownKey = `runaway_${r.id}`;
      const remainingSecs = localCooldowns[cooldownKey] || 0;
      return {
        id: r.id,
        coordinate: { latitude: r.latitude, longitude: r.longitude },
        type: 'runaway' as const,
        name: r.name,
        level: r.difficulty,
        icon: '🚔',
        cooldownSeconds: remainingSecs,
      };
    }),
    ...nearbyPackageGrabs.map((g) => {
      const cooldownKey = `packagegrab_${g.id}`;
      const remainingSecs = localCooldowns[cooldownKey] || 0;
      return {
        id: g.id,
        coordinate: { latitude: g.latitude, longitude: g.longitude },
        type: 'packageGrab' as const,
        name: g.name,
        level: useGameStore.getState().packageGrabLevel,
        icon: '📦',
        cooldownSeconds: remainingSecs,
      };
    }),
    ...nearbyShootouts.map((s) => {
      const cooldownKey = `shootout_${s.id}`;
      const remainingSecs = localCooldowns[cooldownKey] || 0;
      return {
        id: s.id,
        coordinate: { latitude: s.latitude, longitude: s.longitude },
        type: 'shootout' as const,
        name: s.name,
        level: useGameStore.getState().shootoutLevel,
        icon: '🔫',
        cooldownSeconds: remainingSecs,
      };
    }),
  ], [nearbyMonsters, nearbyMissions, nearbyPlayers, nearbyShops, nearbyRestaurants, nearbyNightclubs, nearbyBanks, nearbyCastles, nearbyCarChases, nearbyRunaways, nearbyPackageGrabs, nearbyShootouts, localCooldowns]);

  const handleMarkerPress = useCallback((marker: any) => {
    if (marker.type === 'monster') {
      const monster = nearbyMonsters.find((m) => m.id === marker.id);
      if (monster) setSelectedMarker({ type: 'monster', data: monster });
    } else if (marker.type === 'mission' || marker.type === 'bounty') {
      const mission = nearbyMissions.find((m) => m.id === marker.id);
      if (mission) setSelectedMarker({ type: 'mission', data: mission });
    } else if (marker.type === 'player') {
      const targetPlayer = nearbyPlayers.find((p) => p.id === marker.id);
      if (targetPlayer) {
        setSelectedMarker({ type: 'player', data: targetPlayer });
        setPlayerRelationship(null); // Reset while loading
        loadPlayerRelationship(targetPlayer.id);
      }
    } else if (marker.type === 'shop') {
      const shop = nearbyShops.find((s) => s.id === marker.id);
      if (shop) setSelectedMarker({ type: 'shop', data: shop });
    } else if (marker.type === 'restaurant') {
      const restaurant = nearbyRestaurants.find((r) => r.id === marker.id);
      if (restaurant) setSelectedMarker({ type: 'restaurant', data: restaurant });
    } else if (marker.type === 'nightclub') {
      const nightclub = nearbyNightclubs.find((nc) => nc.id === marker.id);
      if (nightclub) setSelectedMarker({ type: 'nightclub', data: nightclub });
    } else if (marker.type === 'bank') {
      const bank = nearbyBanks.find((b) => b.id === marker.id);
      if (bank) setSelectedBank(bank);
    } else if (marker.type === 'castle') {
      const castle = nearbyCastles.find((c) => c.id === marker.id);
      if (castle) setSelectedCastle(castle);
    } else if (marker.type === 'carChase') {
      const carChase = nearbyCarChases.find((cc) => cc.id === marker.id);
      if (carChase) setSelectedCarChase(carChase);
    } else if (marker.type === 'runaway') {
      const runaway = nearbyRunaways.find((r) => r.id === marker.id);
      if (runaway) setSelectedRunaway(runaway);
    } else if (marker.type === 'packageGrab') {
      const grab = nearbyPackageGrabs.find((g) => g.id === marker.id);
      if (grab) setSelectedPackageGrab(grab);
    } else if (marker.type === 'shootout') {
      const shootout = nearbyShootouts.find((s) => s.id === marker.id);
      if (shootout) setSelectedShootout(shootout);
    }
  }, [nearbyMonsters, nearbyMissions, nearbyPlayers, nearbyShops, nearbyRestaurants, nearbyNightclubs, nearbyBanks, nearbyCastles, nearbyCarChases, nearbyRunaways, nearbyPackageGrabs, nearbyShootouts]);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4285F4" />
        <Text style={styles.loadingText}>Finding your location...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {currentPosition && (
        <GameMap
          center={currentPosition}
          markers={mapMarkers}
          heading={heading}
          playerAvatar={globalProfilePic}
          territories={mapTerritories}
          onMarkerPress={handleMarkerPress}
          onTerritoryPress={handleTerritoryPress}
        />
      )}

      <SafeAreaView style={styles.hud}>
        <View style={styles.playerHud}>
          <View style={styles.hudNameRow}>
            <Text style={styles.playerName}>{player?.name}</Text>
            <Text style={styles.playerLevel}>Lv.{player?.level}</Text>
          </View>
          {/* HP Bar */}
          <View style={styles.statBarRow}>
            <Text style={styles.statBarLabel}>HP</Text>
            <View style={styles.statBarTrack}>
              <View style={[styles.statBarFill, styles.hpFill, { width: `${Math.min(100, ((player?.stats?.health ?? 0) / (player?.stats?.max_health || 1)) * 100)}%` }]} />
            </View>
            <Text style={styles.statBarValue}>{player?.stats?.health ?? 0}/{player?.stats?.max_health ?? 0}</Text>
          </View>
          {/* Energy Bar */}
          <View style={styles.statBarRow}>
            <Text style={styles.statBarLabel}>EN</Text>
            <View style={styles.statBarTrack}>
              <View style={[styles.statBarFill, styles.energyFill, { width: `${Math.min(100, ((player?.stats?.energy ?? 0) / (player?.stats?.max_energy || 1)) * 100)}%` }]} />
            </View>
            <Text style={styles.statBarValue}>{player?.stats?.energy ?? 0}/{player?.stats?.max_energy ?? 0}</Text>
          </View>
        </View>
        <View style={styles.hudRight}>
          <TouchableOpacity style={styles.shopButton} onPress={() => router.push('/shop')}>
            <Ionicons name="storefront" size={16} color="#f39c12" />
            <Text style={styles.shopCash}>${player?.cash || 0}</Text>
          </TouchableOpacity>
          <View style={[styles.gpsIndicator, isTracking && styles.gpsActive]}>
            <Ionicons name="navigate" size={14} color={isTracking ? '#34A853' : '#888'} />
          </View>
          <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh} disabled={isRefreshing}>
            <Ionicons name="refresh" size={22} color="#5F6368" style={isRefreshing ? styles.rotating : undefined} />
          </TouchableOpacity>
        </View>
      </SafeAreaView>

      {/* Popup */}
      {selectedMarker && (
        <View style={styles.popup}>
          <TouchableOpacity style={styles.popupClose} onPress={() => setSelectedMarker(null)}>
            <Ionicons name="close" size={24} color="#5F6368" />
          </TouchableOpacity>

          {selectedMarker.type === 'monster' && (
            <View>
              <View style={styles.popupHeader}>
                {getEnemyBattleImage(selectedMarker.data.name || '') ? (
                  <Image source={{ uri: getEnemyBattleImage(selectedMarker.data.name || '') as string }} style={{ width: 36, height: 36, borderRadius: 18 }} />
                ) : (
                  <Ionicons name="skull" size={28} color="#EA4335" />
                )}
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Level {selectedMarker.data.level}</Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={14} color="#34A853" />
                  <Text style={styles.rewardText}>${selectedMarker.data.loot_cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={14} color="#4285F4" />
                  <Text style={styles.rewardText}>{selectedMarker.data.loot_xp} XP</Text>
                </View>
              </View>
              <TouchableOpacity style={styles.actionButton} onPress={() => handleStartBattle(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>FIGHT</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'mission' && (
            <View>
              <View style={styles.popupHeader}>
                <Ionicons name="briefcase" size={28} color="#FBBC04" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.title}</Text>
                  <Text style={styles.popupSubtitle}>{selectedMarker.data.difficulty.toUpperCase()}</Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={14} color="#34A853" />
                  <Text style={styles.rewardText}>${selectedMarker.data.rewards.cash}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="star" size={14} color="#4285F4" />
                  <Text style={styles.rewardText}>{selectedMarker.data.rewards.xp} XP</Text>
                </View>
              </View>
              {selectedMarker.data.accepted_by === playerId ? (
                <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#4caf50'}]} onPress={() => handleStartMission(selectedMarker.data)}>
                  <Text style={styles.actionButtonText}>VIEW PROGRESS</Text>
                </TouchableOpacity>
              ) : selectedMarker.data.accepted_by ? (
                <View style={[styles.actionButton, {backgroundColor: '#555', opacity: 0.6}]}>
                  <Text style={styles.actionButtonText}>TAKEN</Text>
                </View>
              ) : (
                <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#FBBC04'}]} onPress={() => handleStartMission(selectedMarker.data)}>
                  <Text style={styles.actionButtonText}>VIEW MISSION</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {selectedMarker.type === 'player' && (
            <View>
              <View style={styles.popupHeader}>
                <Ionicons name="person" size={28} color="#4285F4" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Lv.{selectedMarker.data.level} • {selectedMarker.data.distance}m</Text>
                </View>
              </View>
              
              {/* Social Status */}
              {playerRelationship && (
                <View style={styles.socialStatusRow}>
                  {playerRelationship.is_friend && (
                    <View style={styles.friendIndicator}>
                      <Ionicons name="people" size={12} color="#27ae60" />
                      <Text style={styles.friendIndicatorText}>Friend</Text>
                    </View>
                  )}
                  {playerRelationship.is_followed_by && !playerRelationship.is_friend && (
                    <View style={styles.followsYouIndicator}>
                      <Text style={styles.followsYouText}>Follows you</Text>
                    </View>
                  )}
                </View>
              )}
              
              {/* Social Buttons */}
              <View style={styles.socialButtonsRow}>
                <TouchableOpacity 
                  style={[
                    styles.socialButton, 
                    playerRelationship?.is_following && styles.socialButtonActive
                  ]} 
                  onPress={() => handleFollowPlayer(selectedMarker.data)}
                  disabled={loadingFollow}
                >
                  {loadingFollow ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <>
                      <Ionicons 
                        name={playerRelationship?.is_following ? "checkmark-circle" : "add"} 
                        size={14} 
                        color="#fff" 
                      />
                      <Text style={styles.socialButtonText}>
                        {playerRelationship?.is_following ? 'Following' : 'Follow'}
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
                
                {!playerRelationship?.is_friend && (
                  <TouchableOpacity 
                    style={[
                      styles.socialButton, 
                      styles.friendRequestButton,
                      playerRelationship?.has_sent_friend_request && styles.socialButtonPending
                    ]} 
                    onPress={() => handleAddFriend(selectedMarker.data)}
                    disabled={loadingFriendRequest || playerRelationship?.has_sent_friend_request}
                  >
                    {loadingFriendRequest ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <>
                        <Ionicons 
                          name={playerRelationship?.has_sent_friend_request ? "hourglass" : "person-add"} 
                          size={14} 
                          color="#fff" 
                        />
                        <Text style={styles.socialButtonText}>
                          {playerRelationship?.has_sent_friend_request ? 'Pending' : 'Add Friend'}
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>
                )}
              </View>
              
              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#e74c3c'}]} onPress={() => handlePvPChallenge(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>CHALLENGE TO BATTLE</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'shop' && (
            <View>
              <View style={styles.popupHeader}>
                <Ionicons name="storefront" size={28} color="#FF6F00" />
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>
                    {selectedMarker.data.stock?.length || 0} items • {selectedMarker.data.price_multiplier < 1 ? 'SALE!' : selectedMarker.data.price_multiplier > 1.2 ? 'Expensive' : 'Fair prices'}
                  </Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="pricetag" size={14} color="#FF6F00" />
                  <Text style={styles.rewardText}>{selectedMarker.data.price_multiplier < 1 ? `${Math.round((1 - selectedMarker.data.price_multiplier) * 100)}% OFF` : `${Math.round(selectedMarker.data.price_multiplier * 100)}% prices`}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={14} color="#34A853" />
                  <Text style={styles.rewardText}>Your cash: ${player?.cash || 0}</Text>
                </View>
              </View>
              <TouchableOpacity 
                style={[styles.actionButton, {backgroundColor: '#FF6F00'}]} 
                onPress={() => {
                  SFX.gunShop();
                  setSelectedMarker(null);
                  router.push({ pathname: '/shop-detail', params: { shopData: JSON.stringify(selectedMarker.data) } });
                }}
              >
                <Text style={styles.actionButtonText}>BROWSE SHOP</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'restaurant' && (
            <View>
              <View style={styles.popupHeader}>
                <Text style={{ fontSize: 28 }}>🍔</Text>
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Heals 25% HP</Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="heart" size={14} color="#e74c3c" />
                  <Text style={styles.rewardText}>HP: {player?.stats?.health ?? 0}/{player?.stats?.max_health ?? 0}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="add-circle" size={14} color="#4caf50" />
                  <Text style={styles.rewardText}>+{Math.round((player?.stats?.max_health || 100) * 0.25)} HP</Text>
                </View>
              </View>
              <TouchableOpacity 
                style={[styles.actionButton, {backgroundColor: '#FF5722'}]} 
                onPress={async () => {
                  if (!playerId) return;
                  try {
                    const result = await eatAtRestaurant(selectedMarker.data.id, playerId);
                    SFX.restaurant();
                    showGameToast({
                      type: 'success',
                      title: `${selectedMarker.data.name}`,
                      message: result.healed > 0 ? `Healed ${result.healed} HP! (${result.health}/${result.max_health})` : 'Already at full health!',
                      duration: 3000,
                    });
                    // Refresh player data using TanStack Query
                    await refetchPlayer();
                    setSelectedMarker(null);
                  } catch (err: any) {
                    showGameToast({
                      type: 'warning',
                      title: 'Not Hungry Yet',
                      message: err?.response?.data?.detail || 'Try again later',
                      duration: 3000,
                    });
                  }
                }}
              >
                <Text style={styles.actionButtonText}>EAT HERE</Text>
              </TouchableOpacity>
            </View>
          )}

          {selectedMarker.type === 'nightclub' && (
            <View>
              <View style={styles.popupHeader}>
                <Text style={{ fontSize: 28 }}>🪩</Text>
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Restores 25% Energy</Text>
                </View>
              </View>
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="flash" size={14} color="#3498db" />
                  <Text style={styles.rewardText}>Energy: {player?.stats?.energy ?? 0}/{player?.stats?.max_energy ?? 100}</Text>
                </View>
                <View style={styles.rewardItem}>
                  <Ionicons name="add-circle" size={14} color="#9b59b6" />
                  <Text style={styles.rewardText}>+{Math.round((player?.stats?.max_energy || 100) * 0.25)} EN</Text>
                </View>
              </View>
              <TouchableOpacity 
                style={[styles.actionButton, {backgroundColor: '#9b59b6'}]} 
                onPress={async () => {
                  if (!playerId) return;
                  try {
                    const result = await visitNightclub(selectedMarker.data.id, playerId);
                    SFX.nightclub();
                    showGameToast({
                      type: 'success',
                      title: `${selectedMarker.data.name}`,
                      message: result.restored > 0 ? `Restored ${result.restored} Energy! (${result.energy}/${result.max_energy})` : 'Already at full energy!',
                      duration: 3000,
                    });
                    // Refresh player data using TanStack Query
                    await refetchPlayer();
                    setSelectedMarker(null);
                  } catch (err: any) {
                    showGameToast({
                      type: 'warning',
                      title: 'Too Soon!',
                      message: err?.response?.data?.detail || 'Try again later',
                      duration: 3000,
                    });
                  }
                }}
              >
                <Text style={styles.actionButtonText}>PARTY HERE</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {/* Territory Modal */}
      <Modal
        visible={!!selectedTerritory}
        transparent
        animationType="slide"
        onRequestClose={() => { setSelectedTerritory(null); setTerritoryBattleLog([]); }}
      >
        <Pressable style={styles.terrOverlay} onPress={() => { setSelectedTerritory(null); setTerritoryBattleLog([]); }}>
          <Pressable style={styles.terrModal} onPress={() => {}}>
            {selectedTerritory && (
              <>
                {/* Header */}
                <View style={[styles.terrHeader, { borderLeftColor: selectedTerritory.color || '#e74c3c' }]}>
                  <View style={styles.terrHeaderLeft}>
                    {selectedTerritory.owner_pic ? (
                      <Image
                        source={{ uri: selectedTerritory.owner_pic }}
                        style={styles.terrOwnerPic}
                      />
                    ) : (
                      <Text style={styles.terrIcon}>{selectedTerritory.owner_id ? '👑' : '⚔️'}</Text>
                    )}
                    <View>
                      <Text style={styles.terrTitle}>{selectedTerritory.name}</Text>
                      <Text style={styles.terrOwner}>
                        {selectedTerritory.owner_id === playerId ? 'Owned by YOU'
                          : selectedTerritory.owner_id ? `Owned by ${selectedTerritory.owner_name}`
                          : 'Unclaimed Territory'}
                      </Text>
                    </View>
                  </View>
                  <TouchableOpacity onPress={() => { setSelectedTerritory(null); setTerritoryBattleLog([]); }}>
                    <Ionicons name="close-circle" size={28} color="#555" />
                  </TouchableOpacity>
                </View>

                {/* Info */}
                <View style={styles.terrInfoRow}>
                  <View style={styles.terrInfoBox}>
                    <Ionicons name="cash" size={20} color="#f39c12" />
                    <Text style={styles.terrInfoLabel}>DAILY INCOME</Text>
                    <Text style={styles.terrInfoValue}>${selectedTerritory.rewards?.passive_income || 0}/day</Text>
                  </View>
                </View>

                {/* Boss info (if unclaimed) */}
                {!selectedTerritory.owner_id && selectedTerritory.boss && (
                  <View style={styles.terrBossRow}>
                    <Ionicons name="skull" size={16} color="#e74c3c" />
                    <Text style={styles.terrBossText}>
                      Boss: {selectedTerritory.boss.name} (Lv.{selectedTerritory.boss.level}) — HP: {selectedTerritory.boss.health} / ATK: {selectedTerritory.boss.attack}
                    </Text>
                  </View>
                )}

                {/* Battle Log */}
                {territoryBattleLog.length > 0 && (
                  <ScrollView style={styles.terrBattleLog} showsVerticalScrollIndicator={true} nestedScrollEnabled={true}>
                    {territoryBattleLog.map((line, idx) => (
                      <Text key={idx} style={[
                        styles.terrLogLine,
                        line.includes('Victory') && styles.terrLogVictory,
                        line.includes('Defeated') && styles.terrLogDefeat,
                        line.includes('CRITICAL') && styles.terrLogCrit,
                      ]}>{line}</Text>
                    ))}
                  </ScrollView>
                )}

                {/* Actions */}
                <View style={styles.terrActions}>
                  {selectedTerritory.owner_id === playerId ? (
                    <TouchableOpacity
                      style={[styles.terrBtn, { backgroundColor: '#f39c12' }]}
                      onPress={handleCollectIncome}
                    >
                      <Ionicons name="cash" size={18} color="#fff" />
                      <Text style={styles.terrBtnText}>COLLECT INCOME</Text>
                    </TouchableOpacity>
                  ) : (
                    <TouchableOpacity
                      style={[styles.terrBtn, { backgroundColor: '#e74c3c' }]}
                      onPress={handleTerritoryCapture}
                      disabled={territoryFighting}
                    >
                      {territoryFighting ? (
                        <ActivityIndicator size="small" color="#fff" />
                      ) : (
                        <>
                          <Ionicons name="flash" size={18} color="#fff" />
                          <Text style={styles.terrBtnText}>
                            {selectedTerritory.owner_id ? 'CHALLENGE OWNER' : 'FIGHT BOSS'}
                          </Text>
                        </>
                      )}
                    </TouchableOpacity>
                  )}
                </View>
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>

      {/* Bank Robbery Modal */}
      <Modal
        visible={!!selectedBank}
        transparent
        animationType="fade"
        onRequestClose={() => setSelectedBank(null)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setSelectedBank(null)}>
          <Pressable style={styles.terrModal} onPress={(e) => e.stopPropagation()}>
            <TouchableOpacity style={styles.terrClose} onPress={() => setSelectedBank(null)}>
              <Ionicons name="close" size={22} color="#666" />
            </TouchableOpacity>

            {selectedBank && (
              <>
                <View style={styles.terrHeader}>
                  <Text style={styles.bankIcon}>🏦</Text>
                  <View style={styles.terrHeaderText}>
                    <Text style={styles.terrName}>{selectedBank.name}</Text>
                    <Text style={styles.terrSubtitle}>Bank Robbery Mission</Text>
                  </View>
                </View>

                <View style={styles.terrStats}>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="cash-outline" size={16} color="#f39c12" />
                    <Text style={styles.terrStatLabel}>Potential Loot:</Text>
                    <Text style={styles.terrStatValue}>${selectedBank.min_reward} - ${selectedBank.max_reward}</Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="warning-outline" size={16} color="#e74c3c" />
                    <Text style={styles.terrStatLabel}>Risk Level:</Text>
                    <Text style={[styles.terrStatValue, { color: '#e74c3c' }]}>50% Chance of Getting Caught</Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="time-outline" size={16} color="#888" />
                    <Text style={styles.terrStatLabel}>Cooldown:</Text>
                    <Text style={styles.terrStatValue}>30 minutes</Text>
                  </View>
                </View>

                <Text style={styles.bankWarning}>
                  ⚠️ If caught, you will lose money as a fine!
                </Text>

                <View style={styles.terrActions}>
                  <TouchableOpacity
                    style={[styles.terrBtn, { backgroundColor: '#e74c3c' }]}
                    onPress={handleRobBank}
                    disabled={robbingBank}
                  >
                    {robbingBank ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="flash" size={18} color="#fff" />
                        <Text style={styles.terrBtnText}>ROB THE BANK</Text>
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>

      {/* Castle Cannon / Car Chase / Runaway / Package Grab / Shootout Mini-game Modal */}
      <Modal
        visible={!!selectedCastle || !!selectedCarChase || !!selectedRunaway || !!selectedPackageGrab || !!selectedShootout}
        transparent
        animationType="fade"
        onRequestClose={() => { setSelectedCastle(null); setSelectedCarChase(null); setSelectedRunaway(null); setSelectedPackageGrab(null); setSelectedShootout(null); }}
      >
        <Pressable style={styles.modalOverlay} onPress={() => { setSelectedCastle(null); setSelectedCarChase(null); setSelectedRunaway(null); setSelectedPackageGrab(null); setSelectedShootout(null); }}>
          <Pressable style={styles.terrModal} onPress={(e) => e.stopPropagation()}>
            <TouchableOpacity style={styles.terrClose} onPress={() => { setSelectedCastle(null); setSelectedCarChase(null); setSelectedRunaway(null); setSelectedPackageGrab(null); setSelectedShootout(null); }}>
              <Ionicons name="close" size={22} color="#666" />
            </TouchableOpacity>

            {selectedCastle && (
              <>
                <View style={styles.terrHeader}>
                  <Text style={styles.bankIcon}>🏰</Text>
                  <View style={styles.terrHeaderText}>
                    <Text style={styles.terrName}>{selectedCastle.name}</Text>
                    <Text style={styles.terrSubtitle}>Cannon Assault Mission</Text>
                  </View>
                </View>

                <View style={styles.terrStats}>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="flash-outline" size={16} color="#e74c3c" />
                    <Text style={styles.terrStatLabel}>Difficulty:</Text>
                    <Text style={[styles.terrStatValue, { color: '#e74c3c' }]}>
                      {'⚔️'.repeat(selectedCastle.difficulty)}
                    </Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="cash-outline" size={16} color="#f39c12" />
                    <Text style={styles.terrStatLabel}>Reward:</Text>
                    <Text style={styles.terrStatValue}>${selectedCastle.min_reward} - ${selectedCastle.max_reward}</Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="star-outline" size={16} color="#9b59b6" />
                    <Text style={styles.terrStatLabel}>XP/Rep:</Text>
                    <Text style={styles.terrStatValue}>+{selectedCastle.xp_reward} XP, +{selectedCastle.rep_reward} Rep</Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Ionicons name="time-outline" size={16} color="#888" />
                    <Text style={styles.terrStatLabel}>Cooldown:</Text>
                    <Text style={styles.terrStatValue}>15 minutes per attempt</Text>
                  </View>
                </View>

                {/* Show cooldown warning if active */}
                {localCooldowns[`castle_${selectedCastle.id}`] > 0 && (
                  <View style={styles.cooldownWarning}>
                    <Ionicons name="time" size={20} color="#f39c12" />
                    <Text style={styles.cooldownWarningText}>
                      Cooldown: {Math.floor(localCooldowns[`castle_${selectedCastle.id}`] / 60)}m {localCooldowns[`castle_${selectedCastle.id}`] % 60}s
                    </Text>
                  </View>
                )}

                <View style={styles.castleInfo}>
                  <Text style={styles.castleInfoTitle}>🎯 Mission Briefing</Text>
                  <Text style={styles.castleInfoText}>
                    Use your cannon to eliminate all gang members!{'\n'}
                    • Drag to aim the cannon angle{'\n'}
                    • You have exactly 3 shots{'\n'}
                    • Destroy forts to knock down enemies{'\n'}
                    • Eliminate all targets to win!
                  </Text>
                </View>

                <View style={styles.terrActions}>
                  <TouchableOpacity
                    style={[
                      styles.terrBtn, 
                      { backgroundColor: localCooldowns[`castle_${selectedCastle.id}`] > 0 ? '#555' : '#8B4513' }
                    ]}
                    onPress={handleStartCastleGame}
                    disabled={localCooldowns[`castle_${selectedCastle.id}`] > 0}
                  >
                    {localCooldowns[`castle_${selectedCastle.id}`] > 0 ? (
                      <>
                        <Ionicons name="time" size={18} color="#aaa" />
                        <Text style={[styles.terrBtnText, { color: '#aaa' }]}>ON COOLDOWN</Text>
                      </>
                    ) : (
                      <>
                        <Ionicons name="flame" size={18} color="#fff" />
                        <Text style={styles.terrBtnText}>ATTACK FORTRESS</Text>
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}

            {/* Car Chase Modal Content */}
            {selectedCarChase && (
              <>
                <View style={styles.terrHeader}>
                  <Text style={{ fontSize: 28 }}>🚗💨</Text>
                  <View style={styles.terrHeaderInfo}>
                    <Text style={[styles.terrName, { color: '#e74c3c' }]}>{selectedCarChase.name}</Text>
                    <Text style={styles.terrOwner}>Car Chase Event</Text>
                  </View>
                  <TouchableOpacity 
                    style={styles.terrClose} 
                    onPress={() => setSelectedCarChase(null)}
                  >
                    <Ionicons name="close" size={24} color="#666" />
                  </TouchableOpacity>
                </View>

                <View style={styles.terrStats}>
                  <View style={styles.terrStatRow}>
                    <Text style={styles.terrStatLabel}>Difficulty:</Text>
                    <Text style={[styles.terrStatValue, { color: '#e74c3c' }]}>
                      {'⭐'.repeat(Math.min(5, Math.ceil(selectedCarChase.difficulty / 2)))}
                    </Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Text style={styles.terrStatLabel}>Distance:</Text>
                    <Text style={styles.terrStatValue}>{selectedCarChase.county_line_distance}m to county line</Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Text style={styles.terrStatLabel}>Cash Reward:</Text>
                    <Text style={[styles.terrStatValue, { color: '#4caf50' }]}>
                      ${selectedCarChase.min_reward} - ${selectedCarChase.max_reward}
                    </Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Text style={styles.terrStatLabel}>XP/Rep:</Text>
                    <Text style={styles.terrStatValue}>
                      +{selectedCarChase.xp_reward} XP / +{selectedCarChase.rep_reward} Rep
                    </Text>
                  </View>
                  <View style={styles.terrStatRow}>
                    <Text style={styles.terrStatLabel}>Cooldown:</Text>
                    <Text style={styles.terrStatValue}>15 minutes per attempt</Text>
                  </View>
                </View>

                {/* Show cooldown warning if active */}
                {localCooldowns[`carchase_${selectedCarChase.id}`] > 0 && (
                  <View style={styles.cooldownWarning}>
                    <Ionicons name="time" size={20} color="#f39c12" />
                    <Text style={styles.cooldownWarningText}>
                      Cooldown: {Math.floor(localCooldowns[`carchase_${selectedCarChase.id}`] / 60)}m {localCooldowns[`carchase_${selectedCarChase.id}`] % 60}s
                    </Text>
                  </View>
                )}

                <View style={styles.castleInfo}>
                  <Text style={styles.castleInfoTitle}>🚔 Mission Briefing</Text>
                  <Text style={styles.castleInfoText}>
                    Escape the cops before they catch you!{'\n'}
                    • Tap LEFT or RIGHT to change lanes{'\n'}
                    • Avoid traffic and obstacles{'\n'}
                    • Police get closer over time{'\n'}
                    • Reach the county line to escape!
                  </Text>
                </View>

                <View style={styles.terrActions}>
                  <TouchableOpacity
                    style={[
                      styles.terrBtn, 
                      { backgroundColor: localCooldowns[`carchase_${selectedCarChase.id}`] > 0 ? '#555' : '#e74c3c' }
                    ]}
                    onPress={handleStartCarChase}
                    disabled={startingCarChase || localCooldowns[`carchase_${selectedCarChase.id}`] > 0}
                  >
                    {startingCarChase ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : localCooldowns[`carchase_${selectedCarChase.id}`] > 0 ? (
                      <>
                        <Ionicons name="time" size={18} color="#aaa" />
                        <Text style={[styles.terrBtnText, { color: '#aaa' }]}>ON COOLDOWN</Text>
                      </>
                    ) : (
                      <>
                        <Ionicons name="car-sport" size={18} color="#fff" />
                        <Text style={styles.terrBtnText}>START CHASE</Text>
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}
            
            {/* Runaway Modal Content */}
            {selectedRunaway && (
              <>
                {/* Header */}
                <View style={styles.runawayHeader}>
                  <View style={styles.runawayIconContainer}>
                    <Text style={styles.runawayIcon}>🚔</Text>
                  </View>
                  <View style={styles.runawayHeaderText}>
                    <Text style={styles.runawayTitle}>{selectedRunaway.name}</Text>
                    <Text style={styles.runawaySubtitle}>Runaway Simulator</Text>
                  </View>
                </View>
                
                {/* Selected Level Card */}
                <View style={styles.runawayLevelCard}>
                  <View style={styles.runawayLevelRow}>
                    <Text style={styles.runawayLevelLabel}>Selected Level:</Text>
                    <Text style={styles.runawayLevelValue}>
                      Level {useGameStore.getState().runawayLevel} {'⭐'.repeat(Math.min(5, Math.ceil(useGameStore.getState().runawayLevel / 4)))}
                    </Text>
                  </View>
                  <Text style={styles.runawayLevelHint}>
                    Change level in Options → Mini Games → Runaway
                  </Text>
                </View>
                
                {/* Instructions Card - Clearly Visible */}
                <View style={styles.runawayInstructionsCard}>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>🏃</Text>
                    <Text style={styles.runawayInstructionText}>Run through the streets and avoid obstacles!</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>⬆️</Text>
                    <Text style={styles.runawayInstructionText}>Jump over low obstacles (trash cans, barriers)</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>⬇️</Text>
                    <Text style={styles.runawayInstructionText}>Duck under high obstacles (signs, awnings)</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>🏠</Text>
                    <Text style={styles.runawayInstructionText}>Reach the hideout to escape and win rewards!</Text>
                  </View>
                </View>
                
                {/* Cooldown Warning */}
                {localCooldowns[`runaway_${selectedRunaway.id}`] > 0 && (
                  <View style={styles.cooldownWarning}>
                    <Ionicons name="time" size={18} color="#f39c12" />
                    <Text style={styles.cooldownWarningText}>
                      Cooldown: {Math.floor(localCooldowns[`runaway_${selectedRunaway.id}`] / 60)}m {localCooldowns[`runaway_${selectedRunaway.id}`] % 60}s
                    </Text>
                  </View>
                )}
                
                {/* Action Buttons */}
                <View style={styles.runawayButtonContainer}>
                  {/* Cancel Button - Styled Secondary */}
                  <TouchableOpacity 
                    style={styles.runawayCancelButton} 
                    onPress={() => setSelectedRunaway(null)}
                    activeOpacity={0.7}
                  >
                    <Ionicons name="close-circle-outline" size={20} color="#888" />
                    <Text style={styles.runawayCancelText}>CANCEL</Text>
                  </TouchableOpacity>
                  
                  {/* Start Button - Polished Game Button */}
                  <TouchableOpacity 
                    style={[
                      styles.runawayStartButton, 
                      localCooldowns[`runaway_${selectedRunaway.id}`] > 0 && styles.runawayStartButtonDisabled
                    ]}
                    onPress={handleStartRunaway}
                    disabled={startingRunaway || localCooldowns[`runaway_${selectedRunaway.id}`] > 0}
                    activeOpacity={0.8}
                  >
                    {startingRunaway ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : localCooldowns[`runaway_${selectedRunaway.id}`] > 0 ? (
                      <>
                        <Ionicons name="time" size={22} color="#888" />
                        <Text style={styles.runawayStartTextDisabled}>ON COOLDOWN</Text>
                      </>
                    ) : (
                      <>
                        <Ionicons name="flash" size={22} color="#fff" />
                        <Text style={styles.runawayStartText}>START RUNNING</Text>
                        <Ionicons name="arrow-forward" size={20} color="#fff" />
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}
            
            {/* Package Grab Modal Content */}
            {selectedPackageGrab && (
              <>
                {/* Header */}
                <View style={styles.runawayHeader}>
                  <View style={[styles.runawayIconContainer, { backgroundColor: 'rgba(230,126,34,0.2)', borderColor: '#e67e22' }]}>
                    <Text style={styles.runawayIcon}>📦</Text>
                  </View>
                  <View style={styles.runawayHeaderText}>
                    <Text style={[styles.runawayTitle, { color: '#e67e22' }]}>{selectedPackageGrab.name}</Text>
                    <Text style={styles.runawaySubtitle}>Package Grab</Text>
                  </View>
                </View>
                
                {/* Selected Level Card */}
                <View style={[styles.runawayLevelCard, { backgroundColor: 'rgba(230,126,34,0.12)', borderColor: 'rgba(230,126,34,0.25)' }]}>
                  <View style={styles.runawayLevelRow}>
                    <Text style={styles.runawayLevelLabel}>Selected Level:</Text>
                    <Text style={[styles.runawayLevelValue, { color: '#e67e22' }]}>
                      Level {useGameStore.getState().packageGrabLevel} {'⭐'.repeat(Math.min(5, Math.ceil(useGameStore.getState().packageGrabLevel / 4)))}
                    </Text>
                  </View>
                  <Text style={styles.runawayLevelHint}>
                    Change level in Options → Mini Games → Package Grab
                  </Text>
                </View>
                
                {/* Instructions Card */}
                <View style={styles.runawayInstructionsCard}>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>⬅️➡️</Text>
                    <Text style={styles.runawayInstructionText}>Move left/right to collect boxes</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>📦</Text>
                    <Text style={styles.runawayInstructionText}>Collect boxes for bonus rewards</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>🚧</Text>
                    <Text style={styles.runawayInstructionText}>Avoid obstacles or you will crash!</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>🏁</Text>
                    <Text style={styles.runawayInstructionText}>Reach the finish to complete delivery</Text>
                  </View>
                </View>
                
                {/* Cooldown Warning */}
                {localCooldowns[`packagegrab_${selectedPackageGrab.id}`] > 0 && (
                  <View style={styles.cooldownWarning}>
                    <Ionicons name="time" size={18} color="#f39c12" />
                    <Text style={styles.cooldownWarningText}>
                      Cooldown: {Math.floor(localCooldowns[`packagegrab_${selectedPackageGrab.id}`] / 60)}m {localCooldowns[`packagegrab_${selectedPackageGrab.id}`] % 60}s
                    </Text>
                  </View>
                )}
                
                {/* Action Buttons */}
                <View style={styles.runawayButtonContainer}>
                  <TouchableOpacity 
                    style={styles.runawayCancelButton} 
                    onPress={() => setSelectedPackageGrab(null)}
                    activeOpacity={0.7}
                  >
                    <Ionicons name="close-circle-outline" size={20} color="#888" />
                    <Text style={styles.runawayCancelText}>CANCEL</Text>
                  </TouchableOpacity>
                  
                  <TouchableOpacity 
                    style={[
                      styles.runawayStartButton, 
                      { backgroundColor: '#e67e22', borderColor: '#f39c12' },
                      localCooldowns[`packagegrab_${selectedPackageGrab.id}`] > 0 && styles.runawayStartButtonDisabled
                    ]}
                    onPress={handleStartPackageGrab}
                    disabled={startingPackageGrab || localCooldowns[`packagegrab_${selectedPackageGrab.id}`] > 0}
                    activeOpacity={0.8}
                  >
                    {startingPackageGrab ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : localCooldowns[`packagegrab_${selectedPackageGrab.id}`] > 0 ? (
                      <>
                        <Ionicons name="time" size={22} color="#888" />
                        <Text style={styles.runawayStartTextDisabled}>ON COOLDOWN</Text>
                      </>
                    ) : (
                      <>
                        <Ionicons name="car" size={22} color="#fff" />
                        <Text style={styles.runawayStartText}>START DELIVERY</Text>
                        <Ionicons name="arrow-forward" size={20} color="#fff" />
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}
            
            {/* Shootout Modal Content */}
            {selectedShootout && (
              <>
                {/* Header */}
                <View style={styles.runawayHeader}>
                  <View style={[styles.runawayIconContainer, { backgroundColor: 'rgba(192,57,43,0.2)', borderColor: '#c0392b' }]}>
                    <Text style={styles.runawayIcon}>🔫</Text>
                  </View>
                  <View style={styles.runawayHeaderText}>
                    <Text style={[styles.runawayTitle, { color: '#c0392b' }]}>{selectedShootout.name}</Text>
                    <Text style={styles.runawaySubtitle}>Shootout Simulator</Text>
                  </View>
                </View>
                
                {/* Selected Level Card */}
                <View style={[styles.runawayLevelCard, { backgroundColor: 'rgba(192,57,43,0.12)', borderColor: 'rgba(192,57,43,0.25)' }]}>
                  <View style={styles.runawayLevelRow}>
                    <Text style={styles.runawayLevelLabel}>Selected Level:</Text>
                    <Text style={[styles.runawayLevelValue, { color: '#c0392b' }]}>
                      Level {useGameStore.getState().shootoutLevel} {'⭐'.repeat(Math.min(5, Math.ceil(useGameStore.getState().shootoutLevel / 4)))}
                    </Text>
                  </View>
                  <Text style={styles.runawayLevelHint}>
                    Change level in Options → Mini Games → Shootout
                  </Text>
                </View>
                
                {/* Instructions Card */}
                <View style={styles.runawayInstructionsCard}>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>🎯</Text>
                    <Text style={styles.runawayInstructionText}>Crosshair moves automatically</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>👆</Text>
                    <Text style={styles.runawayInstructionText}>Tap anywhere to shoot (12 shots total)</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>🧍</Text>
                    <Text style={styles.runawayInstructionText}>Hit gang members for cash & XP</Text>
                  </View>
                  <View style={styles.runawayInstructionRow}>
                    <Text style={styles.runawayInstructionIcon}>⏱️</Text>
                    <Text style={styles.runawayInstructionText}>Score before time runs out!</Text>
                  </View>
                </View>
                
                {/* Cooldown Warning */}
                {localCooldowns[`shootout_${selectedShootout.id}`] > 0 && (
                  <View style={styles.cooldownWarning}>
                    <Ionicons name="time" size={18} color="#f39c12" />
                    <Text style={styles.cooldownWarningText}>
                      Cooldown: {Math.floor(localCooldowns[`shootout_${selectedShootout.id}`] / 60)}m {localCooldowns[`shootout_${selectedShootout.id}`] % 60}s
                    </Text>
                  </View>
                )}
                
                {/* Action Buttons */}
                <View style={styles.runawayButtonContainer}>
                  <TouchableOpacity 
                    style={styles.runawayCancelButton} 
                    onPress={() => setSelectedShootout(null)}
                    activeOpacity={0.7}
                  >
                    <Ionicons name="close-circle-outline" size={20} color="#888" />
                    <Text style={styles.runawayCancelText}>CANCEL</Text>
                  </TouchableOpacity>
                  
                  {/* Start Button */}
                  <TouchableOpacity 
                    style={[
                      styles.runawayStartButton, 
                      { backgroundColor: '#c0392b', borderColor: '#e74c3c' },
                      localCooldowns[`shootout_${selectedShootout.id}`] > 0 && styles.runawayStartButtonDisabled
                    ]}
                    onPress={handleStartShootout}
                    disabled={startingShootout || localCooldowns[`shootout_${selectedShootout.id}`] > 0}
                    activeOpacity={0.8}
                  >
                    {startingShootout ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : localCooldowns[`shootout_${selectedShootout.id}`] > 0 ? (
                      <>
                        <Ionicons name="time" size={22} color="#888" />
                        <Text style={styles.runawayStartTextDisabled}>ON COOLDOWN</Text>
                      </>
                    ) : (
                      <>
                        <Ionicons name="flash" size={22} color="#fff" />
                        <Text style={styles.runawayStartText}>START SHOOTOUT</Text>
                        <Ionicons name="arrow-forward" size={20} color="#fff" />
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
  loadingText: { color: '#5F6368', marginTop: 12, fontSize: 14 },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff', padding: 24 },
  errorTitle: { color: '#202124', fontSize: 18, fontWeight: '600', marginTop: 16 },
  errorText: { color: '#5F6368', marginTop: 8, textAlign: 'center' },
  retryButton: { marginTop: 20, backgroundColor: '#4285F4', paddingHorizontal: 24, paddingVertical: 10, borderRadius: 20 },
  retryText: { color: '#fff', fontWeight: '600' },
  hud: { position: 'absolute', top: 0, left: 0, right: 0, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingTop: 4 },
  playerHud: { backgroundColor: '#fff', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 14, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3, minWidth: 150 },
  hudNameRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  playerName: { color: '#202124', fontWeight: '700', fontSize: 13 },
  playerLevel: { color: '#4285F4', fontWeight: '700', marginLeft: 6, fontSize: 13 },
  statBarRow: { flexDirection: 'row', alignItems: 'center', marginTop: 3 },
  statBarLabel: { color: '#888', fontSize: 9, fontWeight: '800', width: 18 },
  statBarTrack: { flex: 1, height: 8, backgroundColor: '#e0e0e0', borderRadius: 4, overflow: 'hidden' },
  statBarFill: { height: '100%', borderRadius: 4 },
  hpFill: { backgroundColor: '#e74c3c' },
  energyFill: { backgroundColor: '#3498db' },
  statBarValue: { color: '#555', fontSize: 9, fontWeight: '700', marginLeft: 5, minWidth: 40, textAlign: 'right' },
  hudRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  shopButton: { backgroundColor: '#fff', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 20, flexDirection: 'row', alignItems: 'center', gap: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  shopCash: { color: '#f39c12', fontSize: 12, fontWeight: '700' },
  gpsIndicator: { backgroundColor: '#fff', padding: 8, borderRadius: 20, marginRight: 6, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  gpsActive: { backgroundColor: '#E8F5E9' },
  refreshButton: { backgroundColor: '#fff', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  rotating: { opacity: 0.5 },
  entityList: { position: 'absolute', bottom: 90, left: 0, right: 0, paddingHorizontal: 8 },
  entityCard: { backgroundColor: '#fff', borderRadius: 12, padding: 10, marginHorizontal: 4, alignItems: 'center', minWidth: 85, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.15, shadowRadius: 3, elevation: 3 },
  monsterCard: { borderLeftWidth: 3, borderLeftColor: '#EA4335' },
  missionCard: { borderLeftWidth: 3, borderLeftColor: '#FBBC04' },
  entityName: { color: '#202124', fontSize: 11, fontWeight: '600', marginTop: 4, maxWidth: 70 },
  entityLevel: { color: '#5F6368', fontSize: 10, marginTop: 2 },
  popup: { position: 'absolute', bottom: 170, left: 12, right: 12, backgroundColor: '#fff', borderRadius: 16, padding: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.2, shadowRadius: 8, elevation: 5 },
  popupClose: { position: 'absolute', top: 10, right: 10, zIndex: 1 },
  popupHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  popupHeaderText: { marginLeft: 10 },
  popupTitle: { color: '#202124', fontSize: 16, fontWeight: '600' },
  popupSubtitle: { color: '#5F6368', fontSize: 12 },
  rewardsRow: { flexDirection: 'row', marginBottom: 12 },
  rewardItem: { flexDirection: 'row', alignItems: 'center', marginRight: 16 },
  rewardText: { color: '#202124', marginLeft: 4, fontWeight: '600', fontSize: 13 },
  actionButton: { backgroundColor: '#EA4335', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, borderRadius: 8 },
  actionButtonText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  // Territory Modal
  terrOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end', zIndex: 9999 },
  terrModal: { backgroundColor: '#1a1a1a', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 32, maxHeight: '80%' },
  terrHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderLeftWidth: 4, paddingLeft: 12, marginBottom: 16 },
  terrHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  terrIcon: { fontSize: 28 },
  terrOwnerPic: { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: '#f39c12' },
  terrTitle: { color: '#fff', fontSize: 18, fontWeight: '800' },
  terrOwner: { color: '#888', fontSize: 12, marginTop: 2 },
  terrInfoRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  terrInfoBox: { flex: 1, backgroundColor: '#222', borderRadius: 12, padding: 12, alignItems: 'center', gap: 4 },
  terrInfoLabel: { color: '#888', fontSize: 10, fontWeight: '700' },
  terrInfoValue: { color: '#fff', fontSize: 13, fontWeight: '700' },
  terrBossRow: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: 'rgba(231,76,60,0.1)', padding: 10, borderRadius: 10, marginBottom: 12 },
  terrBossText: { color: '#e74c3c', fontSize: 12, fontWeight: '600', flex: 1 },
  terrBattleLog: { maxHeight: 200, backgroundColor: '#111', borderRadius: 10, padding: 10, marginBottom: 12, flexGrow: 0 },
  terrLogLine: { color: '#aaa', fontSize: 11, marginBottom: 3, fontFamily: 'monospace' },
  terrLogVictory: { color: '#4caf50', fontWeight: '700' },
  terrLogDefeat: { color: '#e74c3c', fontWeight: '700' },
  terrLogCrit: { color: '#f39c12' },
  terrActions: { marginTop: 4 },
  terrBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderRadius: 12 },
  terrBtnText: { color: '#fff', fontSize: 15, fontWeight: '800', letterSpacing: 1 },
  
  // Bank Modal  
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end', zIndex: 9999 },
  bankIcon: { fontSize: 40 },
  bankWarning: { color: '#f39c12', fontSize: 12, textAlign: 'center', marginBottom: 12, padding: 10, backgroundColor: 'rgba(243,156,18,0.1)', borderRadius: 8 },
  terrName: { color: '#fff', fontSize: 18, fontWeight: '800' },
  terrSubtitle: { color: '#888', fontSize: 12, marginTop: 2 },
  terrHeaderText: { marginLeft: 12, flex: 1 },
  terrStats: { backgroundColor: '#222', borderRadius: 12, padding: 12, marginBottom: 12 },
  terrStatRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  terrStatLabel: { color: '#888', fontSize: 12, flex: 1 },
  terrStatValue: { color: '#fff', fontSize: 12, fontWeight: '600' },
  terrClose: { position: 'absolute', top: 12, right: 12, zIndex: 10 },
  
  // Castle Modal
  castleInfo: { backgroundColor: '#2a1a0a', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#8B4513' },
  castleInfoTitle: { color: '#CD853F', fontSize: 14, fontWeight: '700', marginBottom: 8 },
  castleInfoText: { color: '#d1d5db', fontSize: 12, lineHeight: 20 },
  
  // Cooldown Warning
  cooldownWarning: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'center',
    gap: 8, 
    backgroundColor: 'rgba(243,156,18,0.15)', 
    borderRadius: 10, 
    padding: 12, 
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(243,156,18,0.3)',
  },
  cooldownWarningText: { 
    color: '#f39c12', 
    fontSize: 14, 
    fontWeight: '700' 
  },
  
  // ========== RUNAWAY SIMULATOR MODAL STYLES ==========
  runawayHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,184,148,0.3)',
  },
  runawayIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 16,
    backgroundColor: 'rgba(0,184,148,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#00b894',
  },
  runawayIcon: {
    fontSize: 30,
  },
  runawayHeaderText: {
    marginLeft: 14,
    flex: 1,
  },
  runawayTitle: {
    color: '#00b894',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  runawaySubtitle: {
    color: '#888',
    fontSize: 13,
    marginTop: 2,
  },
  runawayLevelCard: {
    backgroundColor: 'rgba(0,184,148,0.12)',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,184,148,0.25)',
  },
  runawayLevelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  runawayLevelLabel: {
    color: '#aaa',
    fontSize: 13,
    fontWeight: '600',
  },
  runawayLevelValue: {
    color: '#00b894',
    fontSize: 15,
    fontWeight: '800',
  },
  runawayLevelHint: {
    color: '#666',
    fontSize: 10,
    marginTop: 6,
    fontStyle: 'italic',
  },
  runawayInstructionsCard: {
    backgroundColor: '#252525',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  runawayInstructionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  runawayInstructionIcon: {
    fontSize: 20,
    width: 32,
    textAlign: 'center',
  },
  runawayInstructionText: {
    color: '#e0e0e0',
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
    marginLeft: 8,
    lineHeight: 20,
  },
  runawayButtonContainer: {
    gap: 12,
    paddingTop: 4,
  },
  runawayCancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    backgroundColor: '#2a2a2a',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#444',
  },
  runawayCancelText: {
    color: '#888',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 1,
  },
  runawayStartButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 18,
    borderRadius: 16,
    backgroundColor: '#00b894',
    borderWidth: 3,
    borderColor: '#00d4aa',
    shadowColor: '#00b894',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  runawayStartButtonDisabled: {
    backgroundColor: '#3a3a3a',
    borderColor: '#555',
    shadowOpacity: 0,
    elevation: 0,
  },
  runawayStartText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1.5,
    textShadowColor: 'rgba(0,0,0,0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  runawayStartTextDisabled: {
    color: '#888',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 1,
  },
  
  // Social buttons for player popup
  socialStatusRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
    flexWrap: 'wrap',
  },
  friendIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(39, 174, 96, 0.2)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  friendIndicatorText: {
    color: '#27ae60',
    fontSize: 11,
    fontWeight: '600',
  },
  followsYouIndicator: {
    backgroundColor: 'rgba(52, 152, 219, 0.2)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  followsYouText: {
    color: '#3498db',
    fontSize: 11,
    fontWeight: '600',
  },
  socialButtonsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  socialButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#3498db',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    gap: 6,
  },
  socialButtonActive: {
    backgroundColor: '#27ae60',
  },
  socialButtonPending: {
    backgroundColor: '#7f8c8d',
  },
  friendRequestButton: {
    backgroundColor: '#9b59b6',
  },
  socialButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },
});
