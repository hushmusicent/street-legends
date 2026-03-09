import React, { useEffect, useRef, useState, memo } from 'react';
import { View, Text, StyleSheet, Platform, Animated, TouchableOpacity } from 'react-native';
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
}

interface GameMapProps {
  center: Position;
  markers: MapMarker[];
  heading?: number;
  onMarkerPress?: (marker: MapMarker) => void;
}

// Memoized marker component
const MarkerIcon = memo(({ type, level }: { type: string; level?: number }) => {
  const getColor = () => {
    switch (type) {
      case 'monster': return '#EA4335';
      case 'mission': return '#FBBC04';
      case 'player': return '#4285F4';
      default: return '#888';
    }
  };
  
  const getIcon = (): keyof typeof Ionicons.glyphMap => {
    switch (type) {
      case 'monster': return 'skull';
      case 'mission': return 'briefcase';
      case 'player': return 'person';
      default: return 'location';
    }
  };

  return (
    <View style={[styles.marker, { backgroundColor: getColor() }]}>
      <Ionicons name={getIcon()} size={14} color="#fff" />
      {level && <Text style={styles.markerLevel}>{level}</Text>}
    </View>
  );
});

// Fast, lightweight map component
export const GameMap: React.FC<GameMapProps> = ({ center, markers, heading = 0, onMarkerPress }) => {
  const [zoom, setZoom] = useState(1);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.2, duration: 1200, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1200, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const getMapPosition = (markerPos: Position) => {
    const scale = 2500 / zoom;
    const dx = (markerPos.longitude - center.longitude) * 111000 * Math.cos(center.latitude * Math.PI / 180);
    const dy = (markerPos.latitude - center.latitude) * 111000;
    return {
      left: `${Math.min(92, Math.max(8, 50 + (dx / scale) * 40))}%`,
      top: `${Math.min(92, Math.max(8, 50 - (dy / scale) * 40))}%`,
    };
  };

  return (
    <View style={styles.container}>
      <View style={styles.mapArea}>
        {/* Grid background */}
        {[...Array(5)].map((_, i) => (
          <View key={`h${i}`} style={[styles.gridLine, { top: `${(i + 1) * 20}%`, left: 0, right: 0, height: 1 }]} />
        ))}
        {[...Array(5)].map((_, i) => (
          <View key={`v${i}`} style={[styles.gridLine, { left: `${(i + 1) * 20}%`, top: 0, bottom: 0, width: 1 }]} />
        ))}

        {/* Player location dot */}
        <View style={styles.playerContainer}>
          <Animated.View style={[styles.playerPulse, { transform: [{ scale: pulseAnim }] }]} />
          <View style={styles.playerDot}>
            <View style={styles.playerDotInner} />
          </View>
        </View>

        {/* Entity markers */}
        {markers.map((marker) => {
          const pos = getMapPosition(marker.coordinate);
          return (
            <TouchableOpacity
              key={marker.id}
              style={[styles.markerContainer, { left: pos.left, top: pos.top }]}
              onPress={() => onMarkerPress?.(marker)}
              activeOpacity={0.8}
            >
              <MarkerIcon type={marker.type} level={marker.level} />
            </TouchableOpacity>
          );
        })}

        {/* Zoom controls */}
        <View style={styles.zoomControls}>
          <TouchableOpacity style={styles.zoomBtn} onPress={() => setZoom(z => Math.min(3, z + 0.3))}>
            <Ionicons name="add" size={20} color="#5F6368" />
          </TouchableOpacity>
          <View style={styles.zoomDivider} />
          <TouchableOpacity style={styles.zoomBtn} onPress={() => setZoom(z => Math.max(0.5, z - 0.3))}>
            <Ionicons name="remove" size={20} color="#5F6368" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Bottom info bar */}
      <View style={styles.infoBar}>
        <Ionicons name="location" size={12} color="#4285F4" />
        <Text style={styles.coordsText}>
          {center.latitude.toFixed(4)}, {center.longitude.toFixed(4)}
        </Text>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>
            {markers.filter(m => m.type === 'monster').length} enemies • {markers.filter(m => m.type === 'mission').length} missions
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F3' },
  mapArea: { flex: 1, position: 'relative' },
  gridLine: { position: 'absolute', backgroundColor: '#E0E0E0' },
  playerContainer: { 
    position: 'absolute', 
    left: '50%', 
    top: '50%', 
    marginLeft: -20, 
    marginTop: -20, 
    width: 40, 
    height: 40, 
    alignItems: 'center', 
    justifyContent: 'center' 
  },
  playerPulse: { 
    position: 'absolute', 
    width: 36, 
    height: 36, 
    borderRadius: 18, 
    backgroundColor: 'rgba(66,133,244,0.2)' 
  },
  playerDot: { 
    width: 20, 
    height: 20, 
    borderRadius: 10, 
    backgroundColor: '#fff', 
    justifyContent: 'center', 
    alignItems: 'center', 
    borderWidth: 2, 
    borderColor: 'rgba(66,133,244,0.3)' 
  },
  playerDotInner: { 
    width: 12, 
    height: 12, 
    borderRadius: 6, 
    backgroundColor: '#4285F4' 
  },
  markerContainer: { 
    position: 'absolute', 
    transform: [{ translateX: -14 }, { translateY: -14 }] 
  },
  marker: { 
    width: 28, 
    height: 28, 
    borderRadius: 14, 
    justifyContent: 'center', 
    alignItems: 'center', 
    borderWidth: 2, 
    borderColor: '#fff' 
  },
  markerLevel: { 
    position: 'absolute', 
    bottom: -5, 
    backgroundColor: '#fff', 
    paddingHorizontal: 3, 
    borderRadius: 3, 
    color: '#202124', 
    fontSize: 8, 
    fontWeight: 'bold' 
  },
  zoomControls: { 
    position: 'absolute', 
    right: 12, 
    bottom: 12, 
    backgroundColor: '#fff', 
    borderRadius: 8, 
    overflow: 'hidden' 
  },
  zoomBtn: { 
    width: 36, 
    height: 36, 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  zoomDivider: { 
    height: 1, 
    backgroundColor: '#E0E0E0' 
  },
  infoBar: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    padding: 10, 
    backgroundColor: '#fff', 
    borderTopWidth: 1, 
    borderTopColor: '#E0E0E0' 
  },
  coordsText: { 
    color: '#5F6368', 
    fontSize: 11, 
    marginLeft: 6 
  },
  countBadge: { 
    marginLeft: 'auto' 
  },
  countText: { 
    color: '#5F6368', 
    fontSize: 11 
  },
});
