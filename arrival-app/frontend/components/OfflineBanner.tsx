/**
 * OfflineBanner — shows a persistent banner when the device has no network connection.
 * Uses a simple polling approach (no extra dependency needed).
 */

import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, AppState } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const CHECK_URL = 'https://clients3.google.com/generate_204';
const CHECK_INTERVAL = 10_000; // 10 seconds

export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;

    const check = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        await fetch(CHECK_URL, { method: 'HEAD', signal: controller.signal });
        clearTimeout(timeout);
        setIsOnline(true);
      } catch {
        setIsOnline(false);
      }
    };

    check();
    timer = setInterval(check, CHECK_INTERVAL);

    // Re-check when app comes back to foreground
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') check();
    });

    return () => {
      clearInterval(timer);
      sub.remove();
    };
  }, []);

  return isOnline;
}

export default function OfflineBanner() {
  const isOnline = useNetworkStatus();
  const slideAnim = useRef(new Animated.Value(-50)).current;
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!isOnline) {
      setVisible(true);
      Animated.spring(slideAnim, {
        toValue: 0,
        useNativeDriver: true,
        tension: 80,
        friction: 10,
      }).start();
    } else if (visible) {
      Animated.timing(slideAnim, {
        toValue: -50,
        duration: 200,
        useNativeDriver: true,
      }).start(() => setVisible(false));
    }
  }, [isOnline]);

  if (!visible) return null;

  return (
    <Animated.View style={[styles.banner, { transform: [{ translateY: slideAnim }] }]}>
      <Ionicons name="cloud-offline-outline" size={16} color="#FFF" />
      <Text style={styles.text}>No internet connection</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    backgroundColor: '#C75450',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    paddingHorizontal: 16,
    gap: 8,
    zIndex: 999,
  },
  text: {
    color: '#FFF',
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: -0.2,
  },
});
