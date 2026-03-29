/**
 * OnboardingModal — "How Arrival Works"
 * Plays an ElevenLabs narration and shows 4 slides covering Voice, Job, Text, and Docs.
 * Auto-shown on first 3 app opens. Accessible via "How it Works" button at any time.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import {
  cacheDirectory,
  EncodingType,
  writeAsStringAsync,
  deleteAsync,
} from 'expo-file-system/legacy';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import api from '../services/api';
import { Colors, Spacing, Radius, FontSize } from '../constants/Colors';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface Slide {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  title: string;
  body: string;
  /** ms into audio playback when this slide becomes active */
  startMs: number;
}

const SLIDES: Slide[] = [
  {
    icon: 'mic',
    title: 'Voice Mode',
    body: 'Tap the button and ask anything.\nWire sizes, torque specs, error codes, code requirements — a real answer in seconds.',
    startMs: 0,
  },
  {
    icon: 'camera',
    title: 'Job Mode',
    body: "Arrival watches through your camera while you work. It flags issues before they become problems.\nSay 'Guide Me' to walk through a job hands free.",
    startMs: 10500,
  },
  {
    icon: 'chatbubble-ellipses',
    title: 'Text Mode',
    body: 'Type a question or attach a photo.\nArrival reads it and gives you exactly what you need.',
    startMs: 24000,
  },
  {
    icon: 'document-text',
    title: 'Company Documents',
    body: 'Upload your manuals, SOPs, and spec sheets.\nArrival pulls from them in every answer — your team\'s knowledge, always on site.',
    startMs: 33000,
  },
];

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function OnboardingModal({ visible, onClose }: Props) {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slideIdx, setSlideIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [finished, setFinished] = useState(false);

  const soundRef = useRef<Audio.Sound | null>(null);
  const tempFileRef = useRef<string | null>(null);
  const slideAnim = useRef(new Animated.Value(1)).current;
  const statusIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Animate slide change
  const transitionSlide = useCallback((nextIdx: number) => {
    Animated.sequence([
      Animated.timing(slideAnim, { toValue: 0, duration: 150, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 1, duration: 250, useNativeDriver: true }),
    ]).start();
    setSlideIdx(nextIdx);
  }, [slideAnim]);

  const cleanup = useCallback(async () => {
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
      statusIntervalRef.current = null;
    }
    if (soundRef.current) {
      try {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
      } catch {}
      soundRef.current = null;
    }
    if (tempFileRef.current) {
      await deleteAsync(tempFileRef.current, { idempotent: true }).catch(() => {});
      tempFileRef.current = null;
    }
  }, []);

  const playNarration = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    setSlideIdx(0);
    setFinished(false);
    setPlaying(false);

    try {
      const res = await api.get('/onboarding-narration');
      const audioB64: string = res.data.audio_base64;

      await cleanup();

      const fileUri = `${cacheDirectory}onboarding_${Date.now()}.mp3`;
      await writeAsStringAsync(fileUri, audioB64, { encoding: EncodingType.Base64 });
      tempFileRef.current = fileUri;

      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });

      const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
      soundRef.current = sound;

      // Poll position every 500ms and advance slides
      statusIntervalRef.current = setInterval(async () => {
        if (!soundRef.current) return;
        try {
          const status = await soundRef.current.getStatusAsync() as any;
          if (!status.isLoaded) return;
          const pos = status.positionMillis ?? 0;
          // Find which slide we should be on
          for (let i = SLIDES.length - 1; i >= 0; i--) {
            if (pos >= SLIDES[i].startMs) {
              setSlideIdx(prev => {
                if (prev !== i) {
                  transitionSlide(i);
                  return i;
                }
                return prev;
              });
              break;
            }
          }
        } catch {}
      }, 400);

      sound.setOnPlaybackStatusUpdate(async (status: any) => {
        if (!status.isLoaded) {
          setPlaying(false);
          return;
        }
        setPlaying(status.isPlaying);
        if (status.didJustFinish) {
          setPlaying(false);
          setFinished(true);
          if (statusIntervalRef.current) {
            clearInterval(statusIntervalRef.current);
            statusIntervalRef.current = null;
          }
          // Show last slide for a moment then offer "Got it"
        }
      });

      await sound.playAsync();
      setPlaying(true);
    } catch (e: any) {
      console.error('[onboarding] playback failed:', e);
      setError('Could not load narration. Check your connection.');
    } finally {
      setLoading(false);
    }
  }, [loading, cleanup, transitionSlide]);

  // Start playing when modal opens
  useEffect(() => {
    if (visible) {
      setSlideIdx(0);
      setFinished(false);
      playNarration();
    } else {
      cleanup();
    }
    return () => { cleanup(); };
  }, [visible]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClose = useCallback(async () => {
    await cleanup();
    onClose();
  }, [cleanup, onClose]);

  const handleReplay = useCallback(() => {
    playNarration();
  }, [playNarration]);

  const slide = SLIDES[slideIdx];

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={handleClose}
    >
      <View style={styles.overlay}>
        <View style={[styles.card, { paddingTop: insets.top > 0 ? insets.top + 8 : 24 }]}>
          {/* Header row */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>How Arrival Works</Text>
            <TouchableOpacity onPress={handleClose} style={styles.skipBtn} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Text style={styles.skipText}>Skip</Text>
            </TouchableOpacity>
          </View>

          {/* Slide content */}
          <Animated.View style={[styles.slideContent, { opacity: slideAnim }]}>
            <View style={styles.iconCircle}>
              <Ionicons name={slide.icon} size={36} color={Colors.accent} />
            </View>
            <Text style={styles.slideTitle}>{slide.title}</Text>
            <Text style={styles.slideBody}>{slide.body}</Text>
          </Animated.View>

          {/* Progress dots */}
          <View style={styles.dots}>
            {SLIDES.map((_, i) => (
              <View
                key={i}
                style={[
                  styles.dot,
                  i === slideIdx && styles.dotActive,
                ]}
              />
            ))}
          </View>

          {/* Status / Actions */}
          <View style={styles.actions}>
            {loading && (
              <View style={styles.loadingRow}>
                <ActivityIndicator size="small" color={Colors.accent} />
                <Text style={styles.loadingText}>Loading...</Text>
              </View>
            )}

            {error && (
              <View style={styles.errorRow}>
                <Text style={styles.errorText}>{error}</Text>
                <TouchableOpacity onPress={handleReplay} style={styles.retryBtn}>
                  <Text style={styles.retryText}>Retry</Text>
                </TouchableOpacity>
              </View>
            )}

            {!loading && !error && finished && (
              <View style={styles.finishedRow}>
                <TouchableOpacity onPress={handleReplay} style={styles.replayBtn}>
                  <Ionicons name="refresh" size={16} color={Colors.textSecondary} />
                  <Text style={styles.replayText}>Replay</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={handleClose} style={styles.gotItBtn}>
                  <Text style={styles.gotItText}>Got it</Text>
                </TouchableOpacity>
              </View>
            )}

            {!loading && !error && !finished && playing && (
              <View style={styles.playingRow}>
                <View style={styles.playingDot} />
                <Text style={styles.playingText}>Playing</Text>
              </View>
            )}
          </View>

          {/* Bottom safe area */}
          <View style={{ height: insets.bottom + 8 }} />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.88)',
    justifyContent: 'flex-end',
  },
  card: {
    backgroundColor: '#1A1A1C',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: Spacing.lg,
    minHeight: SCREEN_WIDTH * 0.9,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.xl,
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: FontSize.lg,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  skipBtn: {
    paddingVertical: 4,
  },
  skipText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  slideContent: {
    alignItems: 'center',
    paddingHorizontal: Spacing.base,
    flex: 1,
    justifyContent: 'center',
    minHeight: 220,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(212,132,42,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.lg,
  },
  slideTitle: {
    color: '#FFFFFF',
    fontSize: FontSize.xl,
    fontWeight: '700',
    marginBottom: Spacing.sm,
    textAlign: 'center',
    letterSpacing: 0.3,
  },
  slideBody: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: FontSize.base,
    lineHeight: 24,
    textAlign: 'center',
  },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginTop: Spacing.lg,
    marginBottom: Spacing.base,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  dotActive: {
    backgroundColor: Colors.accent,
    width: 20,
  },
  actions: {
    minHeight: 52,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: Spacing.sm,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  loadingText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  errorRow: {
    alignItems: 'center',
    gap: 8,
  },
  errorText: {
    color: Colors.error,
    fontSize: FontSize.sm,
    textAlign: 'center',
  },
  retryBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: Radius.full,
  },
  retryText: {
    color: '#FFFFFF',
    fontSize: FontSize.sm,
  },
  finishedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  replayBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  replayText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  gotItBtn: {
    paddingHorizontal: 28,
    paddingVertical: 12,
    borderRadius: Radius.full,
    backgroundColor: Colors.accent,
  },
  gotItText: {
    color: '#FFFFFF',
    fontSize: FontSize.base,
    fontWeight: '600',
  },
  playingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  playingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.accent,
  },
  playingText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
});
