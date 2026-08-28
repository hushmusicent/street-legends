import React, { useState } from 'react';
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
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import * as NavigationBar from 'expo-navigation-bar';
import { useGameStore } from '../stores/gameStore';
import { deletePlayerAccount } from '../services/api';

interface OptionsModalProps {
  visible: boolean;
  onClose: () => void;
  onToggleMute: () => void;
  isMuted: boolean;
  showQuit?: boolean;
}

export function OptionsModal({ visible, onClose, onToggleMute, isMuted, showQuit = true }: OptionsModalProps) {
  const { clearPlayer, playerId } = useGameStore();
  const [isDeleting, setIsDeleting] = useState(false);

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

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={onClose}>
        <TouchableOpacity style={styles.panel} activeOpacity={1}>
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

          {/* Castle Assault Mini-game */}
          <TouchableOpacity 
            style={styles.castleRow} 
            onPress={() => {
              onClose();
              setTimeout(() => router.push('/castle-levels'), 300);
            }} 
            activeOpacity={0.7}
          >
            <Text style={{ fontSize: 18 }}>🏰</Text>
            <Text style={styles.castleText}>CASTLE ASSAULT</Text>
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
  castleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 14,
    backgroundColor: 'rgba(139, 69, 19, 0.15)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(139, 69, 19, 0.4)',
  },
  castleText: {
    color: '#CD853F',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
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
});
