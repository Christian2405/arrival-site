import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, Animated, StyleSheet, TouchableOpacity, ScrollView, TextInput } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';
import { jobContextAPI, JobContext } from '../services/api';

export type JobAIState = 'monitoring' | 'listening' | 'processing' | 'speaking';

export type QuickActionType = 'text' | 'explain' | 'walkthrough';

export interface JobAlert {
  message: string;
  severity: string;
  ts?: number; // Timestamp to force useEffect re-trigger on identical messages
}

interface JobModeViewProps {
  aiState: JobAIState;
  onPause?: () => void;
  isPaused?: boolean;
  /** The most recent proactive alert (frame analysis only). Triggers quick action chips. */
  lastAlert?: JobAlert | null;
  /** Called when the tech taps a quick action chip */
  onQuickAction?: (action: QuickActionType, alertMessage: string) => void;
}

// Equipment type display config
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

const STATE_CONFIG = {
  monitoring: { icon: 'eye' as const, label: 'Monitoring...', color: '#34C759', ringColor: 'rgba(52,199,89,0.3)' },
  listening: { icon: 'ear' as const, label: 'Listening...', color: '#FF9500', ringColor: 'rgba(255,149,0,0.3)' },
  processing: { icon: 'sparkles' as const, label: 'Thinking...', color: Colors.accent, ringColor: `rgba(212,132,42,0.3)` },
  speaking: { icon: 'volume-high' as const, label: 'Speaking...', color: '#4A90D9', ringColor: 'rgba(74,144,217,0.3)' },
};

const QUICK_ACTIONS: { key: QuickActionType; icon: string; label: string }[] = [
  { key: 'text', icon: 'document-text-outline', label: 'Show in text' },
  { key: 'explain', icon: 'chatbubble-outline', label: 'Explain more' },
  { key: 'walkthrough', icon: 'list-outline', label: 'Walk me through it' },
];

const CHIP_AUTO_DISMISS_MS = 8000;
const TEXT_DISPLAY_MS = 10000;

export default function JobModeView({ aiState, onPause, isPaused, lastAlert, onQuickAction }: JobModeViewProps) {
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const ringOpacity = useRef(new Animated.Value(0.3)).current;
  const dotOpacity = useRef(new Animated.Value(1)).current;

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
    } catch (e) {
      console.warn('[JobMode] Failed to set context:', e);
    }
  }, [selectedEquipment, selectedBrand, modelInput]);

  const handleClearContext = useCallback(async () => {
    try {
      await jobContextAPI.clear();
      setJobContext(null);
      setSelectedEquipment(null);
      setSelectedBrand(null);
      setModelInput('');
    } catch (e) {
      console.warn('[JobMode] Failed to clear context:', e);
    }
  }, []);

  // --- Quick Action Chips: show/hide when lastAlert changes ---
  useEffect(() => {
    if (lastAlert && lastAlert.message) {
      // New proactive alert arrived — show chips
      setActiveAlert(lastAlert);
      setShowChips(true);

      // Clear any existing text card
      dismissTextCard();

      // Animate in
      chipsOpacity.setValue(0);
      chipsTranslateY.setValue(20);
      Animated.parallel([
        Animated.timing(chipsOpacity, { toValue: 1, duration: 300, useNativeDriver: true }),
        Animated.timing(chipsTranslateY, { toValue: 0, duration: 300, useNativeDriver: true }),
      ]).start();

      // Auto-dismiss timer
      if (chipsDismissTimer.current) clearTimeout(chipsDismissTimer.current);
      chipsDismissTimer.current = setTimeout(() => {
        dismissChips();
      }, CHIP_AUTO_DISMISS_MS);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastAlert]);

  const dismissChips = useCallback(() => {
    if (chipsDismissTimer.current) {
      clearTimeout(chipsDismissTimer.current);
      chipsDismissTimer.current = null;
    }
    Animated.parallel([
      Animated.timing(chipsOpacity, { toValue: 0, duration: 200, useNativeDriver: true }),
      Animated.timing(chipsTranslateY, { toValue: 10, duration: 200, useNativeDriver: true }),
    ]).start(() => {
      setShowChips(false);
      setActiveAlert(null);
    });
  }, [chipsOpacity, chipsTranslateY]);

  const dismissTextCard = useCallback(() => {
    if (textDismissTimer.current) {
      clearTimeout(textDismissTimer.current);
      textDismissTimer.current = null;
    }
    Animated.timing(textCardOpacity, { toValue: 0, duration: 250, useNativeDriver: true }).start(() => {
      setTextCardMessage(null);
    });
  }, [textCardOpacity]);

  const handleQuickAction = useCallback((action: QuickActionType) => {
    if (!activeAlert) return;
    const msg = activeAlert.message;

    // Dismiss chips immediately
    dismissChips();

    if (action === 'text') {
      // Show the text card on screen
      setTextCardMessage(msg);
      textCardOpacity.setValue(0);
      Animated.timing(textCardOpacity, { toValue: 1, duration: 300, useNativeDriver: true }).start();
      // Auto-dismiss text card
      if (textDismissTimer.current) clearTimeout(textDismissTimer.current);
      textDismissTimer.current = setTimeout(() => {
        dismissTextCard();
      }, TEXT_DISPLAY_MS);
    } else {
      // Delegate to parent (explain / walkthrough)
      onQuickAction?.(action, msg);
    }
  }, [activeAlert, dismissChips, onQuickAction, textCardOpacity, dismissTextCard]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (chipsDismissTimer.current) clearTimeout(chipsDismissTimer.current);
      if (textDismissTimer.current) clearTimeout(textDismissTimer.current);
    };
  }, []);

  // --- Pulse animations ---
  useEffect(() => {
    pulseAnim.stopAnimation();
    ringOpacity.stopAnimation();
    dotOpacity.stopAnimation();

    if (aiState === 'monitoring') {
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

  const equipLabel = jobContext
    ? `${jobContext.brand || ''} ${jobContext.equipment_type.replace('_', ' ')}${jobContext.model ? ` (${jobContext.model})` : ''}`.trim()
    : null;

  return (
    <View style={styles.container}>
      {/* Equipment context bar */}
      {jobContext && !showEquipmentPicker ? (
        <TouchableOpacity style={styles.contextBar} onPress={() => setShowEquipmentPicker(true)} activeOpacity={0.7}>
          <Ionicons name="build-outline" size={14} color={Colors.accent} />
          <Text style={styles.contextText} numberOfLines={1}>{equipLabel}</Text>
          <TouchableOpacity onPress={handleClearContext} hitSlop={8} style={styles.contextClear}>
            <Ionicons name="close-circle" size={16} color="rgba(255,255,255,0.4)" />
          </TouchableOpacity>
        </TouchableOpacity>
      ) : !showEquipmentPicker ? (
        <TouchableOpacity style={styles.setContextBtn} onPress={() => setShowEquipmentPicker(true)} activeOpacity={0.7}>
          <Ionicons name="build-outline" size={14} color="rgba(255,255,255,0.5)" />
          <Text style={styles.setContextText}>Set equipment</Text>
        </TouchableOpacity>
      ) : null}

      {/* Equipment picker */}
      {showEquipmentPicker ? (
        <View style={styles.pickerContainer}>
          <Text style={styles.pickerTitle}>What are you working on?</Text>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow} contentContainerStyle={styles.chipRowContent}>
            {EQUIPMENT_OPTIONS.map(opt => (
              <TouchableOpacity
                key={opt.key}
                style={[styles.chip, selectedEquipment === opt.key && styles.chipSelected]}
                onPress={() => setSelectedEquipment(opt.key)}
                activeOpacity={0.7}
              >
                <Ionicons name={opt.icon} size={14} color={selectedEquipment === opt.key ? '#FFF' : 'rgba(255,255,255,0.6)'} />
                <Text style={[styles.chipText, selectedEquipment === opt.key && styles.chipTextSelected]}>{opt.label}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {selectedEquipment && (
            <>
              <Text style={styles.pickerSubtitle}>Brand (optional)</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow} contentContainerStyle={styles.chipRowContent}>
                {TOP_BRANDS.map(brand => (
                  <TouchableOpacity
                    key={brand}
                    style={[styles.chip, selectedBrand === brand && styles.chipSelected]}
                    onPress={() => setSelectedBrand(selectedBrand === brand ? null : brand)}
                    activeOpacity={0.7}
                  >
                    <Text style={[styles.chipText, selectedBrand === brand && styles.chipTextSelected]}>{brand}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <TextInput
                style={styles.modelInput}
                placeholder="Model # (optional)"
                placeholderTextColor="rgba(255,255,255,0.3)"
                value={modelInput}
                onChangeText={setModelInput}
                maxLength={50}
              />
            </>
          )}

          <View style={styles.pickerActions}>
            <TouchableOpacity onPress={() => setShowEquipmentPicker(false)} style={styles.pickerCancel}>
              <Text style={styles.pickerCancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleSetContext}
              style={[styles.pickerConfirm, !selectedEquipment && styles.pickerConfirmDisabled]}
              disabled={!selectedEquipment}
            >
              <Text style={styles.pickerConfirmText}>Set</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <>
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

          {/* "Show in text" card — appears when tech taps the text chip */}
          {textCardMessage && (
            <Animated.View style={[styles.textCard, { opacity: textCardOpacity }]}>
              <TouchableOpacity style={styles.textCardClose} onPress={dismissTextCard} hitSlop={8}>
                <Ionicons name="close" size={14} color="rgba(255,255,255,0.5)" />
              </TouchableOpacity>
              <Text style={styles.textCardMessage}>{textCardMessage}</Text>
            </Animated.View>
          )}

          {/* Quick action chips — only after proactive alerts */}
          {showChips && activeAlert && (
            <Animated.View style={[styles.quickActionsContainer, { opacity: chipsOpacity, transform: [{ translateY: chipsTranslateY }] }]}>
              {QUICK_ACTIONS.map((action) => (
                <TouchableOpacity
                  key={action.key}
                  style={styles.quickActionChip}
                  onPress={() => handleQuickAction(action.key)}
                  activeOpacity={0.7}
                >
                  <Ionicons name={action.icon as any} size={15} color="#FFF" />
                  <Text style={styles.quickActionLabel}>{action.label}</Text>
                </TouchableOpacity>
              ))}
            </Animated.View>
          )}

          {/* Pause button */}
          {onPause && (
            <TouchableOpacity style={styles.pauseButton} onPress={onPause} activeOpacity={0.7}>
              <Ionicons name={isPaused ? 'play' : 'pause'} size={18} color="rgba(255,255,255,0.8)" />
              <Text style={styles.pauseText}>{isPaused ? 'Resume' : 'Pause'}</Text>
            </TouchableOpacity>
          )}
        </>
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

  // Equipment context bar
  contextBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 20,
    marginBottom: 16,
    maxWidth: '80%',
  },
  contextText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 13,
    fontWeight: '500',
    flex: 1,
    textTransform: 'capitalize',
  },
  contextClear: {
    padding: 2,
  },
  setContextBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
    borderStyle: 'dashed',
    marginBottom: 16,
  },
  setContextText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 13,
  },

  // Equipment picker
  pickerContainer: {
    width: '100%',
    paddingHorizontal: 20,
    flex: 1,
    justifyContent: 'center',
  },
  pickerTitle: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
    textAlign: 'center',
  },
  pickerSubtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 13,
    marginTop: 16,
    marginBottom: 8,
  },
  chipRow: {
    flexGrow: 0,
  },
  chipRowContent: {
    gap: 8,
    paddingVertical: 4,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  chipSelected: {
    backgroundColor: Colors.accent,
    borderColor: Colors.accent,
  },
  chipText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 13,
    fontWeight: '500',
  },
  chipTextSelected: {
    color: '#FFF',
  },
  modelInput: {
    marginTop: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    color: '#FFF',
    fontSize: 14,
  },
  pickerActions: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 16,
    marginTop: 24,
  },
  pickerCancel: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  pickerCancelText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 14,
    fontWeight: '500',
  },
  pickerConfirm: {
    paddingHorizontal: 32,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: Colors.accent,
  },
  pickerConfirmDisabled: {
    opacity: 0.4,
  },
  pickerConfirmText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },

  // Quick action chips
  quickActionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: 24,
    paddingHorizontal: 20,
  },
  quickActionChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  quickActionLabel: {
    color: '#FFF',
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: -0.2,
  },

  // Text card (shown when "Show in text" is tapped)
  textCard: {
    marginTop: 20,
    marginHorizontal: 24,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 14,
    padding: 16,
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
  textCardMessage: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 14,
    lineHeight: 20,
    letterSpacing: -0.2,
    paddingRight: 20,
  },
});
