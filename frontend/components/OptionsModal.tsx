import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Alert,
  Platform,
  Share,
  Clipboard,
  ActivityIndicator,
  ScrollView,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import * as NavigationBar from 'expo-navigation-bar';
import { useGameStore } from '../stores/gameStore';
import { deletePlayerAccount } from '../services/api';
import { getLevelConfig, getRunawayRewards } from '../hooks/useRunawayGame';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

// Credits Text
const CREDITS_TEXT = `Powered by - Emergent

Lead Director - Calvin King

Lead Game Designer - Calvin King

Environment Designer - Emergent

Software Engineer - Emergent

Art Director - Meta Ai & Emergent

Narrative Director - Calvin King

Testers - You the People`;


interface OptionsModalProps {
  visible: boolean;
  onClose: () => void;
  onToggleMute: () => void;
  isMuted: boolean;
  showQuit?: boolean;
}

// Modal content screens
type ModalScreen = 'main' | 'credits';

export function OptionsModal({ visible, onClose, onToggleMute, isMuted, showQuit = true }: OptionsModalProps) {
  const { clearPlayer, playerId, runawayLevel, setRunawayLevel, saveRunawayLevel, loadRunawayLevel, packageGrabLevel, setPackageGrabLevel, savePackageGrabLevel, loadPackageGrabLevel, shootoutLevel, setShootoutLevel, saveShootoutLevel, loadShootoutLevel } = useGameStore();
  const [isDeleting, setIsDeleting] = useState(false);
  const [showMiniGames, setShowMiniGames] = useState(false);
  const [showRunawayLevels, setShowRunawayLevels] = useState(false);
  const [showPackageGrabLevels, setShowPackageGrabLevels] = useState(false);
  const [showShootoutLevels, setShowShootoutLevels] = useState(false);
  const [currentScreen, setCurrentScreen] = useState<ModalScreen>('main');

  // Load mini-game levels from storage when modal opens
  useEffect(() => {
    if (visible) {
      loadRunawayLevel();
      loadPackageGrabLevel();
      loadShootoutLevel();
    }
  }, [visible]);

  const shareMessage = '🎮 Check out Street Legends - A GTA-style GPS RPG game! Fight enemies, capture territories, and build your criminal empire in real life locations! Download now: https://street-empire-test.preview.emergentagent.com';

  const handleShare = async () => {
    try {
      // For web, try Web Share API first, then fallback to clipboard
      if (Platform.OS === 'web') {
        if (typeof navigator !== 'undefined' && navigator.share) {
          await navigator.share({
            title: 'Street Legends - GPS RPG Game',
            text: shareMessage,
            url: 'https://street-empire-test.preview.emergentagent.com',
          });
        } else {
          // Fallback to clipboard for web browsers without share API
          await Clipboard.setString(shareMessage);
          Alert.alert('Link Copied!', 'The game link has been copied to your clipboard. Share it with your friends!');
        }
      } else {
        // Native share for mobile
        const result = await Share.share({
          message: shareMessage,
          title: 'Street Legends - GPS RPG Game',
        });
        if (result.action === Share.sharedAction) {
          console.log('Shared successfully');
        }
      }
    } catch (error: any) {
      // Final fallback - try clipboard
      try {
        await Clipboard.setString(shareMessage);
        Alert.alert('Link Copied!', 'The game link has been copied to your clipboard.');
      } catch (clipErr) {
        Alert.alert('Share Failed', 'Could not share the game link. Please copy this link manually: https://street-empire-test.preview.emergentagent.com');
      }
    }
  };

  const handleQuit = () => {
    Alert.alert(
      'Quit Game',
      'Are you sure you want to quit? You will be logged out.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Quit',
          style: 'destructive',
          onPress: async () => {
            try {
              // Restore Android navigation bar before quitting
              if (Platform.OS === 'android') {
                await NavigationBar.setVisibilityAsync('visible');
              }
              await AsyncStorage.removeItem('playerId');
              clearPlayer();
              onClose();
              // Navigate back to intro screen with delay for modal to close
              setTimeout(() => {
                try { router.dismissAll(); } catch (_) {}
                router.replace('/');
              }, 300);
            } catch (e) {
              console.log('Quit error:', e);
              try { router.replace('/'); } catch (_) {}
            }
          },
        },
      ]
    );
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      '⚠️ Delete Account',
      'Are you sure you want to permanently delete your account?\n\nThis action CANNOT be undone and will delete:\n\n• All character stats and progress\n• Your territories and income\n• Skills and inventory\n• Battle history\n• Fitness data\n• Guild memberships',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Forever',
          style: 'destructive',
          onPress: () => {
            // Second confirmation for safety
            Alert.alert(
              '🚨 Final Confirmation',
              'This is your LAST CHANCE. Your account and ALL data will be permanently deleted.\n\nType your understanding by pressing DELETE.',
              [
                { text: 'Go Back', style: 'cancel' },
                {
                  text: 'DELETE',
                  style: 'destructive',
                  onPress: async () => {
                    if (!playerId) {
                      Alert.alert('Error', 'No player ID found. Please try again.');
                      return;
                    }
                    
                    setIsDeleting(true);
                    try {
                      await deletePlayerAccount(playerId);
                      
                      // Restore Android navigation bar
                      if (Platform.OS === 'android') {
                        await NavigationBar.setVisibilityAsync('visible');
                      }
                      
                      // Clear local storage
                      await AsyncStorage.removeItem('playerId');
                      clearPlayer();
                      onClose();
                      
                      // Show success and redirect
                      Alert.alert(
                        'Account Deleted',
                        'Your account has been permanently deleted. Thank you for playing Street Legends.',
                        [
                          {
                            text: 'OK',
                            onPress: () => {
                              try { router.dismissAll(); } catch (_) {}
                              router.replace('/');
                            }
                          }
                        ]
                      );
                    } catch (error: any) {
                      setIsDeleting(false);
                      Alert.alert(
                        'Deletion Failed',
                        error?.response?.data?.detail || 'Failed to delete account. Please try again.'
                      );
                    }
                  },
                },
              ]
            );
          },
        },
      ]
    );
  };

  // Reset screen to main when modal closes
  useEffect(() => {
    if (!visible) {
      setCurrentScreen('main');
    }
  }, [visible]);

  // Render Credits Screen
  const renderCreditsScreen = () => (
    <View style={styles.subScreenContainer}>
      <View style={styles.subScreenHeader}>
        <TouchableOpacity onPress={() => setCurrentScreen('main')} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Ionicons name="heart" size={24} color="#f59e0b" />
        <Text style={styles.subScreenTitle}>CREDITS</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
          <Ionicons name="close" size={22} color="#888" />
        </TouchableOpacity>
      </View>
      <View style={styles.subScreenDivider} />
      <View style={styles.creditsContainer}>
        <Text style={styles.creditsText}>{CREDITS_TEXT}</Text>
      </View>
    </View>
  );

  // Render Main Options Screen
  const renderMainScreen = () => (
    <>
      {/* Header */}
      <View style={styles.header}>
        <Ionicons name="settings" size={24} color="#FBBC04" />
        <Text style={styles.title}>OPTIONS</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
          <Ionicons name="close" size={22} color="#888" />
        </TouchableOpacity>
      </View>

      <View style={styles.divider} />

      {/* Mute Music */}
      <TouchableOpacity style={styles.optionRow} onPress={onToggleMute} activeOpacity={0.7}>
        <View style={styles.optionLeft}>
          <Ionicons
            name={isMuted ? 'volume-mute' : 'volume-high'}
            size={22}
            color={isMuted ? '#e74c3c' : '#4caf50'}
          />
          <Text style={styles.optionText}>Music</Text>
        </View>
        <View style={[styles.toggleTrack, isMuted && styles.toggleTrackOff]}>
          <View style={[styles.toggleThumb, isMuted && styles.toggleThumbOff]} />
        </View>
      </TouchableOpacity>

      <View style={styles.divider} />

      {/* Share Game */}
      <TouchableOpacity style={styles.shareRow} onPress={handleShare} activeOpacity={0.7}>
        <Ionicons name="share-social" size={22} color="#3498db" />
        <Text style={styles.shareText}>SHARE GAME</Text>
      </TouchableOpacity>

      <View style={styles.divider} />

      {/* How to Play */}
      <TouchableOpacity 
        style={styles.howToPlayRow} 
        onPress={() => {
          onClose();
          setTimeout(() => router.push('/instructions'), 300);
        }} 
        activeOpacity={0.7}
      >
        <Ionicons name="help-circle" size={22} color="#f59e0b" />
        <Text style={styles.howToPlayText}>HOW TO PLAY</Text>
      </TouchableOpacity>

      <View style={styles.divider} />

      {/* Mini Games Button */}
      <TouchableOpacity 
        style={styles.miniGamesRow} 
        onPress={() => setShowMiniGames(!showMiniGames)} 
        activeOpacity={0.7}
      >
        <View style={styles.miniGamesLeft}>
          <Text style={{ fontSize: 18 }}>🎮</Text>
          <Text style={styles.miniGamesText}>MINI GAMES</Text>
        </View>
        <Ionicons 
          name={showMiniGames ? "chevron-up" : "chevron-down"} 
          size={20} 
          color="#9b59b6" 
        />
      </TouchableOpacity>

      {/* Mini Games Sub-menu */}
      {showMiniGames && (
        <View style={styles.miniGamesMenu}>
          {/* Castle Assault Mini-game */}
          <TouchableOpacity 
            style={styles.miniGameItem} 
            onPress={() => {
              onClose();
              setShowMiniGames(false);
              setTimeout(() => router.push({
                pathname: '/castle-levels',
                params: { standalone: 'true' }
              }), 300);
            }} 
            activeOpacity={0.7}
          >
            <Text style={{ fontSize: 22 }}>🏰</Text>
            <View style={styles.miniGameInfo}>
              <Text style={styles.miniGameTitle}>Castle Assault</Text>
              <Text style={styles.miniGameDesc}>Cannon physics puzzle game • 50% rewards</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#CD853F" />
          </TouchableOpacity>

          {/* Car Chase Mini-game */}
          <TouchableOpacity 
            style={styles.miniGameItem} 
            onPress={() => {
              onClose();
              setShowMiniGames(false);
              setTimeout(() => router.push({
                pathname: '/car-chase',
                params: {
                  standalone: 'true',
                  chaseName: 'Practice Run',
                  difficulty: '5',
                  countyLineDistance: '8000',
                },
              }), 300);
            }} 
            activeOpacity={0.7}
          >
            <Text style={{ fontSize: 22 }}>🚗</Text>
            <View style={styles.miniGameInfo}>
              <Text style={styles.miniGameTitle}>Car Chase</Text>
              <Text style={styles.miniGameDesc}>Dodge traffic & escape cops • 50% rewards</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#e74c3c" />
          </TouchableOpacity>

          {/* Runaway Simulator Mini-game with Level Selection */}
          <View style={styles.runawayContainer}>
            <TouchableOpacity 
              style={styles.miniGameItem} 
              onPress={() => setShowRunawayLevels(!showRunawayLevels)} 
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 22 }}>🚔</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.miniGameTitle}>Runaway Simulator</Text>
                <Text style={styles.miniGameDesc}>Side-scroller • Level {runawayLevel} • 50% rewards</Text>
              </View>
              <Ionicons 
                name={showRunawayLevels ? "chevron-up" : "chevron-down"} 
                size={18} 
                color="#00b894" 
              />
            </TouchableOpacity>

            {/* Level Selection Panel */}
            {showRunawayLevels && (
              <View style={styles.levelSelectionPanel}>
                <Text style={styles.levelSelectionTitle}>SELECT LEVEL</Text>
                <Text style={styles.levelSelectionHint}>Higher levels = longer distance, more rewards</Text>
                
                <ScrollView 
                  horizontal 
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.levelScrollContent}
                >
                  {Array.from({ length: 20 }, (_, i) => i + 1).map((level) => {
                    const config = getLevelConfig(level);
                    const rewards = getRunawayRewards(level);
                    const isSelected = runawayLevel === level;
                    
                    return (
                      <TouchableOpacity
                        key={level}
                        style={[
                          styles.levelCard,
                          isSelected && styles.levelCardSelected,
                        ]}
                        onPress={() => {
                          setRunawayLevel(level);
                          saveRunawayLevel(level);
                        }}
                        activeOpacity={0.7}
                      >
                        <Text style={[styles.levelNumber, isSelected && styles.levelNumberSelected]}>
                          {level}
                        </Text>
                        <Text style={styles.levelDistance}>{config.hideoutDistance}m</Text>
                        <Text style={styles.levelReward}>${rewards.cash}</Text>
                        {isSelected && (
                          <View style={styles.selectedBadge}>
                            <Ionicons name="checkmark" size={10} color="#fff" />
                          </View>
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>

                {/* Current Level Stats */}
                <View style={styles.currentLevelStats}>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Distance</Text>
                    <Text style={styles.statValue}>{getLevelConfig(runawayLevel).hideoutDistance}m</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Reward</Text>
                    <Text style={[styles.statValue, { color: '#f39c12' }]}>${getRunawayRewards(runawayLevel).cash}</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>XP</Text>
                    <Text style={[styles.statValue, { color: '#3498db' }]}>+{getRunawayRewards(runawayLevel).xp}</Text>
                  </View>
                </View>

                {/* Play Button */}
                <TouchableOpacity
                  style={styles.playRunawayButton}
                  onPress={() => {
                    onClose();
                    setShowMiniGames(false);
                    setShowRunawayLevels(false);
                    setTimeout(() => router.push({
                      pathname: '/runaway-simulator',
                      params: {
                        standalone: 'true',
                        runawayName: `Level ${runawayLevel} Run`,
                        difficulty: runawayLevel.toString(),
                      },
                    }), 300);
                  }}
                  activeOpacity={0.7}
                >
                  <Ionicons name="play" size={18} color="#fff" />
                  <Text style={styles.playRunawayText}>PLAY LEVEL {runawayLevel}</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
          
          {/* Package Grab Mini-game with Level Selection */}
          <View style={[styles.runawayContainer, { backgroundColor: 'rgba(230, 126, 34, 0.08)' }]}>
            <TouchableOpacity 
              style={styles.miniGameItem} 
              onPress={() => setShowPackageGrabLevels(!showPackageGrabLevels)} 
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 22 }}>📦</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.miniGameTitle}>Package Grab</Text>
                <Text style={styles.miniGameDesc}>Delivery run • Level {packageGrabLevel} • 50% rewards</Text>
              </View>
              <Ionicons 
                name={showPackageGrabLevels ? "chevron-up" : "chevron-down"} 
                size={18} 
                color="#e67e22" 
              />
            </TouchableOpacity>

            {/* Level Selection Panel */}
            {showPackageGrabLevels && (
              <View style={[styles.levelSelectionPanel, { borderTopColor: 'rgba(230, 126, 34, 0.2)' }]}>
                <Text style={[styles.levelSelectionTitle, { color: '#e67e22' }]}>SELECT LEVEL</Text>
                <Text style={styles.levelSelectionHint}>Higher levels = longer route, more rewards</Text>
                
                <ScrollView 
                  horizontal 
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.levelScrollContent}
                >
                  {Array.from({ length: 20 }, (_, i) => i + 1).map((level) => {
                    const isSelected = packageGrabLevel === level;
                    // Calculate distance and reward for package grab
                    const distance = 2000 + (level - 1) * 370;
                    const baseReward = 20 + level * 10;
                    
                    return (
                      <TouchableOpacity
                        key={level}
                        style={[
                          styles.levelCard,
                          isSelected && [styles.levelCardSelected, { backgroundColor: 'rgba(230, 126, 34, 0.2)', borderColor: '#e67e22' }],
                        ]}
                        onPress={() => {
                          setPackageGrabLevel(level);
                          savePackageGrabLevel(level);
                        }}
                        activeOpacity={0.7}
                      >
                        <Text style={[styles.levelNumber, isSelected && { color: '#e67e22' }]}>
                          {level}
                        </Text>
                        <Text style={styles.levelDistance}>{distance}m</Text>
                        <Text style={styles.levelReward}>${baseReward}+</Text>
                        {isSelected && (
                          <View style={[styles.selectedBadge, { backgroundColor: '#e67e22' }]}>
                            <Ionicons name="checkmark" size={10} color="#fff" />
                          </View>
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>

                {/* Current Level Stats */}
                <View style={styles.currentLevelStats}>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Distance</Text>
                    <Text style={styles.statValue}>{2000 + (packageGrabLevel - 1) * 370}m</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Base Reward</Text>
                    <Text style={[styles.statValue, { color: '#f39c12' }]}>${20 + packageGrabLevel * 10}+</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Bonus</Text>
                    <Text style={[styles.statValue, { color: '#e67e22' }]}>📦 +$</Text>
                  </View>
                </View>

                {/* Play Button */}
                <TouchableOpacity
                  style={[styles.playRunawayButton, { backgroundColor: '#e67e22' }]}
                  onPress={() => {
                    onClose();
                    setShowMiniGames(false);
                    setShowPackageGrabLevels(false);
                    setTimeout(() => router.push({
                      pathname: '/package-grab',
                      params: {
                        standalone: 'true',
                        grabName: `Level ${packageGrabLevel} Delivery`,
                        difficulty: packageGrabLevel.toString(),
                      },
                    }), 300);
                  }}
                  activeOpacity={0.7}
                >
                  <Ionicons name="car" size={18} color="#fff" />
                  <Text style={styles.playRunawayText}>PLAY LEVEL {packageGrabLevel}</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
          
          {/* Shootout Simulator Mini-game with Level Selection */}
          <View style={[styles.runawayContainer, { backgroundColor: 'rgba(192, 57, 43, 0.08)' }]}>
            <TouchableOpacity 
              style={styles.miniGameItem} 
              onPress={() => setShowShootoutLevels(!showShootoutLevels)} 
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 22 }}>🔫</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.miniGameTitle}>Shootout Simulator</Text>
                <Text style={styles.miniGameDesc}>Target shooting • Level {shootoutLevel} • 50% rewards</Text>
              </View>
              <Ionicons 
                name={showShootoutLevels ? "chevron-up" : "chevron-down"} 
                size={18} 
                color="#c0392b" 
              />
            </TouchableOpacity>

            {/* Level Selection Panel */}
            {showShootoutLevels && (
              <View style={[styles.levelSelectionPanel, { borderTopColor: 'rgba(192, 57, 43, 0.2)' }]}>
                <Text style={[styles.levelSelectionTitle, { color: '#c0392b' }]}>SELECT LEVEL</Text>
                <Text style={styles.levelSelectionHint}>Higher levels = faster crosshair, less time</Text>
                
                <ScrollView 
                  horizontal 
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.levelScrollContent}
                >
                  {Array.from({ length: 20 }, (_, i) => i + 1).map((level) => {
                    const isSelected = shootoutLevel === level;
                    // Calculate time and reward for shootout
                    const timeLimit = Math.max(15, 45 - (level - 1) * 1.5);
                    const hitReward = 5 + level * 2;
                    
                    return (
                      <TouchableOpacity
                        key={level}
                        style={[
                          styles.levelCard,
                          isSelected && [styles.levelCardSelected, { backgroundColor: 'rgba(192, 57, 43, 0.2)', borderColor: '#c0392b' }],
                        ]}
                        onPress={() => {
                          setShootoutLevel(level);
                          saveShootoutLevel(level);
                        }}
                        activeOpacity={0.7}
                      >
                        <Text style={[styles.levelNumber, isSelected && { color: '#c0392b' }]}>
                          {level}
                        </Text>
                        <Text style={styles.levelDistance}>{Math.floor(timeLimit)}s</Text>
                        <Text style={styles.levelReward}>${hitReward}/hit</Text>
                        {isSelected && (
                          <View style={[styles.selectedBadge, { backgroundColor: '#c0392b' }]}>
                            <Ionicons name="checkmark" size={10} color="#fff" />
                          </View>
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>

                {/* Current Level Stats */}
                <View style={styles.currentLevelStats}>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Time Limit</Text>
                    <Text style={styles.statValue}>{Math.floor(Math.max(15, 45 - (shootoutLevel - 1) * 1.5))}s</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Per Hit</Text>
                    <Text style={[styles.statValue, { color: '#f39c12' }]}>${5 + shootoutLevel * 2}</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Shots</Text>
                    <Text style={[styles.statValue, { color: '#c0392b' }]}>12</Text>
                  </View>
                </View>

                {/* Play Button */}
                <TouchableOpacity
                  style={[styles.playRunawayButton, { backgroundColor: '#c0392b' }]}
                  onPress={() => {
                    onClose();
                    setShowMiniGames(false);
                    setShowShootoutLevels(false);
                    setTimeout(() => router.push({
                      pathname: '/shootout-simulator',
                      params: {
                        standalone: 'true',
                        shootoutName: `Level ${shootoutLevel} Shootout`,
                        difficulty: shootoutLevel.toString(),
                      },
                    }), 300);
                  }}
                  activeOpacity={0.7}
                >
                  <Ionicons name="flash" size={18} color="#fff" />
                  <Text style={styles.playRunawayText}>PLAY LEVEL {shootoutLevel}</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
          
          {/* Casino Games Section */}
          <View style={[styles.runawayContainer, { backgroundColor: 'rgba(255, 215, 0, 0.08)' }]}>
            <View style={styles.miniGameItem}>
              <Text style={{ fontSize: 22 }}>🎰</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.miniGameTitle}>Casino Games</Text>
                <Text style={styles.miniGameDesc}>Slots, Blackjack & Roulette</Text>
              </View>
            </View>
            
            {/* Slots */}
            <TouchableOpacity 
              style={[styles.casinoGameItem, { marginTop: 8 }]} 
              onPress={() => {
                onClose();
                setShowMiniGames(false);
                setTimeout(() => router.push({
                  pathname: '/casino',
                  params: { game: 'slots', standalone: 'true' }
                }), 300);
              }} 
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 20 }}>🍒</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.casinoGameTitle}>Slots</Text>
                <Text style={styles.casinoGameDesc}>Match symbols to win big!</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#FFD700" />
            </TouchableOpacity>
            
            {/* Blackjack */}
            <TouchableOpacity 
              style={styles.casinoGameItem} 
              onPress={() => {
                onClose();
                setShowMiniGames(false);
                setTimeout(() => router.push({
                  pathname: '/casino',
                  params: { game: 'blackjack', standalone: 'true' }
                }), 300);
              }} 
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 20 }}>🃏</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.casinoGameTitle}>Blackjack</Text>
                <Text style={styles.casinoGameDesc}>Beat the dealer to 21!</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#FFD700" />
            </TouchableOpacity>
            
            {/* Roulette */}
            <TouchableOpacity 
              style={styles.casinoGameItem} 
              onPress={() => {
                onClose();
                setShowMiniGames(false);
                setTimeout(() => router.push({
                  pathname: '/casino',
                  params: { game: 'roulette', standalone: 'true' }
                }), 300);
              }} 
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 20 }}>🎡</Text>
              <View style={styles.miniGameInfo}>
                <Text style={styles.casinoGameTitle}>Roulette</Text>
                <Text style={styles.casinoGameDesc}>Bet on red, black, or numbers!</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#FFD700" />
            </TouchableOpacity>
          </View>
        </View>
      )}

      <View style={styles.divider} />

      {/* Credits */}
      <TouchableOpacity 
        style={styles.creditsRow} 
        onPress={() => setCurrentScreen('credits')} 
        activeOpacity={0.7}
      >
        <Ionicons name="heart" size={22} color="#f59e0b" />
        <Text style={styles.creditsRowText}>CREDITS</Text>
        <Ionicons name="chevron-forward" size={18} color="#f59e0b" />
      </TouchableOpacity>

      {/* Quit Game */}
      {showQuit && (
        <>
          <View style={styles.divider} />
          <TouchableOpacity style={styles.quitRow} onPress={handleQuit} activeOpacity={0.7}>
            <Ionicons name="exit" size={22} color="#e74c3c" />
            <Text style={styles.quitText}>QUIT GAME</Text>
          </TouchableOpacity>
        </>
      )}

      {/* Delete Account */}
      <View style={styles.divider} />
      <TouchableOpacity 
        style={styles.deleteRow} 
        onPress={handleDeleteAccount} 
        activeOpacity={0.7}
        disabled={isDeleting}
      >
        {isDeleting ? (
          <ActivityIndicator size="small" color="#dc2626" />
        ) : (
          <Ionicons name="trash" size={20} color="#dc2626" />
        )}
        <Text style={styles.deleteText}>
          {isDeleting ? 'DELETING...' : 'DELETE ACCOUNT'}
        </Text>
      </TouchableOpacity>
    </>
  );

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={currentScreen === 'main' ? onClose : undefined}>
        <TouchableOpacity 
          style={[
            styles.panel, 
            currentScreen !== 'main' && styles.panelExpanded
          ]} 
          activeOpacity={1}
        >
          {currentScreen === 'main' && renderMainScreen()}
          {currentScreen === 'credits' && renderCreditsScreen()}
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  panel: {
    width: '85%',
    maxWidth: 340,
    backgroundColor: '#1a1a1a',
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: '#333',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  title: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 2,
    flex: 1,
  },
  closeBtn: {
    padding: 4,
  },
  divider: {
    height: 1,
    backgroundColor: '#333',
    marginVertical: 16,
  },
  optionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  optionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  optionText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  toggleTrack: {
    width: 48,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#4caf50',
    justifyContent: 'center',
    paddingHorizontal: 3,
  },
  toggleTrackOff: {
    backgroundColor: '#555',
  },
  toggleThumb: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#fff',
    alignSelf: 'flex-end',
  },
  toggleThumbOff: {
    alignSelf: 'flex-start',
  },
  quitRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 14,
    backgroundColor: 'rgba(231, 76, 60, 0.12)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.3)',
  },
  quitText: {
    color: '#e74c3c',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
  },
  shareRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 14,
    backgroundColor: 'rgba(52, 152, 219, 0.12)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(52, 152, 219, 0.3)',
  },
  shareText: {
    color: '#3498db',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
  },
  howToPlayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 14,
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.3)',
  },
  howToPlayText: {
    color: '#f59e0b',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
  },
  // Mini Games Menu Styles
  miniGamesRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(155, 89, 182, 0.12)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(155, 89, 182, 0.3)',
  },
  miniGamesLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  miniGamesText: {
    color: '#9b59b6',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
  },
  miniGamesMenu: {
    marginTop: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 12,
    padding: 8,
    gap: 8,
  },
  miniGameItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 10,
    gap: 12,
  },
  miniGameInfo: {
    flex: 1,
  },
  miniGameTitle: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  miniGameDesc: {
    color: '#888',
    fontSize: 11,
    marginTop: 2,
  },
  // Runaway Level Selection Styles
  runawayContainer: {
    backgroundColor: 'rgba(0, 184, 148, 0.08)',
    borderRadius: 10,
    overflow: 'hidden',
  },
  levelSelectionPanel: {
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0, 184, 148, 0.2)',
  },
  levelSelectionTitle: {
    color: '#00b894',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
    textAlign: 'center',
    marginBottom: 4,
  },
  levelSelectionHint: {
    color: '#666',
    fontSize: 9,
    textAlign: 'center',
    marginBottom: 10,
  },
  levelScrollContent: {
    paddingHorizontal: 4,
    gap: 8,
  },
  levelCard: {
    width: 54,
    height: 70,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
    position: 'relative',
  },
  levelCardSelected: {
    backgroundColor: 'rgba(0, 184, 148, 0.2)',
    borderColor: '#00b894',
  },
  levelNumber: {
    color: '#888',
    fontSize: 18,
    fontWeight: '900',
  },
  levelNumberSelected: {
    color: '#00b894',
  },
  levelDistance: {
    color: '#666',
    fontSize: 8,
    marginTop: 2,
  },
  levelReward: {
    color: '#f39c12',
    fontSize: 9,
    fontWeight: '700',
    marginTop: 1,
  },
  selectedBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: '#00b894',
    alignItems: 'center',
    justifyContent: 'center',
  },
  currentLevelStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    color: '#666',
    fontSize: 9,
    marginBottom: 2,
  },
  statValue: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  playRunawayButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#00b894',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  playRunawayText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1,
  },
  // Casino Game Item Styles
  casinoGameItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginHorizontal: 8,
    marginBottom: 6,
    backgroundColor: 'rgba(255, 215, 0, 0.1)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.2)',
    gap: 10,
  },
  casinoGameTitle: {
    color: '#FFD700',
    fontSize: 13,
    fontWeight: '700',
  },
  casinoGameDesc: {
    color: '#888',
    fontSize: 10,
    marginTop: 1,
  },
  deleteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 14,
    backgroundColor: 'rgba(220, 38, 38, 0.1)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(220, 38, 38, 0.3)',
    marginTop: 8,
  },
  deleteText: {
    color: '#dc2626',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 1,
  },
  // Credits Row Styles
  creditsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.3)',
  },
  creditsRowText: {
    color: '#f59e0b',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
    flex: 1,
    marginLeft: 10,
  },
  // Sub-Screen Styles
  subScreenContainer: {
    flex: 1,
  },
  subScreenHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  backBtn: {
    padding: 4,
  },
  subScreenTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
    flex: 1,
  },
  subScreenDivider: {
    height: 1,
    backgroundColor: '#333',
    marginVertical: 16,
  },
  panelExpanded: {
    maxHeight: SCREEN_HEIGHT * 0.75,
    height: SCREEN_HEIGHT * 0.7,
  },
  // Credits Screen Styles
  creditsContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  creditsText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 36,
  },
});
