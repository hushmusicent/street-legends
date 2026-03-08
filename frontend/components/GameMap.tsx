import React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface MapMarker {
  id: string;
  coordinate: {
    latitude: number;
    longitude: number;
  };
  type: 'monster' | 'mission' | 'player' | 'self';
  level?: number;
  name?: string;
  onPress?: () => void;
}

interface GameMapProps {
  center: {
    latitude: number;
    longitude: number;
  };
  markers: MapMarker[];
  onMarkerPress?: (marker: MapMarker) => void;
}

// Web fallback component
const WebMapFallback: React.FC<GameMapProps> = ({ center, markers, onMarkerPress }) => {
  const getMarkerColor = (type: string) => {
    switch (type) {
      case 'monster':
        return '#e74c3c';
      case 'mission':
        return '#f39c12';
      case 'player':
        return '#3498db';
      case 'self':
        return '#27ae60';
      default:
        return '#888';
    }
  };

  const getMarkerIcon = (type: string): keyof typeof Ionicons.glyphMap => {
    switch (type) {
      case 'monster':
        return 'skull';
      case 'mission':
        return 'briefcase';
      case 'player':
        return 'person';
      case 'self':
        return 'navigate';
      default:
        return 'location';
    }
  };

  return (
    <View style={webStyles.container}>
      <View style={webStyles.mapArea}>
        <View style={webStyles.gridOverlay}>
          {/* Grid lines */}
          {[...Array(10)].map((_, i) => (
            <View key={`h-${i}`} style={[webStyles.gridLine, webStyles.horizontalLine, { top: `${i * 10}%` }]} />
          ))}
          {[...Array(10)].map((_, i) => (
            <View key={`v-${i}`} style={[webStyles.gridLine, webStyles.verticalLine, { left: `${i * 10}%` }]} />
          ))}
        </View>

        {/* Self marker in center */}
        <View style={[webStyles.marker, webStyles.selfMarker]}>
          <Ionicons name="navigate" size={24} color="#fff" />
        </View>

        {/* Other markers positioned around */}
        {markers.filter(m => m.type !== 'self').map((marker, index) => {
          const angle = (index / markers.length) * 2 * Math.PI;
          const radius = 30 + (index % 3) * 15;
          const x = 50 + Math.cos(angle) * radius;
          const y = 50 + Math.sin(angle) * radius;
          
          return (
            <View
              key={marker.id}
              style={[
                webStyles.marker,
                {
                  backgroundColor: getMarkerColor(marker.type),
                  left: `${Math.min(90, Math.max(10, x))}%`,
                  top: `${Math.min(90, Math.max(10, y))}%`,
                },
              ]}
              onTouchEnd={() => onMarkerPress?.(marker)}
            >
              <Ionicons name={getMarkerIcon(marker.type)} size={16} color="#fff" />
              {marker.level && (
                <Text style={webStyles.levelBadge}>{marker.level}</Text>
              )}
            </View>
          );
        })}

        {/* Radar effect */}
        <View style={webStyles.radarRing} />
        <View style={[webStyles.radarRing, { width: 200, height: 200 }]} />
      </View>

      <View style={webStyles.coordsBar}>
        <Ionicons name="location" size={14} color="#e74c3c" />
        <Text style={webStyles.coordsText}>
          {center.latitude.toFixed(4)}, {center.longitude.toFixed(4)}
        </Text>
      </View>

      <View style={webStyles.legendBar}>
        <View style={webStyles.legendItem}>
          <View style={[webStyles.legendDot, { backgroundColor: '#e74c3c' }]} />
          <Text style={webStyles.legendText}>Enemies ({markers.filter(m => m.type === 'monster').length})</Text>
        </View>
        <View style={webStyles.legendItem}>
          <View style={[webStyles.legendDot, { backgroundColor: '#f39c12' }]} />
          <Text style={webStyles.legendText}>Missions ({markers.filter(m => m.type === 'mission').length})</Text>
        </View>
        <View style={webStyles.legendItem}>
          <View style={[webStyles.legendDot, { backgroundColor: '#3498db' }]} />
          <Text style={webStyles.legendText}>Players ({markers.filter(m => m.type === 'player').length})</Text>
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
  },
  gridOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  gridLine: {
    position: 'absolute',
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
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
  marker: {
    position: 'absolute',
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#fff',
    transform: [{ translateX: -18 }, { translateY: -18 }],
  },
  selfMarker: {
    left: '50%',
    top: '50%',
    backgroundColor: '#27ae60',
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 3,
    transform: [{ translateX: -22 }, { translateY: -22 }],
  },
  levelBadge: {
    position: 'absolute',
    bottom: -8,
    backgroundColor: '#000',
    paddingHorizontal: 4,
    borderRadius: 4,
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  radarRing: {
    position: 'absolute',
    left: '50%',
    top: '50%',
    width: 100,
    height: 100,
    borderRadius: 100,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.3)',
    transform: [{ translateX: -50 }, { translateY: -50 }],
  },
  coordsBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
  },
  coordsText: {
    color: '#888',
    fontSize: 12,
    marginLeft: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  legendBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
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

export const GameMap: React.FC<GameMapProps> = (props) => {
  // For web, use our custom fallback
  if (Platform.OS === 'web') {
    return <WebMapFallback {...props} />;
  }

  // For native, we'd use react-native-maps
  // But since we're primarily targeting web preview, return the fallback
  return <WebMapFallback {...props} />;
};
