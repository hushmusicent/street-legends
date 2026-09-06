import { useCallback } from 'react';
import { Platform } from 'react-native';
import { useGameStore } from '../stores/gameStore';

// Sound effect URLs - Only custom uploaded battle sounds
const SOUND_URLS = {
  // Battle sounds - Custom uploaded sounds
  attack: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/3i9okyhw_Regular_Attack.mp3',
  criticalHit: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/q05riiz5_Critical_Attack.mp3',
  miss: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/6lvtbvdm_Missed_Attack.mp3',
  // Location sounds - Custom uploaded sounds
  restaurant: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/wf1fljj6_Restaurant.mp3',
  nightclub: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/9td6dqpm_Night_Club.mp3',
  gunShop: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/ga1bfhgv_Gun_Shop.mp3',
  // Mission sounds - Custom uploaded sounds
  bountyMission: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/m730rzhk_Bounty_Missions.mp3',
  phoneMission: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/8n4qehpc_Phone_Booth_Missions.mp3',
  // Bank mission sound
  bankMission: 'https://customer-assets.emergentagent.com/job_2c85d534-e12b-4e94-a416-c23d686f8184/artifacts/q19r3g3d_Bank_missions.mp3',
};

export type SoundEffect = keyof typeof SOUND_URLS;

// Global sound player function (works on web and native)
export const playSound = async (key: SoundEffect, volume: number = 0.5) => {
  if (Platform.OS === 'web') {
    // Use Web Audio API for web
    try {
      const audio = new window.Audio(SOUND_URLS[key]);
      audio.volume = volume;
      await audio.play();
    } catch {
      // Silently fail on web
    }
    return;
  }
  
  // For native, we'll use the dynamic import approach
  try {
    const { Audio } = await import('expo-audio');
    const player = Audio.createSoundPlayer({ uri: SOUND_URLS[key] });
    player.volume = volume;
    player.play();
  } catch (err) {
    console.log(`Failed to play sound ${key}:`, err);
  }
};

// Hook for using sound effects with mute support
export const useSoundEffects = () => {
  const isMuted = useGameStore((s) => s.isMuted);
  
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
  restaurant: () => playSound('restaurant', 0.5),
  nightclub: () => playSound('nightclub', 0.5),
  gunShop: () => playSound('gunShop', 0.5),
  bountyMission: () => playSound('bountyMission', 0.5),
  phoneMission: () => playSound('phoneMission', 0.5),
  bankMission: () => playSound('bankMission', 0.6),
};

export default useSoundEffects;
