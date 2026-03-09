import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, StyleSheet, Platform, TouchableOpacity } from 'react-native';
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

// Generate the Leaflet map HTML
const generateMapHTML = (center: Position, markers: MapMarker[], heading: number = 0) => {
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
      try {
        if (window.ReactNativeWebView) {
          window.ReactNativeWebView.postMessage(JSON.stringify({type: 'marker', id: '${m.id}', markerType: '${m.type}'}));
        } else if (window.parent) {
          window.parent.postMessage(JSON.stringify({type: 'marker', id: '${m.id}', markerType: '${m.type}'}), '*');
        }
      } catch(e) {}
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
    .player-dot {
      position: relative;
      width: 22px; height: 22px;
    }
    .player-dot-inner {
      width: 22px; height: 22px; background: #4285F4; border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      position: relative; z-index: 2;
    }
    .player-pulse {
      position: absolute; top: 50%; left: 50%;
      width: 40px; height: 40px;
      margin-left: -20px; margin-top: -20px;
      background: rgba(66,133,244,0.2);
      border-radius: 50%;
      animation: pulse 2s ease-out infinite;
      z-index: 1;
    }
    .player-heading {
      position: absolute; top: -12px; left: 50%;
      margin-left: -6px;
      width: 0; height: 0;
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-bottom: 14px solid #4285F4;
      transform-origin: center bottom;
      z-index: 3;
      filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
    }
    @keyframes pulse {
      0% { transform: scale(0.5); opacity: 1; }
      100% { transform: scale(2.5); opacity: 0; }
    }
    .leaflet-control-zoom { border: none !important; box-shadow: 0 2px 6px rgba(0,0,0,0.2) !important; border-radius: 8px !important; }
    .leaflet-control-zoom a { width: 36px !important; height: 36px !important; line-height: 36px !important; font-size: 18px !important; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {
      center: [${center.latitude}, ${center.longitude}],
      zoom: 17,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map);

    // Player marker with heading arrow
    var currentHeading = ${heading};
    var playerIcon = L.divIcon({
      className: 'custom-marker',
      html: '<div class="player-dot"><div class="player-pulse"></div><div class="player-dot-inner"></div><div class="player-heading" id="heading-arrow" style="transform: rotate(' + currentHeading + 'deg)"></div></div>',
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    var playerMarker = L.marker([${center.latitude}, ${center.longitude}], {
      icon: playerIcon,
      zIndexOffset: 1000
    }).addTo(map);

    var isFollowing = true;
    var animFrame = null;
    var currentLat = ${center.latitude};
    var currentLng = ${center.longitude};
    var targetLat = ${center.latitude};
    var targetLng = ${center.longitude};

    // Smooth animation using requestAnimationFrame
    function animatePosition() {
      var dx = targetLat - currentLat;
      var dy = targetLng - currentLng;
      
      if (Math.abs(dx) > 0.0000001 || Math.abs(dy) > 0.0000001) {
        // Lerp toward target (smooth interpolation)
        currentLat += dx * 0.15;
        currentLng += dy * 0.15;
        playerMarker.setLatLng([currentLat, currentLng]);
        
        if (isFollowing) {
          map.setView([currentLat, currentLng], map.getZoom(), { animate: false });
        }
      }
      
      animFrame = requestAnimationFrame(animatePosition);
    }
    animFrame = requestAnimationFrame(animatePosition);

    // Called from React to update position
    window.updatePosition = function(lat, lng) {
      targetLat = lat;
      targetLng = lng;
    };

    // Called to update heading
    window.updateHeading = function(deg) {
      currentHeading = deg;
      var arrow = document.getElementById('heading-arrow');
      if (arrow) {
        arrow.style.transform = 'rotate(' + deg + 'deg)';
      }
    };

    // Center on player
    window.centerOnPlayer = function() {
      isFollowing = true;
      map.setView([currentLat, currentLng], 17, { animate: true });
    };

    // Stop following when user drags map
    map.on('dragstart', function() {
      isFollowing = false;
    });

    ${markersJS}

    // Listen for messages from parent (for web iframe communication)
    window.addEventListener('message', function(event) {
      try {
        var data = JSON.parse(event.data);
        if (data.type === 'updatePosition') {
          window.updatePosition(data.lat, data.lng);
        } else if (data.type === 'updateHeading') {
          window.updateHeading(data.heading);
        } else if (data.type === 'centerOnPlayer') {
          window.centerOnPlayer();
        }
      } catch(e) {}
    });

    // Handle zoom changes
    map.on('zoomend', function() {
      try {
        if (window.ReactNativeWebView) {
          window.ReactNativeWebView.postMessage(JSON.stringify({type: 'zoom', level: map.getZoom()}));
        }
      } catch(e) {}
    });
  </script>
</body>
</html>
  `;
};

// Main Map Component
export const GameMap: React.FC<GameMapProps> = ({ center, markers, heading = 0, onMarkerPress }) => {
  const webViewRef = useRef<WebView>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [isFollowing, setIsFollowing] = useState(true);

  // Update position on native (WebView)
  useEffect(() => {
    if (Platform.OS !== 'web' && mapReady && webViewRef.current) {
      webViewRef.current.injectJavaScript(`
        window.updatePosition(${center.latitude}, ${center.longitude});
        true;
      `);
    }
  }, [center.latitude, center.longitude, mapReady]);

  // Update position on web (iframe postMessage)
  useEffect(() => {
    if (Platform.OS === 'web' && iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'updatePosition', lat: center.latitude, lng: center.longitude }),
        '*'
      );
    }
  }, [center.latitude, center.longitude]);

  // Update heading
  useEffect(() => {
    if (Platform.OS !== 'web' && mapReady && webViewRef.current) {
      webViewRef.current.injectJavaScript(`
        window.updateHeading(${heading});
        true;
      `);
    } else if (Platform.OS === 'web' && iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'updateHeading', heading }),
        '*'
      );
    }
  }, [heading, mapReady]);

  // Listen for messages from iframe on web
  useEffect(() => {
    if (Platform.OS === 'web') {
      const handleMessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'marker' && onMarkerPress) {
            const marker = markers.find(m => m.id === data.id);
            if (marker) onMarkerPress(marker);
          }
        } catch {}
      };
      window.addEventListener('message', handleMessage);
      return () => window.removeEventListener('message', handleMessage);
    }
  }, [markers, onMarkerPress]);

  const handleNativeMessage = useCallback((event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'marker' && onMarkerPress) {
        const marker = markers.find(m => m.id === data.id);
        if (marker) onMarkerPress(marker);
      }
    } catch {}
  }, [markers, onMarkerPress]);

  const handleCenterPress = useCallback(() => {
    setIsFollowing(true);
    if (Platform.OS !== 'web' && webViewRef.current) {
      webViewRef.current.injectJavaScript(`window.centerOnPlayer(); true;`);
    } else if (Platform.OS === 'web' && iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'centerOnPlayer' }),
        '*'
      );
    }
  }, []);

  const mapHTML = generateMapHTML(center, markers, heading);

  // Web platform: iframe with ref for postMessage communication
  if (Platform.OS === 'web') {
    return (
      <View style={styles.container}>
        <iframe
          ref={(el: any) => { iframeRef.current = el; }}
          srcDoc={mapHTML}
          style={{ flex: 1, border: 'none', width: '100%', height: '100%' } as any}
          title="Game Map"
        />
        {/* Center on Me button */}
        <TouchableOpacity style={styles.centerButton} onPress={handleCenterPress} activeOpacity={0.7}>
          <Ionicons name="locate" size={22} color="#4285F4" />
        </TouchableOpacity>
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

  // Native: WebView with injectJavaScript
  return (
    <View style={styles.container}>
      <WebView
        ref={webViewRef}
        source={{ html: mapHTML }}
        style={styles.map}
        onLoad={() => setMapReady(true)}
        onMessage={handleNativeMessage}
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
      {/* Center on Me button */}
      <TouchableOpacity style={styles.centerButton} onPress={handleCenterPress} activeOpacity={0.7}>
        <Ionicons name="locate" size={22} color="#4285F4" />
      </TouchableOpacity>
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
  centerButton: {
    position: 'absolute',
    bottom: 55,
    right: 12,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
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
