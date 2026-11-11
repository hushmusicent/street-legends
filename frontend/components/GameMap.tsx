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
  type: 'monster' | 'mission' | 'bounty' | 'player' | 'self' | 'restaurant' | 'nightclub' | 'bank' | 'castle' | 'carChase' | 'runaway' | 'packageGrab' | 'shootout' | 'casino' | 'fiend' | 'pharmacy' | 'park' | 'billboard' | 'house';
  level?: number;
  name?: string;
  icon?: string;
  isBoss?: boolean;
  cooldownSeconds?: number;
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
    var markerColors = { monster: '#EA4335', mission: '#FBBC04', bounty: '#4CAF50', player: '#4285F4', shop: '#FF6F00', restaurant: '#FF5722', nightclub: '#9b59b6', bank: '#2E7D32', castle: '#8B4513', carChase: '#e74c3c', runaway: '#00b894', packageGrab: '#e67e22', shootout: '#c0392b', casino: '#d4af37', house: '#FF9800' , activityCenter: '#7b1fa2', fiend: '#8BC34A', pharmacy: '#009688', park: '#E91E63', billboard: '#FFD700'};
    var markerIcons = { monster: '\\u{1F480}', activityCenter: '🎮', mission: '\\u{260E}\\u{FE0F}', bounty: '\\u{1F4B2}', player: '\\u{1F464}', shop: '\\u{1F3EA}', restaurant: '\\u{1F354}', nightclub: '🎵', bank: '\\u{1F3E6}', castle: '\\u{1F3F0}', carChase: '🚗', runaway: '🚔', packageGrab: '📦', shootout: '🔫', casino: '🎰', house: '🏠', fiend: '🧟' , pharmacy: '💊', park: '⛹️', billboard: '🛣️'};
    var BILLBOARD_THUMB = "data:image/jpeg;base64,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";
    var ENEMY_IMGS = JSON.parse('${enemyImagesJSON}');
    
    // Mini-game marker settings - only show ONE random mini-game at a time
    var miniGameTypes = ['castle', 'carChase', 'runaway', 'packageGrab', 'shootout'];
    var currentSelectedMiniGameId = null;  // ID of the currently visible mini-game marker
    var lastMiniGameSelection = 0;  // Timestamp of last selection
    var miniGameSelectionCooldown = 30000;  // 30 seconds before allowing new selection
    
    function isMiniGameMarker(type) {
      return miniGameTypes.indexOf(type) !== -1;
    }
    
    // Select one random mini-game marker from the available ones
    function selectRandomMiniGame(miniGameMarkers) {
      if (miniGameMarkers.length === 0) return null;
      var randomIndex = Math.floor(Math.random() * miniGameMarkers.length);
      return miniGameMarkers[randomIndex];
    }
    
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
    var territoryLayers = {};  // Changed to object for easier lookup: { id: [layers] }
    window.updateTerritories = function(territories) {
      // Create a set of new territory IDs
      var newIds = new Set(territories.map(function(t) { return t.id; }));
      
      // Remove territories that are no longer in the data
      Object.keys(territoryLayers).forEach(function(id) {
        if (!newIds.has(id)) {
          // Remove all layers for this territory
          territoryLayers[id].forEach(function(layer) {
            map.removeLayer(layer);
          });
          delete territoryLayers[id];
        }
      });
      
      // Update existing and add new territories
      territories.forEach(function(t) {
        var color = t.color || '#e74c3c';
        var isOwned = !!t.owner_id;
        var ownerPic = t.owner_pic || '';
        
        // If territory already exists, just update its style
        if (territoryLayers[t.id]) {
          territoryLayers[t.id].forEach(function(layer) {
            if (layer._isRect) {
              layer.setStyle({
                color: color,
                fillColor: color,
                fillOpacity: isOwned ? 0.35 : 0.2,
                dashArray: isOwned ? null : '8, 10',
              });
            }
          });
          return; // Skip adding new layers
        }
        
        // Add new territory - create array to hold all its layers
        territoryLayers[t.id] = [];
        
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
        rect._territoryId = t.id;
        rect._isRect = true;
        rect.on('click', function() {
          sendMessage({ type: 'territory', id: t.id });
        });
        rect.addTo(map);
        territoryLayers[t.id].push(rect);
        
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
          picMarker._territoryId = t.id;
          picMarker.on('click', function() {
            sendMessage({ type: 'territory', id: t.id });
          });
          picMarker.addTo(map);
          territoryLayers[t.id].push(picMarker);
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
        label._territoryId = t.id;
        label.on('click', function() {
          sendMessage({ type: 'territory', id: t.id });
        });
        label.addTo(map);
        territoryLayers[t.id].push(label);
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
        
        // Separate mini-game markers from regular markers
        var regularMarkers = [];
        var miniGameMarkers = [];
        
        newMarkers.forEach(function(m) {
          if (isMiniGameMarker(m.type)) {
            miniGameMarkers.push(m);
          } else {
            regularMarkers.push(m);
          }
        });
        
        // Helper function to create and add a marker
        function createMarker(m) {
          newIds[m.id] = true;
          if (entityMarkers[m.id]) {
            // Update existing marker position
            entityMarkers[m.id].setLatLng([m.lat, m.lng]);
            return;
          }
          
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
                '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#9b59b6,#8e44ad);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(155,89,182,0.6);font-size:22px;cursor:pointer;">🎵</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(155,89,182,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + ncName + '</div>' +
                '</div>';
            } else if (m.type === 'activityCenter') {
              var acName = m.name || 'Activity Center';
              markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#7b1fa2,#4a148c);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(123,31,162,0.6);font-size:22px;cursor:pointer;">🎮</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(123,31,162,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + acName + '</div>' +
                '</div>';
            
} else if (m.type === 'fiend') {
  var fiendName = m.name || 'Fiend';
  markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
    '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#8BC34A,#558B2F);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(139,195,74,0.6);font-size:22px;cursor:pointer;">🧟</div>' +
    '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(85,139,47,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + fiendName + '</div>' +
    '</div>';
} else if (m.type === 'pharmacy') {
  var pharmName = m.name || 'Pharmacy';
  markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
    '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#009688,#00695C);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(0,150,136,0.6);font-size:22px;cursor:pointer;">💊</div>' +
    '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(0,105,92,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + pharmName + '</div>' +
    '</div>';
} else if (m.type === 'park') {
  var parkName = m.name || 'Park';
  markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
    '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#E91E63,#AD1457);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(233,30,99,0.6);font-size:22px;cursor:pointer;">⛹️</div>' +
    '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(173,20,87,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + parkName + '</div>' +
    '</div>';
} else if (m.type === 'billboard') {
  var bbName = m.name || 'Highway';
  markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
    '<div style="width:46px;height:31px;border-radius:6px;overflow:hidden;border:2px solid #FFD700;box-shadow:0 3px 10px rgba(0,0,0,0.6);background:#000;">' +
    '<img src="' + BILLBOARD_THUMB + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +
    '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.85);color:#FFD700;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #FFD700;">' + bbName + '</div>' +
    '</div>';
} else if (m.type === 'bank') {
              var bankName = m.name || 'Bank';
              markerHTML = '<div style="width:52px;height:68px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,#2E7D32,#1B5E20);display:flex;align-items:center;justify-content:center;border:3px solid #FFD700;box-shadow:0 3px 12px rgba(46,125,50,0.7);font-size:26px;cursor:pointer;">\\u{1F3E6}</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(46,125,50,0.95);color:#FFD700;padding:2px 8px;border-radius:5px;font-size:8px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #FFD700;">' + bankName + '</div>' +
                '</div>';
            } else if (m.type === 'casino') {
              var casinoName = m.name || 'Casino';
              markerHTML = '<div style="width:52px;height:68px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,#d4af37,#b8860b);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 12px rgba(212,175,55,0.7);font-size:26px;cursor:pointer;">🎰</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(212,175,55,0.95);color:#000;padding:2px 8px;border-radius:5px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + casinoName + '</div>' +
                '</div>';
            } else if (m.type === 'castle') {
              var castleName = m.name || 'Castle';
              var diffLevel = m.level || 1;
              var cooldownSecs = m.cooldownSeconds || 0;
              var cooldownHTML = '';
              if (cooldownSecs > 0) {
                var mins = Math.floor(cooldownSecs / 60);
                var secs = cooldownSecs % 60;
                var timeStr = mins + ':' + (secs < 10 ? '0' : '') + secs;
                cooldownHTML = '<div style="position:absolute;top:0;left:0;right:0;bottom:20px;background:rgba(0,0,0,0.7);border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:20;">' +
                  '<div style="font-size:10px;color:#ff6b6b;">⏱</div>' +
                  '<div style="font-size:11px;color:#fff;font-weight:bold;">' + timeStr + '</div>' +
                  '</div>';
              }
              markerHTML = '<div style="width:56px;height:72px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:50px;height:50px;border-radius:8px;background:linear-gradient(135deg,#8B4513,#5D3A1A);display:flex;align-items:center;justify-content:center;border:3px solid ' + (cooldownSecs > 0 ? '#666' : '#CD853F') + ';box-shadow:0 4px 14px rgba(139,69,19,0.7);font-size:28px;cursor:pointer;' + (cooldownSecs > 0 ? 'filter:grayscale(50%);' : '') + '">\\u{1F3F0}</div>' +
                cooldownHTML +
                '<div style="position:absolute;top:-8px;right:-4px;background:#e74c3c;color:#fff;padding:1px 5px;border-radius:8px;font-size:9px;font-weight:bold;border:2px solid #fff;">\\u{2694}' + diffLevel + '</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(139,69,19,0.95);color:#FFE4B5;padding:2px 8px;border-radius:5px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #CD853F;">' + castleName + '</div>' +
                '</div>';
            } else if (m.type === 'carChase') {
              var chaseName = m.name || 'Car Chase';
              var chaseLevel = m.level || 1;
              var chaseCooldownSecs = m.cooldownSeconds || 0;
              var chaseCooldownHTML = '';
              if (chaseCooldownSecs > 0) {
                var cMins = Math.floor(chaseCooldownSecs / 60);
                var cSecs = chaseCooldownSecs % 60;
                var cTimeStr = cMins + ':' + (cSecs < 10 ? '0' : '') + cSecs;
                chaseCooldownHTML = '<div style="position:absolute;top:0;left:0;right:0;bottom:20px;background:rgba(0,0,0,0.7);border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:20;">' +
                  '<div style="font-size:10px;color:#ff6b6b;">⏱</div>' +
                  '<div style="font-size:11px;color:#fff;font-weight:bold;">' + cTimeStr + '</div>' +
                  '</div>';
              }
              markerHTML = '<div style="width:56px;height:72px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:50px;height:50px;border-radius:12px;background:linear-gradient(135deg,#e74c3c,#c0392b);display:flex;align-items:center;justify-content:center;border:3px solid ' + (chaseCooldownSecs > 0 ? '#666' : '#fff') + ';box-shadow:0 4px 14px rgba(231,76,60,0.7);font-size:26px;cursor:pointer;' + (chaseCooldownSecs > 0 ? 'filter:grayscale(50%);' : '') + '">🚗</div>' +
                chaseCooldownHTML +
                '<div style="position:absolute;top:-8px;right:-4px;background:#f39c12;color:#fff;padding:1px 5px;border-radius:8px;font-size:9px;font-weight:bold;border:2px solid #fff;">🚔' + chaseLevel + '</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(231,76,60,0.95);color:#fff;padding:2px 8px;border-radius:5px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + chaseName + '</div>' +
                '</div>';
            } else if (m.type === 'runaway') {
              var runawayName = m.name || 'Runaway';
              var runawayLevel = m.level || 1;
              var runawayCooldownSecs = m.cooldownSeconds || 0;
              var runawayCooldownHTML = '';
              if (runawayCooldownSecs > 0) {
                var rMins = Math.floor(runawayCooldownSecs / 60);
                var rSecs = runawayCooldownSecs % 60;
                var rTimeStr = rMins + ':' + (rSecs < 10 ? '0' : '') + rSecs;
                runawayCooldownHTML = '<div style="position:absolute;top:0;left:0;right:0;bottom:20px;background:rgba(0,0,0,0.7);border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:20;">' +
                  '<div style="font-size:10px;color:#ff6b6b;">⏱</div>' +
                  '<div style="font-size:11px;color:#fff;font-weight:bold;">' + rTimeStr + '</div>' +
                  '</div>';
              }
              markerHTML = '<div style="width:56px;height:72px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:50px;height:50px;border-radius:12px;background:linear-gradient(135deg,#00b894,#00a085);display:flex;align-items:center;justify-content:center;border:3px solid ' + (runawayCooldownSecs > 0 ? '#666' : '#fff') + ';box-shadow:0 4px 14px rgba(0,184,148,0.7);font-size:26px;cursor:pointer;' + (runawayCooldownSecs > 0 ? 'filter:grayscale(50%);' : '') + '">🚔</div>' +
                runawayCooldownHTML +
                '<div style="position:absolute;top:-8px;right:-4px;background:#00cec9;color:#fff;padding:1px 5px;border-radius:8px;font-size:9px;font-weight:bold;border:2px solid #fff;">🏃' + runawayLevel + '</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(0,184,148,0.95);color:#fff;padding:2px 8px;border-radius:5px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + runawayName + '</div>' +
                '</div>';
            } else if (m.type === 'packageGrab') {
              var grabName = m.name || 'Package Grab';
              var grabLevel = m.level || 1;
              var grabCooldownSecs = m.cooldownSeconds || 0;
              var grabCooldownHTML = '';
              if (grabCooldownSecs > 0) {
                var gMins = Math.floor(grabCooldownSecs / 60);
                var gSecs = grabCooldownSecs % 60;
                var gTimeStr = gMins + ':' + (gSecs < 10 ? '0' : '') + gSecs;
                grabCooldownHTML = '<div style="position:absolute;top:0;left:0;right:0;bottom:20px;background:rgba(0,0,0,0.7);border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:20;">' +
                  '<div style="font-size:10px;color:#ff6b6b;">⏱</div>' +
                  '<div style="font-size:11px;color:#fff;font-weight:bold;">' + gTimeStr + '</div>' +
                  '</div>';
              }
              markerHTML = '<div style="width:56px;height:72px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:50px;height:50px;border-radius:12px;background:linear-gradient(135deg,#e67e22,#d35400);display:flex;align-items:center;justify-content:center;border:3px solid ' + (grabCooldownSecs > 0 ? '#666' : '#fff') + ';box-shadow:0 4px 14px rgba(230,126,34,0.7);font-size:26px;cursor:pointer;' + (grabCooldownSecs > 0 ? 'filter:grayscale(50%);' : '') + '">📦</div>' +
                grabCooldownHTML +
                '<div style="position:absolute;top:-8px;right:-4px;background:#f39c12;color:#fff;padding:1px 5px;border-radius:8px;font-size:9px;font-weight:bold;border:2px solid #fff;">🚚' + grabLevel + '</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(230,126,34,0.95);color:#fff;padding:2px 8px;border-radius:5px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + grabName + '</div>' +
                '</div>';
            } else if (m.type === 'shootout') {
              var shootoutName = m.name || 'Shootout';
              var shootoutLevel = m.level || 1;
              var shootoutCooldownSecs = m.cooldownSeconds || 0;
              var shootoutCooldownHTML = '';
              if (shootoutCooldownSecs > 0) {
                var sMins = Math.floor(shootoutCooldownSecs / 60);
                var sSecs = shootoutCooldownSecs % 60;
                var sTimeStr = sMins + ':' + (sSecs < 10 ? '0' : '') + sSecs;
                shootoutCooldownHTML = '<div style="position:absolute;top:0;left:0;right:0;bottom:20px;background:rgba(0,0,0,0.7);border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:20;">' +
                  '<div style="font-size:10px;color:#ff6b6b;">⏱</div>' +
                  '<div style="font-size:11px;color:#fff;font-weight:bold;">' + sTimeStr + '</div>' +
                  '</div>';
              }
              markerHTML = '<div style="width:56px;height:72px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:50px;height:50px;border-radius:12px;background:linear-gradient(135deg,#c0392b,#a93226);display:flex;align-items:center;justify-content:center;border:3px solid ' + (shootoutCooldownSecs > 0 ? '#666' : '#fff') + ';box-shadow:0 4px 14px rgba(192,57,43,0.7);font-size:26px;cursor:pointer;' + (shootoutCooldownSecs > 0 ? 'filter:grayscale(50%);' : '') + '">🔫</div>' +
                shootoutCooldownHTML +
                '<div style="position:absolute;top:-8px;right:-4px;background:#e74c3c;color:#fff;padding:1px 5px;border-radius:8px;font-size:9px;font-weight:bold;border:2px solid #fff;">🎯' + shootoutLevel + '</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(192,57,43,0.95);color:#fff;padding:2px 8px;border-radius:5px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + shootoutName + '</div>' +
                '</div>';
            } else if (m.type === 'house') {
              markerHTML = '<div style="font-size:64px;line-height:1;filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));cursor:pointer;">🏠</div>';
            } else if (enemyImg) {
              var isBoss = m.isBoss || false;
              var lvlBadge = m.level ? '<div style="position:absolute;bottom:-6px;left:50%;transform:translateX(-50%);background:' + (isBoss ? '#FFD700' : '#ff6b35') + ';color:' + (isBoss ? '#000' : '#fff') + ';padding:1px 5px;border-radius:6px;font-size:9px;font-weight:bold;white-space:nowrap;border:1px solid #fff;z-index:10;">' + m.level + '</div>' : '';
              var nameBadge = m.name ? '<div style="position:absolute;bottom:-20px;left:50%;transform:translateX(-50%);background:' + (isBoss ? 'rgba(255,215,0,0.9)' : 'rgba(0,0,0,0.75)') + ';color:' + (isBoss ? '#000' : '#fff') + ';padding:1px 5px;border-radius:4px;font-size:8px;font-weight:bold;white-space:nowrap;z-index:10;">' + m.name + '</div>' : '';
              var crownHTML = isBoss ? '<div style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:16px;z-index:20;">\\u{1F451}</div>' : '';
              var borderRadius = isBoss ? '8px' : '50%';
              var borderColor = isBoss ? '#FFD700' : '#ff6b35';
              var shadowColor = isBoss ? 'rgba(255,215,0,0.7)' : 'rgba(255,107,53,0.5)';
              markerHTML = '<div style="width:' + (isBoss ? '48px' : '42px') + ';height:' + (isBoss ? '68px' : '58px') + ';position:relative;display:flex;flex-direction:column;align-items:center;">' +
                crownHTML +
                '<div style="width:' + (isBoss ? '44px' : '38px') + ';height:' + (isBoss ? '44px' : '38px') + ';border-radius:' + borderRadius + ';overflow:hidden;border:3px solid ' + borderColor + ';box-shadow:0 2px 12px ' + shadowColor + ';background:#1a1a1a;' + (isBoss ? 'margin-top:2px;' : '') + '">' +
                '<img src="' + enemyImg + '" style="width:100%;height:100%;object-fit:cover;" /></div>' + lvlBadge + nameBadge + '</div>';
            } else {
              markerHTML = '<div style="background:' + color + ';width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:14px;position:relative;">' + icon + levelHTML + '</div>';
            }
            
            var isBossMarker = (m.type === 'monster' && m.isBoss);
            var isHouseMarker = (m.type === 'house');
            var isLocationMarker = (m.type === 'restaurant' || m.type === 'nightclub' || m.type === 'activityCenter' || m.type === 'fiend' || m.type === 'pharmacy' || m.type === 'park' || m.type === 'billboard');
            var isBankMarker = (m.type === 'bank');
            var isCasinoMarker = (m.type === 'casino');
            var isCastleMarker = (m.type === 'castle');
            var isCarChaseMarker = (m.type === 'carChase');
            var isRunawayMarker = (m.type === 'runaway');
            var isPackageGrabMarker = (m.type === 'packageGrab');
            var isShootoutMarker = (m.type === 'shootout');
            var markerWidth = isHouseMarker ? 72 : ((isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 56 : (isLocationMarker ? 48 : ((isBankMarker || isCasinoMarker) ? 52 : (isBossMarker ? 48 : (enemyImg ? 42 : 32)))));
            var markerHeight = isHouseMarker ? 72 : ((isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 72 : (isLocationMarker ? 62 : ((isBankMarker || isCasinoMarker) ? 68 : (isBossMarker ? 68 : (enemyImg ? 58 : 32)))));
            var iconAnchorY = isHouseMarker ? 36 : ((isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 36 : (isLocationMarker ? 31 : ((isBankMarker || isCasinoMarker) ? 34 : (isBossMarker ? 34 : (enemyImg ? 29 : 16)))));
            var divIcon = L.divIcon({
              className: 'custom-marker',
              html: markerHTML,
              iconSize: [markerWidth, markerHeight],
              iconAnchor: [markerWidth/2, iconAnchorY]
            });
            var marker = L.marker([m.lat, m.lng], { icon: divIcon }).addTo(map);
            marker.on('click', (function(id, type) {
              return function() { sendMessage({ type: 'marker', id: id, markerType: type }); };
            })(m.id, m.type));
            entityMarkers[m.id] = marker;
        }
        
        // Process regular markers immediately
        regularMarkers.forEach(function(m) {
          createMarker(m);
        });
        
        // Process mini-game markers - only show ONE random mini-game at a time
        var now = Date.now();
        var needsNewSelection = false;
        
        // Check if we need to select a new mini-game
        // 1. No current selection
        // 2. Current selection is no longer in the available markers
        // 3. Cooldown has passed (allows new random selection when moving to new area)
        if (!currentSelectedMiniGameId) {
          needsNewSelection = true;
        } else {
          // Check if current selection is still available
          var currentStillAvailable = miniGameMarkers.some(function(m) {
            return m.id === currentSelectedMiniGameId;
          });
          if (!currentStillAvailable) {
            needsNewSelection = true;
          }
        }
        
        // Select a new random mini-game if needed
        if (needsNewSelection && miniGameMarkers.length > 0) {
          var selected = selectRandomMiniGame(miniGameMarkers);
          if (selected) {
            currentSelectedMiniGameId = selected.id;
            lastMiniGameSelection = now;
          }
        }
        
        // Only process the selected mini-game marker
        miniGameMarkers.forEach(function(m) {
          // Only show the selected mini-game, hide all others
          if (m.id === currentSelectedMiniGameId) {
            newIds[m.id] = true;
            
            // If marker already exists, just update position
            if (entityMarkers[m.id]) {
              entityMarkers[m.id].setLatLng([m.lat, m.lng]);
            } else {
              // Create the selected marker with a small delay for effect
              setTimeout(function() {
                createMarker(m);
              }, 300 + Math.random() * 500);
            }
          }
          // Other mini-game markers are not added to newIds, so they'll be removed
        });

        // Remove markers no longer present (including non-selected mini-games)
        Object.keys(entityMarkers).forEach(function(id) {
          if (!newIds[id]) {
            map.removeLayer(entityMarkers[id]);
            delete entityMarkers[id];
          }
        });
        
        // Clear the selection if the marker was removed
        if (currentSelectedMiniGameId && !newIds[currentSelectedMiniGameId]) {
          currentSelectedMiniGameId = null;
        }
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
        cooldownSeconds: (m as any).cooldownSeconds || 0,
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
        onLoad={() => {
          // Delay setting mapReady to ensure WebView is fully initialized
          setTimeout(() => setMapReady(true), 100);
        }}
        onLoadEnd={() => {
          setTimeout(() => setMapReady(true), 100);
        }}
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
        // SDK 57 specific props for better stability
        webviewDebuggingEnabled={false}
        cacheEnabled={true}
        cacheMode="LOAD_DEFAULT"
        setSupportMultipleWindows={false}
        renderLoading={() => (
          <View style={styles.loading}>
            <Text style={styles.loadingText}>Loading map...</Text>
          </View>
        )}
        onError={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.warn('WebView error: ', nativeEvent);
        }}
        onRenderProcessGone={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.warn('WebView process gone: ', nativeEvent.didCrash);
        }}
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
