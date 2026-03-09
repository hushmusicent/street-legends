import React, { useEffect, useRef, useState, memo } from 'react';
import { View, Text, StyleSheet, Platform, Animated, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { WebView } from 'react-native-webview';

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

// Generate HTML for the map with Leaflet.js and OpenStreetMap
const generateMapHTML = (center: Position, markers: MapMarker[], zoom: number = 17) => {
  const markerColors: Record<string, string> = {
    monster: '#EA4335',
    mission: '#FBBC04', 
    player: '#4285F4',
  };

  const markerIcons: Record<string, string> = {
    monster: '💀',
    mission: '📋',
    player: '👤',
  };

  const markersJS = markers.map(m => `
    L.marker([${m.coordinate.latitude}, ${m.coordinate.longitude}], {
      icon: L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:${markerColors[m.type]};width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:14px;">${markerIcons[m.type]}${m.level ? `<span style="position:absolute;bottom:-8px;background:white;padding:0 4px;border-radius:4px;font-size:10px;font-weight:bold;">${m.level}</span>` : ''}</div>',
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      })
    }).addTo(map).on('click', function() {
      window.ReactNativeWebView.postMessage(JSON.stringify({type: 'marker', id: '${m.id}', markerType: '${m.type}'}));
    });
  `).join('\n');

  return `
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body, #map { width: 100%; height: 100%; }
    .custom-marker { background: transparent !important; border: none !important; }
    .player-marker {
      width: 24px; height: 24px; background: #4285F4; border-radius: 50%;
      border: 3px solid white; box-shadow: 0 0 0 8px rgba(66,133,244,0.25), 0 2px 6px rgba(0,0,0,0.3);
      animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 0 8px rgba(66,133,244,0.25), 0 2px 6px rgba(0,0,0,0.3); }
      50% { box-shadow: 0 0 0 16px rgba(66,133,244,0.15), 0 2px 6px rgba(0,0,0,0.3); }
    }
    .leaflet-control-zoom { border: none !important; box-shadow: 0 2px 6px rgba(0,0,0,0.2) !important; }
    .leaflet-control-zoom a { width: 36px !important; height: 36px !important; line-height: 36px !important; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {
      center: [${center.latitude}, ${center.longitude}],
      zoom: ${zoom},
      zoomControl: true,
      attributionControl: false
    });

    // OpenStreetMap tiles (free, shows streets & buildings)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map);

    // Player marker (your location)
    var playerMarker = L.marker([${center.latitude}, ${center.longitude}], {
      icon: L.divIcon({
        className: 'custom-marker',
        html: '<div class="player-marker"></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      }),
      zIndexOffset: 1000
    }).addTo(map);

    // Add other markers
    ${markersJS}

    // Update player position
    window.updatePosition = function(lat, lng) {
      playerMarker.setLatLng([lat, lng]);
      map.panTo([lat, lng], { animate: true, duration: 0.5 });
    };

    // Handle zoom changes
    map.on('zoomend', function() {
      window.ReactNativeWebView.postMessage(JSON.stringify({type: 'zoom', level: map.getZoom()}));
    });
  </script>
</body>
</html>
  `;
};

// Main Map Component with real streets
export const GameMap: React.FC<GameMapProps> = ({ center, markers, heading = 0, onMarkerPress }) => {
  const webViewRef = useRef<WebView>(null);
  const [mapReady, setMapReady] = useState(false);
  const lastCenter = useRef(center);

  // Update player position when center changes
  useEffect(() => {
    if (mapReady && webViewRef.current) {
      const distance = Math.sqrt(
        Math.pow(center.latitude - lastCenter.current.latitude, 2) +
        Math.pow(center.longitude - lastCenter.current.longitude, 2)
      );
      
      // Only update if moved significantly
      if (distance > 0.00001) {
        webViewRef.current.injectJavaScript(`
          window.updatePosition(${center.latitude}, ${center.longitude});
          true;
        `);
        lastCenter.current = center;
      }
    }
  }, [center.latitude, center.longitude, mapReady]);

  const handleMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'marker' && onMarkerPress) {
        const marker = markers.find(m => m.id === data.id);
        if (marker) {
          onMarkerPress(marker);
        }
      }
    } catch (e) {
      console.log('Map message:', event.nativeEvent.data);
    }
  };

  const mapHTML = generateMapHTML(center, markers);

  // For web platform, use iframe
  if (Platform.OS === 'web') {
    return (
      <View style={styles.container}>
        <iframe
          srcDoc={mapHTML}
          style={{ flex: 1, border: 'none', width: '100%', height: '100%' }}
          title="Game Map"
        />
        <View style={styles.infoBar}>
          <Ionicons name="location" size={14} color="#4285F4" />
          <Text style={styles.coordsText}>
            {center.latitude.toFixed(5)}, {center.longitude.toFixed(5)}
          </Text>
          <Text style={styles.countText}>
            {markers.filter(m => m.type === 'monster').length} enemies • {markers.filter(m => m.type === 'mission').length} missions
          </Text>
        </View>
      </View>
    );
  }

  // For native platforms, use WebView
  return (
    <View style={styles.container}>
      <WebView
        ref={webViewRef}
        source={{ html: mapHTML }}
        style={styles.map}
        onLoad={() => setMapReady(true)}
        onMessage={handleMessage}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
        scalesPageToFit={true}
        showsHorizontalScrollIndicator={false}
        showsVerticalScrollIndicator={false}
        bounces={false}
        scrollEnabled={false}
        renderLoading={() => (
          <View style={styles.loading}>
            <Text style={styles.loadingText}>Loading map...</Text>
          </View>
        )}
      />
      <View style={styles.infoBar}>
        <Ionicons name="location" size={14} color="#4285F4" />
        <Text style={styles.coordsText}>
          {center.latitude.toFixed(5)}, {center.longitude.toFixed(5)}
        </Text>
        <Text style={styles.countText}>
          {markers.filter(m => m.type === 'monster').length} enemies • {markers.filter(m => m.type === 'mission').length} missions
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#E5E3DF',
  },
  map: {
    flex: 1,
  },
  loading: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#E5E3DF',
  },
  loadingText: {
    color: '#5F6368',
    fontSize: 14,
  },
  infoBar: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  coordsText: {
    color: '#5F6368',
    fontSize: 11,
    marginLeft: 6,
    flex: 1,
  },
  countText: {
    color: '#5F6368',
    fontSize: 11,
  },
});
