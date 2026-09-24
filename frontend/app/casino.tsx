import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  ScrollView,
  Image,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { LinearGradient } from 'expo-linear-gradient';
import { SFX } from '../hooks/useSoundEffects';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Background removal endpoint
const REMBG_URL = `${API_URL}/api/sprites/remove-bg?url=`;

// Slot symbol images with background removal
// Jackpot (rarest): AppSolut Group logo, Street Legends logo
// Rare: Hush Music Ent logo
// Common: Banana, Eggplant, Peach, Coconut
const SLOT_IMAGES: Record<string, { url: string; name: string; rarity: string }> = {
  banana: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/5a2da761865e4e32818ef3af04296bfb_banana_final.png')}`,
    name: 'Banana',
    rarity: 'common',
  },
  eggplant: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/9b5ee5acc4454e269ea52d57d4df54a1_eggplant_proper.png')}`,
    name: 'Eggplant',
    rarity: 'common',
  },
  peach: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/e9d8aa533f704231be47c56cf388b7cb_peach_final.png')}`,
    name: 'Peach',
    rarity: 'common',
  },
  coconut: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/f8704c1fe227420a8027a9ef920493cd_coconut_better_final.png')}`,
    name: 'Coconut',
    rarity: 'common',
  },
  hush_logo: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/f70cdaecfe084894947e2e9f80662a91_Resized_mainlogo.jpeg')}`,
    name: 'Hush Music',
    rarity: 'rare',
  },
  appsolut_logo: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/704a54f626164a05996c41329984e341_appsolut_atg.jpg')}`,
    name: 'AppSolut',
    rarity: 'jackpot',
  },
  street_legends: {
    url: `${REMBG_URL}${encodeURIComponent('https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/92f4c42dca2347bf8580d69135bfa1cd_sl_2_512.png')}`,
    name: 'Street Legends',
    rarity: 'jackpot',
  },
};

const SYMBOL_KEYS = Object.keys(SLOT_IMAGES);

type GameType = 'menu' | 'slots' | 'blackjack' | 'roulette';

export default function CasinoScreen() {
  const { name: casinoName, game: initialGame, standalone } = useLocalSearchParams<{ id: string; name: string; game?: string; standalone?: string }>();
  const { player, playerId, setPlayer } = useGameStore();
  
  // Determine initial game based on URL param
  const getInitialGame = (): GameType => {
    if (initialGame === 'slots') return 'slots';
    if (initialGame === 'blackjack') return 'blackjack';
    if (initialGame === 'roulette') return 'roulette';
    return 'menu';
  };
  
  const [currentGame, setCurrentGame] = useState<GameType>(getInitialGame());
  
  // Slots state
  const [slotBet, setSlotBet] = useState(10);
  const [slotReels, setSlotReels] = useState<string[]>(['banana', 'peach', 'eggplant']);
  const [slotSpinning, setSlotSpinning] = useState(false);
  const [slotResult, setSlotResult] = useState<any>(null);
  const spinIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [imagesLoaded, setImagesLoaded] = useState(false);
  const [showSlotsHelp, setShowSlotsHelp] = useState(false);
  
  // Blackjack state
  const [bjBet, setBjBet] = useState(50);
  const [bjGame, setBjGame] = useState<any>(null);
  const [bjLoading, setBjLoading] = useState(false);
  const [bjDealerRevealing, setBjDealerRevealing] = useState(false);
  const [bjShowResult, setBjShowResult] = useState(false);
  const [bjFinalResult, setBjFinalResult] = useState<any>(null);
  
  // Roulette state
  const [selectedChip, setSelectedChip] = useState(25);
  const [placedBets, setPlacedBets] = useState<{[key: string]: number}>({});
  const [rouletteResult, setRouletteResult] = useState<any>(null);
  const [rouletteSpinning, setRouletteSpinning] = useState(false);
  const [wheelRotation, setWheelRotation] = useState(0);
  const wheelAnimationRef = useRef<NodeJS.Timeout | null>(null);

  // American Roulette wheel sequence (clockwise from 0)
  const WHEEL_NUMBERS = [
    '0', '28', '9', '26', '30', '11', '7', '20', '32', '17', '5', '22', '34', '15', '3', '24', '36', '13', '1',
    '00', '27', '10', '25', '29', '12', '8', '19', '31', '18', '6', '21', '33', '16', '4', '23', '35', '14', '2'
  ];

  // Red numbers in American roulette
  const RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
  
  const getNumberColor = (num: string): string => {
    if (num === '0' || num === '00') return 'green';
    return RED_NUMBERS.includes(parseInt(num)) ? 'red' : 'black';
  };

  const getTotalBets = (): number => {
    return Object.values(placedBets).reduce((sum, bet) => sum + bet, 0);
  };

  const placeBet = (betType: string) => {
    if (rouletteSpinning) return;
    const totalAfterBet = getTotalBets() + selectedChip;
    if ((player?.cash || 0) < totalAfterBet) {
      Alert.alert('Not Enough Cash', `You need $${totalAfterBet} total. You have $${player?.cash || 0}`);
      return;
    }
    setPlacedBets(prev => ({
      ...prev,
      [betType]: (prev[betType] || 0) + selectedChip
    }));
  };

  const clearBets = () => {
    if (rouletteSpinning) return;
    setPlacedBets({});
    setRouletteResult(null);
  };

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      if (spinIntervalRef.current) {
        clearInterval(spinIntervalRef.current);
        spinIntervalRef.current = null;
      }
      if (wheelAnimationRef.current) {
        clearInterval(wheelAnimationRef.current);
        wheelAnimationRef.current = null;
      }
    };
  }, []);

  // Preload images when component mounts
  useEffect(() => {
    const preloadImages = async () => {
      try {
        const imagePromises = Object.values(SLOT_IMAGES).map(img => 
          Image.prefetch(img.url).catch(() => {})
        );
        await Promise.all(imagePromises);
        setImagesLoaded(true);
      } catch (e) {
        console.log('Image preload completed with some failures');
        setImagesLoaded(true);
      }
    };
    preloadImages();
  }, []);

  const refreshPlayer = async () => {
    if (!playerId) return;
    try {
      const response = await fetch(`${API_URL}/api/players/${playerId}`);
      const data = await response.json();
      setPlayer(data);
    } catch (e) {
      console.error('Failed to refresh player:', e);
    }
  };

  // Get random symbol for spinning animation - weighted towards common symbols
  const getRandomSymbol = () => {
    // During spin animation, use only common symbols for faster rendering
    const commonSymbols = ['banana', 'eggplant', 'peach', 'coconut'];
    return commonSymbols[Math.floor(Math.random() * commonSymbols.length)];
  };

  // ============== SLOTS ==============
  const playSlots = async () => {
    if (!playerId) {
      Alert.alert('Error', 'Please log in to play');
      return;
    }
    if (slotSpinning) return;
    if ((player?.cash || 0) < slotBet) {
      Alert.alert('Not Enough Cash', `You need $${slotBet} to play. You have $${player?.cash || 0}`);
      return;
    }

    setSlotSpinning(true);
    setSlotResult(null);

    // Play slot machine spin sound
    SFX.slotSpin();

    // Start spinning animation - use shorter interval
    spinIntervalRef.current = setInterval(() => {
      setSlotReels([getRandomSymbol(), getRandomSymbol(), getRandomSymbol()]);
    }, 100);

    try {
      const response = await fetch(`${API_URL}/api/casinos/slots?player_id=${playerId}&bet_amount=${slotBet}`, {
        method: 'POST',
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to play slots');
      }

      // Map backend symbols to our frontend symbol keys
      const mapSymbol = (symbol: string): string => {
        const symbolMap: Record<string, string> = {
          'banana': 'banana',
          'eggplant': 'eggplant',
          'peach': 'peach',
          'coconut': 'coconut',
          'hush_logo': 'hush_logo',
          'appsolut_logo': 'appsolut_logo',
          'street_legends': 'street_legends',
        };
        return symbolMap[symbol] || symbol;
      };

      // Stop spinning after delay and show result
      setTimeout(() => {
        if (spinIntervalRef.current) {
          clearInterval(spinIntervalRef.current);
          spinIntervalRef.current = null;
        }
        
        const finalReels = data.reels ? data.reels.map(mapSymbol) : [getRandomSymbol(), getRandomSymbol(), getRandomSymbol()];
        setSlotReels(finalReels);
        setSlotResult(data);
        setSlotSpinning(false);
        
        // Play win sound if player won money
        if (data.win && data.win > 0) {
          SFX.slotWin();
        }
        
        refreshPlayer();
      }, 1500);

    } catch (e: any) {
      console.error('Slots error:', e);
      if (spinIntervalRef.current) {
        clearInterval(spinIntervalRef.current);
        spinIntervalRef.current = null;
      }
      setSlotSpinning(false);
      Alert.alert('Error', e.message || 'Failed to play slots');
    }
  };

  // ============== BLACKJACK ==============
  const startBlackjack = async () => {
    if (!playerId || bjLoading) return;
    if ((player?.cash || 0) < bjBet) {
      Alert.alert('Not Enough Cash', `You need $${bjBet} to play. You have $${player?.cash || 0}`);
      return;
    }

    setBjLoading(true);
    setBjDealerRevealing(false);
    setBjShowResult(false);
    setBjFinalResult(null);
    
    try {
      const response = await fetch(`${API_URL}/api/casinos/blackjack/start?player_id=${playerId}&bet_amount=${bjBet}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start blackjack');
      }

      setBjGame(data);
      if (data.status !== 'playing') {
        refreshPlayer();
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setBjLoading(false);
    }
  };

  const blackjackAction = async (action: string) => {
    if (!bjGame || bjLoading || bjDealerRevealing) return;

    setBjLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/casinos/blackjack/${bjGame.game_id}/action?action=${action}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Action failed');
      }

      // If game is over (stand, double, or bust), show dealer reveal animation
      if (data.status !== 'playing') {
        setBjDealerRevealing(true);
        setBjFinalResult(data);
        
        // First show dealer's full hand (cards revealed)
        setBjGame({ 
          ...bjGame, 
          dealer_cards: data.dealer_cards,
          dealer_value: data.dealer_value,
          player_cards: data.player_cards,
          player_value: data.player_value,
          status: 'revealing' // Custom status for reveal phase
        });
        
        // After delay, show the result
        setTimeout(() => {
          setBjGame({ ...bjGame, ...data });
          setBjDealerRevealing(false);
          setBjShowResult(true);
          refreshPlayer();
          
          // Reset after showing result
          setTimeout(() => {
            setBjShowResult(false);
          }, 3000);
        }, 2500); // 2.5 second delay to see the cards
      } else {
        // Game continues (hit and not bust)
        setBjGame({ ...bjGame, ...data });
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
      setBjDealerRevealing(false);
    } finally {
      setBjLoading(false);
    }
  };

  // ============== ROULETTE ==============
  // Calculate winnings for a given bet
  const calculateWinnings = (betType: string, betAmount: number, winningNumber: string): number => {
    const num = winningNumber === '00' ? -1 : parseInt(winningNumber);
    const isRed = RED_NUMBERS.includes(num);
    const isBlack = num > 0 && !isRed;
    const isEven = num > 0 && num % 2 === 0;
    const isOdd = num > 0 && num % 2 === 1;
    
    // Single number bet
    if (betType === winningNumber || betType === `num_${winningNumber}`) {
      return betAmount * 35;
    }
    
    // Color bets
    if (betType === 'red' && isRed) return betAmount;
    if (betType === 'black' && isBlack) return betAmount;
    
    // Even/Odd bets
    if (betType === 'even' && isEven) return betAmount;
    if (betType === 'odd' && isOdd) return betAmount;
    
    // 1-18 / 19-36 bets
    if (betType === '1-18' && num >= 1 && num <= 18) return betAmount;
    if (betType === '19-36' && num >= 19 && num <= 36) return betAmount;
    
    // Dozen bets
    if (betType === '1st12' && num >= 1 && num <= 12) return betAmount * 2;
    if (betType === '2nd12' && num >= 13 && num <= 24) return betAmount * 2;
    if (betType === '3rd12' && num >= 25 && num <= 36) return betAmount * 2;
    
    // Column bets (1st column: 1,4,7... 2nd: 2,5,8... 3rd: 3,6,9...)
    if (betType === 'col1' && num > 0 && num % 3 === 1) return betAmount * 2;
    if (betType === 'col2' && num > 0 && num % 3 === 2) return betAmount * 2;
    if (betType === 'col3' && num > 0 && num % 3 === 0) return betAmount * 2;
    
    return 0; // Loss
  };

  const spinRoulette = async () => {
    if (!playerId) {
      Alert.alert('Error', 'Please log in to play');
      return;
    }
    if (rouletteSpinning) return;
    
    const totalBet = getTotalBets();
    if (totalBet === 0) {
      Alert.alert('No Bets Placed', 'Please place at least one bet before spinning');
      return;
    }
    if ((player?.cash || 0) < totalBet) {
      Alert.alert('Not Enough Cash', `You need $${totalBet} to play. You have $${player?.cash || 0}`);
      return;
    }

    setRouletteSpinning(true);
    setRouletteResult(null);

    // Start wheel animation
    let rotation = wheelRotation;
    let speed = 30;
    wheelAnimationRef.current = setInterval(() => {
      rotation += speed;
      setWheelRotation(rotation % 360);
      if (speed > 2) {
        speed *= 0.98; // Slow down gradually
      }
    }, 50);

    try {
      // Call backend to get result
      const response = await fetch(
        `${API_URL}/api/casinos/roulette/spin?player_id=${playerId}`,
        { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bets: placedBets })
        }
      );
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to spin roulette');
      }

      // Let wheel spin for a bit then show result
      setTimeout(() => {
        if (wheelAnimationRef.current) {
          clearInterval(wheelAnimationRef.current);
          wheelAnimationRef.current = null;
        }
        
        // Calculate the final rotation to land on the winning number
        const winningIndex = WHEEL_NUMBERS.indexOf(data.winning_number);
        const anglePerNumber = 360 / WHEEL_NUMBERS.length;
        const finalRotation = (winningIndex * anglePerNumber + 180) % 360; // 180 offset to point to top
        setWheelRotation(finalRotation);
        
        setRouletteResult(data);
        setRouletteSpinning(false);
        refreshPlayer();
        
        // Clear bets after showing result
        setTimeout(() => {
          setPlacedBets({});
        }, 3000);
      }, 3000);
    } catch (e: any) {
      if (wheelAnimationRef.current) {
        clearInterval(wheelAnimationRef.current);
        wheelAnimationRef.current = null;
      }
      setRouletteSpinning(false);
      Alert.alert('Error', e.message || 'Failed to spin roulette');
    }
  };

  const renderMenu = () => (
    <View style={styles.menuContainer}>
      <Text style={styles.casinoTitle}>{casinoName || 'CASINO'}</Text>
      <Text style={styles.balanceText}>Balance: ${player?.cash || 0}</Text>
      
      <View style={styles.gameButtons}>
        <TouchableOpacity style={styles.gameButton} onPress={() => setCurrentGame('slots')}>
          <LinearGradient colors={['#d4af37', '#b8860b', '#d4af37']} style={styles.gameButtonGradient}>
            <Text style={styles.gameButtonIcon}>🎰</Text>
            <Text style={styles.gameButtonText}>SLOTS</Text>
          </LinearGradient>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.gameButton} onPress={() => setCurrentGame('blackjack')}>
          <LinearGradient colors={['#d4af37', '#b8860b', '#d4af37']} style={styles.gameButtonGradient}>
            <Text style={styles.gameButtonIcon}>🃏</Text>
            <Text style={styles.gameButtonText}>BLACKJACK</Text>
          </LinearGradient>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.gameButton} onPress={() => setCurrentGame('roulette')}>
          <LinearGradient colors={['#d4af37', '#b8860b', '#d4af37']} style={styles.gameButtonGradient}>
            <Text style={styles.gameButtonIcon}>🎡</Text>
            <Text style={styles.gameButtonText}>ROULETTE</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderSlotsHelpModal = () => (
    <Modal
      visible={showSlotsHelp}
      transparent
      animationType="fade"
      onRequestClose={() => setShowSlotsHelp(false)}
    >
      <View style={styles.helpOverlay}>
        <View style={styles.helpModal}>
          <View style={styles.helpHeader}>
            <Text style={styles.helpTitle}>🎰 HOW TO PLAY</Text>
            <TouchableOpacity onPress={() => setShowSlotsHelp(false)} style={styles.helpCloseBtn}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
          
          <ScrollView style={styles.helpContent} showsVerticalScrollIndicator={false}>
            {/* Instructions */}
            <View style={styles.helpSection}>
              <Text style={styles.helpSectionTitle}>INSTRUCTIONS</Text>
              <Text style={styles.helpText}>1. Select your bet amount ($10, $50, or $100)</Text>
              <Text style={styles.helpText}>2. Press BET to spin the reels</Text>
              <Text style={styles.helpText}>3. Match symbols on the center line to win!</Text>
            </View>
            
            {/* Payout Chart */}
            <View style={styles.helpSection}>
              <Text style={styles.helpSectionTitle}>PAYOUT CHART</Text>
              
              {/* Jackpot Symbols */}
              <View style={styles.payoutCategory}>
                <Text style={styles.payoutCategoryTitle}>💎 JACKPOT SYMBOLS</Text>
                
                <View style={styles.payoutRow}>
                  <View style={styles.payoutSymbolContainer}>
                    <Image source={{ uri: SLOT_IMAGES.appsolut_logo.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>AppSolut Group</Text>
                    <Text style={styles.payoutJackpot}>3x = 100x BET (JACKPOT!)</Text>
                    <Text style={styles.payoutSmall}>2x = 10x BET</Text>
                  </View>
                </View>
                
                <View style={styles.payoutRow}>
                  <View style={styles.payoutSymbolContainer}>
                    <Image source={{ uri: SLOT_IMAGES.street_legends.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>Street Legends</Text>
                    <Text style={styles.payoutJackpot}>3x = 100x BET (JACKPOT!)</Text>
                    <Text style={styles.payoutSmall}>2x = 10x BET</Text>
                  </View>
                </View>
              </View>
              
              {/* Rare Symbol */}
              <View style={styles.payoutCategory}>
                <Text style={[styles.payoutCategoryTitle, { color: '#9b59b6' }]}>💜 RARE SYMBOL</Text>
                
                <View style={styles.payoutRow}>
                  <View style={[styles.payoutSymbolContainer, { borderColor: '#9b59b6' }]}>
                    <Image source={{ uri: SLOT_IMAGES.hush_logo.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>Hush Music Ent</Text>
                    <Text style={styles.payoutRare}>3x = 25x BET (BIG WIN!)</Text>
                    <Text style={styles.payoutSmall}>2x = 5x BET</Text>
                  </View>
                </View>
              </View>
              
              {/* Common Symbols */}
              <View style={styles.payoutCategory}>
                <Text style={[styles.payoutCategoryTitle, { color: '#27ae60' }]}>💚 COMMON SYMBOLS</Text>
                
                <View style={styles.payoutRow}>
                  <View style={[styles.payoutSymbolContainer, { borderColor: '#27ae60' }]}>
                    <Image source={{ uri: SLOT_IMAGES.coconut.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>Coconut</Text>
                    <Text style={styles.payoutCommon}>3x = 8x BET</Text>
                    <Text style={styles.payoutSmall}>2x = 2x BET</Text>
                  </View>
                </View>
                
                <View style={styles.payoutRow}>
                  <View style={[styles.payoutSymbolContainer, { borderColor: '#27ae60' }]}>
                    <Image source={{ uri: SLOT_IMAGES.peach.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>Peach</Text>
                    <Text style={styles.payoutCommon}>3x = 6x BET</Text>
                    <Text style={styles.payoutSmall}>2x = 1.5x BET</Text>
                  </View>
                </View>
                
                <View style={styles.payoutRow}>
                  <View style={[styles.payoutSymbolContainer, { borderColor: '#27ae60' }]}>
                    <Image source={{ uri: SLOT_IMAGES.eggplant.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>Eggplant</Text>
                    <Text style={styles.payoutCommon}>3x = 5x BET</Text>
                    <Text style={styles.payoutSmall}>2x = 1.5x BET</Text>
                  </View>
                </View>
                
                <View style={styles.payoutRow}>
                  <View style={[styles.payoutSymbolContainer, { borderColor: '#27ae60' }]}>
                    <Image source={{ uri: SLOT_IMAGES.banana.url }} style={styles.payoutImage} resizeMode="contain" />
                  </View>
                  <View style={styles.payoutInfo}>
                    <Text style={styles.payoutName}>Banana</Text>
                    <Text style={styles.payoutCommon}>3x = 5x BET</Text>
                    <Text style={styles.payoutSmall}>2x = 1.5x BET</Text>
                  </View>
                </View>
              </View>
              
              {/* No Match */}
              <View style={styles.payoutCategory}>
                <Text style={[styles.payoutCategoryTitle, { color: '#e74c3c' }]}>❌ NO MATCH</Text>
                <Text style={styles.payoutLoss}>No matching symbols = Lose bet</Text>
              </View>
            </View>
          </ScrollView>
          
          <TouchableOpacity style={styles.helpCloseButton} onPress={() => setShowSlotsHelp(false)}>
            <Text style={styles.helpCloseButtonText}>GOT IT!</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  const renderSlots = () => (
    <View style={styles.slotsContainer}>
      {/* Help Button */}
      <TouchableOpacity style={styles.helpButton} onPress={() => setShowSlotsHelp(true)}>
        <Text style={styles.helpButtonText}>?</Text>
      </TouchableOpacity>
      
      {/* Help Modal */}
      {renderSlotsHelpModal()}
      
      <View style={styles.slotsHeader}>
        <LinearGradient colors={['#1a1a1a', '#0d0d0d']} style={styles.slotsHeaderBg}>
          <Text style={styles.slotsTitle}>🎰 SLOTS 🎰</Text>
        </LinearGradient>
      </View>
      
      <View style={styles.reelsContainer}>
        <LinearGradient colors={['#2a1a0a', '#1a0a00', '#2a1a0a']} style={styles.reelsBg}>
          <View style={styles.reels}>
            {slotReels.map((symbol, index) => {
              const symbolData = SLOT_IMAGES[symbol];
              const isRare = symbolData?.rarity === 'rare';
              const isJackpot = symbolData?.rarity === 'jackpot';
              
              return (
                <View 
                  key={index} 
                  style={[
                    styles.reel, 
                    slotSpinning && styles.reelSpinning,
                    isJackpot && styles.reelJackpot,
                    isRare && styles.reelRare,
                  ]}
                >
                  {symbolData ? (
                    <Image 
                      source={{ uri: symbolData.url }}
                      style={styles.reelImage}
                      resizeMode="contain"
                    />
                  ) : (
                    <Text style={styles.reelEmoji}>🎰</Text>
                  )}
                </View>
              );
            })}
          </View>
        </LinearGradient>
      </View>

      {/* Symbol Legend */}
      <View style={styles.legendContainer}>
        <Text style={styles.legendTitle}>SYMBOLS</Text>
        <View style={styles.legendRow}>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: '#FFD700' }]} />
            <Text style={styles.legendText}>Jackpot (x100)</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: '#9b59b6' }]} />
            <Text style={styles.legendText}>Rare (x25)</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: '#27ae60' }]} />
            <Text style={styles.legendText}>Common (x5)</Text>
          </View>
        </View>
      </View>
      
      {slotResult && (
        <View style={[styles.resultContainer, slotResult.result_type === 'loss' ? styles.lossResult : styles.winResult]}>
          <Text style={styles.resultText}>
            {slotResult.result_type === 'jackpot' ? '🎉 JACKPOT! 🎉' :
             slotResult.result_type === 'big_win' ? '🎊 BIG WIN! 🎊' :
             slotResult.result_type === 'small_win' ? '💰 Winner!' :
             '😔 No luck this time'}
          </Text>
          <Text style={styles.resultAmount}>
            {slotResult.net_change >= 0 ? `+$${slotResult.winnings}` : `-$${slotBet}`}
          </Text>
        </View>
      )}
      
      <Text style={styles.balanceSmall}>Balance: ${player?.cash || 0}</Text>
      
      <View style={styles.betButtons}>
        {[10, 50, 100].map((amount) => (
          <TouchableOpacity
            key={amount}
            style={[styles.betButton, slotBet === amount && styles.betButtonActive]}
            onPress={() => !slotSpinning && setSlotBet(amount)}
            disabled={slotSpinning}
          >
            <Text style={[styles.betButtonText, slotBet === amount && styles.betButtonTextActive]}>
              ${amount}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      
      <TouchableOpacity 
        style={[styles.spinButton, slotSpinning && styles.spinButtonDisabled]}
        onPress={playSlots}
        disabled={slotSpinning}
      >
        <LinearGradient colors={slotSpinning ? ['#666', '#444', '#666'] : ['#e74c3c', '#c0392b', '#e74c3c']} style={styles.spinButtonGradient}>
          {slotSpinning ? (
            <View style={styles.spinningContainer}>
              <ActivityIndicator color="#fff" size="small" />
              <Text style={styles.spinningText}>SPINNING...</Text>
            </View>
          ) : (
            <Text style={styles.spinButtonText}>🎰 BET ${slotBet}</Text>
          )}
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );

  const renderCard = (card: any, hidden: boolean = false) => {
    if (hidden || card.suit === 'hidden') {
      return (
        <View style={[styles.card, styles.cardHidden]}>
          <Text style={styles.cardBack}>?</Text>
        </View>
      );
    }
    
    const isRed = card.suit === 'hearts' || card.suit === 'diamonds';
    const suitSymbol = { hearts: '♥', diamonds: '♦', clubs: '♣', spades: '♠' }[card.suit] || '?';
    
    return (
      <View style={styles.card}>
        <Text style={[styles.cardRank, isRed && styles.cardRed]}>{card.rank}</Text>
        <Text style={[styles.cardSuit, isRed && styles.cardRed]}>{suitSymbol}</Text>
      </View>
    );
  };

  const renderBlackjack = () => {
    const isGameActive = bjGame && (bjGame.status === 'playing' || bjGame.status === 'revealing' || bjDealerRevealing);
    const showDealerValue = bjGame?.status !== 'playing' || bjDealerRevealing;
    
    return (
      <ScrollView style={styles.bjContainer} contentContainerStyle={styles.bjContent}>
        <Text style={styles.gameTitle}>BLACKJACK</Text>
        <Text style={styles.balanceSmall}>Balance: ${player?.cash || 0}</Text>
        
        {!isGameActive ? (
          <View style={styles.bjSetup}>
            <Text style={styles.bjBetLabel}>Select Bet Amount</Text>
            <View style={styles.bjBetButtons}>
              {[25, 50, 100, 250, 500].map((amount) => (
                <TouchableOpacity
                  key={amount}
                  style={[styles.bjBetBtn, bjBet === amount && styles.bjBetBtnActive]}
                  onPress={() => setBjBet(amount)}
                >
                  <Text style={[styles.bjBetBtnText, bjBet === amount && styles.bjBetBtnTextActive]}>
                    ${amount}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            
            {bjGame && bjGame.status !== 'playing' && bjShowResult && (
              <View style={[styles.bjResultBox, bjGame.winnings >= 0 ? styles.winResult : styles.lossResult]}>
                <Text style={styles.bjResultText}>{bjGame.message}</Text>
                <Text style={styles.bjResultAmount}>
                  {bjGame.winnings >= 0 ? `+$${bjGame.winnings}` : `-$${Math.abs(bjGame.winnings)}`}
                </Text>
              </View>
            )}
            
            <TouchableOpacity 
              style={styles.dealButton}
              onPress={startBlackjack}
              disabled={bjLoading}
            >
              <LinearGradient colors={['#27ae60', '#1e8449', '#27ae60']} style={styles.dealButtonGradient}>
                {bjLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.dealButtonText}>DEAL</Text>}
              </LinearGradient>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.bjTable}>
            {/* Dealer's Hand */}
            <View style={styles.bjHand}>
              <Text style={styles.bjHandLabel}>
                DEALER {showDealerValue && bjGame.dealer_value ? `(${bjGame.dealer_value})` : ''}
              </Text>
              <View style={styles.bjCards}>
                {bjGame.dealer_cards?.map((card: any, i: number) => (
                  <View key={i} style={styles.bjCardWrapper}>
                    {renderCard(card)}
                    {bjDealerRevealing && i === bjGame.dealer_cards.length - 1 && (
                      <View style={styles.cardRevealGlow} />
                    )}
                  </View>
                ))}
              </View>
            </View>
            
            {/* Dealer Revealing Message */}
            {bjDealerRevealing && (
              <View style={styles.revealingMessage}>
                <Text style={styles.revealingText}>Dealer reveals...</Text>
              </View>
            )}
            
            {/* Result Display (shown during reveal phase) */}
            {bjFinalResult && bjDealerRevealing && (
              <View style={[styles.bjInGameResult, bjFinalResult.winnings >= 0 ? styles.winResult : styles.lossResult]}>
                <Text style={styles.bjResultText}>{bjFinalResult.message}</Text>
                <Text style={styles.bjResultAmount}>
                  {bjFinalResult.winnings >= 0 ? `+$${bjFinalResult.winnings}` : `-$${Math.abs(bjFinalResult.winnings)}`}
                </Text>
              </View>
            )}
            
            {/* Player's Hand */}
            <View style={styles.bjHand}>
              <Text style={styles.bjHandLabel}>YOUR HAND ({bjGame.player_value})</Text>
              <View style={styles.bjCards}>
                {bjGame.player_cards?.map((card: any, i: number) => (
                  <View key={i}>{renderCard(card)}</View>
                ))}
              </View>
            </View>
            
            {/* Action Buttons - only show when game is active and not revealing */}
            {bjGame.status === 'playing' && !bjDealerRevealing && (
              <View style={styles.bjActions}>
                <TouchableOpacity 
                  style={styles.bjActionBtn} 
                  onPress={() => blackjackAction('hit')}
                  disabled={bjLoading}
                >
                  <Text style={styles.bjActionText}>HIT</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={styles.bjActionBtn} 
                  onPress={() => blackjackAction('stand')}
                  disabled={bjLoading}
                >
                  <Text style={styles.bjActionText}>STAND</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.bjActionBtn, styles.bjDoubleBtn]} 
                  onPress={() => blackjackAction('double')}
                  disabled={bjLoading || (player?.cash || 0) < bjBet * 2}
                >
                  <Text style={styles.bjActionText}>DOUBLE</Text>
                </TouchableOpacity>
              </View>
            )}
            
            {/* New Hand Button - shown after result */}
            {bjDealerRevealing && (
              <View style={styles.bjNewHandContainer}>
                <ActivityIndicator color="#d4af37" size="small" />
                <Text style={styles.bjNewHandHint}>Returning to bet screen...</Text>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    );
  };

  const renderRoulette = () => {
    const renderChip = (betType: string, small: boolean = false) => {
      const amount = placedBets[betType];
      if (!amount) return null;
      return (
        <View style={[styles.placedChip, small && styles.placedChipSmall]}>
          <Text style={[styles.placedChipText, small && styles.placedChipTextSmall]}>${amount}</Text>
        </View>
      );
    };

    const renderNumberCell = (num: string) => {
      const color = getNumberColor(num);
      const betKey = `num_${num}`;
      return (
        <TouchableOpacity
          key={num}
          style={[
            styles.tableCell,
            color === 'red' && styles.tableCellRed,
            color === 'black' && styles.tableCellBlack,
            color === 'green' && styles.tableCellGreen,
          ]}
          onPress={() => placeBet(betKey)}
          disabled={rouletteSpinning}
        >
          <Text style={styles.tableCellText}>{num}</Text>
          {renderChip(betKey, true)}
        </TouchableOpacity>
      );
    };

    return (
      <ScrollView style={styles.rouletteContainer} contentContainerStyle={styles.rouletteScrollContent}>
        {/* Header */}
        <View style={styles.rouletteHeader}>
          <Text style={styles.rouletteTitle}>🎰 AMERICAN ROULETTE</Text>
          <Text style={styles.rouletteBalance}>Balance: ${player?.cash || 0}</Text>
          {getTotalBets() > 0 && (
            <Text style={styles.rouletteTotalBet}>Total Bet: ${getTotalBets()}</Text>
          )}
        </View>

        {/* Roulette Wheel */}
        <View style={styles.wheelContainer}>
          <View style={[styles.wheel, { transform: [{ rotate: `${wheelRotation}deg` }] }]}>
            {WHEEL_NUMBERS.map((num, index) => {
              const angle = (index * 360) / WHEEL_NUMBERS.length;
              const color = getNumberColor(num);
              return (
                <View
                  key={num}
                  style={[
                    styles.wheelNumber,
                    { transform: [{ rotate: `${angle}deg` }, { translateY: -65 }] },
                  ]}
                >
                  <View style={[
                    styles.wheelNumberInner,
                    color === 'red' && styles.wheelNumberRed,
                    color === 'black' && styles.wheelNumberBlack,
                    color === 'green' && styles.wheelNumberGreen,
                  ]}>
                    <Text style={[styles.wheelNumberText, { transform: [{ rotate: `-${angle + wheelRotation}deg` }] }]}>
                      {num}
                    </Text>
                  </View>
                </View>
              );
            })}
            <View style={styles.wheelCenter}>
              <Text style={styles.wheelCenterText}>🎰</Text>
            </View>
          </View>
          <View style={styles.wheelPointer}>
            <Text style={styles.wheelPointerText}>▼</Text>
          </View>
        </View>

        {/* Result Display */}
        {rouletteResult && (
          <View style={[styles.rouletteResultBox, rouletteResult.total_winnings > 0 ? styles.rouletteWin : styles.rouletteLoss]}>
            <View style={[
              styles.resultNumberBadge,
              getNumberColor(rouletteResult.winning_number) === 'red' && styles.resultBadgeRed,
              getNumberColor(rouletteResult.winning_number) === 'black' && styles.resultBadgeBlack,
              getNumberColor(rouletteResult.winning_number) === 'green' && styles.resultBadgeGreen,
            ]}>
              <Text style={styles.resultNumberText}>{rouletteResult.winning_number}</Text>
            </View>
            <Text style={styles.rouletteResultText}>
              {rouletteResult.total_winnings > 0 ? `🎉 Won $${rouletteResult.total_winnings}!` : '😔 No win'}
            </Text>
          </View>
        )}

        {/* Chip Selection */}
        <View style={styles.chipSelector}>
          <Text style={styles.chipSelectorTitle}>SELECT CHIP</Text>
          <View style={styles.chipRow}>
            {[25, 50, 100, 500].map((value) => (
              <TouchableOpacity
                key={value}
                style={[styles.chip, selectedChip === value && styles.chipSelected]}
                onPress={() => setSelectedChip(value)}
                disabled={rouletteSpinning}
              >
                <Text style={[styles.chipValue, selectedChip === value && styles.chipValueSelected]}>${value}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Betting Table - Green Felt */}
        <View style={styles.bettingTable}>
          {/* 0 and 00 */}
          <View style={styles.zeroRow}>
            {renderNumberCell('0')}
            {renderNumberCell('00')}
          </View>

          {/* Main Number Grid - 3 columns x 12 rows */}
          <View style={styles.numberGrid}>
            {[...Array(12)].map((_, rowIndex) => (
              <View key={rowIndex} style={styles.numberRow}>
                {[1, 2, 3].map((col) => {
                  const num = (rowIndex * 3) + col;
                  return renderNumberCell(String(num));
                })}
              </View>
            ))}
          </View>

          {/* Column bets (2 to 1) */}
          <View style={styles.columnBets}>
            <TouchableOpacity style={styles.columnBet} onPress={() => placeBet('col1')} disabled={rouletteSpinning}>
              <Text style={styles.columnBetText}>2:1</Text>
              {renderChip('col1', true)}
            </TouchableOpacity>
            <TouchableOpacity style={styles.columnBet} onPress={() => placeBet('col2')} disabled={rouletteSpinning}>
              <Text style={styles.columnBetText}>2:1</Text>
              {renderChip('col2', true)}
            </TouchableOpacity>
            <TouchableOpacity style={styles.columnBet} onPress={() => placeBet('col3')} disabled={rouletteSpinning}>
              <Text style={styles.columnBetText}>2:1</Text>
              {renderChip('col3', true)}
            </TouchableOpacity>
          </View>

          {/* Dozen bets */}
          <View style={styles.dozenBets}>
            <TouchableOpacity style={styles.dozenBet} onPress={() => placeBet('1st12')} disabled={rouletteSpinning}>
              <Text style={styles.dozenBetText}>1st 12</Text>
              {renderChip('1st12', true)}
            </TouchableOpacity>
            <TouchableOpacity style={styles.dozenBet} onPress={() => placeBet('2nd12')} disabled={rouletteSpinning}>
              <Text style={styles.dozenBetText}>2nd 12</Text>
              {renderChip('2nd12', true)}
            </TouchableOpacity>
            <TouchableOpacity style={styles.dozenBet} onPress={() => placeBet('3rd12')} disabled={rouletteSpinning}>
              <Text style={styles.dozenBetText}>3rd 12</Text>
              {renderChip('3rd12', true)}
            </TouchableOpacity>
          </View>

          {/* Outside bets - Row 1 */}
          <View style={styles.outsideBets}>
            <TouchableOpacity style={styles.outsideBet} onPress={() => placeBet('1-18')} disabled={rouletteSpinning}>
              <Text style={styles.outsideBetText}>1-18</Text>
              {renderChip('1-18', true)}
            </TouchableOpacity>
            <TouchableOpacity style={[styles.outsideBet, styles.outsideBetEven]} onPress={() => placeBet('even')} disabled={rouletteSpinning}>
              <Text style={styles.outsideBetText}>EVEN</Text>
              {renderChip('even', true)}
            </TouchableOpacity>
            <TouchableOpacity style={[styles.outsideBet, styles.outsideBetRed]} onPress={() => placeBet('red')} disabled={rouletteSpinning}>
              <Text style={styles.outsideBetText}>RED</Text>
              {renderChip('red', true)}
            </TouchableOpacity>
            <TouchableOpacity style={[styles.outsideBet, styles.outsideBetBlack]} onPress={() => placeBet('black')} disabled={rouletteSpinning}>
              <Text style={styles.outsideBetText}>BLACK</Text>
              {renderChip('black', true)}
            </TouchableOpacity>
            <TouchableOpacity style={[styles.outsideBet, styles.outsideBetOdd]} onPress={() => placeBet('odd')} disabled={rouletteSpinning}>
              <Text style={styles.outsideBetText}>ODD</Text>
              {renderChip('odd', true)}
            </TouchableOpacity>
            <TouchableOpacity style={styles.outsideBet} onPress={() => placeBet('19-36')} disabled={rouletteSpinning}>
              <Text style={styles.outsideBetText}>19-36</Text>
              {renderChip('19-36', true)}
            </TouchableOpacity>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.rouletteActions}>
          <TouchableOpacity 
            style={[styles.clearBetsBtn, rouletteSpinning && styles.btnDisabled]}
            onPress={clearBets}
            disabled={rouletteSpinning}
          >
            <Text style={styles.clearBetsBtnText}>CLEAR BETS</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={[styles.spinRouletteBtn, (rouletteSpinning || getTotalBets() === 0) && styles.btnDisabled]}
            onPress={spinRoulette}
            disabled={rouletteSpinning || getTotalBets() === 0}
          >
            <LinearGradient 
              colors={rouletteSpinning ? ['#666', '#444'] : ['#c0392b', '#e74c3c', '#c0392b']} 
              style={styles.spinRouletteBtnGradient}
            >
              {rouletteSpinning ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.spinRouletteBtnText}>SPIN</Text>
              )}
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Payouts Info */}
        <View style={styles.payoutsInfo}>
          <Text style={styles.payoutsTitle}>PAYOUTS</Text>
          <Text style={styles.payoutText}>Single Number: 35 to 1</Text>
          <Text style={styles.payoutText}>Dozens/Columns: 2 to 1</Text>
          <Text style={styles.payoutText}>Red/Black/Odd/Even/1-18/19-36: 1 to 1</Text>
        </View>
      </ScrollView>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={() => {
            if (currentGame === 'menu') {
              router.back();
            } else if (standalone === 'true' && initialGame) {
              // If opened directly to a game from options, go back to previous screen
              router.back();
            } else {
              setCurrentGame('menu');
            }
          }}
        >
          <Ionicons name="arrow-back" size={24} color="#d4af37" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {currentGame === 'menu' ? (casinoName || 'CASINO') : currentGame.toUpperCase()}
        </Text>
        <View style={styles.headerSpacer} />
      </View>
      
      {currentGame === 'menu' && renderMenu()}
      {currentGame === 'slots' && renderSlots()}
      {currentGame === 'blackjack' && renderBlackjack()}
      {currentGame === 'roulette' && renderRoulette()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#d4af37',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    color: '#d4af37',
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  headerSpacer: {
    width: 40,
  },
  
  // Menu styles
  menuContainer: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
  },
  casinoTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#d4af37',
    marginBottom: 8,
    letterSpacing: 3,
  },
  balanceText: {
    color: '#fff',
    fontSize: 18,
    marginBottom: 40,
  },
  balanceSmall: {
    color: '#888',
    fontSize: 14,
    marginBottom: 16,
  },
  gameButtons: {
    width: '100%',
    gap: 20,
  },
  gameButton: {
    width: '100%',
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: '#d4af37',
  },
  gameButtonGradient: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  gameButtonIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  gameButtonText: {
    color: '#0a0a0a',
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 3,
  },
  
  // Slots styles
  slotsContainer: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
  },
  slotsHeader: {
    width: '100%',
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 3,
    borderColor: '#d4af37',
    marginBottom: 20,
  },
  slotsHeaderBg: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  slotsTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#d4af37',
    letterSpacing: 4,
    textShadowColor: '#d4af37',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  reelsContainer: {
    width: '100%',
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 4,
    borderColor: '#d4af37',
    marginBottom: 20,
  },
  reelsBg: {
    padding: 16,
  },
  reels: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    height: 140,
    backgroundColor: 'rgba(0,0,0,0.7)',
    borderRadius: 12,
    paddingHorizontal: 8,
  },
  reel: {
    width: 90,
    height: 100,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#27ae60',
    shadowColor: '#27ae60',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 5,
    overflow: 'hidden',
  },
  reelSpinning: {
    borderColor: '#fff',
    backgroundColor: '#2a2a2a',
  },
  reelJackpot: {
    borderColor: '#FFD700',
    shadowColor: '#FFD700',
    backgroundColor: '#2a2a1a',
  },
  reelRare: {
    borderColor: '#9b59b6',
    shadowColor: '#9b59b6',
    backgroundColor: '#2a1a2a',
  },
  reelEmoji: {
    fontSize: 56,
  },
  reelImage: {
    width: 70,
    height: 70,
  },
  legendContainer: {
    width: '100%',
    paddingVertical: 10,
    paddingHorizontal: 12,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 8,
    marginBottom: 12,
  },
  legendTitle: {
    color: '#d4af37',
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 6,
  },
  legendRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    color: '#888',
    fontSize: 10,
  },
  resultContainer: {
    width: '100%',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    alignItems: 'center',
  },
  winResult: {
    backgroundColor: 'rgba(39, 174, 96, 0.3)',
    borderWidth: 2,
    borderColor: '#27ae60',
  },
  lossResult: {
    backgroundColor: 'rgba(231, 76, 60, 0.3)',
    borderWidth: 2,
    borderColor: '#e74c3c',
  },
  resultText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  resultAmount: {
    color: '#d4af37',
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 4,
  },
  spinningContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  spinningText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  betButtons: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 20,
  },
  betButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#d4af37',
  },
  betButtonActive: {
    backgroundColor: '#d4af37',
  },
  betButtonText: {
    color: '#d4af37',
    fontSize: 16,
    fontWeight: 'bold',
  },
  betButtonTextActive: {
    color: '#0a0a0a',
  },
  spinButton: {
    width: '80%',
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 3,
    borderColor: '#d4af37',
  },
  spinButtonDisabled: {
    opacity: 0.6,
  },
  spinButtonGradient: {
    paddingVertical: 18,
    alignItems: 'center',
  },
  spinButtonText: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
    letterSpacing: 4,
  },
  
  // Blackjack styles
  bjContainer: {
    flex: 1,
  },
  bjContent: {
    padding: 20,
    alignItems: 'center',
  },
  gameTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#d4af37',
    marginBottom: 8,
    letterSpacing: 3,
  },
  bjSetup: {
    width: '100%',
    alignItems: 'center',
  },
  bjBetLabel: {
    color: '#888',
    fontSize: 14,
    marginBottom: 12,
    marginTop: 16,
  },
  bjBetButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 10,
  },
  bjBetBtn: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    borderWidth: 2,
    borderColor: '#333',
  },
  bjBetBtnActive: {
    borderColor: '#d4af37',
    backgroundColor: '#2a2a2a',
  },
  bjBetBtnText: {
    color: '#888',
    fontSize: 16,
    fontWeight: 'bold',
  },
  bjBetBtnTextActive: {
    color: '#d4af37',
  },
  bjResultBox: {
    width: '100%',
    padding: 16,
    borderRadius: 12,
    marginVertical: 20,
    alignItems: 'center',
  },
  bjInGameResult: {
    width: '90%',
    padding: 16,
    borderRadius: 12,
    marginVertical: 10,
    alignItems: 'center',
  },
  bjResultText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  bjResultAmount: {
    color: '#d4af37',
    fontSize: 22,
    fontWeight: 'bold',
    marginTop: 4,
  },
  revealingMessage: {
    paddingVertical: 10,
    alignItems: 'center',
  },
  revealingText: {
    color: '#d4af37',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  bjCardWrapper: {
    position: 'relative',
  },
  cardRevealGlow: {
    position: 'absolute',
    top: -4,
    left: -4,
    right: -4,
    bottom: -4,
    borderRadius: 10,
    borderWidth: 3,
    borderColor: '#d4af37',
    shadowColor: '#d4af37',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 10,
  },
  bjNewHandContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 16,
  },
  bjNewHandHint: {
    color: '#888',
    fontSize: 12,
  },
  dealButton: {
    width: '60%',
    borderRadius: 12,
    overflow: 'hidden',
    marginTop: 20,
  },
  dealButtonGradient: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  dealButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  bjTable: {
    width: '100%',
    alignItems: 'center',
    gap: 20,
  },
  bjHand: {
    width: '100%',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
  },
  bjHandLabel: {
    color: '#888',
    fontSize: 12,
    marginBottom: 12,
    letterSpacing: 2,
  },
  bjCards: {
    flexDirection: 'row',
    gap: 8,
  },
  card: {
    width: 60,
    height: 85,
    backgroundColor: '#fff',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#333',
  },
  cardHidden: {
    backgroundColor: '#1a4d1a',
  },
  cardBack: {
    color: '#fff',
    fontSize: 32,
    fontWeight: 'bold',
  },
  cardRank: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#000',
  },
  cardSuit: {
    fontSize: 24,
    color: '#000',
  },
  cardRed: {
    color: '#e74c3c',
  },
  bjActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 10,
  },
  bjActionBtn: {
    paddingHorizontal: 24,
    paddingVertical: 14,
    backgroundColor: '#d4af37',
    borderRadius: 8,
  },
  bjDoubleBtn: {
    backgroundColor: '#9b59b6',
  },
  bjActionText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  
  // Roulette styles - American Roulette
  rouletteContainer: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  rouletteScrollContent: {
    padding: 12,
    alignItems: 'center',
    paddingBottom: 40,
  },
  rouletteHeader: {
    alignItems: 'center',
    marginBottom: 10,
  },
  rouletteTitle: {
    color: '#d4af37',
    fontSize: 22,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  rouletteBalance: {
    color: '#fff',
    fontSize: 14,
    marginTop: 4,
  },
  rouletteTotalBet: {
    color: '#f39c12',
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 4,
  },
  
  // Wheel styles
  wheelContainer: {
    width: 180,
    height: 180,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 15,
  },
  wheel: {
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: '#1a1a1a',
    borderWidth: 4,
    borderColor: '#d4af37',
    justifyContent: 'center',
    alignItems: 'center',
  },
  wheelNumber: {
    position: 'absolute',
    width: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  wheelNumberInner: {
    width: 18,
    height: 18,
    borderRadius: 9,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#d4af37',
  },
  wheelNumberRed: {
    backgroundColor: '#c0392b',
  },
  wheelNumberBlack: {
    backgroundColor: '#1a1a1a',
  },
  wheelNumberGreen: {
    backgroundColor: '#27ae60',
  },
  wheelNumberText: {
    color: '#fff',
    fontSize: 7,
    fontWeight: 'bold',
  },
  wheelCenter: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#0d0d0d',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#d4af37',
  },
  wheelCenterText: {
    fontSize: 24,
  },
  wheelPointer: {
    position: 'absolute',
    top: -5,
  },
  wheelPointerText: {
    color: '#d4af37',
    fontSize: 24,
    textShadowColor: '#000',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  
  // Result styles
  rouletteResultBox: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
    gap: 12,
  },
  rouletteWin: {
    backgroundColor: 'rgba(39, 174, 96, 0.3)',
    borderWidth: 2,
    borderColor: '#27ae60',
  },
  rouletteLoss: {
    backgroundColor: 'rgba(231, 76, 60, 0.3)',
    borderWidth: 2,
    borderColor: '#e74c3c',
  },
  resultNumberBadge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  resultBadgeRed: {
    backgroundColor: '#c0392b',
  },
  resultBadgeBlack: {
    backgroundColor: '#2c3e50',
  },
  resultBadgeGreen: {
    backgroundColor: '#27ae60',
  },
  resultNumberText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  rouletteResultText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  
  // Chip Selector
  chipSelector: {
    alignItems: 'center',
    marginBottom: 12,
  },
  chipSelectorTitle: {
    color: '#888',
    fontSize: 11,
    letterSpacing: 1,
    marginBottom: 6,
  },
  chipRow: {
    flexDirection: 'row',
    gap: 8,
  },
  chip: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#555',
  },
  chipSelected: {
    borderColor: '#d4af37',
    backgroundColor: '#2a2a1a',
  },
  chipValue: {
    color: '#888',
    fontSize: 11,
    fontWeight: 'bold',
  },
  chipValueSelected: {
    color: '#d4af37',
  },
  
  // Betting Table
  bettingTable: {
    backgroundColor: '#0d5f2d',
    borderRadius: 10,
    padding: 8,
    borderWidth: 3,
    borderColor: '#8B4513',
    width: '100%',
    maxWidth: 360,
  },
  zeroRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 4,
    marginBottom: 4,
  },
  numberGrid: {
    alignItems: 'center',
  },
  numberRow: {
    flexDirection: 'row',
    gap: 2,
    marginBottom: 2,
  },
  tableCell: {
    width: 34,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#fff',
    borderRadius: 3,
  },
  tableCellRed: {
    backgroundColor: '#c0392b',
  },
  tableCellBlack: {
    backgroundColor: '#1a1a1a',
  },
  tableCellGreen: {
    backgroundColor: '#27ae60',
  },
  tableCellText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  placedChip: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#d4af37',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#8B4513',
    zIndex: 10,
  },
  placedChipSmall: {
    width: 20,
    height: 20,
    borderRadius: 10,
  },
  placedChipText: {
    color: '#000',
    fontSize: 8,
    fontWeight: 'bold',
  },
  placedChipTextSmall: {
    fontSize: 6,
  },
  
  // Column and Dozen Bets
  columnBets: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 2,
    marginTop: 4,
  },
  columnBet: {
    width: 34,
    height: 24,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#fff',
    borderRadius: 3,
  },
  columnBetText: {
    color: '#fff',
    fontSize: 9,
    fontWeight: 'bold',
  },
  dozenBets: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 2,
    marginTop: 4,
  },
  dozenBet: {
    flex: 1,
    maxWidth: 110,
    height: 26,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#fff',
    borderRadius: 3,
  },
  dozenBetText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  
  // Outside Bets
  outsideBets: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 2,
    marginTop: 4,
  },
  outsideBet: {
    width: 54,
    height: 26,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#fff',
    borderRadius: 3,
  },
  outsideBetRed: {
    backgroundColor: '#c0392b',
  },
  outsideBetBlack: {
    backgroundColor: '#1a1a1a',
  },
  outsideBetEven: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  outsideBetOdd: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  outsideBetText: {
    color: '#fff',
    fontSize: 9,
    fontWeight: 'bold',
  },
  
  // Action Buttons
  rouletteActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
    marginBottom: 12,
  },
  clearBetsBtn: {
    paddingHorizontal: 24,
    paddingVertical: 14,
    backgroundColor: '#444',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#666',
  },
  clearBetsBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  spinRouletteBtn: {
    flex: 1,
    borderRadius: 8,
    overflow: 'hidden',
  },
  spinRouletteBtnGradient: {
    paddingVertical: 14,
    paddingHorizontal: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  spinRouletteBtnText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  btnDisabled: {
    opacity: 0.5,
  },
  
  // Payouts Info
  payoutsInfo: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    width: '100%',
    maxWidth: 360,
  },
  payoutsTitle: {
    color: '#d4af37',
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 6,
  },
  payoutText: {
    color: '#888',
    fontSize: 10,
    marginBottom: 2,
  },
  
  // Help Button & Modal Styles
  helpButton: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#d4af37',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
    shadowColor: '#d4af37',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 6,
    elevation: 5,
  },
  helpButtonText: {
    color: '#000',
    fontSize: 20,
    fontWeight: 'bold',
  },
  helpOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  helpModal: {
    width: '100%',
    maxHeight: '85%',
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    borderWidth: 3,
    borderColor: '#d4af37',
    overflow: 'hidden',
  },
  helpHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#0d0d0d',
    borderBottomWidth: 2,
    borderBottomColor: '#d4af37',
  },
  helpTitle: {
    color: '#d4af37',
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  helpCloseBtn: {
    padding: 4,
  },
  helpContent: {
    padding: 16,
    maxHeight: 400,
  },
  helpSection: {
    marginBottom: 20,
  },
  helpSectionTitle: {
    color: '#d4af37',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
    letterSpacing: 1,
  },
  helpText: {
    color: '#ccc',
    fontSize: 14,
    marginBottom: 8,
    lineHeight: 20,
  },
  payoutCategory: {
    marginBottom: 16,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 8,
    padding: 12,
  },
  payoutCategoryTitle: {
    color: '#FFD700',
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  payoutRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  payoutSymbolContainer: {
    width: 50,
    height: 50,
    borderRadius: 8,
    backgroundColor: '#2a2a2a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#FFD700',
    marginRight: 12,
  },
  payoutImage: {
    width: 40,
    height: 40,
  },
  payoutInfo: {
    flex: 1,
  },
  payoutName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  payoutJackpot: {
    color: '#FFD700',
    fontSize: 13,
    fontWeight: '600',
  },
  payoutRare: {
    color: '#9b59b6',
    fontSize: 13,
    fontWeight: '600',
  },
  payoutCommon: {
    color: '#27ae60',
    fontSize: 13,
    fontWeight: '600',
  },
  payoutSmall: {
    color: '#888',
    fontSize: 11,
    marginTop: 2,
  },
  payoutLoss: {
    color: '#e74c3c',
    fontSize: 14,
    fontWeight: '600',
  },
  helpCloseButton: {
    backgroundColor: '#d4af37',
    paddingVertical: 14,
    alignItems: 'center',
    borderTopWidth: 2,
    borderTopColor: '#b8860b',
  },
  helpCloseButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
});
