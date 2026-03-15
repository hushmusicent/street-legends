import { Audio } from 'expo-av';
import { useCallback, useRef, useEffect } from 'react';
import { Platform } from 'react-native';
import { useGameStore } from '../stores/gameStore';

// Sound effect URLs (using free sound effects)
const SOUND_URLS = {
  // Battle sounds
  attack: 'https://assets.mixkit.co/active_storage/sfx/2785/2785-preview.mp3',
  criticalHit: 'https://assets.mixkit.co/active_storage/sfx/2788/2788-preview.mp3',
  miss: 'https://assets.mixkit.co/active_storage/sfx/2572/2572-preview.mp3',
  enemyDeath: 'https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3',
  victory: 'https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3',
  defeat: 'https://assets.mixkit.co/active_storage/sfx/2658/2658-preview.mp3',
  playerHit: 'https://assets.mixkit.co/active_storage/sfx/2357/2357-preview.mp3',
  
  // UI sounds
  buttonClick: 'https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3',
  levelUp: 'https://assets.mixkit.co/active_storage/sfx/1997/1997-preview.mp3',
  collectMoney: 'https://assets.mixkit.co/active_storage/sfx/888/888-preview.mp3',
  missionAccept: 'https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3',
  missionComplete: 'https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3',
  error: 'https://assets.mixkit.co/active_storage/sfx/2572/2572-preview.mp3',
  equip: 'https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3',
  purchase: 'https://assets.mixkit.co/active_storage/sfx/888/888-preview.mp3',
};

export type SoundEffect = keyof typeof SOUND_URLS;

// Preloaded sounds cache
const soundCache: Map<SoundEffect, Audio.Sound> = new Map();
let audioInitialized = false;

// Initialize audio mode
const initAudio = async () => {
  if (audioInitialized) return;
  try {
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
      shouldDuckAndroid: true,
    });
    audioInitialized = true;
  } catch (e) {
    console.log('Audio init error:', e);
  }
};

// Preload a sound
const preloadSound = async (key: SoundEffect): Promise<Audio.Sound | null> => {
  if (soundCache.has(key)) {
    return soundCache.get(key)!;
  }
  
  try {
    const { sound } = await Audio.Sound.createAsync(
      { uri: SOUND_URLS[key] },
      { shouldPlay: false, volume: 0.5 }
    );
    soundCache.set(key, sound);
    return sound;
  } catch (e) {
    console.log(`Failed to preload sound ${key}:`, e);
    return null;
  }
};

// Global sound player function
export const playSound = async (key: SoundEffect, volume: number = 0.5) => {
  if (Platform.OS === 'web') {
    // Use Web Audio API for web
    try {
      const audio = new window.Audio(SOUND_URLS[key]);
      audio.volume = volume;
      await audio.play();
    } catch (e) {
      // Silently fail on web
    }
    return;
  }
  
  try {
    await initAudio();
    
    // Try to use cached sound first
    let sound = soundCache.get(key);
    
    if (sound) {
      // Reset and play cached sound
      await sound.setPositionAsync(0);
      await sound.setVolumeAsync(volume);
      await sound.playAsync();
    } else {
      // Create new sound and play
      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: SOUND_URLS[key] },
        { shouldPlay: true, volume }
      );
      
      // Clean up after playing
      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          newSound.unloadAsync();
        }
      });
    }
  } catch (e) {
    // Silently fail
  }
};

// Hook for using sound effects with mute support
export const useSoundEffects = () => {
  const isMuted = useGameStore((s) => s.isMuted);
  const preloadedRef = useRef(false);
  
  // Preload common sounds on mount
  useEffect(() => {
    if (preloadedRef.current || Platform.OS === 'web') return;
    preloadedRef.current = true;
    
    const preload = async () => {
      await initAudio();
      // Preload battle sounds
      await preloadSound('attack');
      await preloadSound('criticalHit');
      await preloadSound('miss');
      await preloadSound('victory');
      await preloadSound('playerHit');
    };
    
    preload();
    
    // Cleanup on unmount
    return () => {
      soundCache.forEach((sound) => {
        sound.unloadAsync().catch(() => {});
      });
      soundCache.clear();
    };
  }, []);
  
  const play = useCallback(async (key: SoundEffect, volume: number = 0.5) => {
    if (isMuted) return;
    await playSound(key, volume);
  }, [isMuted]);
  
  return { play, isMuted };
};

// Convenience functions for common sounds
export const SFX = {
  attack: () => playSound('attack', 0.4),
  criticalHit: () => playSound('criticalHit', 0.6),
  miss: () => playSound('miss', 0.3),
  enemyDeath: () => playSound('enemyDeath', 0.5),
  victory: () => playSound('victory', 0.6),
  defeat: () => playSound('defeat', 0.5),
  playerHit: () => playSound('playerHit', 0.4),
  
  buttonClick: () => playSound('buttonClick', 0.2),
  levelUp: () => playSound('levelUp', 0.6),
  collectMoney: () => playSound('collectMoney', 0.4),
  missionAccept: () => playSound('missionAccept', 0.4),
  missionComplete: () => playSound('missionComplete', 0.5),
  error: () => playSound('error', 0.3),
  equip: () => playSound('equip', 0.4),
  purchase: () => playSound('purchase', 0.4),
};

export default useSoundEffects;
