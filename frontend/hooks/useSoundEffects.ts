import { Audio } from 'expo-av';
import { useCallback, useRef, useEffect } from 'react';
import { Platform } from 'react-native';
import { useGameStore } from '../stores/gameStore';

// Sound effect URLs (GTA-style gun sounds)
const SOUND_URLS = {
  // Battle sounds - Gun themed
  attack: 'https://assets.mixkit.co/active_storage/sfx/2751/2751-preview.mp3', // Gunshot
  criticalHit: 'https://assets.mixkit.co/active_storage/sfx/1662/1662-preview.mp3', // Shotgun blast
  miss: 'https://assets.mixkit.co/active_storage/sfx/2763/2763-preview.mp3', // Ricochet
  enemyDeath: 'https://assets.mixkit.co/active_storage/sfx/1661/1661-preview.mp3', // Body drop
  victory: 'https://assets.mixkit.co/active_storage/sfx/2019/2019-preview.mp3', // Win fanfare
  defeat: 'https://assets.mixkit.co/active_storage/sfx/2020/2020-preview.mp3', // Lose sound
  playerHit: 'https://assets.mixkit.co/active_storage/sfx/2785/2785-preview.mp3', // Impact hit
  
  // UI sounds - Street style
  buttonClick: 'https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3', // Click
  levelUp: 'https://assets.mixkit.co/active_storage/sfx/2018/2018-preview.mp3', // Level up celebration
  collectMoney: 'https://assets.mixkit.co/active_storage/sfx/2001/2001-preview.mp3', // Cash register
  missionAccept: 'https://assets.mixkit.co/active_storage/sfx/2866/2866-preview.mp3', // Phone notification
  missionComplete: 'https://assets.mixkit.co/active_storage/sfx/2019/2019-preview.mp3', // Success
  error: 'https://assets.mixkit.co/active_storage/sfx/2955/2955-preview.mp3', // Error buzz
  equip: 'https://assets.mixkit.co/active_storage/sfx/2754/2754-preview.mp3', // Gun cock/reload
  purchase: 'https://assets.mixkit.co/active_storage/sfx/2001/2001-preview.mp3', // Cash sound
  
  // Location sounds
  eating: 'https://assets.mixkit.co/active_storage/sfx/2940/2940-preview.mp3', // Eating/munching
  glassToast: 'https://assets.mixkit.co/active_storage/sfx/2891/2891-preview.mp3', // Glass clinking toast
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
  
  // Location sounds
  eating: () => playSound('eating', 0.5),
  glassToast: () => playSound('glassToast', 0.5),
};

export default useSoundEffects;
