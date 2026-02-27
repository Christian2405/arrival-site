import React, { useEffect, useRef } from 'react';
import { View, Text, Animated, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';

export type JobAIState = 'monitoring' | 'listening' | 'processing' | 'speaking';

interface JobModeViewProps {
  aiState: JobAIState;
  onPause?: () => void;
  isPaused?: boolean;
}

const STATE_CONFIG = {
  monitoring: { icon: 'eye' as const, label: 'Monitoring...', color: '#34C759', ringColor: 'rgba(52,199,89,0.3)' },
  listening: { icon: 'ear' as const, label: 'Listening...', color: '#FF9500', ringColor: 'rgba(255,149,0,0.3)' },
  processing: { icon: 'sparkles' as const, label: 'Thinking...', color: Colors.accent, ringColor: `rgba(212,132,42,0.3)` },
  speaking: { icon: 'volume-high' as const, label: 'Speaking...', color: '#4A90D9', ringColor: 'rgba(74,144,217,0.3)' },
};

export default function JobModeView({ aiState, onPause, isPaused }: JobModeViewProps) {
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const ringOpacity = useRef(new Animated.Value(0.3)).current;
  const dotOpacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    pulseAnim.stopAnimation();
    ringOpacity.stopAnimation();
    dotOpacity.stopAnimation();

    if (aiState === 'monitoring') {
      // Slow, calm pulse
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.08, duration: 2500, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 2500, useNativeDriver: true }),
        ])
      ).start();
      Animated.loop(
        Animated.sequence([
          Animated.timing(ringOpacity, { toValue: 0.6, duration: 2500, useNativeDriver: true }),
          Animated.timing(ringOpacity, { toValue: 0.2, duration: 2500, useNativeDriver: true }),
        ])
      ).start();
    } else if (aiState === 'listening') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.2, duration: 300, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 300, useNativeDriver: true }),
        ])
      ).start();
      Animated.timing(ringOpacity, { toValue: 0.8, duration: 200, useNativeDriver: true }).start();
    } else if (aiState === 'processing') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.05, duration: 800, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 0.95, duration: 800, useNativeDriver: true }),
        ])
      ).start();
      Animated.timing(ringOpacity, { toValue: 0.5, duration: 200, useNativeDriver: true }).start();
    } else if (aiState === 'speaking') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.12, duration: 500, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
        ])
      ).start();
      Animated.timing(ringOpacity, { toValue: 0.7, duration: 200, useNativeDriver: true }).start();
    }

    // Blinking recording dot
    Animated.loop(
      Animated.sequence([
        Animated.timing(dotOpacity, { toValue: 0.3, duration: 800, useNativeDriver: true }),
        Animated.timing(dotOpacity, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();

    return () => {
      pulseAnim.stopAnimation();
      ringOpacity.stopAnimation();
      dotOpacity.stopAnimation();
    };
  }, [aiState]);

  const config = STATE_CONFIG[aiState];

  return (
    <View style={styles.container}>
      {/* LIVE indicator */}
      <View style={styles.liveRow}>
        <Animated.View style={[styles.liveDot, { opacity: dotOpacity }]} />
        <Text style={styles.liveText}>LIVE</Text>
      </View>

      {/* Main status ring */}
      <View style={styles.ringContainer}>
        <Animated.View
          style={[
            styles.outerRing,
            {
              borderColor: config.color,
              backgroundColor: config.ringColor,
              transform: [{ scale: pulseAnim }],
              opacity: ringOpacity,
            },
          ]}
        />
        <View style={[styles.innerCircle, { backgroundColor: config.color }]}>
          <Ionicons name={config.icon} size={40} color="#FFF" />
        </View>
      </View>

      <Text style={[styles.stateLabel, { color: config.color }]}>{config.label}</Text>
      <Text style={styles.subtitle}>
        {aiState === 'monitoring' ? 'Watching for issues...' :
         aiState === 'listening' ? 'Hearing you...' :
         aiState === 'processing' ? 'Analyzing...' :
         'Responding...'}
      </Text>

      {/* Pause button */}
      {onPause && (
        <TouchableOpacity style={styles.pauseButton} onPress={onPause} activeOpacity={0.7}>
          <Ionicons name={isPaused ? 'play' : 'pause'} size={18} color="rgba(255,255,255,0.8)" />
          <Text style={styles.pauseText}>{isPaused ? 'Resume' : 'Pause'}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 40,
  },
  liveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 40,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FF3B30',
  },
  liveText: {
    color: '#FF3B30',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 2,
  },
  ringContainer: {
    width: 160,
    height: 160,
    justifyContent: 'center',
    alignItems: 'center',
  },
  outerRing: {
    position: 'absolute',
    width: 160,
    height: 160,
    borderRadius: 80,
    borderWidth: 3,
  },
  innerCircle: {
    width: 90,
    height: 90,
    borderRadius: 45,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stateLabel: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 24,
  },
  subtitle: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 14,
    marginTop: 6,
  },
  pauseButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 32,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  pauseText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 14,
    fontWeight: '500',
  },
});
