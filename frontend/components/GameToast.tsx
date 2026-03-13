import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, StyleSheet, Animated, Platform } from 'react-native';

type ToastType = 'success' | 'info' | 'warning' | 'error';

interface ToastMessage {
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

// Global toast queue
let toastHandler: ((msg: ToastMessage) => void) | null = null;

export const showGameToast = (msg: ToastMessage) => {
  if (toastHandler) {
    toastHandler(msg);
  }
};

const COLORS: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: { bg: '#1a3a1a', border: '#4caf50', icon: '✅' },
  info: { bg: '#1a2a3a', border: '#2196f3', icon: '💡' },
  warning: { bg: '#3a3a1a', border: '#ff9800', icon: '⚠️' },
  error: { bg: '#3a1a1a', border: '#f44336', icon: '❌' },
};

export function GameToastProvider() {
  const [visible, setVisible] = useState(false);
  const [current, setCurrent] = useState<ToastMessage | null>(null);
  const slideAnim = useRef(new Animated.Value(-100)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((msg: ToastMessage) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    
    setCurrent(msg);
    setVisible(true);
    
    Animated.parallel([
      Animated.spring(slideAnim, {
        toValue: 0,
        useNativeDriver: true,
        tension: 100,
        friction: 8,
      }),
      Animated.timing(opacityAnim, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start();

    timeoutRef.current = setTimeout(() => {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: -100,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(opacityAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start(() => {
        setVisible(false);
        setCurrent(null);
      });
    }, msg.duration || 3000);
  }, [slideAnim, opacityAnim]);

  useEffect(() => {
    toastHandler = show;
    return () => {
      toastHandler = null;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [show]);

  if (!visible || !current) return null;

  const colors = COLORS[current.type];

  return (
    <Animated.View
      style={[
        styles.container,
        {
          transform: [{ translateY: slideAnim }],
          opacity: opacityAnim,
          backgroundColor: colors.bg,
          borderColor: colors.border,
        },
      ]}
      pointerEvents="none"
    >
      <Text style={styles.icon}>{colors.icon}</Text>
      <View style={styles.textContainer}>
        <Text style={[styles.title, { color: colors.border }]}>{current.title}</Text>
        {current.message ? (
          <Text style={styles.message}>{current.message}</Text>
        ) : null}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 60 : 40,
    left: 16,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    zIndex: 9999,
    elevation: 10,
  },
  icon: {
    fontSize: 20,
    marginRight: 12,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  message: {
    fontSize: 12,
    color: '#ccc',
    marginTop: 2,
    lineHeight: 16,
  },
});
