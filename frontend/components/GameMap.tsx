import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { View, Text, StyleSheet, Platform, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { THUG_MAP_IMAGE, ENEMY_MAP_IMAGES } from '../assets/enemyImages';

// Conditionally import WebView - only available on native
let WebView: any = null;
if (Platform.OS !== 'web') {
  try {
    WebView = require('react-native-webview').default;
  } catch {}
}

interface Position {
  latitude: number;
  longitude: number;
}

interface MapMarker {
  id: string;
  coordinate: Position;
  type: 'monster' | 'mission' | 'bounty' | 'player' | 'self' | 'restaurant' | 'nightclub';
  level?: number;
  name?: string;
  icon?: string;
}

interface MapTerritory {
  id: string;
  name: string;
  location: Position;
  radius: number;
  size?: number;
  bounds?: { south: number; north: number; west: number; east: number };
  color: string;
  owner_id: string | null;
  owner_name: string | null;
  owner_pic?: string | null;
}

interface GameMapProps {
  center: Position;
  markers: MapMarker[];
  heading?: number;
  playerAvatar?: string | null;
  territories?: MapTerritory[];
  onMarkerPress?: (marker: MapMarker) => void;
  onTerritoryPress?: (territory: MapTerritory) => void;
}

const generateBaseMapHTML = (initialLat: number, initialLng: number, enemyImages: Record<string, string>) => {
  // Build a JSON string of enemy name -> image URL for use in the HTML
  const enemyImagesJSON = JSON.stringify(enemyImages).replace(/'/g, "\\'");
  return `
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body, #map { width: 100%; height: 100%; overflow: hidden; }
    .custom-marker { background: transparent !important; border: none !important; }
    .player-dot { position: relative; width: 36px; height: 36px; }
    .player-dot-inner {
      width: 36px; height: 36px; background: #4285F4; border-radius: 50%;
      border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      position: relative; z-index: 2;
      overflow: hidden; display: flex; align-items: center; justify-content: center;
    }
    .player-dot-inner img {
      width: 100%; height: 100%; object-fit: cover; border-radius: 50%;
    }
    .player-pulse {
      position: absolute; top: 50%; left: 50%;
      width: 50px; height: 50px; margin-left: -25px; margin-top: -25px;
      background: rgba(66,133,244,0.2); border-radius: 50%;
      animation: pulse 2s ease-out infinite; z-index: 1;
    }
    .player-heading {
      position: absolute; top: -14px; left: 50%; margin-left: -6px;
      width: 0; height: 0;
      border-left: 6px solid transparent; border-right: 6px solid transparent;
      border-bottom: 14px solid #4285F4;
      transform-origin: center bottom; z-index: 3;
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
      center: [${initialLat}, ${initialLng}],
      zoom: 17,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map);

    // Player marker
    var currentHeading = 0;
    var playerIcon = L.divIcon({
      className: 'custom-marker',
      html: '<div class="player-dot"><div class="player-pulse"></div><div class="player-dot-inner" id="player-avatar"></div><div class="player-heading" id="heading-arrow"></div></div>',
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    });

    var playerMarker = L.marker([${initialLat}, ${initialLng}], {
      icon: playerIcon,
      zIndexOffset: 1000
    }).addTo(map);

    var isFollowing = true;
    var currentLat = ${initialLat};
    var currentLng = ${initialLng};
    var targetLat = ${initialLat};
    var targetLng = ${initialLng};

    // Smooth animation loop
    function animatePosition() {
      var dx = targetLat - currentLat;
      var dy = targetLng - currentLng;
      if (Math.abs(dx) > 0.0000001 || Math.abs(dy) > 0.0000001) {
        currentLat += dx * 0.12;
        currentLng += dy * 0.12;
        playerMarker.setLatLng([currentLat, currentLng]);
        if (isFollowing) {
          map.setView([currentLat, currentLng], map.getZoom(), { animate: false });
        }
      }
      requestAnimationFrame(animatePosition);
    }
    requestAnimationFrame(animatePosition);

    // Existing entity markers stored by ID
    var entityMarkers = {};
    var markerColors = { monster: '#EA4335', mission: '#FBBC04', bounty: '#4CAF50', player: '#4285F4', shop: '#FF6F00', restaurant: '#FF5722', nightclub: '#9b59b6' };
    var markerIcons = { monster: '\\u{1F480}', mission: '\\u{260E}\\u{FE0F}', bounty: '\\u{1F4B2}', player: '\\u{1F464}', shop: '\\u{1F3EA}', restaurant: '\\u{1F354}', nightclub: '\\u{1FA69}' };
    var ENEMY_IMGS = JSON.parse('${enemyImagesJSON}');
    
    function getEnemyImage(name) {
      if (!name) return null;
      var lower = name.toLowerCase();
      var keys = Object.keys(ENEMY_IMGS);
      for (var i = 0; i < keys.length; i++) {
        if (lower.indexOf(keys[i]) !== -1) return ENEMY_IMGS[keys[i]];
      }
      return null;
    }

    function sendMessage(data) {
      try {
        if (window.ReactNativeWebView) {
          window.ReactNativeWebView.postMessage(JSON.stringify(data));
        } else if (window.parent !== window) {
          window.parent.postMessage(JSON.stringify(data), '*');
        }
      } catch(e) {}
    }

    // API: Update player position
    window.updatePosition = function(lat, lng) {
      targetLat = lat;
      targetLng = lng;
    };

    // API: Update heading
    window.updateHeading = function(deg) {
      currentHeading = deg;
      var arrow = document.getElementById('heading-arrow');
      if (arrow) arrow.style.transform = 'rotate(' + deg + 'deg)';
    };

    // API: Update player avatar
    window.updatePlayerAvatar = function(avatarUrl) {
      var el = document.getElementById('player-avatar');
      if (el && avatarUrl) {
        el.innerHTML = '<img src="' + avatarUrl + '" alt="avatar" />';
      }
    };

    // API: Update territories (squares on map)
    var territoryLayers = [];
    window.updateTerritories = function(territories) {
      // Remove old territory layers
      territoryLayers.forEach(function(layer) { map.removeLayer(layer); });
      territoryLayers = [];
      
      territories.forEach(function(t) {
        var color = t.color || '#e74c3c';
        var isOwned = !!t.owner_id;
        var ownerPic = t.owner_pic || '';
        
        // Square territory zone using bounds or fallback calculation
        var bounds;
        if (t.bounds) {
          bounds = [[t.bounds.south, t.bounds.west], [t.bounds.north, t.bounds.east]];
        } else {
          // Fallback: calculate from center + size (or radius)
          var sizeM = t.size || t.radius || 200;
          var halfLat = (sizeM / 2) / 111000;
          var halfLng = (sizeM / 2) / (111000 * Math.cos(t.location.latitude * Math.PI / 180));
          bounds = [
            [t.location.latitude - halfLat, t.location.longitude - halfLng],
            [t.location.latitude + halfLat, t.location.longitude + halfLng]
          ];
        }
        
        var rect = L.rectangle(bounds, {
          color: color,
          fillColor: color,
          fillOpacity: isOwned ? 0.35 : 0.2,
          weight: 3,
          dashArray: isOwned ? null : '8, 10',
        });
        rect.on('click', function() {
          sendMessage({ type: 'territory', id: t.id });
        });
        rect.addTo(map);
        territoryLayers.push(rect);
        
        // Owner profile picture marker (large, prominent)
        if (isOwned && ownerPic) {
          var picIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="position:relative;width:44px;height:52px;">' +
              '<div style="width:44px;height:44px;border-radius:50%;border:3px solid ' + color + ';box-shadow:0 2px 8px rgba(0,0,0,0.5);overflow:hidden;background:#222;cursor:pointer;">' +
              '<img src="' + ownerPic.replace(/"/g, '&quot;') + '" style="width:100%;height:100%;object-fit:cover;display:block;" />' +
              '</div>' +
              '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:6px solid ' + color + ';"></div>' +
              '</div>',
            iconSize: [44, 52],
            iconAnchor: [22, 52],
          });
          var picMarker = L.marker([t.location.latitude, t.location.longitude], { icon: picIcon, interactive: true, zIndexOffset: 500 });
          picMarker.on('click', function() {
            sendMessage({ type: 'territory', id: t.id });
          });
          picMarker.addTo(map);
          territoryLayers.push(picMarker);
        }
        
        // Territory name label (below the pic or standalone)
        var prefixIcon = isOwned ? (ownerPic ? '' : '\\u{1F451} ') : '\\u{2694}\\u{FE0F} ';
        var labelOffset = (isOwned && ownerPic) ? 20 : -5;
        var labelIcon = L.divIcon({
          className: 'territory-label',
          html: '<div style="background:' + color + '; color:#fff; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:800; white-space:nowrap; text-align:center; opacity:0.95; border:2px solid rgba(255,255,255,0.4); pointer-events:auto; cursor:pointer; box-shadow:0 2px 6px rgba(0,0,0,0.4);">' + prefixIcon + t.name + '</div>',
          iconSize: [0, 0],
          iconAnchor: [0, -labelOffset],
        });
        var label = L.marker([t.location.latitude, t.location.longitude], { icon: labelIcon, interactive: true });
        label.on('click', function() {
          sendMessage({ type: 'territory', id: t.id });
        });
        label.addTo(map);
        territoryLayers.push(label);
      });
    };

    // API: Center on player
    window.centerOnPlayer = function() {
      isFollowing = true;
      map.setView([currentLat, currentLng], 17, { animate: true });
    };

    // API: Update markers (add/remove/update)
    window.updateMarkers = function(markersJSON) {
      try {
        var newMarkers = JSON.parse(markersJSON);
        var newIds = {};

        newMarkers.forEach(function(m) {
          newIds[m.id] = true;
          if (entityMarkers[m.id]) {
            // Update existing marker position
            entityMarkers[m.id].setLatLng([m.lat, m.lng]);
          } else {
            // Create new marker
            var color = markerColors[m.type] || '#999';
            var icon = markerIcons[m.type] || '?';
            var levelHTML = m.level ? '<span style="position:absolute;bottom:-8px;background:white;padding:0 3px;border-radius:4px;font-size:9px;font-weight:bold;">' + m.level + '</span>' : '';
            
            var isThug = false;
            var enemyImg = null;
            if (m.type === 'monster' && m.name) {
              enemyImg = getEnemyImage(m.name);
            }
            var markerHTML;
            if (m.type === 'restaurant') {
              var rIcon = m.name ? m.name.charAt(0) : '\\u{1F354}';
              var rName = m.name || 'Restaurant';
              markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#FF5722,#E64A19);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(255,87,34,0.6);font-size:22px;cursor:pointer;">\\u{1F354}</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(255,87,34,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + rName + '</div>' +
                '</div>';
            } else if (m.type === 'nightclub') {
              var ncName = m.name || 'Night Club';
              markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#9b59b6,#8e44ad);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(155,89,182,0.6);font-size:22px;cursor:pointer;">\\u{1FA69}</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(155,89,182,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + ncName + '</div>' +
                '</div>';
            } else if (enemyImg) {
              var lvlBadge = m.level ? '<div style="position:absolute;bottom:-6px;left:50%;transform:translateX(-50%);background:#ff6b35;color:#fff;padding:1px 5px;border-radius:6px;font-size:9px;font-weight:bold;white-space:nowrap;border:1px solid #fff;z-index:10;">' + m.level + '</div>' : '';
              var nameBadge = m.name ? '<div style="position:absolute;bottom:-20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.75);color:#fff;padding:1px 5px;border-radius:4px;font-size:8px;font-weight:bold;white-space:nowrap;z-index:10;">' + m.name + '</div>' : '';
              markerHTML = '<div style="width:42px;height:58px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:38px;height:38px;border-radius:50%;overflow:hidden;border:3px solid #ff6b35;box-shadow:0 2px 8px rgba(255,107,53,0.5);background:#1a1a1a;">' +
                '<img src="' + enemyImg + '" style="width:100%;height:100%;object-fit:cover;" /></div>' + lvlBadge + nameBadge + '</div>';
            } else {
              markerHTML = '<div style="background:' + color + ';width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:14px;position:relative;">' + icon + levelHTML + '</div>';
            }
            
            var divIcon = L.divIcon({
              className: 'custom-marker',
              html: markerHTML,
              iconSize: [(m.type === 'restaurant' || m.type === 'nightclub') ? 48 : (enemyImg ? 42 : 32), (m.type === 'restaurant' || m.type === 'nightclub') ? 62 : (enemyImg ? 58 : 32)],
              iconAnchor: [(m.type === 'restaurant' || m.type === 'nightclub') ? 24 : (enemyImg ? 21 : 16), (m.type === 'restaurant' || m.type === 'nightclub') ? 31 : (enemyImg ? 29 : 16)]
            });
            var marker = L.marker([m.lat, m.lng], { icon: divIcon }).addTo(map);
            marker.on('click', (function(id, type) {
              return function() { sendMessage({ type: 'marker', id: id, markerType: type }); };
            })(m.id, m.type));
            entityMarkers[m.id] = marker;
          }
        });

        // Remove markers no longer present
        Object.keys(entityMarkers).forEach(function(id) {
          if (!newIds[id]) {
            map.removeLayer(entityMarkers[id]);
            delete entityMarkers[id];
          }
        });
      } catch(e) {
        console.error('updateMarkers error:', e);
      }
    };

    // Stop follow on manual drag
    map.on('dragstart', function() { isFollowing = false; });

    // Listen for postMessage from parent (web iframe)
    window.addEventListener('message', function(event) {
      try {
        var data = JSON.parse(event.data);
        if (data.type === 'updatePosition') window.updatePosition(data.lat, data.lng);
        else if (data.type === 'updateHeading') window.updateHeading(data.heading);
        else if (data.type === 'centerOnPlayer') window.centerOnPlayer();
        else if (data.type === 'updateMarkers') window.updateMarkers(data.markers);
        else if (data.type === 'updatePlayerAvatar') window.updatePlayerAvatar(data.avatarUrl);
        else if (data.type === 'updateTerritories') window.updateTerritories(data.territories);
      } catch(e) {}
    });

    // Signal ready
    sendMessage({ type: 'ready' });
  </script>
</body>
</html>
  `;
};

export const GameMap: React.FC<GameMapProps> = ({ center, markers, heading = 0, playerAvatar, territories = [], onMarkerPress, onTerritoryPress }) => {
  const webViewRef = useRef<any>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const markersRef = useRef<MapMarker[]>([]);
  const onMarkerPressRef = useRef(onMarkerPress);
  const onTerritoryPressRef = useRef(onTerritoryPress);
  const territoriesRef = useRef(territories);
  onMarkerPressRef.current = onMarkerPress;
  onTerritoryPressRef.current = onTerritoryPress;
  markersRef.current = markers;
  territoriesRef.current = territories;

  // Generate HTML only ONCE with initial position - never regenerate
  const initialCenter = useRef(center);
  const mapHTML = useMemo(() => {
    return generateBaseMapHTML(initialCenter.current.latitude, initialCenter.current.longitude, ENEMY_MAP_IMAGES);
  }, []); // Empty deps = only once

  // --- NATIVE: inject JS for position updates ---
  useEffect(() => {
    if (Platform.OS === 'web' || !mapReady || !webViewRef.current) return;
    webViewRef.current.injectJavaScript(
      `window.updatePosition(${center.latitude}, ${center.longitude}); true;`
    );
  }, [center.latitude, center.longitude, mapReady]);

  // --- WEB: postMessage for position updates ---
  useEffect(() => {
    if (Platform.OS !== 'web' || !iframeRef.current?.contentWindow) return;
    iframeRef.current.contentWindow.postMessage(
      JSON.stringify({ type: 'updatePosition', lat: center.latitude, lng: center.longitude }),
      '*'
    );
  }, [center.latitude, center.longitude]);

  // --- Update heading ---
  useEffect(() => {
    if (Platform.OS !== 'web' && mapReady && webViewRef.current) {
      webViewRef.current.injectJavaScript(`window.updateHeading(${heading}); true;`);
    } else if (Platform.OS === 'web' && iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'updateHeading', heading }), '*'
      );
    }
  }, [heading, mapReady]);

  // --- Update player avatar ---
  useEffect(() => {
    if (!mapReady || !playerAvatar) return;
    const safeUrl = playerAvatar.replace(/'/g, "\\'").replace(/"/g, '\\"');
    if (Platform.OS !== 'web' && webViewRef.current) {
      webViewRef.current.injectJavaScript(`window.updatePlayerAvatar('${safeUrl}'); true;`);
    } else if (Platform.OS === 'web' && iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'updatePlayerAvatar', avatarUrl: playerAvatar }), '*'
      );
    }
  }, [playerAvatar, mapReady]);

  // --- Update territories ---
  useEffect(() => {
    if (!mapReady || !territories || territories.length === 0) return;
    const terrData = JSON.stringify(territories);
    if (Platform.OS !== 'web' && webViewRef.current) {
      webViewRef.current.injectJavaScript(`window.updateTerritories(${terrData}); true;`);
    } else if (Platform.OS === 'web' && iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'updateTerritories', territories }), '*'
      );
    }
  }, [territories, mapReady]);

  // --- Update markers via JS injection (not HTML regen!) ---
  useEffect(() => {
    const markersPayload = JSON.stringify(
      markers.map(m => ({
        id: m.id,
        lat: m.coordinate.latitude,
        lng: m.coordinate.longitude,
        type: m.type,
        level: m.level || 0,
        name: m.name || '',
      }))
    );
    // Double-escape for injectJavaScript string
    const escaped = markersPayload.replace(/'/g, "\\'");

    if (Platform.OS !== 'web' && mapReady && webViewRef.current) {
      webViewRef.current.injectJavaScript(`window.updateMarkers('${escaped}'); true;`);
      // Also send territories
      if (territories.length > 0) {
        const terrData = JSON.stringify(territories);
        webViewRef.current.injectJavaScript(`window.updateTerritories(${terrData}); true;`);
      }
    } else if (Platform.OS === 'web' && iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'updateMarkers', markers: markersPayload }), '*'
      );
      // Send territories with a small delay to avoid message collision
      if (territories.length > 0) {
        setTimeout(() => {
          try {
            if (iframeRef.current?.contentWindow && (iframeRef.current.contentWindow as any).updateTerritories) {
              (iframeRef.current.contentWindow as any).updateTerritories(territories);
            }
          } catch (e) { console.log('Territory update error:', e); }
        }, 500);
      }
    }
  }, [markers, territories, mapReady]);

  // --- Handle messages from map ---
  const handleMapMessage = useCallback((msgData: string) => {
    try {
      const data = JSON.parse(msgData);
      if (data.type === 'ready') {
        setMapReady(true);
      } else if (data.type === 'marker' && onMarkerPressRef.current) {
        const marker = markersRef.current.find(m => m.id === data.id);
        if (marker) onMarkerPressRef.current(marker);
      } else if (data.type === 'territory' && onTerritoryPressRef.current) {
        const territory = territoriesRef.current.find(t => t.id === data.id);
        if (territory) onTerritoryPressRef.current(territory);
      }
    } catch {}
  }, []);

  // Web: listen for iframe messages
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const handler = (event: MessageEvent) => {
      if (typeof event.data === 'string') handleMapMessage(event.data);
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [handleMapMessage]);

  const handleNativeMessage = useCallback((event: any) => {
    handleMapMessage(event.nativeEvent.data);
  }, [handleMapMessage]);

  const handleCenterPress = useCallback(() => {
    if (Platform.OS !== 'web' && webViewRef.current) {
      webViewRef.current.injectJavaScript(`window.centerOnPlayer(); true;`);
    } else if (Platform.OS === 'web' && iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({ type: 'centerOnPlayer' }), '*'
      );
    }
  }, []);

  const monsterCount = markers.filter(m => m.type === 'monster').length;
  const missionCount = markers.filter(m => m.type === 'mission').length;

  // --- Web: iframe ---
  if (Platform.OS === 'web') {
    return (
      <View style={styles.container}>
        <iframe
          ref={(el: any) => { iframeRef.current = el; }}
          srcDoc={mapHTML}
          style={{ flex: 1, border: 'none', width: '100%', height: '100%' } as any}
          title="Game Map"
          onLoad={() => setMapReady(true)}
        />
        <TouchableOpacity style={styles.centerButton} onPress={handleCenterPress} activeOpacity={0.7}>
          <Ionicons name="locate" size={22} color="#4285F4" />
        </TouchableOpacity>
        <View style={styles.infoBar}>
          <Ionicons name="location" size={14} color="#4285F4" />
          <Text style={styles.coordsText}>
            {center.latitude.toFixed(5)}, {center.longitude.toFixed(5)}
          </Text>
          <Text style={styles.countText}>
            {monsterCount} enemies • {missionCount} missions
          </Text>
        </View>
      </View>
    );
  }

  // --- Native: WebView ---
  if (!WebView) {
    return (
      <View style={[styles.container, styles.loading]}>
        <Text style={styles.loadingText}>Map requires native device</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <WebView
        ref={webViewRef}
        source={{ html: mapHTML }}
        style={styles.map}
        onLoad={() => setMapReady(true)}
        onLoadEnd={() => setMapReady(true)}
        onMessage={handleNativeMessage}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
        originWhitelist={['*']}
        mixedContentMode="always"
        allowsInlineMediaPlayback={true}
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
      <TouchableOpacity style={styles.centerButton} onPress={handleCenterPress} activeOpacity={0.7}>
        <Ionicons name="locate" size={22} color="#4285F4" />
      </TouchableOpacity>
      <View style={styles.infoBar}>
        <Ionicons name="location" size={14} color="#4285F4" />
        <Text style={styles.coordsText}>
          {center.latitude.toFixed(5)}, {center.longitude.toFixed(5)}
        </Text>
        <Text style={styles.countText}>
          {monsterCount} enemies • {missionCount} missions
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
