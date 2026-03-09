import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Keyboard,
  ScrollView,
} from 'react-native';
import { router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { loginAccount } from '../services/api';
import { GameButton } from '../components/GameButton';

export default function LoginScreen() {
  const { setPlayer, savePlayerId } = useGameStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    Keyboard.dismiss();
    if (!username.trim()) {
      setError('Please enter your username');
      return;
    }
    if (!password) {
      setError('Please enter your password');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const player = await loginAccount(username.trim(), password);
      await savePlayerId(player.id);
      setPlayer(player);
      router.replace('/(tabs)');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Login failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.inner}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
            {/* Header */}
            <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>

            <View style={styles.header}>
              <View style={styles.iconWrap}>
                <Ionicons name="log-in" size={48} color="#e74c3c" />
              </View>
              <Text style={styles.title}>WELCOME BACK</Text>
              <Text style={styles.subtitle}>Login to continue your adventure</Text>
            </View>

            {/* Form */}
            <View style={styles.form}>
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>USERNAME</Text>
                <View style={styles.inputWrap}>
                  <Ionicons name="person" size={18} color="#666" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    value={username}
                    onChangeText={(t) => { setUsername(t); setError(null); }}
                    placeholder="Enter username"
                    placeholderTextColor="#444"
                    autoCapitalize="none"
                    autoCorrect={false}
                  />
                </View>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>PASSWORD</Text>
                <View style={styles.inputWrap}>
                  <Ionicons name="lock-closed" size={18} color="#666" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    value={password}
                    onChangeText={(t) => { setPassword(t); setError(null); }}
                    placeholder="Enter password"
                    placeholderTextColor="#444"
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                  />
                  <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeBtn}>
                    <Ionicons name={showPassword ? 'eye-off' : 'eye'} size={20} color="#666" />
                  </TouchableOpacity>
                </View>
              </View>

              {error && (
                <View style={styles.errorBox}>
                  <Ionicons name="alert-circle" size={16} color="#e74c3c" />
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              )}
            </View>

            {/* Actions */}
            <View style={styles.actions}>
              <GameButton
                title={loading ? 'LOGGING IN...' : 'LOGIN'}
                onPress={handleLogin}
                variant="primary"
                icon="log-in"
                size="large"
                disabled={loading}
                style={styles.loginBtn}
              />
              {loading && <ActivityIndicator style={{ marginTop: 12 }} color="#e74c3c" />}

              <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>OR</Text>
                <View style={styles.dividerLine} />
              </View>

              <TouchableOpacity onPress={() => router.replace('/create-character')} style={styles.signupLink}>
                <Text style={styles.signupText}>Don't have an account? </Text>
                <Text style={[styles.signupText, { color: '#e74c3c', fontWeight: '700' }]}>Sign Up</Text>
              </TouchableOpacity>
            </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  keyboardView: { flex: 1 },
  inner: { flexGrow: 1, paddingHorizontal: 24, justifyContent: 'center', paddingBottom: 40 },

  backButton: {
    position: 'absolute',
    top: 16,
    left: 0,
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },

  header: { alignItems: 'center', marginBottom: 32 },
  iconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(231,76,60,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#e74c3c',
    marginBottom: 16,
  },
  title: { fontSize: 28, fontWeight: '900', color: '#fff', letterSpacing: 3 },
  subtitle: { fontSize: 14, color: '#666', marginTop: 8 },

  form: { marginBottom: 24 },
  inputGroup: { marginBottom: 16 },
  inputLabel: { color: '#888', fontSize: 11, fontWeight: '700', letterSpacing: 2, marginBottom: 8 },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#222',
    paddingHorizontal: 12,
  },
  inputIcon: { marginRight: 8 },
  input: {
    flex: 1,
    color: '#fff',
    fontSize: 16,
    paddingVertical: 14,
  },
  eyeBtn: { padding: 8 },

  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(231,76,60,0.1)',
    borderRadius: 8,
    padding: 12,
    marginTop: 8,
    gap: 8,
  },
  errorText: { color: '#e74c3c', fontSize: 13 },

  actions: { alignItems: 'center' },
  loginBtn: { width: '100%' },

  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 20,
    width: '100%',
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: '#222' },
  dividerText: { color: '#555', fontSize: 12, fontWeight: '600', marginHorizontal: 12 },

  signupLink: { flexDirection: 'row' },
  signupText: { color: '#888', fontSize: 14 },
});
