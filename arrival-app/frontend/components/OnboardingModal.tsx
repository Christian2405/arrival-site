/**
 * OnboardingModal — "How Arrival Works"
 * Swipeable slides with ElevenLabs voice narration.
 * Auto-shown first 3 opens. "How it Works" button replays anytime.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
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

const { width: W, height: H } = Dimensions.get('window');

interface Slide {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  iconColor: string;
  bg: string;
  tag: string;
  title: string;
  bullets: string[];
  audioStartMs: number;
}

const SLIDES: Slide[] = [
  {
    icon: 'mic-outline',
    iconColor: '#FFFFFF',
    bg: '#1C2333',
    tag: 'VOICE MODE',
    title: 'Ask anything, hands free',
    bullets: [
      'Hold the mic button and speak naturally',
      'Wire sizes, torque specs, error codes, code compliance',
      'Answer comes back in seconds via voice',
    ],
    audioStartMs: 0,
  },
  {
    icon: 'camera-outline',
    iconColor: '#FFFFFF',
    bg: '#1C2A24',
    tag: 'JOB MODE',
    title: 'Arrival watches while you work',
    bullets: [
      'Camera stays on — Arrival monitors continuously',
      'Flags issues before they become problems',
      "Say 'Guide Me' for step-by-step guidance, hands free",
    ],
    audioStartMs: 10500,
  },
  {
    icon: 'chatbubble-ellipses-outline',
    iconColor: '#FFFFFF',
    bg: '#1C1C2E',
    tag: 'TEXT MODE',
    title: 'Type it or photo it',
    bullets: [
      'Type any question and get a detailed answer',
      'Attach a photo — Arrival reads it',
      'Full chat history saved automatically',
    ],
    audioStartMs: 24000,
  },
  {
    icon: 'document-text-outline',
    iconColor: '#FFFFFF',
    bg: '#2A1C1C',
    tag: 'DOCUMENTS',
    title: "Your team's knowledge, on site",
    bullets: [
      'Upload manuals, SOPs, and spec sheets',
      'Arrival references them in every answer',
      'Works alongside the built-in trade knowledge base',
    ],
    audioStartMs: 33000,
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
  const [finished, setFinished] = useState(false);

  const scrollRef = useRef<ScrollView>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const tempFileRef = useRef<string | null>(null);
  const audioIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Track manual vs audio-driven scroll to avoid fighting each other
  const isManualScrollRef = useRef(false);
  const manualScrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopAudio = useCallback(async () => {
    if (audioIntervalRef.current) {
      clearInterval(audioIntervalRef.current);
      audioIntervalRef.current = null;
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

  const scrollToSlide = useCallback((idx: number, animated = true) => {
    scrollRef.current?.scrollTo({ x: idx * W, animated });
    setSlideIdx(idx);
  }, []);

  const goNext = useCallback(() => {
    const next = Math.min(slideIdx + 1, SLIDES.length - 1);
    isManualScrollRef.current = true;
    if (manualScrollTimeoutRef.current) clearTimeout(manualScrollTimeoutRef.current);
    manualScrollTimeoutRef.current = setTimeout(() => { isManualScrollRef.current = false; }, 1500);
    scrollToSlide(next);
    if (next === SLIDES.length - 1) setFinished(true);
  }, [slideIdx, scrollToSlide]);

  const goBack = useCallback(() => {
    isManualScrollRef.current = true;
    if (manualScrollTimeoutRef.current) clearTimeout(manualScrollTimeoutRef.current);
    manualScrollTimeoutRef.current = setTimeout(() => { isManualScrollRef.current = false; }, 1500);
    scrollToSlide(Math.max(slideIdx - 1, 0));
  }, [slideIdx, scrollToSlide]);

  const playNarration = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    setFinished(false);
    scrollToSlide(0, false);

    try {
      const res = await api.get('/onboarding-narration');
      const audioB64: string = res.data.audio_base64;

      await stopAudio();

      const fileUri = `${cacheDirectory}onboarding_${Date.now()}.mp3`;
      await writeAsStringAsync(fileUri, audioB64, { encoding: EncodingType.Base64 });
      tempFileRef.current = fileUri;

      // NOTE: Do NOT call Audio.setAudioModeAsync here — it disrupts the
      // camera session and LiveKit audio. The app's existing audio mode is fine.
      const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
      soundRef.current = sound;

      // Poll position and auto-advance slides (only when user isn't manually scrolling)
      audioIntervalRef.current = setInterval(async () => {
        if (!soundRef.current || isManualScrollRef.current) return;
        try {
          const status = await soundRef.current.getStatusAsync() as any;
          if (!status.isLoaded) return;
          const pos: number = status.positionMillis ?? 0;
          for (let i = SLIDES.length - 1; i >= 0; i--) {
            if (pos >= SLIDES[i].audioStartMs) {
              setSlideIdx(prev => {
                if (prev !== i) scrollToSlide(i);
                return i;
              });
              break;
            }
          }
        } catch {}
      }, 500);

      sound.setOnPlaybackStatusUpdate((status: any) => {
        if (status.isLoaded && status.didJustFinish) {
          setFinished(true);
          if (audioIntervalRef.current) {
            clearInterval(audioIntervalRef.current);
            audioIntervalRef.current = null;
          }
        }
      });

      await sound.playAsync();
    } catch (e: any) {
      console.error('[onboarding] failed:', e);
      setError('Could not load audio. Check your connection.');
    } finally {
      setLoading(false);
    }
  }, [loading, stopAudio, scrollToSlide]);

  useEffect(() => {
    if (visible) {
      setSlideIdx(0);
      setFinished(false);
      playNarration();
    } else {
      stopAudio();
    }
    return () => { stopAudio(); };
  }, [visible]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClose = useCallback(async () => {
    await stopAudio();
    onClose();
  }, [stopAudio, onClose]);

  return (
    <Modal
      visible={visible}
      transparent={false}
      animationType="slide"
      statusBarTranslucent
      onRequestClose={handleClose}
    >
      <View style={[styles.root, { backgroundColor: SLIDES[slideIdx]?.bg ?? '#1C2333' }]}>
        {/* Header */}
        <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
          <Text style={styles.headerLabel}>HOW ARRIVAL WORKS</Text>
          <TouchableOpacity
            onPress={handleClose}
            hitSlop={{ top: 12, bottom: 12, left: 16, right: 16 }}
          >
            <Text style={styles.skipText}>Skip</Text>
          </TouchableOpacity>
        </View>

        {/* Slides */}
        <ScrollView
          ref={scrollRef}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          scrollEventThrottle={16}
          onMomentumScrollEnd={(e) => {
            const idx = Math.round(e.nativeEvent.contentOffset.x / W);
            isManualScrollRef.current = true;
            if (manualScrollTimeoutRef.current) clearTimeout(manualScrollTimeoutRef.current);
            manualScrollTimeoutRef.current = setTimeout(() => { isManualScrollRef.current = false; }, 1500);
            setSlideIdx(idx);
            if (idx === SLIDES.length - 1) setFinished(true);
          }}
          style={styles.scrollView}
        >
          {SLIDES.map((slide, i) => (
            <View key={i} style={styles.slide}>
              {/* Big icon */}
              <View style={styles.iconWrap}>
                <Ionicons name={slide.icon} size={56} color={slide.iconColor} />
              </View>

              {/* Tag + title */}
              <Text style={styles.tag}>{slide.tag}</Text>
              <Text style={styles.title}>{slide.title}</Text>

              {/* Bullets */}
              <View style={styles.bullets}>
                {slide.bullets.map((b, j) => (
                  <View key={j} style={styles.bulletRow}>
                    <View style={styles.bulletDot} />
                    <Text style={styles.bulletText}>{b}</Text>
                  </View>
                ))}
              </View>
            </View>
          ))}
        </ScrollView>

        {/* Bottom controls */}
        <View style={[styles.footer, { paddingBottom: insets.bottom + 16 }]}>
          {/* Dots */}
          <View style={styles.dots}>
            {SLIDES.map((_, i) => (
              <TouchableOpacity
                key={i}
                onPress={() => { isManualScrollRef.current = true; scrollToSlide(i); }}
                hitSlop={{ top: 8, bottom: 8, left: 6, right: 6 }}
              >
                <View style={[styles.dot, i === slideIdx && styles.dotActive]} />
              </TouchableOpacity>
            ))}
          </View>

          {/* Audio status */}
          {loading && (
            <View style={styles.audioStatus}>
              <ActivityIndicator size="small" color="rgba(255,255,255,0.4)" />
              <Text style={styles.audioStatusText}>Loading audio...</Text>
            </View>
          )}
          {error && (
            <TouchableOpacity onPress={playNarration} style={styles.audioStatus}>
              <Ionicons name="refresh" size={14} color="rgba(255,255,255,0.5)" />
              <Text style={styles.audioStatusText}>Retry audio</Text>
            </TouchableOpacity>
          )}

          {/* Nav buttons */}
          <View style={styles.navRow}>
            <TouchableOpacity
              onPress={goBack}
              style={[styles.navBtn, slideIdx === 0 && styles.navBtnDisabled]}
              disabled={slideIdx === 0}
            >
              <Ionicons name="chevron-back" size={20} color={slideIdx === 0 ? 'rgba(255,255,255,0.2)' : '#FFF'} />
              <Text style={[styles.navBtnText, slideIdx === 0 && styles.navBtnTextDisabled]}>Back</Text>
            </TouchableOpacity>

            {finished || slideIdx === SLIDES.length - 1 ? (
              <TouchableOpacity onPress={handleClose} style={styles.doneBtn}>
                <Text style={styles.doneBtnText}>Got it</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity onPress={goNext} style={styles.nextBtn}>
                <Text style={styles.nextBtnText}>Next</Text>
                <Ionicons name="chevron-forward" size={20} color="#FFF" />
              </TouchableOpacity>
            )}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.base,
  },
  headerLabel: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.4,
  },
  skipText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: FontSize.sm,
  },
  scrollView: {
    flex: 1,
  },
  slide: {
    width: W,
    flex: 1,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.xl,
    justifyContent: 'center',
  },
  iconWrap: {
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: 'rgba(255,255,255,0.08)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.lg,
  },
  tag: {
    color: Colors.accent,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.6,
    marginBottom: 10,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 26,
    fontWeight: '700',
    lineHeight: 34,
    marginBottom: Spacing.lg,
  },
  bullets: {
    gap: 14,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  bulletDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.accent,
    marginTop: 8,
  },
  bulletText: {
    color: 'rgba(255,255,255,0.75)',
    fontSize: FontSize.base,
    lineHeight: 24,
    flex: 1,
  },
  footer: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.base,
    gap: 16,
  },
  dots: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  dotActive: {
    backgroundColor: Colors.accent,
    width: 22,
    borderRadius: 4,
  },
  audioStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  audioStatusText: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 12,
  },
  navRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  navBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 12,
    paddingHorizontal: 8,
    minWidth: 80,
  },
  navBtnDisabled: {
    opacity: 0.3,
  },
  navBtnText: {
    color: '#FFFFFF',
    fontSize: FontSize.base,
  },
  navBtnTextDisabled: {
    color: 'rgba(255,255,255,0.3)',
  },
  nextBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: Radius.full,
  },
  nextBtnText: {
    color: '#FFFFFF',
    fontSize: FontSize.base,
    fontWeight: '600',
  },
  doneBtn: {
    backgroundColor: Colors.accent,
    paddingVertical: 14,
    paddingHorizontal: 36,
    borderRadius: Radius.full,
  },
  doneBtnText: {
    color: '#FFFFFF',
    fontSize: FontSize.base,
    fontWeight: '700',
  },
});
