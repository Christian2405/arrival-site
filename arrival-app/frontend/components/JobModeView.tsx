import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, Animated, StyleSheet, TouchableOpacity, ScrollView, TextInput, Pressable, Image, Easing } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Radius, FontSize, IconSize } from '../constants/Colors';
import { jobContextAPI, JobContext } from '../services/api';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const robotMascot = require('../assets/robot-mascot.png');

export type JobAIState = 'monitoring' | 'listening' | 'processing' | 'speaking';

export type QuickActionType = 'text' | 'explain' | 'walkthrough' | 'guidance_stop';

export interface JobAlert {
  message: string;
  severity: string;
  ts?: number;
}

export interface EquipmentInfo {
  equipment_type: string;
  brand?: string;
  model?: string;
}

interface JobModeViewProps {
  aiState: JobAIState;
  voiceConnected?: boolean;
  onPause?: () => void;
  isPaused?: boolean;
  lastAlert?: JobAlert | null;
  onQuickAction?: (action: QuickActionType, alertMessage: string) => void;
  /** Called when user taps to interrupt AI speaking */
  onInterrupt?: () => void;
  /** Called when user taps the robot to start job mode */
  onStart?: () => void;
  /** Whether job mode session is actively running */
  isStarted?: boolean;
  /** Called when equipment context changes (set or cleared) */
  onEquipmentChange?: (equipment: EquipmentInfo | null) => void;
  /** Whether guidance is currently active */
  guidanceActive?: boolean;
}

const EQUIPMENT_OPTIONS = [
  { key: 'furnace', label: 'Furnace', icon: 'flame-outline' as const },
  { key: 'air_conditioner', label: 'AC', icon: 'snow-outline' as const },
  { key: 'heat_pump', label: 'Heat Pump', icon: 'swap-horizontal-outline' as const },
  { key: 'water_heater', label: 'Water Heater', icon: 'water-outline' as const },
  { key: 'tankless', label: 'Tankless', icon: 'flash-outline' as const },
  { key: 'mini_split', label: 'Mini Split', icon: 'grid-outline' as const },
  { key: 'electrical_panel', label: 'Panel', icon: 'flash-outline' as const },
  { key: 'boiler', label: 'Boiler', icon: 'thermometer-outline' as const },
  { key: 'plumbing', label: 'Plumbing', icon: 'construct-outline' as const },
];

const TOP_BRANDS = [
  'Carrier', 'Trane', 'Lennox', 'Rheem', 'Goodman',
  'Daikin', 'Mitsubishi', 'Rinnai', 'AO Smith', 'Square D',
];

const QUICK_ACTIONS: { key: QuickActionType; icon: string; label: string }[] = [
  { key: 'text', icon: 'document-text-outline', label: 'Show in text' },
  { key: 'explain', icon: 'chatbubble-outline', label: 'Explain more' },
  { key: 'walkthrough', icon: 'list-outline', label: 'Walk me through it' },
];

const CHIP_AUTO_DISMISS_MS = 8000;
const TEXT_DISPLAY_MS = 10000;

export default function JobModeView({
  aiState, voiceConnected, onPause, isPaused, lastAlert,
  onQuickAction, onInterrupt, onStart, isStarted, onEquipmentChange,
  guidanceActive,
}: JobModeViewProps) {
  // ── Robot start button animations ──

  const robotScale = useRef(new Animated.Value(1)).current;
  const glowOpacity = useRef(new Animated.Value(0.3)).current;
  const glowScale = useRef(new Animated.Value(1)).current;
  const startScreenOpacity = useRef(new Animated.Value(1)).current;
  const hintOpacity = useRef(new Animated.Value(0)).current;
  const [startAnimating, setStartAnimating] = useState(false);

  // ── Glass pill animations ──
  const eyeGlow = useRef(new Animated.Value(0.5)).current;
  const voicePulse = useRef(new Animated.Value(1)).current;
  const interruptOpacity = useRef(new Animated.Value(0)).current;

  // Quick action chips state
  const chipsOpacity = useRef(new Animated.Value(0)).current;
  const chipsTranslateY = useRef(new Animated.Value(20)).current;
  const [showChips, setShowChips] = useState(false);
  const [activeAlert, setActiveAlert] = useState<JobAlert | null>(null);
  const chipsDismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // "Show in text" display state
  const textCardOpacity = useRef(new Animated.Value(0)).current;
  const [textCardMessage, setTextCardMessage] = useState<string | null>(null);
  const textDismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Equipment context state
  const [jobContext, setJobContext] = useState<JobContext | null>(null);
  const [showEquipmentPicker, setShowEquipmentPicker] = useState(false);
  const [selectedEquipment, setSelectedEquipment] = useState<string | null>(null);
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [modelInput, setModelInput] = useState('');

  // Load existing context on mount
  useEffect(() => {
    jobContextAPI.get().then(ctx => {
      if (ctx) setJobContext(ctx);
    }).catch(() => {});
  }, []);

  // ── Robot idle animations (breathing float + glow pulse) ──
  // Use a single linear 0→1 animation mapped via interpolation to avoid loop seam jank
  const floatDriver = useRef(new Animated.Value(0)).current;
  const glowDriver = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (isStarted) return;

    floatDriver.setValue(0);
    glowDriver.setValue(0);

    // Single continuous animation — no sequence, no seam
    const floatAnim = Animated.loop(
      Animated.timing(floatDriver, { toValue: 1, duration: 4000, easing: Easing.linear, useNativeDriver: true })
    );
    floatAnim.start();

    const glowAnim = Animated.loop(
      Animated.timing(glowDriver, { toValue: 1, duration: 3600, easing: Easing.linear, useNativeDriver: true })
    );
    glowAnim.start();

    // Fade in "Tap to start" hint after 1.5s
    const hintTimer = setTimeout(() => {
      Animated.timing(hintOpacity, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    }, 1500);

    return () => {
      floatAnim.stop();
      glowAnim.stop();
      clearTimeout(hintTimer);
    };
  }, [isStarted, floatDriver, glowDriver, hintOpacity]);

  // ── Start tap animation ──
  const handleStartTap = useCallback(() => {
    if (startAnimating) return;
    setStartAnimating(true);

    // 1. Quick pop scale
    Animated.sequence([
      Animated.timing(robotScale, { toValue: 1.2, duration: 150, easing: Easing.out(Easing.back(2)), useNativeDriver: true }),
      Animated.timing(robotScale, { toValue: 1.1, duration: 100, useNativeDriver: true }),
    ]).start();

    // 2. Glow ring expands out
    Animated.parallel([
      Animated.timing(glowScale, { toValue: 2.5, duration: 500, easing: Easing.out(Easing.ease), useNativeDriver: true }),
      Animated.timing(glowOpacity, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();

    // 3. After pop, fade out the whole start screen
    setTimeout(() => {
      Animated.timing(startScreenOpacity, { toValue: 0, duration: 300, useNativeDriver: true }).start(() => {
        onStart?.();
      });
    }, 350);
  }, [startAnimating, robotScale, glowScale, glowOpacity, startScreenOpacity, onStart]);

  const handleSetContext = useCallback(async () => {
    if (!selectedEquipment) return;
    try {
      const ctx = await jobContextAPI.set({
        equipment_type: selectedEquipment,
        brand: selectedBrand || undefined,
        model: modelInput || undefined,
      });
      setJobContext(ctx);
      setShowEquipmentPicker(false);
      // Notify parent so it can send via data channel
      onEquipmentChange?.({
        equipment_type: selectedEquipment,
        brand: selectedBrand || undefined,
        model: modelInput || undefined,
      });
    } catch (e) {
      console.warn('[JobMode] Failed to set context:', e);
    }
  }, [selectedEquipment, selectedBrand, modelInput, onEquipmentChange]);

  const handleClearContext = useCallback(async () => {
    try {
      await jobContextAPI.clear();
      setJobContext(null);
      setSelectedEquipment(null);
      setSelectedBrand(null);
      setModelInput('');
      onEquipmentChange?.(null);
    } catch (e) {
      console.warn('[JobMode] Failed to clear context:', e);
    }
  }, [onEquipmentChange]);

  // --- Eye pill: subtle glow when monitoring/analyzing ---
  useEffect(() => {
    if (!isStarted) return;
    eyeGlow.stopAnimation();
    Animated.loop(
      Animated.sequence([
        Animated.timing(eyeGlow, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(eyeGlow, { toValue: 0.5, duration: 2000, useNativeDriver: true }),
      ])
    ).start();
    return () => { eyeGlow.stopAnimation(); };
  }, [eyeGlow, isStarted]);

  // --- Voice pill: reacts to state ---
  useEffect(() => {
    if (!isStarted) return;
    voicePulse.stopAnimation();
    if (aiState === 'listening') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(voicePulse, { toValue: 1.2, duration: 400, useNativeDriver: true }),
          Animated.timing(voicePulse, { toValue: 1, duration: 400, useNativeDriver: true }),
        ])
      ).start();
    } else if (aiState === 'speaking') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(voicePulse, { toValue: 1.1, duration: 500, useNativeDriver: true }),
          Animated.timing(voicePulse, { toValue: 1, duration: 500, useNativeDriver: true }),
        ])
      ).start();
    } else {
      voicePulse.setValue(1);
    }
    return () => { voicePulse.stopAnimation(); };
  }, [aiState, voicePulse, isStarted]);

  // --- Interrupt hint: fade in when speaking ---
  useEffect(() => {
    if (!isStarted) return;
    Animated.timing(interruptOpacity, {
      toValue: aiState === 'speaking' ? 1 : 0,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }, [aiState, interruptOpacity, isStarted]);

  // --- Quick Action Chips ---
  useEffect(() => {
    if (lastAlert && lastAlert.message && aiState === 'monitoring') {
      setActiveAlert(lastAlert);
      setShowChips(true);
      dismissTextCard();
      chipsOpacity.setValue(0);
      chipsTranslateY.setValue(20);
      Animated.parallel([
        Animated.timing(chipsOpacity, { toValue: 1, duration: 300, useNativeDriver: true }),
        Animated.timing(chipsTranslateY, { toValue: 0, duration: 300, useNativeDriver: true }),
      ]).start();
      if (chipsDismissTimer.current) clearTimeout(chipsDismissTimer.current);
      chipsDismissTimer.current = setTimeout(() => { dismissChips(); }, CHIP_AUTO_DISMISS_MS);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastAlert, aiState]);

  useEffect(() => {
    if (aiState !== 'monitoring' && showChips) { dismissChips(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiState]);

  const dismissChips = useCallback(() => {
    if (chipsDismissTimer.current) { clearTimeout(chipsDismissTimer.current); chipsDismissTimer.current = null; }
    Animated.parallel([
      Animated.timing(chipsOpacity, { toValue: 0, duration: 200, useNativeDriver: true }),
      Animated.timing(chipsTranslateY, { toValue: 10, duration: 200, useNativeDriver: true }),
    ]).start(() => { setShowChips(false); setActiveAlert(null); });
  }, [chipsOpacity, chipsTranslateY]);

  const dismissTextCard = useCallback(() => {
    if (textDismissTimer.current) { clearTimeout(textDismissTimer.current); textDismissTimer.current = null; }
    Animated.timing(textCardOpacity, { toValue: 0, duration: 250, useNativeDriver: true }).start(() => {
      setTextCardMessage(null);
    });
  }, [textCardOpacity]);

  const handleQuickAction = useCallback((action: QuickActionType) => {
    if (!activeAlert) return;
    const msg = activeAlert.message;
    dismissChips();
    if (action === 'text') {
      setTextCardMessage(msg);
      textCardOpacity.setValue(0);
      Animated.timing(textCardOpacity, { toValue: 1, duration: 300, useNativeDriver: true }).start();
      if (textDismissTimer.current) clearTimeout(textDismissTimer.current);
      textDismissTimer.current = setTimeout(() => { dismissTextCard(); }, TEXT_DISPLAY_MS);
    } else {
      onQuickAction?.(action, msg);
    }
  }, [activeAlert, dismissChips, onQuickAction, textCardOpacity, dismissTextCard]);

  useEffect(() => {
    return () => {
      if (chipsDismissTimer.current) clearTimeout(chipsDismissTimer.current);
      if (textDismissTimer.current) clearTimeout(textDismissTimer.current);
    };
  }, []);

  // Voice icon and color based on state
  const voiceIcon: keyof typeof Ionicons.glyphMap =
    aiState === 'speaking' ? 'volume-high' :
    aiState === 'processing' ? 'ellipsis-horizontal' :
    'mic';
  const voiceColor =
    aiState === 'listening' ? '#FF9500' :
    aiState === 'speaking' ? '#4A90D9' :
    aiState === 'processing' ? Colors.accent :
    voiceConnected ? '#34C759' : 'rgba(255,255,255,0.25)';
  const voiceActive = aiState !== 'monitoring';

  const equipLabel = jobContext
    ? `${jobContext.brand || ''} ${jobContext.equipment_type.replace('_', ' ')}${jobContext.model ? ` (${jobContext.model})` : ''}`.trim()
    : null;

  // ════════════════════════════════════════════════════
  // ██  PRE-START SCREEN — Robot mascot button  ██
  // ════════════════════════════════════════════════════
  if (!isStarted) {
    return (
      <Animated.View style={[s.container, { opacity: startScreenOpacity }]} pointerEvents="box-none">
        <Pressable onPress={handleStartTap} style={s.startButton}>
          {/* Floating robot mascot */}
          <Animated.View style={{
            transform: [
              { translateY: floatDriver.interpolate({
                inputRange:  [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0],
                outputRange: [-10, -7.07, 0, 7.07, 10, 7.07, 0, -7.07, -10],
                extrapolate: 'clamp',
              }) },
              { scale: robotScale },
            ],
          }}>
            <Image
              source={robotMascot}
              style={s.robotImage}
              resizeMode="contain"
            />
          </Animated.View>
        </Pressable>

        {/* "Tap to start" hint */}
        <Animated.View style={[s.startHint, { opacity: hintOpacity }]}>
          <Text style={s.startHintText}>Tap to start</Text>
        </Animated.View>
      </Animated.View>
    );
  }

  // ════════════════════════════════════════════════════
  // ██  ACTIVE JOB MODE — Glass pills + controls  ██
  // ════════════════════════════════════════════════════
  return (
    <View style={s.container} pointerEvents="box-none">

      {/* Equipment picker (full overlay) */}
      {showEquipmentPicker ? (
        <View style={s.pickerContainer}>
          <Text style={s.pickerTitle}>What are you working on?</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow} contentContainerStyle={s.chipRowContent}>
            {EQUIPMENT_OPTIONS.map(opt => (
              <TouchableOpacity
                key={opt.key}
                style={[s.eqChip, selectedEquipment === opt.key && s.eqChipSelected]}
                onPress={() => setSelectedEquipment(opt.key)}
                activeOpacity={0.7}
              >
                <Ionicons name={opt.icon} size={IconSize.sm} color={selectedEquipment === opt.key ? '#FFF' : 'rgba(255,255,255,0.6)'} />
                <Text style={[s.eqChipText, selectedEquipment === opt.key && s.eqChipTextSelected]}>{opt.label}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          {selectedEquipment && (
            <>
              <Text style={s.pickerSubtitle}>Brand (optional)</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow} contentContainerStyle={s.chipRowContent}>
                {TOP_BRANDS.map(brand => (
                  <TouchableOpacity
                    key={brand}
                    style={[s.eqChip, selectedBrand === brand && s.eqChipSelected]}
                    onPress={() => setSelectedBrand(selectedBrand === brand ? null : brand)}
                    activeOpacity={0.7}
                  >
                    <Text style={[s.eqChipText, selectedBrand === brand && s.eqChipTextSelected]}>{brand}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TextInput
                style={s.modelInput}
                placeholder="Model # (optional)"
                placeholderTextColor="rgba(255,255,255,0.3)"
                value={modelInput}
                onChangeText={setModelInput}
                maxLength={50}
              />
            </>
          )}
          <View style={s.pickerActions}>
            <TouchableOpacity onPress={() => setShowEquipmentPicker(false)} style={s.pickerCancel}>
              <Text style={s.pickerCancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleSetContext}
              style={[s.pickerConfirm, !selectedEquipment && s.pickerConfirmDisabled]}
              disabled={!selectedEquipment}
            >
              <Text style={s.pickerConfirmText}>Set</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <>
          {/* ── TWO GLASS PILLS ── */}
          <View style={s.pillRow}>
            {/* Eye pill — camera watching */}
            <Animated.View style={[s.pill, { opacity: eyeGlow }]}>
              <Ionicons name="eye" size={18} color="#34C759" />
            </Animated.View>

            {/* Voice pill — mic/speaker state */}
            <Animated.View style={[
              s.pill,
              voiceActive && s.pillActive,
              { transform: [{ scale: voicePulse }] },
            ]}>
              <Ionicons name={voiceIcon} size={18} color={voiceColor} />
            </Animated.View>
          </View>

          {/* Equipment badge — tap to change */}
          {jobContext ? (
            <TouchableOpacity style={s.equipBadge} onPress={() => setShowEquipmentPicker(true)} activeOpacity={0.7}>
              <Ionicons name="build-outline" size={14} color={Colors.accent} />
              <Text style={s.equipBadgeText} numberOfLines={1}>{equipLabel}</Text>
              <TouchableOpacity onPress={handleClearContext} hitSlop={8}>
                <Ionicons name="close-circle" size={14} color="rgba(255,255,255,0.3)" />
              </TouchableOpacity>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={s.setEquipBtn} onPress={() => setShowEquipmentPicker(true)} activeOpacity={0.7}>
              <Ionicons name="build-outline" size={14} color="rgba(255,255,255,0.4)" />
              <Text style={s.setEquipText}>Set equipment</Text>
            </TouchableOpacity>
          )}

          {/* Guide me / Stop guidance button */}
          <TouchableOpacity
            style={[s.guideBtn, guidanceActive && s.guideBtnStop]}
            onPress={() => {
              if (guidanceActive) {
                onQuickAction?.('guidance_stop', '');
              } else {
                onQuickAction?.('walkthrough', '');
              }
            }}
            activeOpacity={0.7}
          >
            <Ionicons name={guidanceActive ? 'stop-circle-outline' : 'compass-outline'} size={16} color="#FFF" />
            <Text style={s.guideBtnText}>{guidanceActive ? 'Stop guidance' : 'Guide me'}</Text>
          </TouchableOpacity>

          {/* "Show in text" card */}
          {textCardMessage && (
            <Animated.View style={[s.textCard, { opacity: textCardOpacity }]}>
              <TouchableOpacity style={s.textCardClose} onPress={dismissTextCard} hitSlop={8}>
                <Ionicons name="close" size={IconSize.sm} color="rgba(255,255,255,0.5)" />
              </TouchableOpacity>
              <Text style={s.textCardMsg}>{textCardMessage}</Text>
            </Animated.View>
          )}

          {/* Quick action chips — after proactive alerts only */}
          {showChips && activeAlert && (
            <Animated.View style={[s.chipsRow, { opacity: chipsOpacity, transform: [{ translateY: chipsTranslateY }] }]}>
              {QUICK_ACTIONS.map(action => (
                <TouchableOpacity
                  key={action.key}
                  style={s.actionChip}
                  onPress={() => handleQuickAction(action.key)}
                  activeOpacity={0.7}
                >
                  <Ionicons name={action.icon as any} size={14} color="#FFF" />
                  <Text style={s.actionChipText}>{action.label}</Text>
                </TouchableOpacity>
              ))}
            </Animated.View>
          )}

          {/* TAP TO INTERRUPT — full screen overlay when AI is speaking */}
          {aiState === 'speaking' && (
            <Animated.View style={[StyleSheet.absoluteFill, { opacity: interruptOpacity }]} pointerEvents="box-none">
              <Pressable style={s.interruptOverlay} onPress={onInterrupt}>
                <View style={s.interruptBadge}>
                  <Ionicons name="hand-left-outline" size={14} color="rgba(255,255,255,0.8)" />
                  <Text style={s.interruptText}>Tap to interrupt</Text>
                </View>
              </Pressable>
            </Animated.View>
          )}
        </>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 60,
  },

  // ── Robot start button ──
  startButton: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 240,
    height: 240,
  },
  robotImage: {
    width: 180,
    height: 180,
  },
  glowRing: {
    position: 'absolute',
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: Colors.accent,
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 10,
  },
  startHint: {
    marginTop: 24,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  startHintText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 14,
    fontWeight: '500',
    letterSpacing: 0.5,
  },

  // --- Two glass pills ---
  pillRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 32,
  },
  pill: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  pillActive: {
    backgroundColor: 'rgba(255,255,255,0.14)',
    borderColor: 'rgba(255,255,255,0.22)',
  },

  // --- Equipment badge ---
  equipBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 20,
    maxWidth: '75%',
  },
  equipBadgeText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 13,
    fontWeight: '500',
    flex: 1,
    textTransform: 'capitalize',
  },
  setEquipBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    borderStyle: 'dashed',
  },
  setEquipText: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 13,
  },
  guideBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 16,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  guideBtnStop: {
    backgroundColor: 'rgba(255,80,80,0.20)',
    borderColor: 'rgba(255,80,80,0.35)',
  },
  guideBtnText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },

  // --- Interrupt overlay ---
  interruptOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingBottom: 100,
  },
  interruptBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  interruptText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 13,
    fontWeight: '500',
  },

  // --- Text card ---
  textCard: {
    marginTop: 24,
    marginHorizontal: 24,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    maxWidth: '85%',
  },
  textCardClose: {
    position: 'absolute',
    top: 8,
    right: 8,
    padding: 4,
  },
  textCardMsg: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 14,
    lineHeight: 20,
    paddingRight: 20,
  },

  // --- Quick action chips ---
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: 20,
    paddingHorizontal: 20,
  },
  actionChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  actionChipText: {
    color: '#FFF',
    fontSize: 13,
    fontWeight: '600',
  },

  // --- Equipment picker ---
  pickerContainer: {
    width: '100%',
    paddingHorizontal: 20,
    flex: 1,
    justifyContent: 'center',
  },
  pickerTitle: {
    color: '#FFF',
    fontSize: FontSize.lg,
    fontWeight: '600',
    marginBottom: Spacing.base,
    textAlign: 'center',
  },
  pickerSubtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: FontSize.sm,
    marginTop: Spacing.base,
    marginBottom: Spacing.sm,
  },
  chipRow: {
    flexGrow: 0,
  },
  chipRowContent: {
    gap: Spacing.sm,
    paddingVertical: Spacing.xs,
  },
  eqChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  eqChipSelected: {
    backgroundColor: Colors.accent,
    borderColor: Colors.accent,
  },
  eqChipText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: FontSize.sm,
    fontWeight: '500',
  },
  eqChipTextSelected: {
    color: '#FFF',
  },
  modelInput: {
    marginTop: Spacing.md,
    paddingHorizontal: Spacing.base,
    paddingVertical: 10,
    borderRadius: Radius.md,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    color: '#FFF',
    fontSize: FontSize.sm,
  },
  pickerActions: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: Spacing.base,
    marginTop: Spacing.lg,
  },
  pickerCancel: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: 10,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  pickerCancelText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: FontSize.sm,
    fontWeight: '500',
  },
  pickerConfirm: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: 10,
    borderRadius: Radius.full,
    backgroundColor: Colors.accent,
  },
  pickerConfirmDisabled: {
    opacity: 0.4,
  },
  pickerConfirmText: {
    color: '#FFF',
    fontSize: FontSize.sm,
    fontWeight: '600',
  },
});
