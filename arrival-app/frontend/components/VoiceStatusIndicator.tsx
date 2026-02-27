import React, { useEffect, useRef } from 'react';
import { View, Text, Animated, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

interface VoiceStatusIndicatorProps {
  state: VoiceState;
}

const STATE_CONFIG = {
  idle: { icon: 'mic' as const, label: 'Hold to talk', color: 'rgba(255,255,255,0.15)' },
  listening: { icon: 'radio' as const, label: 'Listening...', color: Colors.recording || '#FF3B30' },
  processing: { icon: 'hourglass' as const, label: 'Thinking...', color: Colors.accent },
  speaking: { icon: 'volume-high' as const, label: 'Speaking...', color: '#4A90D9' },
};

export default function VoiceStatusIndicator({ state }: VoiceStatusIndicatorProps) {
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const opacityAnim = useRef(new Animated.Value(0.6)).current;
  const bar1 = useRef(new Animated.Value(0.3)).current;
  const bar2 = useRef(new Animated.Value(0.5)).current;
  const bar3 = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    pulseAnim.stopAnimation();
    opacityAnim.stopAnimation();

    if (state === 'idle') {
      // Gentle breathing pulse
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.05, duration: 2000, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
        ])
      ).start();
      Animated.timing(opacityAnim, { toValue: 0.6, duration: 300, useNativeDriver: true }).start();
    } else if (state === 'listening') {
      // Active pulse
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.15, duration: 400, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
        ])
      ).start();
      Animated.timing(opacityAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
      // Waveform bars
      [bar1, bar2, bar3].forEach((bar, i) => {
        Animated.loop(
          Animated.sequence([
            Animated.timing(bar, { toValue: 1, duration: 300 + i * 100, useNativeDriver: true }),
            Animated.timing(bar, { toValue: 0.3, duration: 300 + i * 100, useNativeDriver: true }),
          ])
        ).start();
      });
    } else if (state === 'processing') {
      Animated.timing(pulseAnim, { toValue: 0.9, duration: 300, useNativeDriver: true }).start();
      Animated.timing(opacityAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    } else if (state === 'speaking') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.08, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      ).start();
      Animated.timing(opacityAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    }

    return () => {
      pulseAnim.stopAnimation();
      opacityAnim.stopAnimation();
      [bar1, bar2, bar3].forEach(b => b.stopAnimation());
    };
  }, [state]);

  const config = STATE_CONFIG[state];

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.circle,
          {
            backgroundColor: config.color,
            transform: [{ scale: pulseAnim }],
            opacity: opacityAnim,
          },
        ]}
      >
        {state === 'processing' ? (
          <ActivityIndicator size="large" color="#FFF" />
        ) : state === 'listening' ? (
          <View style={styles.waveform}>
            {[bar1, bar2, bar3].map((bar, i) => (
              <Animated.View
                key={i}
                style={[
                  styles.waveBar,
                  { transform: [{ scaleY: bar }] },
                ]}
              />
            ))}
          </View>
        ) : (
          <Ionicons name={config.icon} size={36} color="#FFF" />
        )}
      </Animated.View>
      <Text style={styles.label}>{config.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  circle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  label: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 16,
    fontWeight: '500',
    marginTop: 20,
  },
  waveform: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  waveBar: {
    width: 6,
    height: 36,
    borderRadius: 3,
    backgroundColor: '#FFF',
  },
});
