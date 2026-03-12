import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';

interface OptionsModalProps {
  visible: boolean;
  onClose: () => void;
  onToggleMute: () => void;
  isMuted: boolean;
  showQuit?: boolean;
}

export function OptionsModal({ visible, onClose, onToggleMute, isMuted, showQuit = true }: OptionsModalProps) {
  const { clearPlayer } = useGameStore();

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
});
