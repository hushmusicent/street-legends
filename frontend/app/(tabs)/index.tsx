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
  spawnMonsters,
  generateMissions,
  getNearbyPlayers,
  startBattle,
  spawnShops,
  getProfilePic,
  getNearbyTerritories,
  captureTerritory,
  collectTerritoryIncome,
  spawnRestaurants,
  eatAtRestaurant,
  spawnNightclubs,
  visitNightclub,
  spawnBanks,
  robBank,
} from '../../services/api';
import { Monster, Mission, NearbyPlayer } from '../../types/game';
import { GameMap } from '../../components/GameMap';
import { showGameToast } from '../../components/GameToast';
import { SFX } from '../../hooks/useSoundEffects';

// Calculate distance between two points in meters
const getDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
};

export default function MapScreen() {
  const {
    player,
    playerId,
    setPlayer,
    currentPosition,
    setCurrentPosition,
    nearbyMonsters,
    setNearbyMonsters,
    nearbyMissions,
    setNearbyMissions,
    nearbyPlayers,
    setNearbyPlayers,
    setCurrentBattle,
  } = useGameStore();

  const [loading, setLoading] = useState(true);
  const [selectedMarker, setSelectedMarker] = useState<{
    type: 'monster' | 'mission' | 'bounty' | 'player' | 'shop' | 'restaurant' | 'nightclub';
    data: any;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [isTracking, setIsTracking] = useState(false);
  const [heading, setHeading] = useState<number>(0);
  const [nearbyShops, setNearbyShops] = useState<any[]>([]);
  const [nearbyRestaurants, setNearbyRestaurants] = useState<any[]>([]);
  const [nearbyNightclubs, setNearbyNightclubs] = useState<any[]>([]);
  const [nearbyBanks, setNearbyBanks] = useState<any[]>([]);
  const [territories, setTerritories] = useState<any[]>([]);
  const [selectedTerritory, setSelectedTerritory] = useState<any | null>(null);
  const [selectedBank, setSelectedBank] = useState<any | null>(null);
  const [territoryBattleLog, setTerritoryBattleLog] = useState<string[]>([]);
  const [territoryFighting, setTerritoryFighting] = useState(false);
  const [robbingBank, setRobbingBank] = useState(false);
  const globalProfilePic = useGameStore(s => s.profilePic);
  const setGlobalProfilePic = useGameStore(s => s.setProfilePic);
  
  const locationSubscription = useRef<Location.LocationSubscription | null>(null);
  const headingSubscription = useRef<Location.LocationSubscription | null>(null);
  const lastEntityLoadPos = useRef<{ lat: number; lon: number } | null>(null);
  const lastServerUpdateTime = useRef<number>(0);
  const entitiesCache = useRef<{ time: number; data: any } | null>(null);

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

  // Only load entities when position changes significantly (50m+)
  useEffect(() => {
    if (currentPosition && player) {
      const shouldLoad = !lastEntityLoadPos.current || 
        getDistance(
          lastEntityLoadPos.current.lat,
          lastEntityLoadPos.current.lon,
          currentPosition.latitude,
          currentPosition.longitude
        ) > 50;
      
      if (shouldLoad) {
        loadNearbyEntities();
        lastEntityLoadPos.current = {
          lat: currentPosition.latitude,
          lon: currentPosition.longitude
        };
      }
    }
  }, [currentPosition?.latitude, currentPosition?.longitude]);

  // Auto-refresh: spawn new enemies every 5 min + refresh player HP/energy regen
  useEffect(() => {
    if (!playerId || !currentPosition) return;
    const interval = setInterval(() => {
      // Refresh player data (triggers health/energy regen on backend)
      getPlayer(playerId).then(setPlayer).catch(console.error);
      // Refresh monsters (triggers new enemy spawn if 5 min passed)
      loadNearbyEntities();
    }, 300000); // 5 minutes = 300,000ms
    return () => clearInterval(interval);
  }, [playerId, currentPosition?.latitude, currentPosition?.longitude]);

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

  const loadNearbyEntities = useCallback(async () => {
    if (!currentPosition || !player || !playerId) return;

    // Check cache (30 second TTL)
    const now = Date.now();
    if (entitiesCache.current && now - entitiesCache.current.time < 30000) {
      return;
    }

    try {
      // Ensure server knows our position before fetching entities
      await updatePlayerPosition(playerId, currentPosition).catch(() => {});

      // Use allSettled so one failure doesn't block others
      const results = await Promise.allSettled([
        spawnMonsters(currentPosition.latitude, currentPosition.longitude, player.level),
        generateMissions(currentPosition.latitude, currentPosition.longitude, player.level, playerId),
        getNearbyPlayers(playerId, 500),
        spawnShops(currentPosition.latitude, currentPosition.longitude, player.level),
        getNearbyTerritories(currentPosition.latitude, currentPosition.longitude, player.level),
        spawnRestaurants(currentPosition.latitude, currentPosition.longitude, player.level),
        spawnNightclubs(currentPosition.latitude, currentPosition.longitude, player.level),
        spawnBanks(currentPosition.latitude, currentPosition.longitude, player.level),
      ]);

      const monsters = results[0].status === 'fulfilled' ? results[0].value : [];
      const missions = results[1].status === 'fulfilled' ? results[1].value : [];
      const players = results[2].status === 'fulfilled' ? results[2].value : [];
      const shops = results[3].status === 'fulfilled' ? results[3].value : [];
      const terrs = results[4].status === 'fulfilled' ? results[4].value : [];
      const restaurants = results[5].status === 'fulfilled' ? results[5].value : [];
      const nightclubs = results[6].status === 'fulfilled' ? results[6].value : [];
      const banks = results[7].status === 'fulfilled' ? results[7].value : [];

      setNearbyMonsters(monsters);
      setNearbyMissions(missions);
      setNearbyPlayers(players);
      setNearbyShops(shops);
      setTerritories(terrs);
      setNearbyRestaurants(restaurants);
      setNearbyNightclubs(nightclubs);
      setNearbyBanks(banks);
      
      entitiesCache.current = { time: now, data: { monsters, missions, players, shops, terrs, restaurants, nightclubs, banks } };
    } catch (error) {
      console.error('Failed to load entities:', error);
    }
  }, [currentPosition, player, playerId]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    entitiesCache.current = null; // Clear cache
    lastEntityLoadPos.current = null; // Force reload
    await loadNearbyEntities();
    setRefreshing(false);
  }, [loadNearbyEntities]);

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
      
      // Update territories list with new ownership
      if (result.territory) {
        setTerritories(prev => prev.map((t: any) => t.id === result.territory.id ? result.territory : t));
        setSelectedTerritory(result.territory);
      }
      
      // Refresh player data
      const updatedPlayer = await getPlayer(playerId);
      setPlayer(updatedPlayer);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to challenge territory');
    } finally {
      setTerritoryFighting(false);
    }
  }, [playerId, selectedTerritory]);

  const handleCollectIncome = useCallback(async () => {
    if (!playerId || !selectedTerritory) return;
    try {
      const result = await collectTerritoryIncome(selectedTerritory.id, playerId);
      Alert.alert('Income Collected!', result.message);
      const updatedPlayer = await getPlayer(playerId);
      setPlayer(updatedPlayer);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to collect income');
    }
  }, [playerId, selectedTerritory]);

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

  const handleRobBank = useCallback(async () => {
    if (!playerId || !selectedBank || robbingBank) return;
    setRobbingBank(true);
    try {
      const result = await robBank(selectedBank.id, playerId);
      
      if (result.success) {
        // Success! Play cash sound and show green toast
        SFX.cashRegister();
        showGameToast(result.message, 'success');
      } else {
        // Busted! Play police siren and show red toast
        SFX.policeSiren();
        showGameToast(result.message, 'error');
      }
      
      // Refresh player data
      const updatedPlayer = await getPlayer(playerId);
      setPlayer(updatedPlayer);
      setSelectedBank(null);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Bank robbery failed');
    } finally {
      setRobbingBank(false);
    }
  }, [playerId, selectedBank, robbingBank]);

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
  ], [nearbyMonsters, nearbyMissions, nearbyPlayers, nearbyShops, nearbyRestaurants, nearbyNightclubs, nearbyBanks]);

  const handleMarkerPress = useCallback((marker: any) => {
    if (marker.type === 'monster') {
      const monster = nearbyMonsters.find((m) => m.id === marker.id);
      if (monster) setSelectedMarker({ type: 'monster', data: monster });
    } else if (marker.type === 'mission' || marker.type === 'bounty') {
      const mission = nearbyMissions.find((m) => m.id === marker.id);
      if (mission) setSelectedMarker({ type: 'mission', data: mission });
    } else if (marker.type === 'player') {
      const targetPlayer = nearbyPlayers.find((p) => p.id === marker.id);
      if (targetPlayer) setSelectedMarker({ type: 'player', data: targetPlayer });
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
    }
  }, [nearbyMonsters, nearbyMissions, nearbyPlayers, nearbyShops, nearbyRestaurants, nearbyNightclubs, nearbyBanks]);

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
          <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh} disabled={refreshing}>
            <Ionicons name="refresh" size={22} color="#5F6368" style={refreshing ? styles.rotating : undefined} />
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
              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#4285F4'}]} onPress={() => handlePvPChallenge(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>CHALLENGE</Text>
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
                    // Refresh player data
                    const updatedPlayer = await getPlayer(playerId);
                    setPlayer(updatedPlayer);
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
                    // Refresh player data
                    const updatedPlayer = await getPlayer(playerId);
                    setPlayer(updatedPlayer);
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
                  <ScrollView style={styles.terrBattleLog}>
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
  terrOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  terrModal: { backgroundColor: '#1a1a1a', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '75%' },
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
  terrBattleLog: { maxHeight: 180, backgroundColor: '#111', borderRadius: 10, padding: 10, marginBottom: 12 },
  terrLogLine: { color: '#aaa', fontSize: 11, marginBottom: 3, fontFamily: 'monospace' },
  terrLogVictory: { color: '#4caf50', fontWeight: '700' },
  terrLogDefeat: { color: '#e74c3c', fontWeight: '700' },
  terrLogCrit: { color: '#f39c12' },
  terrActions: { marginTop: 4 },
  terrBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderRadius: 12 },
  terrBtnText: { color: '#fff', fontSize: 15, fontWeight: '800', letterSpacing: 1 },
  
  // Bank Modal  
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
});
