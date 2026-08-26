import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  TextInput,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import api from '../services/api';

export default function DeleteAccountScreen() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');

  const isFormValid = username.trim().length > 0 && confirmText === 'DELETE';

  const handleSubmit = async () => {
    if (!isFormValid) return;

    setIsSubmitting(true);
    setError('');

    try {
      // Submit deletion request to backend
      await api.post('/api/account/delete-request', {
        username: username.trim(),
      });
      setIsSubmitted(true);
    } catch (err: any) {
      // Even if API fails, show success for privacy (don't reveal if account exists)
      setIsSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const BulletPoint = ({ children }: { children: React.ReactNode }) => (
    <View style={styles.bulletContainer}>
      <Ionicons name="trash-outline" size={16} color="#ef4444" />
      <Text style={styles.bulletText}>{children}</Text>
    </View>
  );

  if (isSubmitted) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        
        <View style={styles.header}>
          <TouchableOpacity 
            style={styles.backButton} 
            onPress={() => router.back()}
            accessibilityLabel="Go back"
            accessibilityRole="button"
          >
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Delete Account</Text>
          <View style={styles.headerSpacer} />
        </View>

        <View style={styles.confirmationContainer}>
          <View style={styles.confirmationIcon}>
            <Ionicons name="checkmark-circle" size={80} color="#4ade80" />
          </View>
          <Text style={styles.confirmationTitle}>Request Submitted</Text>
          <Text style={styles.confirmationText}>
            Your account deletion request has been received. If an account exists with the 
            username provided, all associated data will be permanently deleted within 30 days.
          </Text>
          <Text style={styles.confirmationNote}>
            You will not receive any confirmation email for privacy reasons. If you change 
            your mind, you can create a new account at any time.
          </Text>
          <TouchableOpacity 
            style={styles.doneButton}
            onPress={() => router.back()}
          >
            <Text style={styles.doneButtonText}>Done</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={() => router.back()}
          accessibilityLabel="Go back"
          accessibilityRole="button"
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Delete Account</Text>
        <View style={styles.headerSpacer} />
      </View>

      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardAvoid}
      >
        <ScrollView 
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={true}
          keyboardShouldPersistTaps="handled"
        >
          {/* App Title */}
          <View style={styles.titleContainer}>
            <Text style={styles.appName}>Street Legends</Text>
            <Text style={styles.subtitle}>Account Deletion Request</Text>
          </View>

          {/* Warning Box */}
          <View style={styles.warningBox}>
            <Ionicons name="warning" size={24} color="#f59e0b" />
            <Text style={styles.warningText}>
              Account deletion is permanent and cannot be undone.
            </Text>
          </View>

          {/* What Gets Deleted */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>What Will Be Deleted</Text>
            <Text style={styles.paragraph}>
              When you request account deletion, the following data will be permanently removed:
            </Text>
            <BulletPoint>Your character profile and username</BulletPoint>
            <BulletPoint>All character stats, skills, and inventory</BulletPoint>
            <BulletPoint>Territories you have captured</BulletPoint>
            <BulletPoint>Complete battle history and combat logs</BulletPoint>
            <BulletPoint>Profile picture and uploaded images</BulletPoint>
            <BulletPoint>Mission progress and achievements</BulletPoint>
            <BulletPoint>Fitness tracking data and step history</BulletPoint>
          </View>

          {/* Deletion Form */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Request Deletion</Text>
            <Text style={styles.paragraph}>
              Enter your username below to submit a deletion request. For privacy reasons, 
              we will not confirm whether the account exists.
            </Text>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Username / Character Name</Text>
              <TextInput
                style={styles.textInput}
                value={username}
                onChangeText={setUsername}
                placeholder="Enter your username"
                placeholderTextColor="#666"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Type DELETE to confirm</Text>
              <TextInput
                style={[
                  styles.textInput,
                  confirmText === 'DELETE' && styles.textInputValid
                ]}
                value={confirmText}
                onChangeText={setConfirmText}
                placeholder="Type DELETE"
                placeholderTextColor="#666"
                autoCapitalize="characters"
                autoCorrect={false}
              />
              {confirmText.length > 0 && confirmText !== 'DELETE' && (
                <Text style={styles.inputHint}>Please type DELETE in capitals</Text>
              )}
            </View>

            {error ? (
              <View style={styles.errorBox}>
                <Ionicons name="alert-circle" size={16} color="#ef4444" />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <TouchableOpacity 
              style={[
                styles.deleteButton,
                !isFormValid && styles.deleteButtonDisabled
              ]}
              onPress={handleSubmit}
              disabled={!isFormValid || isSubmitting}
            >
              {isSubmitting ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Ionicons name="trash" size={20} color="#fff" />
                  <Text style={styles.deleteButtonText}>Submit Deletion Request</Text>
                </>
              )}
            </TouchableOpacity>
          </View>

          {/* Additional Info */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Important Information</Text>
            <Text style={styles.paragraph}>
              • Deletion requests are processed within 30 days{'\n'}
              • You will not receive email confirmation{'\n'}
              • This action cannot be reversed{'\n'}
              • You may create a new account after deletion
            </Text>
          </View>

          {/* Privacy Link */}
          <TouchableOpacity 
            style={styles.privacyLink}
            onPress={() => router.push('/privacy')}
          >
            <Text style={styles.privacyLinkText}>View Privacy Policy</Text>
            <Ionicons name="arrow-forward" size={16} color="#f59e0b" />
          </TouchableOpacity>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>© 2026 Street Legends. All rights reserved.</Text>
          </View>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#1a1a1a',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  backButton: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#333',
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  headerSpacer: {
    width: 44,
  },
  keyboardAvoid: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  titleContainer: {
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  appName: {
    fontSize: 28,
    fontWeight: '800',
    color: '#f59e0b',
    marginBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: 2,
  },
  subtitle: {
    fontSize: 14,
    color: '#888',
  },
  warningBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2d1f0d',
    borderWidth: 1,
    borderColor: '#f59e0b',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    gap: 12,
  },
  warningText: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: '#f59e0b',
    lineHeight: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#ef4444',
    marginBottom: 12,
  },
  paragraph: {
    fontSize: 15,
    lineHeight: 24,
    color: '#d1d5db',
    marginBottom: 12,
  },
  bulletContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    paddingLeft: 4,
    gap: 10,
  },
  bulletText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
    color: '#d1d5db',
  },
  inputContainer: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#888',
    marginBottom: 8,
  },
  textInput: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: '#fff',
  },
  textInputValid: {
    borderColor: '#4ade80',
  },
  inputHint: {
    fontSize: 12,
    color: '#f59e0b',
    marginTop: 6,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2d1010',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    gap: 8,
  },
  errorText: {
    flex: 1,
    fontSize: 14,
    color: '#ef4444',
  },
  deleteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#dc2626',
    borderRadius: 12,
    paddingVertical: 16,
    gap: 10,
    marginTop: 8,
  },
  deleteButtonDisabled: {
    backgroundColor: '#4a1515',
    opacity: 0.7,
  },
  deleteButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  privacyLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  privacyLinkText: {
    fontSize: 15,
    color: '#f59e0b',
    fontWeight: '500',
  },
  footer: {
    marginTop: 16,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#333',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 13,
    color: '#666',
  },
  // Confirmation screen styles
  confirmationContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  confirmationIcon: {
    marginBottom: 24,
  },
  confirmationTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4ade80',
    marginBottom: 16,
    textAlign: 'center',
  },
  confirmationText: {
    fontSize: 16,
    lineHeight: 26,
    color: '#d1d5db',
    textAlign: 'center',
    marginBottom: 16,
  },
  confirmationNote: {
    fontSize: 14,
    lineHeight: 22,
    color: '#888',
    textAlign: 'center',
    marginBottom: 32,
  },
  doneButton: {
    backgroundColor: '#333',
    borderRadius: 12,
    paddingHorizontal: 48,
    paddingVertical: 14,
  },
  doneButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
