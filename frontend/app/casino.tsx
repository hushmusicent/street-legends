import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { LinearGradient } from 'expo-linear-gradient';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Slot symbols using emojis for reliable display
const SLOT_SYMBOLS: Record<string, { emoji: string; name: string }> = {
  cherry: { emoji: '🍒', name: 'Cherry' },
  banana: { emoji: '🍌', name: 'Banana' },
  peach: { emoji: '🍑', name: 'Peach' },
  eggplant: { emoji: '🍆', name: 'Eggplant' },
  coconut: { emoji: '🥥', name: 'Coconut' },
  seven: { emoji: '7️⃣', name: 'Lucky 7' },
  diamond: { emoji: '💎', name: 'Diamond' },
};

const SYMBOL_KEYS = Object.keys(SLOT_SYMBOLS);

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
  const [slotReels, setSlotReels] = useState<string[]>(['cherry', 'banana', 'peach']);
  const [slotSpinning, setSlotSpinning] = useState(false);
  const [slotResult, setSlotResult] = useState<any>(null);
  const spinIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Blackjack state
  const [bjBet, setBjBet] = useState(50);
  const [bjGame, setBjGame] = useState<any>(null);
  const [bjLoading, setBjLoading] = useState(false);
  
  // Roulette state
  const [rouletteBet, setRouletteBet] = useState(50);
  const [rouletteBetType, setRouletteBetType] = useState('red');
  const [rouletteNumber, setRouletteNumber] = useState('');
  const [rouletteResult, setRouletteResult] = useState<any>(null);
  const [rouletteSpinning, setRouletteSpinning] = useState(false);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (spinIntervalRef.current) {
        clearInterval(spinIntervalRef.current);
      }
    };
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

  // Get random symbol for spinning animation
  const getRandomSymbol = () => {
    return SYMBOL_KEYS[Math.floor(Math.random() * SYMBOL_KEYS.length)];
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

    // Start spinning animation
    spinIntervalRef.current = setInterval(() => {
      setSlotReels([getRandomSymbol(), getRandomSymbol(), getRandomSymbol()]);
    }, 80);

    try {
      const response = await fetch(`${API_URL}/api/casinos/slots?player_id=${playerId}&bet_amount=${slotBet}`, {
        method: 'POST',
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to play slots');
      }

      // Map backend symbols to our symbols (backend may return different names)
      const mapSymbol = (symbol: string): string => {
        const symbolMap: Record<string, string> = {
          'banana': 'banana',
          'eggplant': 'eggplant',
          'peach': 'peach',
          'cherry': 'cherry',
          'coconut': 'coconut',
          'hush_logo': 'seven',
          'appsolut_logo': 'diamond',
          '7': 'seven',
          'seven': 'seven',
          'diamond': 'diamond',
        };
        return symbolMap[symbol] || 'cherry';
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
    if (!bjGame || bjLoading) return;

    setBjLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/casinos/blackjack/${bjGame.game_id}/action?action=${action}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Action failed');
      }

      setBjGame({ ...bjGame, ...data });
      if (data.status !== 'playing') {
        refreshPlayer();
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setBjLoading(false);
    }
  };

  // ============== ROULETTE ==============
  const playRoulette = async () => {
    if (!playerId || rouletteSpinning) return;
    if ((player?.cash || 0) < rouletteBet) {
      Alert.alert('Not Enough Cash', `You need $${rouletteBet} to play. You have $${player?.cash || 0}`);
      return;
    }

    if (rouletteBetType === 'number' && (rouletteNumber === '' || isNaN(parseInt(rouletteNumber)))) {
      Alert.alert('Invalid Number', 'Please enter a number between 0 and 36');
      return;
    }

    setRouletteSpinning(true);
    setRouletteResult(null);

    try {
      const betValue = rouletteBetType === 'number' ? rouletteNumber : '';
      const response = await fetch(
        `${API_URL}/api/casinos/roulette?player_id=${playerId}&bet_amount=${rouletteBet}&bet_type=${rouletteBetType}&bet_value=${betValue}`,
        { method: 'POST' }
      );
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to play roulette');
      }

      setTimeout(() => {
        setRouletteResult(data);
        setRouletteSpinning(false);
        refreshPlayer();
      }, 2000);
    } catch (e: any) {
      setRouletteSpinning(false);
      Alert.alert('Error', e.message);
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

  const renderSlots = () => (
    <View style={styles.slotsContainer}>
      <View style={styles.slotsHeader}>
        <LinearGradient colors={['#1a1a1a', '#0d0d0d']} style={styles.slotsHeaderBg}>
          <Text style={styles.slotsTitle}>🎰 SLOTS 🎰</Text>
        </LinearGradient>
      </View>
      
      <View style={styles.reelsContainer}>
        <LinearGradient colors={['#2a1a0a', '#1a0a00', '#2a1a0a']} style={styles.reelsBg}>
          <View style={styles.reels}>
            {slotReels.map((symbol, index) => (
              <View key={index} style={[styles.reel, slotSpinning && styles.reelSpinning]}>
                <Text style={styles.reelEmoji}>
                  {SLOT_SYMBOLS[symbol]?.emoji || '🍒'}
                </Text>
              </View>
            ))}
          </View>
        </LinearGradient>
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

  const renderBlackjack = () => (
    <ScrollView style={styles.bjContainer} contentContainerStyle={styles.bjContent}>
      <Text style={styles.gameTitle}>BLACKJACK</Text>
      <Text style={styles.balanceSmall}>Balance: ${player?.cash || 0}</Text>
      
      {!bjGame || bjGame.status !== 'playing' ? (
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
          
          {bjGame && bjGame.status !== 'playing' && (
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
          <View style={styles.bjHand}>
            <Text style={styles.bjHandLabel}>DEALER</Text>
            <View style={styles.bjCards}>
              {bjGame.dealer_cards?.map((card: any, i: number) => (
                <View key={i}>{renderCard(card)}</View>
              ))}
            </View>
          </View>
          
          <View style={styles.bjHand}>
            <Text style={styles.bjHandLabel}>YOUR HAND ({bjGame.player_value})</Text>
            <View style={styles.bjCards}>
              {bjGame.player_cards?.map((card: any, i: number) => (
                <View key={i}>{renderCard(card)}</View>
              ))}
            </View>
          </View>
          
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
        </View>
      )}
    </ScrollView>
  );

  const renderRoulette = () => (
    <ScrollView style={styles.rouletteContainer} contentContainerStyle={styles.rouletteContent}>
      <Text style={styles.gameTitle}>ROULETTE</Text>
      <Text style={styles.balanceSmall}>Balance: ${player?.cash || 0}</Text>
      
      <View style={styles.rouletteWheel}>
        {rouletteSpinning ? (
          <ActivityIndicator size="large" color="#d4af37" />
        ) : rouletteResult ? (
          <View style={styles.rouletteResultDisplay}>
            <View style={[
              styles.rouletteNumber,
              rouletteResult.result_color === 'red' && styles.rouletteRed,
              rouletteResult.result_color === 'black' && styles.rouletteBlack,
              rouletteResult.result_color === 'green' && styles.rouletteGreen,
            ]}>
              <Text style={styles.rouletteNumberText}>{rouletteResult.result_number}</Text>
            </View>
            <Text style={styles.rouletteColorText}>{rouletteResult.result_color.toUpperCase()}</Text>
          </View>
        ) : (
          <Text style={styles.rouletteWheelText}>🎡</Text>
        )}
      </View>
      
      {rouletteResult && (
        <View style={[styles.resultContainer, rouletteResult.win ? styles.winResult : styles.lossResult]}>
          <Text style={styles.resultText}>{rouletteResult.win ? '🎉 Winner!' : '😔 No luck'}</Text>
          <Text style={styles.resultAmount}>
            {rouletteResult.net_change >= 0 ? `+$${rouletteResult.winnings}` : `-$${rouletteBet}`}
          </Text>
        </View>
      )}
      
      <View style={styles.rouletteBetSection}>
        <Text style={styles.rouletteBetLabel}>Bet Amount</Text>
        <View style={styles.rouletteBetAmounts}>
          {[25, 50, 100, 250].map((amount) => (
            <TouchableOpacity
              key={amount}
              style={[styles.rouletteBetBtn, rouletteBet === amount && styles.rouletteBetBtnActive]}
              onPress={() => setRouletteBet(amount)}
            >
              <Text style={[styles.rouletteBetBtnText, rouletteBet === amount && styles.rouletteBetBtnTextActive]}>
                ${amount}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        
        <Text style={styles.rouletteBetLabel}>Bet Type</Text>
        <View style={styles.rouletteBetTypes}>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, styles.rouletteRedBtn, rouletteBetType === 'red' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('red')}
          >
            <Text style={styles.rouletteTypeBtnText}>RED (2x)</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, styles.rouletteBlackBtn, rouletteBetType === 'black' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('black')}
          >
            <Text style={styles.rouletteTypeBtnText}>BLACK (2x)</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.rouletteBetTypes}>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === 'odd' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('odd')}
          >
            <Text style={styles.rouletteTypeBtnText}>ODD (2x)</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === 'even' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('even')}
          >
            <Text style={styles.rouletteTypeBtnText}>EVEN (2x)</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.rouletteBetTypes}>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === '1-18' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('1-18')}
          >
            <Text style={styles.rouletteTypeBtnText}>1-18 (2x)</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === '19-36' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('19-36')}
          >
            <Text style={styles.rouletteTypeBtnText}>19-36 (2x)</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.rouletteBetTypes}>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === '1-12' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('1-12')}
          >
            <Text style={styles.rouletteTypeBtnText}>1-12 (3x)</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === '13-24' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('13-24')}
          >
            <Text style={styles.rouletteTypeBtnText}>13-24 (3x)</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.rouletteTypeBtn, rouletteBetType === '25-36' && styles.rouletteTypeBtnActive]}
            onPress={() => setRouletteBetType('25-36')}
          >
            <Text style={styles.rouletteTypeBtnText}>25-36 (3x)</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          style={[styles.rouletteTypeBtn, styles.rouletteNumberBtn, rouletteBetType === 'number' && styles.rouletteTypeBtnActive]}
          onPress={() => setRouletteBetType('number')}
        >
          <Text style={styles.rouletteTypeBtnText}>SINGLE # (35x)</Text>
        </TouchableOpacity>
        {rouletteBetType === 'number' && (
          <View style={styles.numberInputContainer}>
            <Text style={styles.numberInputLabel}>Enter number (0-36):</Text>
            <View style={styles.numberGrid}>
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36].map((num) => (
                <TouchableOpacity
                  key={num}
                  style={[styles.numberBtn, rouletteNumber === String(num) && styles.numberBtnActive]}
                  onPress={() => setRouletteNumber(String(num))}
                >
                  <Text style={[styles.numberBtnText, rouletteNumber === String(num) && styles.numberBtnTextActive]}>{num}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      </View>
      
      <TouchableOpacity 
        style={[styles.spinButton, rouletteSpinning && styles.spinButtonDisabled]}
        onPress={playRoulette}
        disabled={rouletteSpinning}
      >
        <LinearGradient colors={['#e74c3c', '#c0392b', '#e74c3c']} style={styles.spinButtonGradient}>
          {rouletteSpinning ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.spinButtonText}>SPIN</Text>
          )}
        </LinearGradient>
      </TouchableOpacity>
    </ScrollView>
  );

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
    borderColor: '#d4af37',
    shadowColor: '#d4af37',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 5,
  },
  reelSpinning: {
    borderColor: '#fff',
    backgroundColor: '#2a2a2a',
  },
  reelEmoji: {
    fontSize: 56,
  },
  reelImage: {
    width: 60,
    height: 60,
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
  
  // Roulette styles
  rouletteContainer: {
    flex: 1,
  },
  rouletteContent: {
    padding: 20,
    alignItems: 'center',
  },
  rouletteWheel: {
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: '#1a1a1a',
    borderWidth: 4,
    borderColor: '#d4af37',
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 20,
  },
  rouletteWheelText: {
    fontSize: 64,
  },
  rouletteResultDisplay: {
    alignItems: 'center',
  },
  rouletteNumber: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rouletteRed: {
    backgroundColor: '#e74c3c',
  },
  rouletteBlack: {
    backgroundColor: '#2c3e50',
  },
  rouletteGreen: {
    backgroundColor: '#27ae60',
  },
  rouletteNumberText: {
    color: '#fff',
    fontSize: 32,
    fontWeight: 'bold',
  },
  rouletteColorText: {
    color: '#d4af37',
    fontSize: 14,
    marginTop: 8,
    fontWeight: 'bold',
  },
  rouletteBetSection: {
    width: '100%',
    alignItems: 'center',
  },
  rouletteBetLabel: {
    color: '#888',
    fontSize: 12,
    marginBottom: 8,
    marginTop: 16,
    letterSpacing: 1,
  },
  rouletteBetAmounts: {
    flexDirection: 'row',
    gap: 10,
  },
  rouletteBetBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    borderWidth: 2,
    borderColor: '#333',
  },
  rouletteBetBtnActive: {
    borderColor: '#d4af37',
  },
  rouletteBetBtnText: {
    color: '#888',
    fontSize: 14,
    fontWeight: 'bold',
  },
  rouletteBetBtnTextActive: {
    color: '#d4af37',
  },
  rouletteBetTypes: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  rouletteTypeBtn: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    borderWidth: 2,
    borderColor: '#444',
  },
  rouletteRedBtn: {
    backgroundColor: 'rgba(231, 76, 60, 0.3)',
    borderColor: '#e74c3c',
  },
  rouletteBlackBtn: {
    backgroundColor: 'rgba(44, 62, 80, 0.5)',
    borderColor: '#2c3e50',
  },
  rouletteNumberBtn: {
    marginTop: 8,
    backgroundColor: 'rgba(39, 174, 96, 0.3)',
    borderColor: '#27ae60',
  },
  rouletteTypeBtnActive: {
    borderColor: '#d4af37',
    borderWidth: 3,
  },
  rouletteTypeBtnText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  numberInputContainer: {
    width: '100%',
    marginTop: 12,
    alignItems: 'center',
  },
  numberInputLabel: {
    color: '#888',
    fontSize: 12,
    marginBottom: 8,
  },
  numberGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
    maxWidth: 320,
  },
  numberBtn: {
    width: 36,
    height: 36,
    borderRadius: 6,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
  },
  numberBtnActive: {
    backgroundColor: '#d4af37',
    borderColor: '#d4af37',
  },
  numberBtnText: {
    color: '#888',
    fontSize: 12,
    fontWeight: 'bold',
  },
  numberBtnTextActive: {
    color: '#000',
  },
});
