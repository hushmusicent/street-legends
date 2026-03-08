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

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.15,
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

  return (
    <View style={markerStyles.playerContainer}>
      <Animated.View style={[markerStyles.playerPulse, { transform: [{ scale: pulseAnim }] }]} />
      <View style={markerStyles.playerOuter}>
        <View style={markerStyles.playerInner} />
      </View>
    </View>
  );
};

const markerStyles = StyleSheet.create({
  playerContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 50,
    height: 50,
  },
  playerPulse: {
    position: 'absolute',
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(66, 133, 244, 0.3)',
  },
  playerOuter: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 5,
  },
  playerInner: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: '#4285F4', // Google blue
  },
});

// For native: Use react-native-maps with Google Maps (standard style)
const NativeMap: React.FC<GameMapProps> = ({ center, markers, heading, onMarkerPress }) => {
  const MapViewModule = require('react-native-maps');
  const MapView = MapViewModule.default;
  const { Marker, Circle, PROVIDER_GOOGLE } = MapViewModule;
  
  const mapRef = useRef<any>(null);
  const [region, setRegion] = useState({
    ...center,
    latitudeDelta: 0.005,
    longitudeDelta: 0.005,
  });

  // Smoothly animate to new position when center changes
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.animateToRegion({
        ...center,
        latitudeDelta: region.latitudeDelta,
        longitudeDelta: region.longitudeDelta,
      }, 500);
    }
  }, [center.latitude, center.longitude]);

  return (
    <MapView
      ref={mapRef}
      style={styles.map}
      provider={PROVIDER_GOOGLE}
      initialRegion={region}
      onRegionChangeComplete={setRegion}
      showsUserLocation={false}
      showsMyLocationButton={false}
      showsCompass={true}
      showsScale={true}
      showsBuildings={true}
      showsTraffic={false}
      showsIndoors={true}
      zoomEnabled={true}
      zoomControlEnabled={true}
      rotateEnabled={true}
      pitchEnabled={true}
      scrollEnabled={true}
      minZoomLevel={10}
      maxZoomLevel={20}
    >
      {/* Player accuracy circle - Google Maps blue style */}
      <Circle
        center={center}
        radius={30}
        strokeColor="rgba(66, 133, 244, 0.5)"
        fillColor="rgba(66, 133, 244, 0.15)"
        strokeWidth={2}
      />

      {/* Player marker - Google Maps style blue dot */}
      <Marker 
        coordinate={center} 
        anchor={{ x: 0.5, y: 0.5 }}
        tracksViewChanges={false}
      >
        <AnimatedPlayerMarker heading={heading} />
      </Marker>

      {/* Monster markers - Red */}
      {markers.filter(m => m.type === 'monster').map((marker) => (
        <Marker
          key={marker.id}
          coordinate={marker.coordinate}
          onPress={() => onMarkerPress?.(marker)}
          tracksViewChanges={false}
        >
          <View style={styles.monsterMarker}>
            <Ionicons name="skull" size={16} color="#fff" />
            {marker.level && <Text style={styles.markerLevel}>{marker.level}</Text>}
          </View>
        </Marker>
      ))}

      {/* Mission markers - Orange */}
      {markers.filter(m => m.type === 'mission').map((marker) => (
        <Marker
          key={marker.id}
          coordinate={marker.coordinate}
          onPress={() => onMarkerPress?.(marker)}
          tracksViewChanges={false}
        >
          <View style={styles.missionMarker}>
            <Ionicons name="briefcase" size={16} color="#fff" />
          </View>
        </Marker>
      ))}

      {/* Other player markers - Blue */}
      {markers.filter(m => m.type === 'player').map((marker) => (
        <Marker
          key={marker.id}
          coordinate={marker.coordinate}
          onPress={() => onMarkerPress?.(marker)}
          tracksViewChanges={false}
        >
          <View style={styles.otherPlayerMarker}>
            <Ionicons name="person" size={14} color="#fff" />
          </View>
        </Marker>
      ))}
    </MapView>
  );
};

// Web fallback - cleaner Google Maps style radar
const WebMapFallback: React.FC<GameMapProps> = ({ center, markers, heading = 0, onMarkerPress }) => {
  const [zoom, setZoom] = useState(1);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.3,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const getMarkerColor = (type: string) => {
    switch (type) {
      case 'monster': return '#EA4335'; // Google red
      case 'mission': return '#FBBC04'; // Google yellow
      case 'player': return '#4285F4'; // Google blue
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

  // Calculate relative position on map
  const getMapPosition = (markerPos: Position) => {
    const scale = 3000 / zoom;
    const dx = (markerPos.longitude - center.longitude) * 111000 * Math.cos(center.latitude * Math.PI / 180);
    const dy = (markerPos.latitude - center.latitude) * 111000;
    
    const x = 50 + (dx / scale) * 40;
    const y = 50 - (dy / scale) * 40;
    
    return {
      left: `${Math.min(95, Math.max(5, x))}%`,
      top: `${Math.min(95, Math.max(5, y))}%`,
    };
  };

  return (
    <View style={webStyles.container}>
      {/* Map area with Google Maps-like appearance */}
      <View style={webStyles.mapArea}>
        {/* Grid pattern to simulate map */}
        <View style={webStyles.gridContainer}>
          {[...Array(8)].map((_, i) => (
            <View key={`h-${i}`} style={[webStyles.gridLine, webStyles.horizontalLine, { top: `${(i + 1) * 12.5}%` }]} />
          ))}
          {[...Array(8)].map((_, i) => (
            <View key={`v-${i}`} style={[webStyles.gridLine, webStyles.verticalLine, { left: `${(i + 1) * 12.5}%` }]} />
          ))}
        </View>

        {/* Player location - Google Maps blue dot style */}
        <View style={webStyles.playerContainer}>
          <Animated.View style={[webStyles.playerPulse, { transform: [{ scale: pulseAnim }] }]} />
          <View style={webStyles.playerDot}>
            <View style={webStyles.playerDotInner} />
          </View>
        </View>

        {/* Other markers */}
        {markers.map((marker) => {
          const pos = getMapPosition(marker.coordinate);
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

        {/* Zoom controls */}
        <View style={webStyles.zoomControls}>
          <View style={webStyles.zoomButton} onTouchEnd={() => setZoom(z => Math.min(3, z + 0.5))}>
            <Ionicons name="add" size={24} color="#666" />
          </View>
          <View style={webStyles.zoomDivider} />
          <View style={webStyles.zoomButton} onTouchEnd={() => setZoom(z => Math.max(0.5, z - 0.5))}>
            <Ionicons name="remove" size={24} color="#666" />
          </View>
        </View>
      </View>

      {/* Bottom info bar */}
      <View style={webStyles.infoBar}>
        <View style={webStyles.coordsContainer}>
          <Ionicons name="location" size={14} color="#4285F4" />
          <Text style={webStyles.coordsText}>
            {center.latitude.toFixed(5)}, {center.longitude.toFixed(5)}
          </Text>
        </View>
        <View style={webStyles.legendContainer}>
          <View style={webStyles.legendItem}>
            <View style={[webStyles.legendDot, { backgroundColor: '#EA4335' }]} />
            <Text style={webStyles.legendText}>{markers.filter(m => m.type === 'monster').length}</Text>
          </View>
          <View style={webStyles.legendItem}>
            <View style={[webStyles.legendDot, { backgroundColor: '#FBBC04' }]} />
            <Text style={webStyles.legendText}>{markers.filter(m => m.type === 'mission').length}</Text>
          </View>
          <View style={webStyles.legendItem}>
            <View style={[webStyles.legendDot, { backgroundColor: '#4285F4' }]} />
            <Text style={webStyles.legendText}>{markers.filter(m => m.type === 'player').length}</Text>
          </View>
        </View>
      </View>
    </View>
  );
};

const webStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#E8E4E0', // Google Maps land color
  },
  mapArea: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: '#F5F5F3',
  },
  gridContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  gridLine: {
    position: 'absolute',
    backgroundColor: '#E0E0E0',
  },
  horizontalLine: {
    left: 0,
    right: 0,
    height: 1,
  },
  verticalLine: {
    top: 0,
    bottom: 0,
    width: 1,
  },
  playerContainer: {
    position: 'absolute',
    left: '50%',
    top: '50%',
    marginLeft: -25,
    marginTop: -25,
    width: 50,
    height: 50,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerPulse: {
    position: 'absolute',
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(66, 133, 244, 0.25)',
  },
  playerDot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 5,
  },
  playerDotInner: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: '#4285F4',
  },
  marker: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 5,
    transform: [{ translateX: -15 }, { translateY: -15 }],
  },
  zoomControls: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 5,
  },
  zoomButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  zoomDivider: {
    height: 1,
    backgroundColor: '#E0E0E0',
  },
  infoBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  coordsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  coordsText: {
    color: '#5F6368',
    fontSize: 12,
    marginLeft: 6,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  legendContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 12,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 4,
  },
  legendText: {
    color: '#5F6368',
    fontSize: 12,
    fontWeight: '600',
  },
});

const styles = StyleSheet.create({
  map: {
    flex: 1,
  },
  monsterMarker: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#EA4335',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 5,
  },
  markerLevel: {
    position: 'absolute',
    bottom: -6,
    backgroundColor: '#fff',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 4,
    color: '#EA4335',
    fontSize: 9,
    fontWeight: 'bold',
  },
  missionMarker: {
    backgroundColor: '#FBBC04',
    width: 34,
    height: 34,
    borderRadius: 17,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 5,
  },
  otherPlayerMarker: {
    backgroundColor: '#4285F4',
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 5,
  },
});

// Main export
export const GameMap: React.FC<GameMapProps> = (props) => {
  if (Platform.OS === 'web') {
    return <WebMapFallback {...props} />;
  }
  
  try {
    return <NativeMap {...props} />;
  } catch (error) {
    console.warn('Native maps not available, using fallback');
    return <WebMapFallback {...props} />;
  }
};
