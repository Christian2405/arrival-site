import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, FlatList, StyleSheet, TouchableOpacity, Pressable,
  Animated, Keyboard, Platform, Alert, Dimensions,
  TouchableWithoutFeedback, AppState, Linking,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { cacheDirectory, EncodingType, readAsStringAsync, writeAsStringAsync, deleteAsync } from 'expo-file-system/legacy';
import * as ImagePicker from 'expo-image-picker';
import { Colors } from '../../constants/Colors';
import { getTierLimits } from '../../constants/Tiers';
import { useConversationStore, Message } from '../../store/conversationStore';
import { useSettingsStore } from '../../store/settingsStore';
import { useSavedAnswersStore } from '../../store/savedAnswersStore';
import { useAuthStore } from '../../store/authStore';
import { aiAPI, feedbackAPI } from '../../services/api';
import { useUsageStore, isQueryLimitReached } from '../../store/usageStore';
import ChatBubble from '../../components/ChatBubble';
import ArrivalLogo from '../../components/ArrivalLogo';
import ModeSelector from '../../components/ModeSelector';
import VoiceStatusIndicator, { VoiceState } from '../../components/VoiceStatusIndicator';
import JobModeView, { JobAIState } from '../../components/JobModeView';
import JobModeController from '../../services/jobModeController';

// Collision-safe ID generator
function generateId(): string {
  return Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 10);
}

// Voice save command detection
const SAVE_COMMANDS = /^(save|save that|save this|save it|save answer|bookmark|keep that|remember that)\.?$/i;

// Bug 14: Confidence value validator
function validateConfidence(v?: string): Message['confidence'] | undefined {
  return v && ['high', 'medium', 'low'].includes(v) ? v as Message['confidence'] : undefined;
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { prefill } = useLocalSearchParams<{ prefill?: string }>();

  // Camera
  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();

  // Recording
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null); // Bug 1: ref to avoid stale closure
  const pttStartingRef = useRef(false); // Bug 1: mutex to prevent double-press
  const recordingPulse = useRef(new Animated.Value(1)).current;

  // Voice state machine (for Default Mode)
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');

  // Job Mode state
  const [jobAIState, setJobAIState] = useState<JobAIState>('monitoring');
  const [jobPaused, setJobPaused] = useState(false);
  const jobControllerRef = useRef<JobModeController | null>(null);
  const [lastJobAlert, setLastJobAlert] = useState<{ message: string; severity: string; ts: number } | null>(null);
  const jobAlertHistoryRef = useRef<string[]>([]);

  // Text Mode state
  const [inputText, setInputText] = useState('');
  const [pendingImage, setPendingImage] = useState<string | undefined>();
  const [showChat, setShowChat] = useState(false);
  const chatSlide = useRef(new Animated.Value(0)).current;
  const flatListRef = useRef<FlatList>(null);

  // Keyboard height — tracked manually for instant (no-animation) positioning
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  // PTT frame capture ref
  const pttFrameRef = useRef<string | undefined>(undefined);

  // Audio playback
  const currentSoundRef = useRef<Audio.Sound | null>(null);
  const currentAudioFileRef = useRef<string | null>(null); // Bug 2: track temp file for cleanup

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [convsExpanded, setConvsExpanded] = useState(false);
  const drawerAnim = useRef(new Animated.Value(0)).current;

  // Stores
  const {
    currentConversation, conversations, addMessage, createNewConversation, setCurrentConversation,
    deleteConversation, isRecording, isProcessing, setIsRecording, setIsProcessing,
  } = useConversationStore();
  const messages = currentConversation?.messages || [];

  const { demoMode, voiceOutput, interactionMode, setInteractionMode } = useSettingsStore();
  const { saveAnswer } = useSavedAnswersStore();
  const { profile, subscription } = useAuthStore();

  const plan = subscription?.plan || 'free';
  const tierLimits = getTierLimits(plan);

  // Usage store — fetch on mount + foreground
  const { fetchUsage, incrementQueryCount } = useUsageStore();
  useEffect(() => {
    if (!demoMode) fetchUsage();
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active' && !useSettingsStore.getState().demoMode) {
        fetchUsage();
      }
    });
    return () => sub.remove();
  }, [fetchUsage, demoMode]);

  // Keyboard height listener — instant repositioning instead of slow KAV animation
  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';
    const showSub = Keyboard.addListener(showEvent, (e) => setKeyboardHeight(e.endCoordinates.height));
    const hideSub = Keyboard.addListener(hideEvent, () => setKeyboardHeight(0));
    return () => { showSub.remove(); hideSub.remove(); };
  }, []);

  // Warmup ping — wake up Render server on app open so first query is fast
  useEffect(() => { aiAPI.warmup(); }, []);

  // Prefill from codes screen (or any deep link)
  useEffect(() => {
    if (prefill && typeof prefill === 'string') {
      setInputText(prefill);
      // Switch to text mode if not already
      if (interactionMode !== 'text') {
        setInteractionMode('text');
      }
      // Clear the param so it doesn't re-trigger
      router.setParams({ prefill: undefined } as any);
    }
  }, [prefill]);

  // --- Camera capture (silent, no shutter) ---
  const captureFrame = useCallback(async (): Promise<string | undefined> => {
    if (!cameraRef.current) return undefined;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.3,
        exif: false,
        shutterSound: false,
      });
      return photo?.base64 || undefined;
    } catch {
      return undefined;
    }
  }, []);

  // --- Audio playback (with stop capability) ---
  const playAudio = useCallback(async (audioBase64: string): Promise<void> => {
    // Bug 12: Guard null cacheDirectory
    if (!cacheDirectory) throw new Error('No cache directory');

    // Stop any currently playing audio
    if (currentSoundRef.current) {
      try {
        await currentSoundRef.current.stopAsync();
        await currentSoundRef.current.unloadAsync();
      } catch (_) {}
      currentSoundRef.current = null;
    }
    // Bug 2: Clean up previous temp file if still around
    if (currentAudioFileRef.current) {
      await deleteAsync(currentAudioFileRef.current, { idempotent: true }).catch(() => {});
      currentAudioFileRef.current = null;
    }

    await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });

    const fileUri = cacheDirectory + `tts_${Date.now()}.mp3`;
    await writeAsStringAsync(fileUri, audioBase64, { encoding: EncodingType.Base64 });
    currentAudioFileRef.current = fileUri; // Bug 2: track the file
    const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
    currentSoundRef.current = sound;

    // Bug 3: Wrap in a promise with timeout and error handling
    return new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        cleanup();
        reject(new Error('Audio playback timed out'));
      }, 30000);

      const cleanup = () => {
        clearTimeout(timeout);
        sound.setOnPlaybackStatusUpdate(null);
      };

      sound.setOnPlaybackStatusUpdate(async (status: any) => {
        // Bug fix: When sound becomes unloaded (e.g. user tapped stop),
        // resolve gracefully instead of rejecting — this is expected behavior,
        // not an error. Rejecting here caused spurious error messages.
        if (!status.isLoaded) {
          cleanup();
          currentSoundRef.current = null;
          // Bug 2: Clean up temp file
          if (currentAudioFileRef.current) {
            await deleteAsync(currentAudioFileRef.current, { idempotent: true }).catch(() => {});
            currentAudioFileRef.current = null;
          }
          resolve(); // Not an error — user stopped playback intentionally
          return;
        }
        if (status.didJustFinish) {
          cleanup();
          currentSoundRef.current = null;
          await sound.unloadAsync();
          // Bug 2: Clean up temp file
          if (currentAudioFileRef.current) {
            await deleteAsync(currentAudioFileRef.current, { idempotent: true }).catch(() => {});
            currentAudioFileRef.current = null;
          }
          resolve();
        }
      });

      // Bug 3: Catch playAsync errors
      sound.playAsync().catch((err) => {
        cleanup();
        currentSoundRef.current = null;
        if (currentAudioFileRef.current) {
          deleteAsync(currentAudioFileRef.current, { idempotent: true }).catch(() => {});
          currentAudioFileRef.current = null;
        }
        reject(err);
      });
    });
  }, []);

  const stopAudio = useCallback(async () => {
    if (currentSoundRef.current) {
      try {
        await currentSoundRef.current.stopAsync();
        await currentSoundRef.current.unloadAsync();
      } catch (_) {}
      currentSoundRef.current = null;
    }
    // Bug 2: Delete temp file on early stop (didJustFinish won't fire)
    if (currentAudioFileRef.current) {
      await deleteAsync(currentAudioFileRef.current, { idempotent: true }).catch(() => {});
      currentAudioFileRef.current = null;
    }
  }, []);

  // --- Recording cleanup on unmount ---
  // Bug 18: Use ref instead of stale state closure
  useEffect(() => {
    return () => {
      if (recordingRef.current) {
        recordingRef.current.stopAndUnloadAsync().catch(() => {});
      }
      if (currentSoundRef.current) {
        currentSoundRef.current.stopAsync().catch(() => {});
        currentSoundRef.current.unloadAsync().catch(() => {});
        currentSoundRef.current = null;
      }
      if (currentAudioFileRef.current) {
        deleteAsync(currentAudioFileRef.current, { idempotent: true }).catch(() => {});
        currentAudioFileRef.current = null;
      }
    };
  }, []);

  // --- Start recording ---
  const startRecording = useCallback(async () => {
    try {
      // Bug 1: Use ref to check existing recording (avoids stale closure)
      if (recordingRef.current) {
        await recordingRef.current.stopAndUnloadAsync().catch(() => {});
        recordingRef.current = null;
        setRecording(null);
      }
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone access is needed for voice input.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      // Bug 1: Set ref synchronously so handlePTTEnd always sees it
      recordingRef.current = rec;
      setRecording(rec);
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true }).catch(() => {});
    }
  }, [setIsRecording]);

  // --- Voice save command handler ---
  // Bug 15: Read messages from store at call time to avoid stale closure
  const handleVoiceSaveCommand = useCallback(() => {
    const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
    const lastAssistant = [...currentMessages].reverse().find(m => m.role === 'assistant');
    if (lastAssistant) {
      const currentTrade = useConversationStore.getState().currentConversation?.trade || 'General';
      saveAnswer({
        id: generateId(),
        question: [...currentMessages].reverse().find(m => m.role === 'user')?.content || '',
        answer: lastAssistant.content,
        source: lastAssistant.source,
        trade: currentTrade,
        savedAt: new Date(),
      });
    }
  }, [saveAnswer]);

  // --- DEFAULT MODE: PTT toggle handler ---
  const handlePTTToggle = useCallback(async () => {
    if (voiceState === 'processing') return; // busy, ignore

    // Tap during speaking → stop audio
    if (voiceState === 'speaking') {
      await stopAudio();
      setVoiceState('idle');
      return;
    }

    // Tap during listening → stop recording and process
    if (voiceState === 'listening') {
      // Same logic as the old handlePTTEnd
      const rec = recordingRef.current;
      if (!rec) { setVoiceState('idle'); return; }
      setIsRecording(false);
      setVoiceState('processing');
      setIsProcessing(true);

      try {
        recordingRef.current = null;
        setRecording(null);

        let uri: string | null | undefined = null;
        try {
          await rec.stopAndUnloadAsync();
          uri = rec.getURI();
        } catch (stopErr) {
          console.error('Failed to stop recording:', stopErr);
        }

        if (!uri) { setVoiceState('idle'); setIsProcessing(false); return; }

        const audioBase64 = await readAsStringAsync(uri, { encoding: EncodingType.Base64 });
        const frameBase64 = pttFrameRef.current;
        pttFrameRef.current = undefined;

        const currentDemoMode = useSettingsStore.getState().demoMode;
        const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
        const history = currentMessages.slice(-20).map(m => ({ role: m.role, content: m.content }));
        const result = await aiAPI.voiceChat(audioBase64, frameBase64, history, currentDemoMode, 'default');

        if (SAVE_COMMANDS.test(result.transcript)) {
          handleVoiceSaveCommand();
          setVoiceState('idle');
          setIsProcessing(false);
          return;
        }

        addMessage({
          id: generateId(), role: 'user', content: result.transcript,
          displayMode: 'voice', timestamp: new Date(),
        });
        addMessage({
          id: generateId(), role: 'assistant', content: result.response,
          source: result.source, confidence: validateConfidence(result.confidence),
          displayMode: 'voice', timestamp: new Date(),
        });

        // Optimistic usage increment
        if (!currentDemoMode) incrementQueryCount();

        if (result.audio_base64) {
          setVoiceState('speaking');
          await playAudio(result.audio_base64);
        }
        setVoiceState('idle');
      } catch (error: any) {
        console.error('Voice chat error:', error);
        const isNet = !error?.response && (error?.code === 'ECONNABORTED' || error?.code === 'ERR_NETWORK' || error?.message?.includes('Network'));
        const is429 = error?.response?.status === 429;
        let voiceErrorMsg = 'Voice processing failed. Please try again.';
        if (isNet) voiceErrorMsg = 'Server is starting up — please try again in a moment.';
        else if (is429) voiceErrorMsg = 'Daily query limit reached. Resets at midnight UTC.';
        addMessage({
          id: generateId(), role: 'assistant',
          content: voiceErrorMsg,
          displayMode: 'voice', timestamp: new Date(),
        });
        setVoiceState('idle');
      } finally {
        setIsProcessing(false);
        Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true }).catch(() => {});
      }
      return;
    }

    // Tap during idle → start recording
    // Check query limit before starting (skip in demo mode)
    if (!useSettingsStore.getState().demoMode && isQueryLimitReached()) {
      Alert.alert(
        'Daily Limit Reached',
        'You\'ve used all your queries for today. Upgrade your plan for more.',
        [
          { text: 'OK', style: 'cancel' },
          { text: 'Upgrade', onPress: () => Linking.openURL('https://arrivalcompany.com/pricing').catch(() => {}) },
        ],
      );
      return;
    }
    if (pttStartingRef.current) return;
    pttStartingRef.current = true;
    try {
      setVoiceState('listening');
      captureFrame().then(frame => { pttFrameRef.current = frame; });
      await startRecording();
      if (!recordingRef.current) {
        setVoiceState('idle');
      }
    } catch {
      setVoiceState('idle');
      setIsRecording(false);
    } finally {
      pttStartingRef.current = false;
    }
  }, [voiceState, isProcessing, stopAudio, startRecording, captureFrame, addMessage, playAudio, handleVoiceSaveCommand, setIsRecording, setIsProcessing]);

  // --- TEXT MODE: Send message ---
  const handleTextSubmit = useCallback(async () => {
    const text = inputText.trim();
    if (!text || isProcessing) return;

    // Check query limit before sending (skip in demo mode)
    if (!useSettingsStore.getState().demoMode && isQueryLimitReached()) {
      Alert.alert(
        'Daily Limit Reached',
        'You\'ve used all your queries for today. Upgrade your plan for more.',
        [
          { text: 'OK', style: 'cancel' },
          { text: 'Upgrade', onPress: () => Linking.openURL('https://arrivalcompany.com/pricing').catch(() => {}) },
        ],
      );
      return;
    }

    Keyboard.dismiss();
    setInputText('');
    setIsProcessing(true);

    const imageForThisMessage = pendingImage;
    setPendingImage(undefined);

    // Add user message (visible as bubble in Text Mode)
    addMessage({
      id: generateId(), role: 'user', content: text,
      image: imageForThisMessage, displayMode: 'text', timestamp: new Date(),
    });

    try {
      const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
      const history = currentMessages.slice(-20).map(m => ({ role: m.role, content: m.content }));
      const currentDemoMode = useSettingsStore.getState().demoMode;
      const response = await aiAPI.chat(text, imageForThisMessage, history, currentDemoMode, useSettingsStore.getState().units);

      addMessage({
        id: generateId(), role: 'assistant', content: response.response,
        source: response.source, confidence: validateConfidence(response.confidence), // Bug 14
        displayMode: 'text', timestamp: new Date(),
      });

      // Optimistic usage increment
      if (!currentDemoMode) incrementQueryCount();

      // NO TTS in Text Mode -- text in = text out
    } catch (error: any) {
      const isNetwork = !error?.response && (
        error?.code === 'ECONNABORTED' ||
        error?.code === 'ERR_NETWORK' ||
        error?.message?.includes('Network') ||
        error?.message?.includes('timeout')
      );
      const isServerDown = error?.response?.status === 502 || error?.response?.status === 503;
      let errorMsg = 'Something went wrong. Please try again.';
      if (isNetwork || isServerDown) {
        errorMsg = 'Server is starting up — this can take a moment on the first request. Please try again.';
      } else if (error?.response?.status === 429) {
        errorMsg = 'Daily query limit reached. Resets at midnight UTC.';
      }
      addMessage({
        id: generateId(), role: 'assistant',
        content: errorMsg,
        displayMode: 'text', timestamp: new Date(),
      });
    } finally {
      setIsProcessing(false);
    }
  }, [inputText, isProcessing, pendingImage, messages, demoMode, addMessage, setIsProcessing]);

  // --- MODE SWITCHING ---
  // Bug 4: Tier gate checks FIRST, before any cleanup
  // Bug 16: Make async to await stopAudio
  const handleModeChange = useCallback(async (newMode: 'default' | 'text' | 'job') => {
    // Tier gates — check BEFORE destroying any work
    if (newMode === 'job' && !tierLimits.jobMode) {
      Alert.alert('Business Plan Required', 'Job Mode is available on the Business plan.');
      return;
    }
    if (newMode === 'default' && !tierLimits.voiceOutput) {
      Alert.alert('Pro Plan Required', 'Voice mode requires the Pro plan or above.');
      return;
    }

    // Cancel in-progress work (Bug 1: use ref)
    if (recordingRef.current) {
      try { await recordingRef.current.stopAndUnloadAsync(); } catch {}
      recordingRef.current = null;
      setRecording(null);
      setIsRecording(false);
    }
    await stopAudio(); // Bug 16: await
    setIsProcessing(false);
    setVoiceState('idle');

    // Clean up Job Mode
    if (interactionMode === 'job' && jobControllerRef.current) {
      jobControllerRef.current.stop();
      jobControllerRef.current = null;
    }

    // Bug fix: Reset jobPaused so re-entering job mode doesn't have stale pause state
    setJobPaused(false);
    setJobAIState('monitoring');
    setLastJobAlert(null);
    jobAlertHistoryRef.current = [];

    setInteractionMode(newMode);
  }, [interactionMode, tierLimits, stopAudio, setInteractionMode, setIsRecording, setIsProcessing]);

  // --- JOB MODE EFFECT ---
  useEffect(() => {
    if (interactionMode !== 'job' || !permission?.granted) {
      if (jobControllerRef.current) {
        jobControllerRef.current.stop();
        jobControllerRef.current = null;
      }
      return;
    }

    const controller = new JobModeController(
      {
        cooldownAfterSpeaking: 1000,   // Quick turnaround for conversational flow
        cooldownAfterDismiss: 3000,    // Shorter dismiss cooldown
        maxAlertsPerMinute: 6,
      },
      {
        onAlert: async (message, severity) => {
          // Track alert for session memory + quick action chips
          jobAlertHistoryRef.current.push(message);
          setLastJobAlert({ message, severity, ts: Date.now() });

          addMessage({
            id: generateId(), role: 'assistant', content: message,
            alertType: severity === 'critical' ? 'critical' : 'warning',
            source: 'Job Mode Analysis', displayMode: 'job', timestamp: new Date(),
          });
          try {
            // Bug 5: Read demoMode from store at call time
            const currentDemoMode = useSettingsStore.getState().demoMode;
            const ttsResp = await aiAPI.textToSpeech(message, currentDemoMode);
            // Bug 11: Check audio_base64 before playing
            if (ttsResp.audio_base64) await playAudio(ttsResp.audio_base64);
          } catch (e) {
            console.log('Job Mode TTS error:', e);
          }
        },
        onVoiceResponse: async (audioBase64) => {
          try {
            const frame = await captureFrame();
            const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
            const history = currentMessages.slice(-20).map(m => ({ role: m.role, content: m.content }));
            // Bug 5: Read demoMode from store at call time
            const currentDemoMode = useSettingsStore.getState().demoMode;
            const result = await aiAPI.voiceChat(audioBase64, frame, history, currentDemoMode, 'job');

            addMessage({ id: generateId(), role: 'user', content: result.transcript, displayMode: 'job', timestamp: new Date() });
            addMessage({ id: generateId(), role: 'assistant', content: result.response, source: result.source, confidence: validateConfidence(result.confidence), displayMode: 'job', timestamp: new Date() }); // Bug 14

            // Bug 11: Check audio_base64 before playing
            if (result.audio_base64) {
              await playAudio(result.audio_base64);
            }
          } catch (e) {
            console.log('Job Mode voice error:', e);
          }
        },
        onStateChange: setJobAIState,
      },
      { minInterval: 4000, maxInterval: 15000, changeThreshold: 0.15, captureInterval: 4000 },
      { speechThreshold: -30, silenceThreshold: -50, speechMinDuration: 300, silenceMaxDuration: 1200, meteringInterval: 100 },
    );

    // Wire up the frame batcher to call analyzeFrame with session memory
    controller.frameBatcher['config'].onAnalyze = async (frame: string) => {
      try {
        const recentAlerts = jobAlertHistoryRef.current.slice(-5);
        const result = await aiAPI.analyzeFrame(frame, recentAlerts);
        if (result.alert && result.message) {
          await controller.handleFrameAlert(result.message, result.severity || 'warning');
        }
      } catch (e) {
        console.log('Job Mode frame error:', e);
      }
    };

    controller.start(captureFrame).catch(e => console.error('Job Mode start failed:', e));
    jobControllerRef.current = controller;

    return () => {
      controller.stop();
      jobControllerRef.current = null;
      // Clear alert state when leaving Job Mode
      setLastJobAlert(null);
      jobAlertHistoryRef.current = [];
    };
  }, [interactionMode, permission?.granted]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- TEXT MODE: Chat show/hide effects ---
  // Bug 20: Animate instead of snapping to 1
  useEffect(() => {
    if (interactionMode !== 'text') return;
    if (messages.length > 0 && !showChat) {
      setShowChat(true);
      Animated.timing(chatSlide, { toValue: 1, duration: 250, useNativeDriver: true }).start();
    }
  }, [messages.length, showChat, interactionMode, chatSlide]);

  // Bug 13: Only create new conversation if current one has messages
  const dismissChat = useCallback(() => {
    Animated.timing(chatSlide, { toValue: 0, duration: 250, useNativeDriver: true }).start(() => {
      setShowChat(false);
      const current = useConversationStore.getState().currentConversation;
      if (current?.messages?.length && current.messages.length > 0) {
        createNewConversation();
      }
    });
  }, [createNewConversation, chatSlide]);

  // --- Recording pulse animation ---
  useEffect(() => {
    if (isRecording) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(recordingPulse, { toValue: 1.2, duration: 600, useNativeDriver: true }),
          Animated.timing(recordingPulse, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      );
      pulse.start();
      return () => pulse.stop();
    }
  }, [isRecording, recordingPulse]);

  // --- DRAWER ---
  // Bug 8: Use actual device width instead of hardcoded 350
  const SCREEN_WIDTH = Dimensions.get('window').width;
  const DRAWER_WIDTH = SCREEN_WIDTH * 0.78;

  const toggleDrawer = useCallback(() => {
    Animated.timing(drawerAnim, {
      toValue: drawerOpen ? 0 : 1,
      duration: 250,
      useNativeDriver: true,
    }).start();
    setDrawerOpen(!drawerOpen);
  }, [drawerOpen, drawerAnim]);

  // --- Display name ---
  const displayName = profile
    ? `${profile.first_name || ''} ${profile.last_name || ''}`.trim() || 'Arrival User'
    : 'Arrival User';

  // --- Filtered messages for Text Mode ---
  const textMessages = messages.filter(m => m.displayMode === 'text' || !m.displayMode);

  // --- RENDER ---
  return (
    <View style={styles.container}>
      {/* Camera background - always visible */}
      <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />

      {/* Dark overlay */}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(0,0,0,0.3)' }]} />

      {/* Main content */}
      <View style={{ flex: 1, paddingBottom: interactionMode === 'text' ? keyboardHeight : 0 }}>
        <View style={[styles.content, { paddingTop: insets.top }]}>

          {/* TOP BAR: Hamburger + Mode Selector + New Chat */}
          <View style={styles.topBar}>
            <TouchableOpacity onPress={toggleDrawer} style={styles.iconBtn}>
              <Ionicons name="menu" size={24} color="#FFF" />
            </TouchableOpacity>

            <ModeSelector
              currentMode={interactionMode}
              onModeChange={handleModeChange}
              jobModeAllowed={tierLimits.jobMode}
              voiceAllowed={tierLimits.voiceOutput}
            />

            {messages.length > 0 ? (
              <TouchableOpacity onPress={() => createNewConversation()} style={styles.newSessionBtn}>
                <Ionicons name="refresh" size={14} color="#FFF" />
                <Text style={styles.newSessionText}>New</Text>
              </TouchableOpacity>
            ) : (
              <View style={styles.iconBtn} />
            )}
          </View>

          {/* Demo mode badge */}
          {demoMode && (
            <View style={styles.demoBadge}>
              <Text style={styles.demoBadgeText}>DEMO MODE</Text>
            </View>
          )}

          {/* ===== MODE-SPECIFIC CONTENT ===== */}

          {interactionMode === 'default' && (
            <View style={styles.modeContainer}>
              <VoiceStatusIndicator state={voiceState} />

              {/* Large PTT button at bottom */}
              <View style={styles.pttContainer}>
                <Pressable
                  onPress={handlePTTToggle}
                  disabled={voiceState === 'processing'}
                  style={({ pressed }) => [
                    styles.pttButton,
                    pressed && styles.pttButtonActive,
                    voiceState === 'listening' && styles.pttButtonActive,
                    voiceState === 'speaking' && styles.pttButtonSpeaking,
                    voiceState === 'processing' && styles.pttButtonDisabled,
                  ]}
                >
                  <Ionicons
                    name={
                      voiceState === 'speaking' ? 'stop-circle' :
                      voiceState === 'listening' ? 'radio' :
                      voiceState === 'processing' ? 'hourglass' :
                      'mic'
                    }
                    size={32}
                    color="#FFF"
                  />
                </Pressable>
              </View>
            </View>
          )}

          {interactionMode === 'text' && (
            <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
              <View style={styles.modeContainer}>
                {/* Chat messages */}
                {showChat && textMessages.length > 0 ? (
                  <Animated.View style={[styles.chatArea, { opacity: chatSlide, transform: [{ translateY: chatSlide.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }] }]}>
                    {/* Collapse handle at top */}
                    <TouchableOpacity
                      onPress={() => { dismissChat(); Keyboard.dismiss(); }}
                      style={styles.collapseBar}
                      activeOpacity={0.7}
                    >
                      <View style={styles.collapseHandle} />
                    </TouchableOpacity>

                    <FlatList
                      ref={flatListRef}
                      data={textMessages}
                      keyboardDismissMode="on-drag"
                      keyExtractor={(item) => item.id}
                      renderItem={({ item, index }) => {
                        // Find preceding user message for feedback logging
                        const prevUserMsg = item.role === 'assistant'
                          ? textMessages.slice(0, index).reverse().find(m => m.role === 'user')
                          : undefined;

                        return (
                          <ChatBubble
                            message={item}
                            onSave={item.role === 'assistant' ? () => {
                              saveAnswer({
                                id: item.id, question: '', answer: item.content,
                                source: item.source, trade: currentConversation?.trade || 'General',
                                savedAt: new Date(),
                              });
                            } : undefined}
                            onFeedback={item.role === 'assistant' ? (rating, feedbackText) => {
                              feedbackAPI.submit({
                                question: prevUserMsg?.content || '',
                                answer: item.content,
                                rating,
                                feedback_text: feedbackText,
                                source: item.source,
                                conversation_id: currentConversation?.id,
                              }).catch(() => {}); // Fire-and-forget
                            } : undefined}
                          />
                        );
                      }}
                      contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: 8, paddingTop: 4 }}
                      showsVerticalScrollIndicator={false}
                      inverted={false}
                      onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
                      keyboardShouldPersistTaps="handled"
                    />
                  </Animated.View>
                ) : (
                  <View style={styles.emptyState}>
                    <ArrivalLogo width={48} color="#FFF" />
                    <Text style={styles.emptyTitle}>Arrival AI</Text>
                    <Text style={styles.emptySubtitle}>Type a question to get started</Text>
                  </View>
                )}

                {/* Processing indicator */}
                {isProcessing && (
                  <View style={styles.processingRow}>
                    <Text style={styles.processingText}>Thinking...</Text>
                  </View>
                )}

                {/* Image preview strip */}
                {pendingImage && (
                  <View style={styles.imagePreviewStrip}>
                    <View style={styles.imagePreviewThumb}>
                      <Ionicons name="image" size={14} color={Colors.accent} />
                    </View>
                    <Text style={styles.imagePreviewText}>Photo attached</Text>
                    <TouchableOpacity onPress={() => setPendingImage(undefined)} style={styles.imagePreviewRemove}>
                      <Ionicons name="close-circle" size={18} color="rgba(255,255,255,0.5)" />
                    </TouchableOpacity>
                  </View>
                )}

                {/* Input bar container — no safe area padding when keyboard is up */}
                <View style={{ paddingBottom: keyboardHeight > 0 ? 2 : Math.max(insets.bottom, 6), paddingHorizontal: 8 }}>
                  <View style={styles.inputBar}>
                    {/* Photo picker */}
                    <TouchableOpacity
                      onPress={async () => {
                        try {
                          const result = await ImagePicker.launchImageLibraryAsync({
                            mediaTypes: ['images'],
                            base64: true,
                            quality: 0.5,
                          });
                          if (!result.canceled && result.assets[0]?.base64) {
                            setPendingImage(result.assets[0].base64);
                          }
                        } catch (e) {
                          console.log('[ImagePicker] Error:', e);
                        }
                      }}
                      style={styles.inputIconBtn}
                    >
                      <Ionicons
                        name="image-outline"
                        size={20}
                        color={pendingImage ? Colors.accent : 'rgba(255,255,255,0.5)'}
                      />
                    </TouchableOpacity>

                    {/* Camera capture */}
                    <TouchableOpacity
                      onPress={async () => {
                        try {
                          if (!cameraRef.current) return;
                          const photo = await cameraRef.current.takePictureAsync({
                            base64: true,
                            quality: 0.5,
                            exif: false,
                            shutterSound: false,
                          });
                          if (photo?.base64) {
                            setPendingImage(photo.base64);
                          }
                        } catch (e) {
                          console.log('[Camera] Capture error:', e);
                        }
                      }}
                      style={styles.inputIconBtn}
                    >
                      <Ionicons
                        name="camera-outline"
                        size={20}
                        color={pendingImage ? Colors.accent : 'rgba(255,255,255,0.5)'}
                      />
                    </TouchableOpacity>

                    <TextInput
                      style={styles.textInput}
                      value={inputText}
                      onChangeText={setInputText}
                      placeholder="Ask anything..."
                      placeholderTextColor="rgba(255,255,255,0.35)"
                      editable={!isProcessing}
                      multiline={true}
                      returnKeyType="default"
                      blurOnSubmit={false}
                    />

                    <TouchableOpacity
                      onPress={handleTextSubmit}
                      disabled={!inputText.trim() || isProcessing}
                      style={[styles.sendBtn, (!inputText.trim() || isProcessing) && { opacity: 0.25 }]}
                    >
                      <Ionicons name="arrow-up" size={18} color="#FFF" />
                    </TouchableOpacity>
                  </View>
                </View>
              </View>
            </TouchableWithoutFeedback>
          )}

          {interactionMode === 'job' && (
            <View style={styles.modeContainer}>
              <JobModeView
                aiState={jobAIState}
                onPause={() => {
                  // Bug 17: Guard null controller
                  if (!jobControllerRef.current) return;
                  if (jobPaused) {
                    jobControllerRef.current.vad.resume();
                  } else {
                    jobControllerRef.current.vad.pause();
                    jobControllerRef.current.dismiss();
                  }
                  setJobPaused(!jobPaused);
                }}
                isPaused={jobPaused}
                lastAlert={lastJobAlert}
                onQuickAction={async (action, alertMsg) => {
                  if (action === 'text') return; // Handled internally by JobModeView

                  // Build follow-up prompt based on action type
                  const followUpText = action === 'explain'
                    ? `You just told me: "${alertMsg}". Explain that in more detail.`
                    : `You just told me: "${alertMsg}". Walk me through fixing this step by step.`;

                  try {
                    // Add user follow-up to conversation
                    addMessage({
                      id: generateId(), role: 'user', content: followUpText,
                      displayMode: 'job', timestamp: new Date(),
                    });

                    const frame = await captureFrame();
                    const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
                    const history = currentMessages.slice(-20).map(m => ({ role: m.role, content: m.content }));
                    const currentDemoMode = useSettingsStore.getState().demoMode;

                    setJobAIState('processing');

                    // Use text chat API (not voiceChat) since we're sending a text prompt, not audio.
                    // voiceChat expects audio_base64 as first arg — sending text would cause a backend error.
                    const chatResult = await aiAPI.chat(followUpText, frame, history, currentDemoMode, useSettingsStore.getState().units);

                    addMessage({
                      id: generateId(), role: 'assistant', content: chatResult.response,
                      source: chatResult.source, confidence: validateConfidence(chatResult.confidence),
                      displayMode: 'job', timestamp: new Date(),
                    });

                    // TTS the response so the tech hears it hands-free
                    try {
                      const ttsResp = await aiAPI.textToSpeech(chatResult.response, currentDemoMode);
                      if (ttsResp.audio_base64) {
                        setJobAIState('speaking');
                        await playAudio(ttsResp.audio_base64);
                      }
                    } catch (ttsErr) {
                      console.log('Job Mode quick action TTS error:', ttsErr);
                    }

                    setJobAIState('monitoring');
                  } catch (e) {
                    console.log('Job Mode quick action error:', e);
                    setJobAIState('monitoring');
                  }
                }}
              />
            </View>
          )}
        </View>
      </View>

      {/* DRAWER OVERLAY */}
      {drawerOpen && (
        <TouchableOpacity
          style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(0,0,0,0.4)', zIndex: 10 }]}
          activeOpacity={1}
          onPress={toggleDrawer}
        />
      )}

      {/* DRAWER */}
      <Animated.View style={[styles.drawer, {
        transform: [{ translateX: drawerAnim.interpolate({ inputRange: [0, 1], outputRange: [-DRAWER_WIDTH, 0] }) }],
        width: DRAWER_WIDTH,
      }]}>
        <View style={[styles.drawerContent, { paddingTop: insets.top + 12 }]}>
          {/* Logo at top */}
          <View style={styles.drawerLogoSection}>
            <ArrivalLogo width={110} color={Colors.text} />
          </View>

          {/* Navigation links */}
          <View style={styles.drawerNav}>
            {([
              { icon: 'bookmark-outline' as const, label: 'Saved Answers', route: '/saved-answers' },
              { icon: 'document-text-outline' as const, label: 'Manuals', route: '/manuals' },
              { icon: 'code-slash-outline' as const, label: 'Error Codes', route: '/codes' },
              { icon: 'calculator-outline' as const, label: 'Quick Tools', route: '/quick-tools' },
            ]).map((item) => (
              <TouchableOpacity
                key={item.route}
                style={styles.drawerNavItem}
                onPress={() => { toggleDrawer(); router.push(item.route as any); }}
              >
                <View style={styles.drawerNavIcon}>
                  <Ionicons name={item.icon} size={18} color={Colors.accent} />
                </View>
                <Text style={styles.drawerNavText}>{item.label}</Text>
                <Ionicons name="chevron-forward" size={16} color={Colors.textFaint} />
              </TouchableOpacity>
            ))}
          </View>

          {/* Conversations — collapsible dropdown */}
          <TouchableOpacity
            style={styles.drawerSectionHeader}
            onPress={() => setConvsExpanded(!convsExpanded)}
          >
            <Text style={styles.drawerSectionTitle}>Recent Conversations</Text>
            <Ionicons name={convsExpanded ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.textFaint} />
          </TouchableOpacity>
          {convsExpanded && (
            <FlatList
              data={conversations.filter(c => c.messages.length > 0).slice(0, 20)}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <View style={styles.drawerConvItem}>
                  <TouchableOpacity
                    style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 }}
                    onPress={() => {
                      setCurrentConversation(item);
                      toggleDrawer();
                    }}
                  >
                    <Ionicons name="chatbubble-outline" size={15} color={Colors.textMuted} />
                    <Text style={styles.drawerConvText} numberOfLines={1}>{item.title}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={() => deleteConversation(item.id)}
                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                  >
                    <Ionicons name="trash-outline" size={15} color={Colors.textFaint} />
                  </TouchableOpacity>
                </View>
              )}
              contentContainerStyle={{ paddingHorizontal: 20 }}
              showsVerticalScrollIndicator={false}
              style={{ maxHeight: 300 }}
            />
          )}

          {/* Spacer to push profile to bottom */}
          <View style={{ flex: 1 }} />

          {/* Profile at bottom */}
          <TouchableOpacity
            style={styles.drawerProfile}
            onPress={() => { toggleDrawer(); router.push('/settings' as any); }}
          >
            <View style={styles.drawerAvatar}>
              <Text style={styles.drawerAvatarText}>
                {(displayName || 'U').charAt(0).toUpperCase()}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.drawerName}>{displayName}</Text>
              <Text style={styles.drawerPlan}>{(plan || 'free').charAt(0).toUpperCase() + (plan || 'free').slice(1)} Plan</Text>
            </View>
            <Ionicons name="settings-outline" size={18} color={Colors.textMuted} />
          </TouchableOpacity>
        </View>
      </Animated.View>

      {/* Camera permission request */}
      {!permission?.granted && (
        <View style={[StyleSheet.absoluteFill, styles.permissionOverlay]}>
          <Ionicons name="camera-outline" size={48} color="rgba(255,255,255,0.5)" />
          <Text style={styles.permissionTitle}>Camera Access Needed</Text>
          <Text style={styles.permissionSubtitle}>Arrival needs camera access for visual analysis</Text>
          <TouchableOpacity style={styles.permissionBtn} onPress={requestPermission}>
            <Text style={styles.permissionBtnText}>Grant Access</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  content: {
    flex: 1,
  },

  // --- Top Bar ---
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  iconBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: Colors.glassDark,
    justifyContent: 'center',
    alignItems: 'center',
  },
  newSessionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.glassDark,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    gap: 4,
  },
  newSessionText: {
    color: '#FFF',
    fontSize: 13,
    fontWeight: '600',
  },

  // --- Demo badge ---
  demoBadge: {
    alignSelf: 'center',
    backgroundColor: Colors.accent,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 4,
  },
  demoBadgeText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.5,
  },

  // --- Mode container (wrapper for each mode) ---
  modeContainer: {
    flex: 1,
  },

  // --- Default Mode: PTT ---
  pttContainer: {
    alignItems: 'center',
    paddingBottom: 40,
  },
  pttButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(255,255,255,0.12)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  pttButtonActive: {
    backgroundColor: Colors.recording,
    transform: [{ scale: 1.1 }],
  },
  pttButtonSpeaking: {
    backgroundColor: '#4A90D9',
  },
  pttButtonDisabled: {
    opacity: 0.4,
  },

  // --- Text Mode: Chat area ---
  chatArea: {
    flex: 1,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 80,
  },
  emptyTitle: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 26,
    fontWeight: '700',
    letterSpacing: -0.5,
    textAlign: 'center',
    marginTop: 16,
  },
  emptySubtitle: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 15,
    marginTop: 8,
    textAlign: 'center',
    paddingHorizontal: 40,
    lineHeight: 22,
  },
  collapseBar: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 8,
    paddingBottom: 4,
  },
  collapseHandle: {
    width: 40,
    height: 5,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  processingRow: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  processingText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 14,
    fontStyle: 'italic',
  },

  // --- Text Mode: Input bar ---
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: 22,
    paddingLeft: 6,
    paddingRight: 5,
    paddingVertical: 5,
    minHeight: 44,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  inputIconBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    justifyContent: 'center',
    alignItems: 'center',
  },
  imageBadge: {
    position: 'absolute',
    top: 2,
    right: 2,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.accent,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
    paddingVertical: 6,
    paddingHorizontal: 8,
    maxHeight: 100,
    lineHeight: 20,
  },
  sendBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // --- Image preview strip ---
  imagePreviewStrip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 10,
    marginHorizontal: 12,
    marginBottom: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  imagePreviewThumb: {
    width: 24,
    height: 24,
    borderRadius: 6,
    backgroundColor: 'rgba(212,132,42,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  imagePreviewText: {
    flex: 1,
    marginLeft: 8,
    fontSize: 13,
    color: 'rgba(255,255,255,0.6)',
  },
  imagePreviewRemove: {
    padding: 4,
  },

  // --- Drawer ---
  drawer: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    backgroundColor: '#FFFFF5',
    zIndex: 11,
    shadowColor: '#000',
    shadowOffset: { width: 4, height: 0 },
    shadowOpacity: 0.08,
    shadowRadius: 24,
    elevation: 20,
  },
  drawerContent: {
    flex: 1,
    paddingHorizontal: 0,
  },
  drawerLogoSection: {
    paddingHorizontal: 20,
    paddingBottom: 24,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#EBE7E2',
  },
  drawerProfile: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#EBE7E2',
    marginBottom: 8,
  },
  drawerAvatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#2A2622',
    justifyContent: 'center',
    alignItems: 'center',
  },
  drawerAvatarText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFF',
  },
  drawerName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  drawerPlan: {
    fontSize: 12,
    color: '#A09A93',
    marginTop: 1,
  },
  drawerSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
  },
  drawerSectionTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#A09A93',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  drawerConvItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    gap: 10,
  },
  drawerConvText: {
    flex: 1,
    fontSize: 14,
    color: '#1A1A1A',
  },
  drawerNav: {
    paddingTop: 8,
    paddingBottom: 8,
    paddingHorizontal: 20,
    gap: 2,
  },
  drawerNavIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: 'rgba(212, 132, 42, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  drawerNavItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    gap: 12,
  },
  drawerNavText: {
    flex: 1,
    fontSize: 15,
    fontWeight: '500',
    color: '#1A1A1A',
  },

  // --- Permission overlay ---
  permissionOverlay: {
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    zIndex: 20,
  },
  permissionTitle: {
    color: '#FFF',
    fontSize: 22,
    fontWeight: '700',
    marginTop: 20,
    textAlign: 'center',
  },
  permissionSubtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 15,
    marginTop: 8,
    textAlign: 'center',
    lineHeight: 22,
  },
  permissionBtn: {
    marginTop: 28,
    backgroundColor: Colors.accent,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 14,
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  permissionBtnText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
