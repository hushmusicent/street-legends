import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Platform, Animated, Easing } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Position {
  latitude: number;
  longitude: number;
}

interface MapMarker {
  id: string;
  coordinate: Position;
  type: 'monster' | 'mission' | 'player' | 'self';
  level?: number;
  name?: string;
  onPress?: () => void;
}

interface GameMapProps {
  center: Position;
  markers: MapMarker[];
  heading?: number;
  onMarkerPress?: (marker: MapMarker) => void;
}

// Animated player marker component
const AnimatedPlayerMarker: React.FC<{ heading?: number }> = ({ heading = 0 }) => {
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Pulse animation for the player marker
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 1000,
          easing: Easing.ease,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          easing: Easing.ease,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  useEffect(() => {
    // Smooth rotation based on heading
    Animated.timing(rotateAnim, {
      toValue: heading,
      duration: 300,
      easing: Easing.ease,
      useNativeDriver: true,
    }).start();
  }, [heading]);

  const rotateStyle = {
    transform: [
      { scale: pulseAnim },
      { rotate: rotateAnim.interpolate({
        inputRange: [0, 360],
        outputRange: ['0deg', '360deg'],
      })},
    ],
  };

  return (
    <View style={markerStyles.playerContainer}>
      <Animated.View style={[markerStyles.playerOuter, rotateStyle]}>
        <View style={markerStyles.playerInner}>
          <Ionicons name="navigate" size={20} color="#fff" />
        </View>
      </Animated.View>
      <View style={markerStyles.playerPulse} />
    </View>
  );
};

const markerStyles = StyleSheet.create({
  playerContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerOuter: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#e74c3c',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#fff',
    shadowColor: '#e74c3c',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 10,
    elevation: 10,
  },
  playerInner: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerPulse: {
    position: 'absolute',
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(231, 76, 60, 0.2)',
    zIndex: -1,
  },
});

// For native: Use react-native-maps with Google Maps
const NativeMap: React.FC<GameMapProps> = ({ center, markers, heading, onMarkerPress }) => {
  // Dynamic import to avoid web issues
  const MapViewModule = require('react-native-maps');
  const MapView = MapViewModule.default;
  const { Marker, Circle, PROVIDER_GOOGLE } = MapViewModule;
  
  const mapRef = useRef<any>(null);
  const animatedPosition = useRef(new Animated.ValueXY({ x: center.latitude, y: center.longitude })).current;

  // Animate to new position smoothly
  useEffect(() => {
    Animated.timing(animatedPosition, {
      toValue: { x: center.latitude, y: center.longitude },
      duration: 500,
      easing: Easing.out(Easing.quad),
      useNativeDriver: false,
    }).start();

    // Also animate the map camera
    if (mapRef.current) {
      mapRef.current.animateCamera({
        center: center,
        zoom: 17,
        heading: heading || 0,
      }, { duration: 500 });
    }
  }, [center.latitude, center.longitude, heading]);

  const DARK_MAP_STYLE = [
    { elementType: 'geometry', stylers: [{ color: '#1d1d1d' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#8a8a8a' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#1d1d1d' }] },
    { featureType: 'administrative', elementType: 'geometry', stylers: [{ color: '#333333' }] },
    { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#666666' }] },
    { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#1a2e1a' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2a2a2a' }] },
    { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#666666' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#3c3c3c' }] },
    { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#e74c3c' }] },
    { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#2d2d2d' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e1626' }] },
  ];

  const MONSTER_COLORS: Record<string, string> = {
    humanoid: '#e74c3c',
    boss: '#9b59b6',
    tech: '#3498db',
    stealth: '#1abc9c',
  };

  return (
    <MapView
      ref={mapRef}
      style={styles.map}
      provider={PROVIDER_GOOGLE}
      customMapStyle={DARK_MAP_STYLE}
      initialRegion={{
        ...center,
        latitudeDelta: 0.005,
        longitudeDelta: 0.005,
      }}
      showsUserLocation={false}
      showsMyLocationButton={false}
      showsCompass={false}
      rotateEnabled={true}
      pitchEnabled={true}
    >
      {/* Player accuracy circle */}
      <Circle
        center={center}
        radius={50}
        strokeColor="rgba(231, 76, 60, 0.5)"
        fillColor="rgba(231, 76, 60, 0.1)"
      />

      {/* Player marker */}
      <Marker coordinate={center} anchor={{ x: 0.5, y: 0.5 }}>
        <AnimatedPlayerMarker heading={heading} />
      </Marker>

      {/* Monster markers */}
      {markers.filter(m => m.type === 'monster').map((marker) => (
        <Marker
          key={marker.id}
          coordinate={marker.coordinate}
          onPress={() => onMarkerPress?.(marker)}
        >
          <View style={[styles.monsterMarker, { backgroundColor: '#e74c3c' }]}>
            <Ionicons name="skull" size={18} color="#fff" />
            {marker.level && <Text style={styles.markerLevel}>{marker.level}</Text>}
          </View>
        </Marker>
      ))}

      {/* Mission markers */}
      {markers.filter(m => m.type === 'mission').map((marker) => (
        <Marker
          key={marker.id}
          coordinate={marker.coordinate}
          onPress={() => onMarkerPress?.(marker)}
        >
          <View style={styles.missionMarker}>
            <Ionicons name="briefcase" size={18} color="#fff" />
          </View>
        </Marker>
      ))}

      {/* Other player markers */}
      {markers.filter(m => m.type === 'player').map((marker) => (
        <Marker
          key={marker.id}
          coordinate={marker.coordinate}
          onPress={() => onMarkerPress?.(marker)}
        >
          <View style={styles.otherPlayerMarker}>
            <Ionicons name="person" size={16} color="#fff" />
          </View>
        </Marker>
      ))}
    </MapView>
  );
};

// Web fallback - radar style map
const WebMapFallback: React.FC<GameMapProps> = ({ center, markers, heading = 0, onMarkerPress }) => {
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(rotateAnim, {
      toValue: heading,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [heading]);

  const getMarkerColor = (type: string) => {
    switch (type) {
      case 'monster': return '#e74c3c';
      case 'mission': return '#f39c12';
      case 'player': return '#3498db';
      default: return '#888';
    }
  };

  const getMarkerIcon = (type: string): keyof typeof Ionicons.glyphMap => {
    switch (type) {
      case 'monster': return 'skull';
      case 'mission': return 'briefcase';
      case 'player': return 'person';
      default: return 'location';
    }
  };

  // Calculate relative position on radar
  const getRadarPosition = (markerPos: Position) => {
    const scale = 5000; // meters to percentage scale
    const dx = (markerPos.longitude - center.longitude) * 111000 * Math.cos(center.latitude * Math.PI / 180);
    const dy = (markerPos.latitude - center.latitude) * 111000;
    
    const x = 50 + (dx / scale) * 40;
    const y = 50 - (dy / scale) * 40;
    
    return {
      left: `${Math.min(90, Math.max(10, x))}%`,
      top: `${Math.min(90, Math.max(10, y))}%`,
    };
  };

  return (
    <View style={webStyles.container}>
      <View style={webStyles.mapArea}>
        {/* Radar rings */}
        <View style={[webStyles.radarRing, { width: 100, height: 100 }]} />
        <View style={[webStyles.radarRing, { width: 200, height: 200 }]} />
        <View style={[webStyles.radarRing, { width: 300, height: 300 }]} />

        {/* Radar sweep line */}
        <Animated.View 
          style={[
            webStyles.radarSweep,
            {
              transform: [{
                rotate: rotateAnim.interpolate({
                  inputRange: [0, 360],
                  outputRange: ['0deg', '360deg'],
                })
              }]
            }
          ]} 
        />

        {/* Grid lines */}
        <View style={[webStyles.gridLine, { left: '50%', top: 0, bottom: 0, width: 1 }]} />
        <View style={[webStyles.gridLine, { top: '50%', left: 0, right: 0, height: 1 }]} />

        {/* Player marker in center */}
        <View style={webStyles.selfMarker}>
          <Animated.View style={{
            transform: [{
              rotate: rotateAnim.interpolate({
                inputRange: [0, 360],
                outputRange: ['0deg', '360deg'],
              })
            }]
          }}>
            <Ionicons name="navigate" size={24} color="#fff" />
          </Animated.View>
        </View>

        {/* Other markers */}
        {markers.map((marker) => {
          const pos = getRadarPosition(marker.coordinate);
          return (
            <View
              key={marker.id}
              style={[
                webStyles.marker,
                {
                  backgroundColor: getMarkerColor(marker.type),
                  left: pos.left,
                  top: pos.top,
                },
              ]}
              onTouchEnd={() => onMarkerPress?.(marker)}
            >
              <Ionicons name={getMarkerIcon(marker.type)} size={14} color="#fff" />
            </View>
          );
        })}
      </View>

      <View style={webStyles.coordsBar}>
        <Ionicons name="compass" size={14} color="#e74c3c" />
        <Text style={webStyles.coordsText}>
          {center.latitude.toFixed(5)}, {center.longitude.toFixed(5)}
        </Text>
        <Text style={webStyles.headingText}>
          {heading.toFixed(0)}°
        </Text>
      </View>

      <View style={webStyles.legendBar}>
        <View style={webStyles.legendItem}>
          <View style={[webStyles.legendDot, { backgroundColor: '#e74c3c' }]} />
          <Text style={webStyles.legendText}>
            Enemies ({markers.filter(m => m.type === 'monster').length})
          </Text>
        </View>
        <View style={webStyles.legendItem}>
          <View style={[webStyles.legendDot, { backgroundColor: '#f39c12' }]} />
          <Text style={webStyles.legendText}>
            Missions ({markers.filter(m => m.type === 'mission').length})
          </Text>
        </View>
        <View style={webStyles.legendItem}>
          <View style={[webStyles.legendDot, { backgroundColor: '#3498db' }]} />
          <Text style={webStyles.legendText}>
            Players ({markers.filter(m => m.type === 'player').length})
          </Text>
        </View>
      </View>
    </View>
  );
};

const webStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1117',
  },
  mapArea: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  radarRing: {
    position: 'absolute',
    borderRadius: 1000,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.2)',
  },
  radarSweep: {
    position: 'absolute',
    width: 2,
    height: '50%',
    bottom: '50%',
    backgroundColor: 'rgba(231, 76, 60, 0.5)',
    transformOrigin: 'bottom center',
  },
  gridLine: {
    position: 'absolute',
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
  },
  selfMarker: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#e74c3c',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#fff',
    shadowColor: '#e74c3c',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 15,
    elevation: 10,
  },
  marker: {
    position: 'absolute',
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
    transform: [{ translateX: -16 }, { translateY: -16 }],
  },
  coordsBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
  },
  coordsText: {
    color: '#888',
    fontSize: 12,
    marginLeft: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  headingText: {
    color: '#e74c3c',
    fontSize: 12,
    marginLeft: 12,
    fontWeight: 'bold',
  },
  legendBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    borderTopWidth: 1,
    borderTopColor: '#222',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 6,
  },
  legendText: {
    color: '#888',
    fontSize: 11,
  },
});

const styles = StyleSheet.create({
  map: {
    flex: 1,
  },
  monsterMarker: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
  },
  markerLevel: {
    position: 'absolute',
    bottom: -8,
    backgroundColor: '#000',
    paddingHorizontal: 4,
    borderRadius: 4,
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  missionMarker: {
    backgroundColor: '#f39c12',
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
  },
  otherPlayerMarker: {
    backgroundColor: '#3498db',
    width: 30,
    height: 30,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
  },
});

// Main export - choose based on platform
export const GameMap: React.FC<GameMapProps> = (props) => {
  if (Platform.OS === 'web') {
    return <WebMapFallback {...props} />;
  }
  
  // Use try-catch for native to handle cases where maps might not be available
  try {
    return <NativeMap {...props} />;
  } catch (error) {
    console.warn('Native maps not available, using fallback');
    return <WebMapFallback {...props} />;
  }
};
