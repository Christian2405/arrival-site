import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  View, Text, TextInput, FlatList, StyleSheet, TouchableOpacity, Pressable,
  Animated, Keyboard, Platform, Alert, Dimensions, PanResponder,
  TouchableWithoutFeedback, AppState, Linking, Modal, ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { cacheDirectory, EncodingType, readAsStringAsync, writeAsStringAsync, deleteAsync } from 'expo-file-system/legacy';
import * as ImagePicker from 'expo-image-picker';

import { Colors, Spacing, Radius, FontSize, IconSize, Shadow } from '../../constants/Colors';
import { getTierLimits } from '../../constants/Tiers';
import { useConversationStore, Message } from '../../store/conversationStore';
import { useSettingsStore } from '../../store/settingsStore';
import { useSavedAnswersStore } from '../../store/savedAnswersStore';
import { useAuthStore } from '../../store/authStore';
import api, { aiAPI, feedbackAPI } from '../../services/api';
import { useUsageStore, isQueryLimitReached } from '../../store/usageStore';
import ChatBubble from '../../components/ChatBubble';
import ArrivalLogo from '../../components/ArrivalLogo';
import ModeSelector from '../../components/ModeSelector';
import VoiceStatusIndicator, { VoiceState } from '../../components/VoiceStatusIndicator';
import JobModeView, { JobAIState } from '../../components/JobModeView';
import JobModeController from '../../services/jobModeController';
import StreamingJobModeController from '../../services/streamingJobModeController';
// LiveKit requires native WebRTC — lazy-load so Expo Go doesn't crash
let LiveKitVoiceRoom: React.ComponentType<any> | null = null;
let LKVideoTrack: React.ComponentType<any> | null = null;
try {
  LiveKitVoiceRoom = require('../../components/LiveKitVoiceRoom').default;
  LKVideoTrack = require('@livekit/react-native').VideoTrack;
} catch (e) {
  console.warn('[Home] LiveKit native module not available (Expo Go?) — falling back to REST voice');
}
// OnboardingModal — lazy-load so its module-level code doesn't run at startup
// (static import was disrupting the iOS camera session on app launch)
let OnboardingModal: React.ComponentType<{ visible: boolean; onClose: () => void }> | null = null;
// AgentVoiceState type defined inline to avoid importing the native module
type AgentVoiceState = 'connecting' | 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';
import FrameBatcher from '../../services/frameBatcher';

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

// Animated thinking dots indicator
function ThinkingDots() {
  const dot1 = useRef(new Animated.Value(0.3)).current;
  const dot2 = useRef(new Animated.Value(0.3)).current;
  const dot3 = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const animate = (dot: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, { toValue: 1, duration: 400, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0.3, duration: 400, useNativeDriver: true }),
        ])
      );
    const a1 = animate(dot1, 0);
    const a2 = animate(dot2, 150);
    const a3 = animate(dot3, 300);
    a1.start(); a2.start(); a3.start();
    return () => { a1.stop(); a2.stop(); a3.stop(); };
  }, []);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 4 }}>
      {[dot1, dot2, dot3].map((dot, i) => (
        <Animated.View
          key={i}
          style={{
            width: 7, height: 7, borderRadius: 3.5,
            backgroundColor: Colors.textMuted,
            opacity: dot,
          }}
        />
      ))}
    </View>
  );
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { prefill } = useLocalSearchParams<{ prefill?: string }>();

  // Camera
  const cameraRef = useRef<CameraView>(null);
  const isCapturingRef = useRef(false);
  const [permission, requestPermission] = useCameraPermissions();
  // cameraKey removed — remounting CameraView while LiveKit audio is active crashes iOS

  // Recording
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null); // Bug 1: ref to avoid stale closure
  const pttStartingRef = useRef(false); // Bug 1: mutex to prevent double-press
  const pttFramesRef = useRef<string[]>([]); // Spatial: frames captured during PTT hold
  const pttFrameTimestampsRef = useRef<number[]>([]); // Spatial: device ms timestamp per frame
  const pttFrameIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordingPulse = useRef(new Animated.Value(1)).current;

  // Voice state machine (for Default Mode)
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');

  // Job Mode state
  const [jobAIState, setJobAIState] = useState<JobAIState>('monitoring');
  const [voiceConnected, setVoiceConnected] = useState(false);
  const [jobPaused, setJobPaused] = useState(false);
  const [jobStarted, setJobStarted] = useState(false);
  const [equipmentContext, setEquipmentContext] = useState<{ equipment_type: string; brand?: string; model?: string } | null>(null);
  const jobControllerRef = useRef<JobModeController | null>(null);
  const streamingControllerRef = useRef<StreamingJobModeController | null>(null);
  const [lastJobAlert, setLastJobAlert] = useState<{ message: string; severity: string; ts: number } | null>(null);
  const jobAlertHistoryRef = useRef<string[]>([]);
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [guidanceActive, setGuidanceActive] = useState(false);
  const livekitSendRef = useRef<((msg: Record<string, any>) => void) | null>(null);

  // Text Mode state
  const [inputText, setInputText] = useState('');
  const [pendingImage, setPendingImage] = useState<string | undefined>();
  const [showChat, setShowChat] = useState(false);
  const chatSlide = useRef(new Animated.Value(0)).current;
  const flatListRef = useRef<FlatList>(null);

  // Keyboard height
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  // PTT frame capture ref
  const pttFrameRef = useRef<string | undefined>(undefined);

  // Audio playback
  const currentSoundRef = useRef<Audio.Sound | null>(null);
  const currentAudioFileRef = useRef<string | null>(null); // Bug 2: track temp file for cleanup

  // Drawer
  const [showOnboarding, setShowOnboarding] = useState(false);
  const openOnboarding = useCallback(() => {
    // Load module on first use — NOT at startup so it can't disrupt camera
    if (!OnboardingModal) {
      OnboardingModal = require('../../components/OnboardingModal').default;
    }
    setShowOnboarding(true);
  }, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [convsExpanded, setConvsExpanded] = useState(true);
  const drawerAnim = useRef(new Animated.Value(0)).current;

  // Stores
  const {
    currentConversation, conversations, addMessage, createNewConversation, setCurrentConversation,
    deleteConversation, isRecording, isProcessing, setIsRecording, setIsProcessing,
  } = useConversationStore();
  const messages = currentConversation?.messages || [];

  const { voiceOutput, interactionMode, setInteractionMode, useStreamingVoice, useLiveKit } = useSettingsStore();
  const livekitFrameBatcherRef = useRef<FrameBatcher | null>(null);
  const [livekitActive, setLivekitActive] = useState(false);
  const [localVideoTrackRef, setLocalVideoTrackRef] = useState<any>(null);
  const [activeJob, setActiveJob] = useState<string | null>(null);
  const [userDocs, setUserDocs] = useState<string[]>([]);
  const [showJobPicker, setShowJobPicker] = useState(false);
  const flipCameraRef = useRef<(() => void) | null>(null);
  // Zoom state — 0 = ultra-wide (0.5x), 0.5 = 1x, 1.0 = max telephoto
  // expo-camera zoom prop uses 0-1 range
  // For LiveKit VideoTrack (Job Mode), we use CSS scale 1x-3x as fallback
  const [cameraZoom, setCameraZoom] = useState(0);  // expo-camera native zoom (0-1)
  const cameraZoomRef = useRef(0);
  const cameraZoomAnim = useRef(new Animated.Value(1)).current;  // CSS scale for LiveKit only
  const pinchBaseDistance = useRef(0);
  const pinchBaseZoom = useRef(0);

  const pinchResponder = useMemo(() => PanResponder.create({
    onStartShouldSetPanResponder: (_, gestureState) => gestureState.numberActiveTouches === 2,
    onMoveShouldSetPanResponder: (_, gestureState) => gestureState.numberActiveTouches === 2,
    onPanResponderGrant: (evt) => {
      const touches = evt.nativeEvent.touches;
      if (touches.length >= 2) {
        const dx = touches[0].pageX - touches[1].pageX;
        const dy = touches[0].pageY - touches[1].pageY;
        pinchBaseDistance.current = Math.sqrt(dx * dx + dy * dy);
        pinchBaseZoom.current = cameraZoomRef.current;
      }
    },
    onPanResponderMove: (evt) => {
      const touches = evt.nativeEvent.touches;
      if (touches.length >= 2 && pinchBaseDistance.current > 0) {
        const dx = touches[0].pageX - touches[1].pageX;
        const dy = touches[0].pageY - touches[1].pageY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const ratio = dist / pinchBaseDistance.current;
        // Native camera zoom: 0 to 1 (maps to ~0.5x to ~10x on iPhone)
        const newZoom = Math.min(Math.max(pinchBaseZoom.current + (ratio - 1) * 0.3, 0), 1);
        cameraZoomRef.current = newZoom;
        setCameraZoom(newZoom);
        // CSS scale fallback for LiveKit VideoTrack: 1x to 3x
        const cssScale = 1 + (newZoom * 2);
        cameraZoomAnim.setValue(cssScale);
      }
    },
    onPanResponderRelease: () => {
      pinchBaseDistance.current = 0;
    },
  }), []);
  const { saveAnswer } = useSavedAnswersStore();
  const { profile, subscription } = useAuthStore();

  const plan = subscription?.plan || 'free';
  const tierLimits = getTierLimits(plan);

  // Usage store — fetch on mount + foreground
  const { fetchUsage, incrementQueryCount } = useUsageStore();
  useEffect(() => {
    fetchUsage();
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') fetchUsage();
    });
    return () => sub.remove();
  }, [fetchUsage]);

  // Keyboard height listener
  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';
    const showSub = Keyboard.addListener(showEvent, (e) => setKeyboardHeight(e.endCoordinates.height));
    const hideSub = Keyboard.addListener(hideEvent, () => setKeyboardHeight(0));
    return () => { showSub.remove(); hideSub.remove(); };
  }, []);

  // Re-check camera permission when app returns to foreground
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active' && !permission?.granted) {
        requestPermission();
      }
    });
    return () => sub.remove();
  }, [permission?.granted]);

  // Warmup ping — wake up Render server on app open so first query is fast
  useEffect(() => {
    aiAPI.warmup();
  }, []);

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

  // --- Camera capture ---
  // iOS kills the camera when LiveKit's audio session takes over.
  // takePictureAsync either returns stale frames or throws "Image could not be captured".
  // We cache the last successful frame and return it on failure — stale > nothing.
  // The FIRST capture before LiveKit connects usually works and gives a real frame.
  const lastGoodFrameRef = useRef<string | undefined>(undefined);

  const captureFrame = useCallback(async (): Promise<string | undefined> => {
    if (!cameraRef.current || isCapturingRef.current) {
      return lastGoodFrameRef.current;
    }
    isCapturingRef.current = true;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.5,
        exif: false,
        shutterSound: false,
      });
      if (photo?.base64) {
        lastGoodFrameRef.current = photo.base64;
        return photo.base64;
      }
      return lastGoodFrameRef.current;
    } catch {
      return lastGoodFrameRef.current;
    } finally {
      isCapturingRef.current = false;
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
  // Load user's uploaded document names for the job picker
  useEffect(() => {
    api.get('/documents')
      .then(res => {
        const names: string[] = (res.data.documents || [])
          .map((d: any) => d.filename as string)
          .filter(Boolean);
        setUserDocs([...new Set(names)]);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    return () => {
      if (pttFrameIntervalRef.current) {
        clearInterval(pttFrameIntervalRef.current);
        pttFrameIntervalRef.current = null;
      }
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

        // Spatial: stop frame capture and collect frames
        if (pttFrameIntervalRef.current) {
          clearInterval(pttFrameIntervalRef.current);
          pttFrameIntervalRef.current = null;
        }
        const spatialFrames = [...pttFramesRef.current];
        const spatialTimestamps = [...pttFrameTimestampsRef.current];
        pttFramesRef.current = [];
        pttFrameTimestampsRef.current = [];

        const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
        const history = currentMessages.slice(-10).map(m => ({ role: m.role, content: m.content }));
        const result = await aiAPI.voiceChat(audioBase64, frameBase64, history, false, 'default');

        // Spatial: send captured frames to backend for video stitching (fire and forget)
        if (spatialFrames.length > 2) {
          const consent = useAuthStore.getState().profile?.spatial_capture_consent === true;
          if (consent) {
            const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
            const token = await useAuthStore.getState().getAccessToken();
            if (!token) return;
            fetch(`${BACKEND_URL}/api/spatial/voice-clip`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
              body: JSON.stringify({
                frames: spatialFrames,
                trigger_text: result.transcript,
                ai_response: result.response,
                frame_timestamps_ms: spatialTimestamps,
              }),
            }).catch(() => {}); // Fire and forget
          }
        }

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
        incrementQueryCount();

        if (result.audio_base64) {
          setVoiceState('speaking');
          await playAudio(result.audio_base64);
        }
        setVoiceState('idle');
      } catch (error: any) {
        console.error('Voice chat error:', error);
        const isNet = !error?.response && (error?.code === 'ECONNABORTED' || error?.code === 'ERR_NETWORK' || error?.message?.includes('Network'));
        const is429 = error?.response?.status === 429;
        const is401 = error?.response?.status === 401;
        let voiceErrorMsg = 'Voice processing failed. Please try again.';
        if (isNet) voiceErrorMsg = 'Server is starting up — please try again in a moment.';
        else if (is429) voiceErrorMsg = 'Daily query limit reached. Resets at midnight UTC.';
        else if (is401) voiceErrorMsg = 'Session expired — please log out and back in.';
        // Show Alert in voice mode since errors are invisible otherwise
        Alert.alert('Voice Error', voiceErrorMsg);
        addMessage({
          id: generateId(), role: 'assistant',
          content: voiceErrorMsg,
          displayMode: 'voice', timestamp: new Date(),
        });
        setVoiceState('idle');
      } finally {
        setIsProcessing(false);
      }
      return;
    }

    // Tap during idle → start recording
    // Check query limit before starting (skip in demo mode)
    if (isQueryLimitReached()) {
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
      // Spatial: start capturing frames at 2fps during PTT hold
      pttFramesRef.current = [];
      pttFrameTimestampsRef.current = [];
      pttFrameIntervalRef.current = setInterval(async () => {
        try {
          const f = await captureFrame();
          if (f) {
            pttFramesRef.current.push(f);
            pttFrameTimestampsRef.current.push(Date.now());
          }
        } catch {}
      }, 500);
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
    if (isQueryLimitReached()) {
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

    // Auto-capture camera frame if user asks a visual question and no image is attached
    let imageForThisMessage = pendingImage;
    const imageIsManual = !!pendingImage;
    if (!imageForThisMessage) {
      const visualKeywords = ['see', 'look', 'show', 'what is this', 'what\'s this', 'what is that', 'what\'s that', 'check this', 'wrong here', 'wrong with', 'identify', 'read this', 'read that', 'model number', 'what brand', 'what model', 'point'];
      const textLower = text.toLowerCase();
      const isVisualQuery = visualKeywords.some(kw => textLower.includes(kw));
      if (isVisualQuery && permission?.granted) {
        try {
          const autoFrame = await captureFrame();
          if (autoFrame) imageForThisMessage = autoFrame;
        } catch {}
      }
    }
    setPendingImage(undefined);

    // Add user message (visible as bubble in Text Mode)
    addMessage({
      id: generateId(), role: 'user', content: text,
      image: imageForThisMessage, displayMode: 'text', timestamp: new Date(),
    });

    try {
      const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
      const history = currentMessages.slice(-20).map(m => ({ role: m.role, content: m.content }));
      const response = await aiAPI.chat(
        text,
        imageForThisMessage,
        history,
        false,
        useSettingsStore.getState().units,
        imageIsManual,
      );

      addMessage({
        id: generateId(), role: 'assistant',
        content: response.response || response.message || 'No response.',
        source: response.source,
        confidence: validateConfidence(response.confidence),
        displayMode: 'text', timestamp: new Date(),
      });

      // Optimistic usage increment
      incrementQueryCount();
    } catch (error: any) {
      let errMsg = 'Something went wrong. Please try again.';
      if (error?.response?.status === 401) {
        errMsg = 'Session expired — please sign out and sign back in.';
      } else if (error?.response?.status === 429) {
        errMsg = 'Rate limit reached. Please wait a moment and try again.';
      } else if (error?.response?.status >= 500) {
        errMsg = 'Server error — our backend may be restarting. Try again in 30 seconds.';
      } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network')) {
        errMsg = 'Network error — check your internet connection.';
      } else if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errMsg = 'Request timed out — the server may be waking up. Try again.';
      }
      console.error('[TextChat] Error:', error?.response?.status, error?.message);
      addMessage({
        id: generateId(), role: 'assistant',
        content: errMsg,
        displayMode: 'text', timestamp: new Date(),
      });
    } finally {
      setIsProcessing(false);
    }
  }, [inputText, isProcessing, pendingImage, messages, addMessage, setIsProcessing]);

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

    // Spatial capture consent — ask once on first Job Mode entry
    if (newMode === 'job') {
      const spatialConsent = useAuthStore.getState().profile?.spatial_capture_consent;
      if (spatialConsent === null || spatialConsent === undefined) {
        Alert.alert(
          'Video Recording',
          'Arrival records short video clips when you ask questions or receive alerts. This helps us improve our AI.\n\nYour data is stored securely and never sold. You can disable this anytime in Settings.',
          [
            { text: 'Not Now', style: 'cancel', onPress: () => useAuthStore.getState().updateSpatialConsent(false) },
            { text: 'Enable Recording', onPress: () => useAuthStore.getState().updateSpatialConsent(true) },
          ]
        );
      }
    }

    // Dismiss keyboard when switching modes
    Keyboard.dismiss();

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

    // Clean up Job Mode (LiveKit + both controllers)
    if (interactionMode === 'job') {
      setLivekitActive(false);  // Kill LiveKit room immediately
      if (jobControllerRef.current) {
        jobControllerRef.current.stop();
        jobControllerRef.current = null;
      }
      if (streamingControllerRef.current) {
        streamingControllerRef.current.stop();
        streamingControllerRef.current = null;
      }
    }

    // Bug fix: Reset jobPaused so re-entering job mode doesn't have stale pause state
    setJobPaused(false);
    setJobStarted(false);
    setVoiceConnected(false);
    setJobAIState('monitoring');
    setLastJobAlert(null);
    setInterimTranscript('');
    jobAlertHistoryRef.current = [];

    setInteractionMode(newMode);
  }, [interactionMode, tierLimits, stopAudio, setInteractionMode, setIsRecording, setIsProcessing]);

  // --- JOB MODE EFFECT ---
  // Priority: LiveKit (full-duplex WebRTC) > Streaming (WebSocket) > REST
  // Only activates after user taps the robot start button (jobStarted === true)
  useEffect(() => {
    if (interactionMode !== 'job' || !permission?.granted || !jobStarted) {
      if (jobControllerRef.current) {
        jobControllerRef.current.stop();
        jobControllerRef.current = null;
      }
      if (streamingControllerRef.current) {
        streamingControllerRef.current.stop();
        streamingControllerRef.current = null;
      }
      if (livekitFrameBatcherRef.current) {
        livekitFrameBatcherRef.current.stop();
        livekitFrameBatcherRef.current = null;
      }
      setLivekitActive(false);
      return;
    }

    // Use reactive values so changing these re-runs the effect (enables fallback)
    const livekit = useLiveKit;
    const isStreaming = useStreamingVoice;

    if (livekit && LiveKitVoiceRoom) {
      // --- LIVEKIT PIPELINE (WebRTC full-duplex) ---
      // Voice + vision handled entirely by LiveKit agent (proactive monitor).
      // NO separate FrameBatcher — one AI brain, not two.
      setLivekitActive(true);
      setJobAIState('monitoring');

      return () => {
        setLivekitActive(false);
        setLastJobAlert(null);
        jobAlertHistoryRef.current = [];
      };
    } else if (isStreaming) {
      // --- STREAMING PIPELINE (WebSocket) ---
      const responseTextRef = { current: '' };

      const controller = new StreamingJobModeController(
        {
          onAlert: async (message, severity) => {
            jobAlertHistoryRef.current.push(message);
            if (jobAlertHistoryRef.current.length > 20) jobAlertHistoryRef.current = jobAlertHistoryRef.current.slice(-20);
            setLastJobAlert({ message, severity, ts: Date.now() });
            addMessage({
              id: generateId(), role: 'assistant', content: message,
              alertType: severity === 'critical' ? 'critical' : 'warning',
              source: 'Job Mode Analysis', displayMode: 'job', timestamp: new Date(),
            });
            // Frame alerts still use REST TTS (short one-off utterances)
            try {
      
              const ttsResp = await aiAPI.textToSpeech(message, false);
              if (ttsResp.audio_base64) await playAudio(ttsResp.audio_base64);
            } catch (e) {
              console.log('Job Mode TTS error:', e);
            }
          },
          onTranscriptInterim: (text) => {
            setInterimTranscript(text);
          },
          onTranscriptFinal: (text) => {
            setInterimTranscript('');
            addMessage({ id: generateId(), role: 'user', content: text, displayMode: 'job', timestamp: new Date() });
          },
          onResponseText: (text, done) => {
            responseTextRef.current = text;
            if (done && text) {
              addMessage({ id: generateId(), role: 'assistant', content: text, displayMode: 'job', timestamp: new Date() });
            }
          },
          onStateChange: (state) => {
            // Map streaming states to JobAIState for the UI
            const mapped = state === 'connecting' ? 'monitoring' : state;
            setJobAIState(mapped as JobAIState);
          },
          onInterrupt: () => { /* audio stop handled by streaming controller */ },
          onError: (msg) => {
            console.error('[StreamingJobMode] Error:', msg);
            addMessage({
              id: generateId(), role: 'assistant',
              content: 'Connection issue. Try again.',
              displayMode: 'job', timestamp: new Date(),
            });
          },
          onTurnComplete: () => {
            responseTextRef.current = '';
          },
        },
        { minInterval: 3000, maxInterval: 10000, changeThreshold: 0.10, captureInterval: 3000 },
      );

      // Wire up frame batcher (same as REST controller)
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

      const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
      const history = currentMessages.slice(-6).map(m => ({ role: m.role, content: m.content }));

      controller.start(captureFrame, history).catch(e => {
        console.error('Streaming Job Mode start failed:', e);
        // Fallback: disable streaming and retry with REST
        useSettingsStore.getState().setUseStreamingVoice(false);
      });
      streamingControllerRef.current = controller;

      return () => {
        controller.stop();
        streamingControllerRef.current = null;
        setLastJobAlert(null);
        setInterimTranscript('');
        jobAlertHistoryRef.current = [];
      };
    } else {
      // --- REST PIPELINE (original — unchanged) ---
      const controller = new JobModeController(
        {
          cooldownAfterSpeaking: 2000,
          cooldownAfterDismiss: 5000,
          maxAlertsPerMinute: 4,
        },
        {
          onAlert: async (message, severity) => {
            jobAlertHistoryRef.current.push(message);
            if (jobAlertHistoryRef.current.length > 20) jobAlertHistoryRef.current = jobAlertHistoryRef.current.slice(-20);
            setLastJobAlert({ message, severity, ts: Date.now() });
            addMessage({
              id: generateId(), role: 'assistant', content: message,
              alertType: severity === 'critical' ? 'critical' : 'warning',
              source: 'Job Mode Analysis', displayMode: 'job', timestamp: new Date(),
            });
            try {
      
              const ttsResp = await aiAPI.textToSpeech(message, false);
              if (ttsResp.audio_base64) {
                setJobAIState('speaking');
                await playAudio(ttsResp.audio_base64);
              }
            } catch (e) {
              console.log('Job Mode TTS error:', e);
            }
          },
          onVoiceResponse: async (audioBase64) => {
            try {
              let frame: string | undefined;
              try { frame = await captureFrame(); } catch {}
              const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
              const history = currentMessages.slice(-6).map(m => ({ role: m.role, content: m.content }));
      
              const result = await aiAPI.voiceChat(audioBase64, frame, history, false, 'job');

              addMessage({ id: generateId(), role: 'user', content: result.transcript, displayMode: 'job', timestamp: new Date() });
              addMessage({ id: generateId(), role: 'assistant', content: result.response, source: result.source, confidence: validateConfidence(result.confidence), displayMode: 'job', timestamp: new Date() });

              if (jobControllerRef.current?.wasInterrupted) return;
              if (result.audio_base64) {
                setJobAIState('speaking');
                await playAudio(result.audio_base64);
              }
            } catch (e: any) {
              console.error('[JobMode] voice response failed:', e);
              addMessage({
                id: generateId(), role: 'assistant',
                content: 'Sorry, I didn\'t catch that. Try again.',
                displayMode: 'job', timestamp: new Date(),
              });
            }
          },
          onStateChange: setJobAIState,
          onInterrupt: () => { stopAudio(); },
        },
        { minInterval: 3000, maxInterval: 10000, changeThreshold: 0.10, captureInterval: 3000 },
        { speechThreshold: -25, silenceThreshold: -50, speechMinDuration: 250, silenceMaxDuration: 800, maxSpeechDuration: 10000, meteringInterval: 100 },
      );

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
        setLastJobAlert(null);
        jobAlertHistoryRef.current = [];
      };
    }
  }, [interactionMode, permission?.granted, useLiveKit, useStreamingVoice, jobStarted]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // Swipe-down to dismiss chat
  const chatDragResponder = useMemo(() => PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: (_, g) => g.dy > 10 && Math.abs(g.dy) > Math.abs(g.dx),
    onPanResponderRelease: (_, g) => {
      if (g.dy > 60) {
        dismissChat();
        Keyboard.dismiss();
      }
    },
  }), [dismissChat]);

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
      {/* Camera background — expo-camera for Voice/Text, LiveKit VideoTrack for Job */}
      {/* Voice/Text modes: native camera zoom via zoom prop (0-1 = 0.5x to max) */}
      {permission?.granted && interactionMode !== 'job' && (
        <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" zoom={cameraZoom} />
      )}
      {/* Job Mode: LiveKit VideoTrack — no CSS zoom (causes ugly box), fill screen */}
      {interactionMode === 'job' && localVideoTrackRef && LKVideoTrack && (
        <View style={StyleSheet.absoluteFill}>
          <LKVideoTrack trackRef={localVideoTrackRef} style={StyleSheet.absoluteFill} objectFit="cover" zOrder={0} />
        </View>
      )}
      {interactionMode === 'job' && !localVideoTrackRef && permission?.granted && (
        <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" zoom={cameraZoom} />
      )}

      {/* Dark overlay on camera feed — also handles pinch-to-zoom */}
      <View
        style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(0,0,0,0.35)' }]}
        {...pinchResponder.panHandlers}
      />

      {/* Main content */}
      <View style={{ flex: 1, paddingBottom: interactionMode === 'text' ? keyboardHeight : 0 }}>
        <View style={[styles.content, { paddingTop: insets.top }]}>

          {/* TOP BAR: Hamburger + Mode Selector + New Chat */}
          <View style={styles.topBar}>
            <TouchableOpacity onPress={toggleDrawer} style={styles.iconBtn}>
              <Ionicons name="menu" size={IconSize.lg} color="#FFF" />
            </TouchableOpacity>

            <ModeSelector
              currentMode={interactionMode}
              onModeChange={handleModeChange}
              jobModeAllowed={tierLimits.jobMode}
              voiceAllowed={tierLimits.voiceOutput}
              variant="dark"
            />

            {interactionMode === 'job' ? (
              <TouchableOpacity
                onPress={() => flipCameraRef.current?.()}
                style={styles.iconBtn}
              >
                <Ionicons name="camera-reverse-outline" size={IconSize.lg} color="#FFF" />
              </TouchableOpacity>
            ) : messages.length > 0 ? (
              <TouchableOpacity onPress={() => createNewConversation()} style={styles.newSessionBtn}>
                <Ionicons name="refresh" size={FontSize.sm} color="#FFF" />
                <Text style={styles.newSessionText}>New</Text>
              </TouchableOpacity>
            ) : (
              <View style={styles.iconBtn} />
            )}
          </View>

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
                <TouchableOpacity onPress={openOnboarding} style={styles.howItWorksBtn} activeOpacity={0.7}>
                  <Ionicons name="information-circle-outline" size={14} color="rgba(255,255,255,0.6)" />
                  <Text style={styles.howItWorksText}>How it Works</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {interactionMode === 'text' && (
            <TouchableWithoutFeedback onPress={() => { if (showChat) { dismissChat(); } Keyboard.dismiss(); }} accessible={false}>
              <View style={styles.modeContainer}>
                {/* Chat messages */}
                {showChat && textMessages.length > 0 ? (
                  <Animated.View style={[styles.chatArea, { opacity: chatSlide, transform: [{ translateY: chatSlide.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }] }]}>
                    {/* Collapse handle — tap or swipe down to dismiss */}
                    <View {...chatDragResponder.panHandlers}>
                      <TouchableOpacity
                        onPress={() => { dismissChat(); Keyboard.dismiss(); }}
                        style={styles.collapseBar}
                        activeOpacity={0.7}
                      >
                        <View style={styles.collapseHandle} />
                        <Text style={styles.collapseLabel}>Swipe down to close</Text>
                      </TouchableOpacity>
                    </View>

                    <TouchableWithoutFeedback onPress={() => {}} accessible={false}><View style={{ flex: 1 }}>
                    <FlatList
                      ref={flatListRef}
                      data={textMessages}
                      keyboardDismissMode="on-drag"
                      keyExtractor={(item) => item.id}
                      renderItem={({ item, index }) => {
                        // Typing animation only for the latest assistant message
                        const isLatestAssistant = item.role === 'assistant' && index === textMessages.length - 1;
                        return (
                          <ChatBubble
                            message={item}
                            isLatest={isLatestAssistant}
                            onSave={item.role === 'assistant' ? () => {
                              saveAnswer({
                                id: item.id, question: '', answer: item.content,
                                source: item.source, trade: currentConversation?.trade || 'General',
                                savedAt: new Date(),
                              });
                            } : undefined}
                            onFeedback={item.role === 'assistant' ? (rating, feedbackText) => {
                              // Find the preceding user message as the question
                              const msgIdx = textMessages.findIndex(m => m.id === item.id);
                              const userQ = msgIdx > 0 ? textMessages[msgIdx - 1]?.content : '';
                              // Fire-and-forget — don't block UI
                              feedbackAPI.submit({
                                question: userQ,
                                answer: item.content,
                                rating,
                                feedback_text: feedbackText,
                                source: item.source,
                                conversation_id: currentConversation?.id,
                              }).catch(err => console.warn('[feedback]', err));
                              // Update message in store so rating persists on re-render
                              const conv = useConversationStore.getState().currentConversation;
                              if (conv) {
                                const updatedMessages = conv.messages.map(m =>
                                  m.id === item.id ? { ...m, feedbackRating: rating } : m
                                );
                                useConversationStore.setState(state => ({
                                  currentConversation: state.currentConversation
                                    ? { ...state.currentConversation, messages: updatedMessages }
                                    : null,
                                }));
                              }
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
                    </View></TouchableWithoutFeedback>
                  </Animated.View>
                ) : (
                  <View style={styles.emptyState}>
                    <ArrivalLogo width={48} color="rgba(255,255,255,0.7)" />
                    <Text style={styles.emptyTitle}>Arrival AI</Text>
                    <Text style={styles.emptySubtitle}>Type a question to get started</Text>
                  </View>
                )}

                {/* Processing indicator — animated skeleton bubble */}
                {isProcessing && (
                  <View style={styles.thinkingContainer}>
                    <View style={styles.thinkingAvatar}>
                      <Ionicons name="sparkles" size={IconSize.sm} color={Colors.accent} />
                    </View>
                    <View style={styles.thinkingBubble}>
                      <ThinkingDots />
                    </View>
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
                      <Ionicons name="close-circle" size={18} color={Colors.textMuted} />
                    </TouchableOpacity>
                  </View>
                )}

                {/* Input bar container — no safe area padding when keyboard is up */}
                <View style={{ paddingBottom: keyboardHeight > 0 ? 10 : Math.max(insets.bottom, 6), paddingHorizontal: 10 }}>
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
                        size={IconSize.md}
                        color={pendingImage ? '#FFF' : 'rgba(255,255,255,0.5)'}
                      />
                    </TouchableOpacity>

                    {/* Camera capture */}
                    <TouchableOpacity
                      onPress={async () => {
                        if (isCapturingRef.current) return;
                        isCapturingRef.current = true;
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
                        } finally {
                          isCapturingRef.current = false;
                        }
                      }}
                      activeOpacity={0.7}
                      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                      style={styles.cameraBtn}
                    >
                      <Ionicons
                        name="camera-outline"
                        size={IconSize.md}
                        color={pendingImage ? '#FFF' : 'rgba(255,255,255,0.5)'}
                      />
                    </TouchableOpacity>

                    <TextInput
                      style={styles.textInput}
                      value={inputText}
                      onChangeText={setInputText}
                      placeholder="Ask anything..."
                      placeholderTextColor="rgba(255,255,255,0.4)"
                      editable={true}
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
              {/* LiveKit full-duplex voice — handles all audio via WebRTC */}
              {livekitActive && LiveKitVoiceRoom && (
                <LiveKitVoiceRoom
                  mode="job"
                  active={livekitActive}
                  captureFrame={captureFrame}
                  onVoiceConnected={setVoiceConnected}
                  onStateChange={(state: AgentVoiceState) => {
                    // Map LiveKit agent states to JobAIState for the UI
                    const stateMap: Record<AgentVoiceState, JobAIState> = {
                      connecting: 'monitoring',
                      idle: 'monitoring',
                      listening: 'listening',
                      thinking: 'processing',
                      speaking: 'speaking',
                      error: 'monitoring',
                    };
                    setJobAIState(stateMap[state] || 'monitoring');
                  }}
                  onError={(msg: string) => {
                    // Just log — error is shown inline in LiveKitVoiceRoom with retry button.
                    // Don't add to conversation (it persists and clutters the chat).
                    console.warn('[LiveKit] Error:', msg);
                  }}
                  equipmentContext={equipmentContext}
                  onSendMessageReady={(fn: ((msg: Record<string, any>) => void) | null) => {
                    livekitSendRef.current = fn;
                  }}
                  onGuidanceStateUpdate={(active: boolean) => {
                    console.log(`[Guide] Backend guidance state: active=${active}`);
                    setGuidanceActive(active);
                  }}
                  onLocalVideoTrack={setLocalVideoTrackRef}
                  onFlipCameraReady={(fn: (() => void) | null) => { flipCameraRef.current = fn; }}
                  activeJob={activeJob}
                />
              )}

              {/* ── Job Picker — easily removable block ── */}
              {interactionMode === 'job' && userDocs.length > 0 && (
                <View style={{ position: 'absolute', top: 16, left: 16, zIndex: 20, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  {activeJob ? (
                    <TouchableOpacity
                      onPress={() => setActiveJob(null)}
                      style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(99,102,241,0.85)', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, gap: 6 }}
                    >
                      <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600' }}>{activeJob.replace(/\.[^.]+$/, '')}</Text>
                      <Ionicons name="close-circle" size={15} color="rgba(255,255,255,0.8)" />
                    </TouchableOpacity>
                  ) : (
                    <TouchableOpacity
                      onPress={() => setShowJobPicker(true)}
                      style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.45)', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, gap: 6, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' }}
                    >
                      <Ionicons name="folder-outline" size={14} color="rgba(255,255,255,0.7)" />
                      <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>Set Job</Text>
                    </TouchableOpacity>
                  )}
                </View>
              )}

              {/* Job picker modal */}
              <Modal visible={showJobPicker} transparent animationType="fade" onRequestClose={() => setShowJobPicker(false)}>
                <TouchableOpacity style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center' }} activeOpacity={1} onPress={() => setShowJobPicker(false)}>
                  <View style={{ backgroundColor: '#1a1a2e', borderRadius: 16, padding: 20, width: '80%', maxHeight: '60%' }}>
                    <Text style={{ color: '#fff', fontSize: 17, fontWeight: '700', marginBottom: 16 }}>Select Job</Text>
                    <ScrollView showsVerticalScrollIndicator={false}>
                      {userDocs.map((doc, i) => (
                        <TouchableOpacity
                          key={i}
                          onPress={() => { setActiveJob(doc); setShowJobPicker(false); }}
                          style={{ paddingVertical: 14, borderBottomWidth: i < userDocs.length - 1 ? 1 : 0, borderBottomColor: 'rgba(255,255,255,0.08)', flexDirection: 'row', alignItems: 'center', gap: 10 }}
                        >
                          <Ionicons name="document-text-outline" size={18} color="#6366f1" />
                          <Text style={{ color: '#fff', fontSize: 15 }}>{doc.replace(/\.[^.]+$/, '').replace(/^\d+_/, '')}</Text>
                          {activeJob === doc && <Ionicons name="checkmark-circle" size={18} color="#6366f1" style={{ marginLeft: 'auto' }} />}
                        </TouchableOpacity>
                      ))}
                    </ScrollView>
                  </View>
                </TouchableOpacity>
              </Modal>
              {/* ── End Job Picker ── */}

              <JobModeView
                aiState={jobAIState}
                voiceConnected={voiceConnected}
                isStarted={jobStarted}
                onStart={() => setJobStarted(true)}
                onEquipmentChange={setEquipmentContext}
                onPause={() => {
                  // Handle pause for both streaming and REST controllers
                  if (streamingControllerRef.current) {
                    if (jobPaused) {
                      // Resume is not directly supported — reconnect would be needed
                      // For now, just toggle the pause state
                    } else {
                      streamingControllerRef.current.stop();
                      streamingControllerRef.current = null;
                    }
                  } else if (jobControllerRef.current) {
                    if (jobPaused) {
                      jobControllerRef.current.vad.resume();
                    } else {
                      jobControllerRef.current.vad.pause();
                      jobControllerRef.current.dismiss();
                    }
                  } else {
                    return;
                  }
                  setJobPaused(!jobPaused);
                }}
                isPaused={jobPaused}
                lastAlert={lastJobAlert}
                onInterrupt={() => {
                  if (streamingControllerRef.current) {
                    streamingControllerRef.current.interrupt();
                  } else {
                    jobControllerRef.current?.interrupt();
                  }
                }}
                guidanceActive={guidanceActive}
                onQuickAction={async (action, alertMsg) => {
                  if (action === 'text') return; // Handled internally by JobModeView

                  if (action === 'walkthrough') {
                    // Send guidance request through LiveKit data channel — the agent
                    // handles it natively via start_guidance tool. No separate REST/TTS.
                    // Don't set guidanceActive here — backend broadcasts state update
                    // when guidance actually activates (after start_guidance tool runs).
                    if (livekitSendRef.current) {
                      livekitSendRef.current({ type: 'guidance_request' });
                      console.log('[Guide] Sent guidance_request via data channel');
                    }
                    return;
                  }

                  if (action === 'guidance_stop') {
                    // Stop guidance via data channel — backend broadcasts state update
                    if (livekitSendRef.current) {
                      livekitSendRef.current({ type: 'guidance_stop' });
                      console.log('[Guide] Sent guidance_stop via data channel');
                    }
                    return;
                  }

                  // "Explain" action — still uses REST for quick follow-ups on alerts
                  const followUpText = `You just told me: "${alertMsg}". Explain that in more detail.`;
                  try {
                    addMessage({
                      id: generateId(), role: 'user', content: followUpText,
                      displayMode: 'job', timestamp: new Date(),
                    });

                    const frame = await captureFrame();
                    const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
                    const history = currentMessages.slice(-20).map(m => ({ role: m.role, content: m.content }));

                    setJobAIState('processing');
                    const chatResult = await aiAPI.chat(followUpText, frame, history, false, useSettingsStore.getState().units);

                    addMessage({
                      id: generateId(), role: 'assistant', content: chatResult.response,
                      source: chatResult.source, confidence: validateConfidence(chatResult.confidence),
                      displayMode: 'job', timestamp: new Date(),
                    });

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

          {/* New Chat button */}
          <TouchableOpacity
            style={styles.drawerNewChat}
            onPress={() => { createNewConversation(); toggleDrawer(); }}
            activeOpacity={0.7}
          >
            <Ionicons name="add-circle-outline" size={IconSize.lg} color={Colors.textDark} />
            <Text style={styles.drawerNewChatText}>New Chat</Text>
          </TouchableOpacity>

          {/* Navigation links */}
          <View style={styles.drawerNav}>
            {([
              { icon: 'bookmark-outline' as const, label: 'Saved Answers', route: '/saved-answers' },
              { icon: 'document-text-outline' as const, label: 'Manuals', route: '/manuals' },
              { icon: 'calculator-outline' as const, label: 'Quick Tools', route: '/quick-tools' },
              { icon: 'time-outline' as const, label: 'History', route: '/(tabs)/history' },
              { icon: 'settings-outline' as const, label: 'Settings', route: '/(tabs)/settings' },
            ]).map((item) => (
              <TouchableOpacity
                key={item.route}
                style={styles.drawerNavItem}
                onPress={() => { toggleDrawer(); router.push(item.route as any); }}
              >
                <View style={styles.drawerNavIcon}>
                  <Ionicons name={item.icon} size={18} color={Colors.textMuted} />
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
                    onPress={() => Alert.alert('Delete', 'Delete this conversation?', [
                      { text: 'Cancel', style: 'cancel' },
                      { text: 'Delete', style: 'destructive', onPress: () => deleteConversation(item.id) },
                    ])}
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

      {/* Camera permission request — only shown in voice/job mode */}
      {!permission?.granted && interactionMode !== 'text' && (
        <View style={[StyleSheet.absoluteFill, styles.permissionOverlay]}>
          <Ionicons name="camera-outline" size={48} color="rgba(255,255,255,0.5)" />
          <Text style={styles.permissionTitle}>Camera Access</Text>
          <Text style={styles.permissionSubtitle}>Required for voice and job mode</Text>
          <TouchableOpacity style={styles.permissionBtn} onPress={requestPermission}>
            <Text style={styles.permissionBtnText}>Grant Access</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => Linking.openSettings()}>
            <Text style={styles.permissionLink}>Open Settings Instead</Text>
          </TouchableOpacity>
        </View>
      )}

      {showOnboarding && OnboardingModal && (
        <OnboardingModal visible={true} onClose={() => setShowOnboarding(false)} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.backgroundDark,
  },
  content: {
    flex: 1,
  },

  // --- Top Bar ---
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
  },
  iconBtn: {
    width: 42,
    height: 42,
    borderRadius: Radius.full,
    backgroundColor: Colors.glassDark,
    justifyContent: 'center',
    alignItems: 'center',
  },
  newSessionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.glassDark,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.lg,
    gap: Spacing.xs,
  },
  newSessionText: {
    color: '#FFF',
    fontSize: FontSize.sm,
    fontWeight: '600',
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
  howItWorksBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 14,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.07)',
  },
  howItWorksText: {
    color: 'rgba(255,255,255,0.55)',
    fontSize: 12,
    marginLeft: 4,
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
    fontSize: FontSize.xl,
    fontWeight: '700',
    letterSpacing: -0.5,
    textAlign: 'center',
    marginTop: Spacing.base,
  },
  emptySubtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: FontSize.base,
    marginTop: Spacing.sm,
    textAlign: 'center',
    paddingHorizontal: 40,
    lineHeight: 22,
  },
  collapseBar: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 14,
    paddingBottom: 10,
  },
  collapseHandle: {
    width: 48,
    height: 5,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.35)',
  },
  collapseLabel: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 11,
    fontWeight: '500',
    marginTop: 4,
  },
  processingRow: {
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
  },
  processingText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: FontSize.sm,
    fontStyle: 'italic',
  },
  thinkingContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.xs,
  },
  thinkingAvatar: {
    width: 32,
    height: 32,
    borderRadius: Radius.lg,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: Spacing.sm,
    marginBottom: 2,
  },
  thinkingBubble: {
    backgroundColor: Colors.glassBg,
    borderRadius: Radius.lg,
    borderBottomLeftRadius: 4,
    paddingHorizontal: Spacing.base,
    paddingVertical: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },

  // --- Text Mode: Input bar ---
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: Radius.full,
    paddingLeft: 6,
    paddingRight: 5,
    paddingVertical: 5,
    minHeight: 44,
    maxHeight: 120,
  },
  inputIconBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cameraBtn: {
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
    borderRadius: Spacing.xs,
    backgroundColor: Colors.accent,
  },
  textInput: {
    flex: 1,
    fontSize: FontSize.base,
    color: '#FFF',
    paddingVertical: 6,
    paddingHorizontal: Spacing.sm,
    maxHeight: 100,
    lineHeight: 20,
  },
  sendBtn: {
    width: 32,
    height: 32,
    borderRadius: Radius.lg,
    backgroundColor: 'rgba(255,255,255,0.25)',
    justifyContent: 'center',
    alignItems: 'center',
  },

  // --- Image preview strip ---
  imagePreviewStrip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.backgroundWarm,
    borderRadius: Radius.sm,
    marginHorizontal: Spacing.md,
    marginBottom: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  imagePreviewThumb: {
    width: 24,
    height: 24,
    borderRadius: 6,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
  },
  imagePreviewText: {
    flex: 1,
    marginLeft: Spacing.sm,
    fontSize: FontSize.sm,
    color: Colors.textMuted,
  },
  imagePreviewRemove: {
    padding: Spacing.xs,
  },

  // --- Drawer ---
  drawer: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    backgroundColor: Colors.background,
    zIndex: 11,
    ...Shadow.medium,
  },
  drawerContent: {
    flex: 1,
    paddingHorizontal: 0,
  },
  drawerLogoSection: {
    paddingHorizontal: 20,
    paddingBottom: Spacing.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.borderWarm,
  },
  drawerNewChat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.base,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.backgroundWarm,
    borderRadius: Radius.md,
    marginHorizontal: Spacing.base,
  },
  drawerNewChatText: {
    fontSize: FontSize.base,
    fontWeight: '600',
    color: Colors.textDark,
    letterSpacing: -0.2,
  },
  drawerProfile: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: Spacing.base,
    gap: Spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.borderWarm,
    marginBottom: Spacing.sm,
  },
  drawerAvatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: Colors.buttonDark,
    justifyContent: 'center',
    alignItems: 'center',
  },
  drawerAvatarText: {
    fontSize: FontSize.base,
    fontWeight: '700',
    color: '#FFF',
  },
  drawerName: {
    fontSize: FontSize.base,
    fontWeight: '600',
    color: Colors.text,
  },
  drawerPlan: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    marginTop: 1,
  },
  drawerSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: Spacing.base,
    paddingBottom: Spacing.sm,
  },
  drawerSectionTitle: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textMuted,
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
    fontSize: FontSize.sm,
    color: Colors.text,
  },
  drawerNav: {
    paddingTop: Spacing.sm,
    paddingBottom: Spacing.sm,
    paddingHorizontal: 20,
    gap: 2,
  },
  drawerNavIcon: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    backgroundColor: Colors.backgroundWarm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  drawerNavItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    gap: Spacing.md,
  },
  drawerNavText: {
    flex: 1,
    fontSize: FontSize.base,
    fontWeight: '500',
    color: Colors.text,
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
    fontSize: FontSize.xl,
    fontWeight: '700',
    marginTop: 20,
    textAlign: 'center',
  },
  permissionSubtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: FontSize.base,
    marginTop: Spacing.sm,
    textAlign: 'center',
    lineHeight: 22,
  },
  permissionBtn: {
    marginTop: 28,
    backgroundColor: Colors.accent,
    paddingHorizontal: 28,
    paddingVertical: Spacing.sm + 6,
    borderRadius: Radius.lg,
    ...Shadow.medium,
  },
  permissionBtnText: {
    color: '#FFF',
    fontSize: FontSize.base,
    fontWeight: '600',
  },
  permissionLink: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: FontSize.sm,
    marginTop: Spacing.base,
  },
});
