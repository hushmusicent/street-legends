import { Audio } from 'expo-av';
import { useCallback, useRef, useEffect } from 'react';
import { Platform } from 'react-native';
import { useGameStore } from '../stores/gameStore';

// Sound effect URLs - Only custom uploaded battle sounds
const SOUND_URLS = {
  // Battle sounds - Custom uploaded sounds
  attack: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/3i9okyhw_Regular_Attack.mp3',
  criticalHit: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/q05riiz5_Critical_Attack.mp3',
  miss: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/6lvtbvdm_Missed_Attack.mp3',
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

// Convenience functions for battle sounds only
export const SFX = {
  attack: () => playSound('attack', 0.5),
  criticalHit: () => playSound('criticalHit', 0.6),
  miss: () => playSound('miss', 0.4),
};

export default useSoundEffects;
