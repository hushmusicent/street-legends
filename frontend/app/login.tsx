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
  Modal,
  Pressable,
  Alert,
} from 'react-native';
import { router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useGameStore } from '../stores/gameStore';
import { loginAccount, forgotPassword, resetPassword, default as api } from '../services/api';
import { GameButton } from '../components/GameButton';

type ForgotPasswordStep = 'email' | 'code' | 'newPassword';

export default function LoginScreen() {
  const { setPlayer, savePlayerId } = useGameStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Forgot Password state
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotStep, setForgotStep] = useState<ForgotPasswordStep>('email');
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);
  const [showNewPassword, setShowNewPassword] = useState(false);

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
      
      // Mark player as logged in (visible in game world)
      try {
        await api.post(`/players/${player.id}/login`);
      } catch (e) {
        // Continue even if this fails
        console.log('Login visibility API error:', e);
      }
      
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

  const handleForgotPassword = () => {
    setShowForgotModal(true);
    setForgotStep('email');
    setForgotEmail('');
    setResetCode('');
    setNewPassword('');
    setConfirmPassword('');
    setForgotError(null);
  };

  const closeForgotModal = () => {
    setShowForgotModal(false);
    setForgotStep('email');
    setForgotError(null);
  };

  const handleSendResetCode = async () => {
    Keyboard.dismiss();
    if (!forgotEmail.trim()) {
      setForgotError('Please enter your email or username');
      return;
    }

    try {
      setForgotLoading(true);
      setForgotError(null);
      await forgotPassword(forgotEmail.trim());
      setForgotStep('code');
    } catch (err: any) {
      setForgotError(err?.response?.data?.detail || 'Failed to send reset code');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleVerifyCode = () => {
    Keyboard.dismiss();
    if (!resetCode.trim()) {
      setForgotError('Please enter the reset code');
      return;
    }
    if (resetCode.trim().length < 6) {
      setForgotError('Please enter a valid reset code');
      return;
    }
    setForgotError(null);
    setForgotStep('newPassword');
  };

  const handleResetPassword = async () => {
    Keyboard.dismiss();
    if (!newPassword) {
      setForgotError('Please enter a new password');
      return;
    }
    if (newPassword.length < 4) {
      setForgotError('Password must be at least 4 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setForgotError('Passwords do not match');
      return;
    }

    try {
      setForgotLoading(true);
      setForgotError(null);
      await resetPassword(resetCode.trim(), newPassword);
      closeForgotModal();
      Alert.alert(
        'Success!',
        'Your password has been reset. You can now login with your new password.',
        [{ text: 'OK' }]
      );
    } catch (err: any) {
      setForgotError(err?.response?.data?.detail || 'Failed to reset password');
    } finally {
      setForgotLoading(false);
    }
  };

  const renderForgotModalContent = () => {
    switch (forgotStep) {
      case 'email':
        return (
          <>
            <View style={styles.modalHeader}>
              <View style={styles.modalIconWrap}>
                <Ionicons name="key" size={32} color="#e74c3c" />
              </View>
              <Text style={styles.modalTitle}>Forgot Password?</Text>
              <Text style={styles.modalSubtitle}>
                Enter your email or username and we&apos;ll send you a reset code
              </Text>
            </View>

            <View style={styles.modalInputGroup}>
              <Text style={styles.modalInputLabel}>EMAIL OR USERNAME</Text>
              <View style={styles.modalInputWrap}>
                <Ionicons name="mail" size={18} color="#666" style={styles.modalInputIcon} />
                <TextInput
                  style={styles.modalInput}
                  value={forgotEmail}
                  onChangeText={(t) => { setForgotEmail(t); setForgotError(null); }}
                  placeholder="Enter email or username"
                  placeholderTextColor="#444"
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="email-address"
                />
              </View>
            </View>

            {forgotError && (
              <View style={styles.forgotErrorBox}>
                <Ionicons name="alert-circle" size={16} color="#e74c3c" />
                <Text style={styles.forgotErrorText}>{forgotError}</Text>
              </View>
            )}

            <TouchableOpacity
              style={[styles.modalPrimaryBtn, forgotLoading && styles.modalBtnDisabled]}
              onPress={handleSendResetCode}
              disabled={forgotLoading}
            >
              {forgotLoading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Ionicons name="send" size={18} color="#fff" />
                  <Text style={styles.modalPrimaryBtnText}>Send Reset Code</Text>
                </>
              )}
            </TouchableOpacity>
          </>
        );

      case 'code':
        return (
          <>
            <View style={styles.modalHeader}>
              <View style={styles.modalIconWrap}>
                <Ionicons name="mail-open" size={32} color="#27ae60" />
              </View>
              <Text style={styles.modalTitle}>Check Your Email</Text>
              <Text style={styles.modalSubtitle}>
                We sent a reset code to your email. Enter the 8-character code below.
              </Text>
            </View>

            <View style={styles.modalInputGroup}>
              <Text style={styles.modalInputLabel}>RESET CODE</Text>
              <View style={styles.modalInputWrap}>
                <Ionicons name="keypad" size={18} color="#666" style={styles.modalInputIcon} />
                <TextInput
                  style={[styles.modalInput, styles.codeInput]}
                  value={resetCode}
                  onChangeText={(t) => { setResetCode(t.toUpperCase()); setForgotError(null); }}
                  placeholder="XXXXXXXX"
                  placeholderTextColor="#444"
                  autoCapitalize="characters"
                  autoCorrect={false}
                  maxLength={8}
                />
              </View>
            </View>

            {forgotError && (
              <View style={styles.forgotErrorBox}>
                <Ionicons name="alert-circle" size={16} color="#e74c3c" />
                <Text style={styles.forgotErrorText}>{forgotError}</Text>
              </View>
            )}

            <TouchableOpacity
              style={styles.modalPrimaryBtn}
              onPress={handleVerifyCode}
            >
              <Ionicons name="checkmark-circle" size={18} color="#fff" />
              <Text style={styles.modalPrimaryBtnText}>Continue</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalSecondaryBtn}
              onPress={() => setForgotStep('email')}
            >
              <Ionicons name="arrow-back" size={16} color="#888" />
              <Text style={styles.modalSecondaryBtnText}>Back</Text>
            </TouchableOpacity>
          </>
        );

      case 'newPassword':
        return (
          <>
            <View style={styles.modalHeader}>
              <View style={styles.modalIconWrap}>
                <Ionicons name="lock-open" size={32} color="#3498db" />
              </View>
              <Text style={styles.modalTitle}>Create New Password</Text>
              <Text style={styles.modalSubtitle}>
                Choose a strong password for your account
              </Text>
            </View>

            <View style={styles.modalInputGroup}>
              <Text style={styles.modalInputLabel}>NEW PASSWORD</Text>
              <View style={styles.modalInputWrap}>
                <Ionicons name="lock-closed" size={18} color="#666" style={styles.modalInputIcon} />
                <TextInput
                  style={styles.modalInput}
                  value={newPassword}
                  onChangeText={(t) => { setNewPassword(t); setForgotError(null); }}
                  placeholder="Enter new password"
                  placeholderTextColor="#444"
                  secureTextEntry={!showNewPassword}
                  autoCapitalize="none"
                />
                <TouchableOpacity onPress={() => setShowNewPassword(!showNewPassword)} style={styles.eyeBtn}>
                  <Ionicons name={showNewPassword ? 'eye-off' : 'eye'} size={20} color="#666" />
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.modalInputGroup}>
              <Text style={styles.modalInputLabel}>CONFIRM PASSWORD</Text>
              <View style={styles.modalInputWrap}>
                <Ionicons name="lock-closed" size={18} color="#666" style={styles.modalInputIcon} />
                <TextInput
                  style={styles.modalInput}
                  value={confirmPassword}
                  onChangeText={(t) => { setConfirmPassword(t); setForgotError(null); }}
                  placeholder="Confirm new password"
                  placeholderTextColor="#444"
                  secureTextEntry={!showNewPassword}
                  autoCapitalize="none"
                />
              </View>
            </View>

            {forgotError && (
              <View style={styles.forgotErrorBox}>
                <Ionicons name="alert-circle" size={16} color="#e74c3c" />
                <Text style={styles.forgotErrorText}>{forgotError}</Text>
              </View>
            )}

            <TouchableOpacity
              style={[styles.modalPrimaryBtn, forgotLoading && styles.modalBtnDisabled]}
              onPress={handleResetPassword}
              disabled={forgotLoading}
            >
              {forgotLoading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Ionicons name="checkmark-done" size={18} color="#fff" />
                  <Text style={styles.modalPrimaryBtnText}>Reset Password</Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalSecondaryBtn}
              onPress={() => setForgotStep('code')}
            >
              <Ionicons name="arrow-back" size={16} color="#888" />
              <Text style={styles.modalSecondaryBtnText}>Back</Text>
            </TouchableOpacity>
          </>
        );
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

              {/* Forgot Password Link */}
              <TouchableOpacity onPress={handleForgotPassword} style={styles.forgotLink}>
                <Text style={styles.forgotLinkText}>Forgot Password?</Text>
              </TouchableOpacity>

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
                <Text style={styles.signupText}>Don&apos;t have an account? </Text>
                <Text style={[styles.signupText, { color: '#e74c3c', fontWeight: '700' }]}>Sign Up</Text>
              </TouchableOpacity>
            </View>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Forgot Password Modal */}
      <Modal
        visible={showForgotModal}
        transparent={true}
        animationType="slide"
        onRequestClose={closeForgotModal}
      >
        <Pressable style={styles.modalOverlay} onPress={closeForgotModal}>
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.modalKeyboardView}
          >
            <Pressable style={styles.modalSheet} onPress={(e) => e.stopPropagation()}>
              <View style={styles.modalHandle} />
              
              <TouchableOpacity style={styles.modalCloseBtn} onPress={closeForgotModal}>
                <Ionicons name="close" size={24} color="#666" />
              </TouchableOpacity>

              {renderForgotModalContent()}
            </Pressable>
          </KeyboardAvoidingView>
        </Pressable>
      </Modal>
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

  forgotLink: {
    alignSelf: 'flex-end',
    paddingVertical: 8,
    marginTop: 4,
  },
  forgotLinkText: {
    color: '#e74c3c',
    fontSize: 13,
    fontWeight: '600',
  },

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

  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  modalKeyboardView: {
    width: '100%',
  },
  modalSheet: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 24,
    paddingBottom: 40,
    paddingTop: 12,
    maxHeight: '90%',
  },
  modalHandle: {
    width: 40,
    height: 4,
    backgroundColor: '#333',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  modalCloseBtn: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  modalHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  modalIconWrap: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(231,76,60,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#fff',
    marginBottom: 8,
  },
  modalSubtitle: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: 20,
  },
  modalInputGroup: {
    marginBottom: 16,
  },
  modalInputLabel: {
    color: '#888',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: 8,
  },
  modalInputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#222',
    paddingHorizontal: 12,
  },
  modalInputIcon: {
    marginRight: 8,
  },
  modalInput: {
    flex: 1,
    color: '#fff',
    fontSize: 16,
    paddingVertical: 14,
  },
  codeInput: {
    letterSpacing: 4,
    textAlign: 'center',
    fontWeight: '700',
    fontSize: 20,
  },
  forgotErrorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(231,76,60,0.1)',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    gap: 8,
  },
  forgotErrorText: {
    color: '#e74c3c',
    fontSize: 13,
    flex: 1,
  },
  modalPrimaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#e74c3c',
    borderRadius: 12,
    paddingVertical: 16,
    gap: 8,
    marginTop: 8,
  },
  modalPrimaryBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  modalBtnDisabled: {
    opacity: 0.7,
  },
  modalSecondaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    gap: 6,
    marginTop: 8,
  },
  modalSecondaryBtnText: {
    color: '#888',
    fontSize: 14,
    fontWeight: '600',
  },
});
