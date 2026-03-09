import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { getCharacterClasses, registerAccount } from '../services/api';
import { GameButton } from '../components/GameButton';
import { CharacterClass } from '../types/game';

const CLASS_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  street_soldier: 'fitness',
  hacker: 'hardware-chip',
  enforcer: 'hammer',
  ghost: 'eye-off',
};

const CLASS_COLORS: Record<string, string> = {
  street_soldier: '#e74c3c',
  hacker: '#3498db',
  enforcer: '#f39c12',
  ghost: '#9b59b6',
};

export default function CreateCharacter() {
  const { setPlayer, savePlayerId } = useGameStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [selectedClass, setSelectedClass] = useState<string | null>(null);
  const [classes, setClasses] = useState<Record<string, CharacterClass>>({});
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadClasses();
  }, []);

  const loadClasses = async () => {
    try {
      const classData = await getCharacterClasses();
      setClasses(classData);
    } catch (err) {
      setError('Failed to load character classes');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!username.trim()) {
      setError('Please enter a username');
      return;
    }
    if (!password || password.length < 4) {
      setError('Password must be at least 4 characters');
      return;
    }
    if (!name.trim() || !selectedClass) {
      setError('Please enter a name and select a class');
      return;
    }

    try {
      setCreating(true);
      setError(null);
      const player = await registerAccount(username.trim(), password, name.trim(), selectedClass);
      await savePlayerId(player.id);
      setPlayer(player);
      router.replace('/(tabs)');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create account');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#e74c3c" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>

          <Text style={styles.title}>CREATE YOUR</Text>
          <Text style={styles.subtitle}>CHARACTER</Text>

          {/* Account Fields */}
          <Text style={styles.sectionLabel}>ACCOUNT</Text>
          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>USERNAME</Text>
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={(t) => { setUsername(t); setError(null); }}
              placeholder="Choose a username"
              placeholderTextColor="#444"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>PASSWORD</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={(t) => { setPassword(t); setError(null); }}
              placeholder="Choose a password"
              placeholderTextColor="#444"
              secureTextEntry
              autoCapitalize="none"
            />
          </View>

          <Text style={[styles.sectionLabel, { marginTop: 24 }]}>CHARACTER</Text>
          <View style={styles.inputContainer}>
            <Text style={styles.label}>STREET NAME</Text>
            <TextInput
              style={styles.input}
              value={name}
              onChangeText={setName}
              placeholder="Enter your name..."
              placeholderTextColor="#555"
              maxLength={20}
              autoCapitalize="none"
            />
          </View>

          <Text style={styles.sectionTitle}>SELECT YOUR CLASS</Text>

          <View style={styles.classGrid}>
            {Object.entries(classes).map(([key, classInfo]) => (
              <TouchableOpacity
                key={key}
                style={[
                  styles.classCard,
                  selectedClass === key && {
                    borderColor: CLASS_COLORS[key],
                    backgroundColor: `${CLASS_COLORS[key]}20`,
                  },
                ]}
                onPress={() => setSelectedClass(key)}
                activeOpacity={0.8}
              >
                <View style={[styles.classIcon, { backgroundColor: `${CLASS_COLORS[key]}30` }]}>
                  <Ionicons name={CLASS_ICONS[key]} size={32} color={CLASS_COLORS[key]} />
                </View>
                <Text style={[styles.className, { color: CLASS_COLORS[key] }]}>
                  {classInfo.name}
                </Text>
                <Text style={styles.classDescription}>{classInfo.description}</Text>
                <View style={styles.statsContainer}>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>HP</Text>
                    <Text style={styles.statValue}>{classInfo.base_stats.health}</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>ATK</Text>
                    <Text style={styles.statValue}>{classInfo.base_stats.attack}</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>DEF</Text>
                    <Text style={styles.statValue}>{classInfo.base_stats.defense}</Text>
                  </View>
                  <View style={styles.statRow}>
                    <Text style={styles.statLabel}>SPD</Text>
                    <Text style={styles.statValue}>{classInfo.base_stats.speed}</Text>
                  </View>
                </View>
                {selectedClass === key && (
                  <View style={styles.selectedBadge}>
                    <Ionicons name="checkmark-circle" size={24} color={CLASS_COLORS[key]} />
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </View>

          {error && <Text style={styles.errorText}>{error}</Text>}

          <GameButton
            title="CREATE CHARACTER"
            onPress={handleCreate}
            variant="primary"
            icon="person-add"
            disabled={!username.trim() || !password || !name.trim() || !selectedClass}
            loading={creating}
            size="large"
            style={styles.createButton}
          />

          <TouchableOpacity onPress={() => router.replace('/login')} style={styles.loginLink}>
            <Text style={styles.loginLinkText}>Already have an account? </Text>
            <Text style={[styles.loginLinkText, { color: '#e74c3c', fontWeight: '700' }]}>Login</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#0a0a0a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    padding: 24,
    paddingBottom: 40,
  },
  backButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 32,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 4,
  },
  subtitle: {
    fontSize: 32,
    fontWeight: '700',
    color: '#e74c3c',
    letterSpacing: 4,
    marginBottom: 32,
  },
  inputContainer: {
    marginBottom: 32,
  },
  label: {
    color: '#888',
    fontSize: 12,
    letterSpacing: 2,
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 16,
    fontSize: 18,
    color: '#fff',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    letterSpacing: 2,
    marginBottom: 16,
  },
  classGrid: {
    gap: 16,
  },
  classCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    padding: 20,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    position: 'relative',
  },
  classIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  className: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  classDescription: {
    color: '#888',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statRow: {
    alignItems: 'center',
  },
  statLabel: {
    color: '#555',
    fontSize: 10,
    letterSpacing: 1,
  },
  statValue: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  selectedBadge: {
    position: 'absolute',
    top: 16,
    right: 16,
  },
  errorText: {
    color: '#e74c3c',
    textAlign: 'center',
    marginTop: 16,
    marginBottom: 16,
  },
  createButton: {
    marginTop: 24,
  },
  sectionLabel: {
    color: '#e74c3c',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 3,
    marginBottom: 12,
    textTransform: 'uppercase',
  },
  inputLabel: {
    color: '#888',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 6,
  },
  loginLink: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
    paddingBottom: 20,
  },
  loginLinkText: {
    color: '#888',
    fontSize: 14,
  },
});
