import React, { useEffect, useCallback } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { View, StyleSheet } from 'react-native';
import { GameToastProvider } from '../components/GameToast';
import * as SplashScreen from 'expo-splash-screen';

// Prevent the splash screen from auto-hiding before app is ready
SplashScreen.preventAutoHideAsync().catch(() => {
  // Ignore errors - splash screen may already be hidden
});

const queryClient = new QueryClient();

export default function RootLayout() {
  const onLayoutRootView = useCallback(async () => {
    // Hide splash screen after layout is ready
    try {
      await SplashScreen.hideAsync();
    } catch (e) {
      // Ignore errors - splash screen may already be hidden
    }
  }, []);

  // Also hide splash screen after a short delay as a fallback
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        await SplashScreen.hideAsync();
      } catch (e) {
        // Ignore errors
      }
    }, 500);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <View style={styles.container} onLayout={onLayoutRootView}>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: '#0a0a0a' },
            animation: 'fade',
          }}
        >
          <Stack.Screen name="index" />
          <Stack.Screen name="create-character" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="battle/[id]" options={{ presentation: 'fullScreenModal' }} />
          <Stack.Screen name="mission/[id]" options={{ presentation: 'modal' }} />
          <Stack.Screen name="privacy" options={{ presentation: 'modal' }} />
          <Stack.Screen name="delete-account" options={{ presentation: 'modal' }} />
          <Stack.Screen name="instructions" options={{ presentation: 'modal' }} />
        </Stack>
        <GameToastProvider />
      </View>
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
});
