import { useCallback } from 'react';
import { Platform } from 'react-native';
import { useGameStore } from '../stores/gameStore';
import { createAudioPlayer } from 'expo-audio';

// Sound effect URLs - All custom uploaded sounds
const SOUND_URLS = {
  // Battle sounds
  attack: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/3i9okyhw_Regular_Attack.mp3',
  criticalHit: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/q05riiz5_Critical_Attack.mp3',
  miss: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/6lvtbvdm_Missed_Attack.mp3',
  // Location/Shop ambient sounds
  restaurant: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/wf1fljj6_Restaurant.mp3',
  nightclub: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/9td6dqpm_Night_Club.mp3',
  gunShop: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/ga1bfhgv_Gun_Shop.mp3',
  // Mission sounds
  bountyMission: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/m730rzhk_Bounty_Missions.mp3',
  phoneMission: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/8n4qehpc_Phone_Booth_Missions.mp3',
  bankMission: 'https://customer-assets.emergentagent.com/job_2c85d534-e12b-4e94-a416-c23d686f8184/artifacts/q19r3g3d_Bank_missions.mp3',
  // Background/Ambient music
  mobTies: 'https://customer-assets.emergentagent.com/job_05f5dabc-ec66-4212-831d-f130db9c1387/artifacts/Mob_Ties.mp3',
  // Castle Assault sounds
  cannonFire: 'https://customer-assets-jt897jd0.emergentagent.net/job_2c85d534-e12b-4e94-a416-c23d686f8184/artifacts/fpxr5y5r_CANNON%20SOUND%20EFFECT.mp3',
  bricksFalling: 'https://customer-assets-jt897jd0.emergentagent.net/job_2c85d534-e12b-4e94-a416-c23d686f8184/artifacts/36x6dml9_bricks%20falling.mp3',
  castleVictory: 'https://customer-assets-jt897jd0.emergentagent.net/job_2c85d534-e12b-4e94-a416-c23d686f8184/artifacts/zkwrz766_VICTORY%20SOUND%20EFFECT.mp3',
  castleDefeat: 'https://customer-assets-jt897jd0.emergentagent.net/job_2c85d534-e12b-4e94-a416-c23d686f8184/artifacts/0mth4hdh_Losing%20Horn.mp3',
};

export type SoundEffect = keyof typeof SOUND_URLS;

// Global sound player function (works on web and native)
export const playSound = async (key: SoundEffect, volume: number = 0.5) => {
  const url = SOUND_URLS[key];
  if (!url) {
    console.warn(`Sound "${key}" not found in SOUND_URLS`);
    return;
  }

  if (Platform.OS === 'web') {
    // Use Web Audio API for web
    try {
      const audio = new window.Audio(url);
      audio.volume = volume;
      await audio.play();
    } catch (err) {
      console.log(`Web audio failed for ${key}:`, err);
    }
    return;
  }
  
  // For native, use expo-audio's createAudioPlayer
  try {
    // Create a new player for each sound effect (short sounds)
    const player = createAudioPlayer({ uri: url });
    player.volume = volume;
    
    // Play the sound
    player.play();
    
    // Clean up after playback completes (estimate based on short SFX duration)
    setTimeout(() => {
      try {
        player.release();
      } catch {
        // Ignore cleanup errors
      }
    }, 5000);
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

// Convenience functions for all game sounds
export const SFX = {
  // Battle sounds
  attack: () => playSound('attack', 0.5),
  criticalHit: () => playSound('criticalHit', 0.6),
  miss: () => playSound('miss', 0.4),
  
  // Location/Shop ambient sounds
  restaurant: () => playSound('restaurant', 0.4),
  nightclub: () => playSound('nightclub', 0.4),
  gunShop: () => playSound('gunShop', 0.4),
  
  // Mission sounds
  bountyMission: () => playSound('bountyMission', 0.5),
  phoneMission: () => playSound('phoneMission', 0.5),
  bankMission: () => playSound('bankMission', 0.5),
  
  // Mission completion
  missionComplete: () => playSound('bankMission', 0.6), // Reuse bank mission sound for completion
  
  // Background music
  mobTies: () => playSound('mobTies', 0.3),
  
  // Victory/Defeat
  victory: () => playSound('criticalHit', 0.7), // Use critical hit sound for victory
  defeat: () => playSound('miss', 0.5), // Use miss sound for defeat
  
  // Item purchase
  purchase: () => playSound('attack', 0.4), // Quick confirmation sound
  
  // Castle Assault sounds
  cannonFire: () => playSound('cannonFire', 0.6),
  bricksFalling: () => playSound('bricksFalling', 0.5),
  castleVictory: () => playSound('castleVictory', 0.7),
  castleDefeat: () => playSound('castleDefeat', 0.6),
};

export default useSoundEffects;
