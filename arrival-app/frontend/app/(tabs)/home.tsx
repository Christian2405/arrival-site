import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, FlatList, StyleSheet, TouchableOpacity, Pressable,
  Animated, Keyboard, Platform, Alert, KeyboardAvoidingView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { cacheDirectory, EncodingType, readAsStringAsync, writeAsStringAsync, deleteAsync } from 'expo-file-system/legacy';
import { Colors } from '../../constants/Colors';
import { getTierLimits } from '../../constants/Tiers';
import { useConversationStore } from '../../store/conversationStore';
import { useSettingsStore } from '../../store/settingsStore';
import { useSavedAnswersStore } from '../../store/savedAnswersStore';
import { useAuthStore } from '../../store/authStore';
import { aiAPI } from '../../services/api';
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

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  // Camera
  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();

  // Recording
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const recordingPulse = useRef(new Animated.Value(1)).current;

  // Voice state machine (for Default Mode)
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');

  // Job Mode state
  const [jobAIState, setJobAIState] = useState<JobAIState>('monitoring');
  const [jobPaused, setJobPaused] = useState(false);
  const jobControllerRef = useRef<JobModeController | null>(null);

  // Text Mode state
  const [inputText, setInputText] = useState('');
  const [pendingImage, setPendingImage] = useState<string | undefined>();
  const [showChat, setShowChat] = useState(false);
  const chatSlide = useRef(new Animated.Value(0)).current;
  const flatListRef = useRef<FlatList>(null);

  // PTT frame capture ref
  const pttFrameRef = useRef<string | undefined>(undefined);

  // Audio playback
  const currentSoundRef = useRef<Audio.Sound | null>(null);

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerAnim = useRef(new Animated.Value(0)).current;

  // Stores
  const {
    currentConversation, conversations, addMessage, createNewConversation, setCurrentConversation,
    isRecording, isProcessing, setIsRecording, setIsProcessing,
  } = useConversationStore();
  const messages = currentConversation?.messages || [];

  const { demoMode, voiceOutput, interactionMode, setInteractionMode } = useSettingsStore();
  const { saveAnswer } = useSavedAnswersStore();
  const { profile, subscription } = useAuthStore();

  const plan = subscription?.plan || 'free';
  const tierLimits = getTierLimits(plan);

  // --- Camera capture (silent, no shutter) ---
  const captureFrame = useCallback(async (): Promise<string | undefined> => {
    if (!cameraRef.current) return undefined;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.3,
        exif: false,
      });
      return photo?.base64 || undefined;
    } catch {
      return undefined;
    }
  }, []);

  // --- Audio playback (with stop capability) ---
  const playAudio = useCallback(async (audioBase64: string): Promise<void> => {
    // Stop any currently playing audio
    if (currentSoundRef.current) {
      try {
        await currentSoundRef.current.stopAsync();
        await currentSoundRef.current.unloadAsync();
      } catch (_) {}
      currentSoundRef.current = null;
    }

    await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });

    const fileUri = cacheDirectory + `tts_${Date.now()}.mp3`;
    await writeAsStringAsync(fileUri, audioBase64, { encoding: EncodingType.Base64 });
    const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
    currentSoundRef.current = sound;

    return new Promise((resolve) => {
      sound.setOnPlaybackStatusUpdate(async (status: any) => {
        if (status.isLoaded && status.didJustFinish) {
          currentSoundRef.current = null;
          await sound.unloadAsync();
          await deleteAsync(fileUri, { idempotent: true }).catch(() => {});
          resolve();
        }
      });
      sound.playAsync();
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
  }, []);

  // --- Recording cleanup on unmount ---
  useEffect(() => {
    return () => {
      if (recording) {
        recording.stopAndUnloadAsync().catch(() => {});
      }
    };
  }, [recording]);

  // --- Start recording ---
  const startRecording = useCallback(async () => {
    try {
      if (recording) {
        await recording.stopAndUnloadAsync().catch(() => {});
        setRecording(null);
      }
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone access is needed for voice input.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(rec);
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  }, [recording, setIsRecording]);

  // --- Voice save command handler ---
  const handleVoiceSaveCommand = useCallback(() => {
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
    if (lastAssistant) {
      saveAnswer({
        id: generateId(),
        question: [...messages].reverse().find(m => m.role === 'user')?.content || '',
        answer: lastAssistant.content,
        source: lastAssistant.source,
        trade: currentConversation?.trade || 'General',
        savedAt: new Date(),
      });
    }
  }, [messages, currentConversation, saveAnswer]);

  // --- DEFAULT MODE: PTT handlers ---
  const handlePTTStart = useCallback(async () => {
    if (isProcessing) return;
    setVoiceState('listening');
    // Capture frame silently in background
    captureFrame().then(frame => { pttFrameRef.current = frame; });
    await startRecording();
  }, [isProcessing, captureFrame, startRecording]);

  const handlePTTEnd = useCallback(async () => {
    if (!recording) return;
    setIsRecording(false);
    setVoiceState('processing');
    setIsProcessing(true);

    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) { setVoiceState('idle'); setIsProcessing(false); return; }

      const audioBase64 = await readAsStringAsync(uri, { encoding: EncodingType.Base64 });
      const frameBase64 = pttFrameRef.current;
      pttFrameRef.current = undefined;

      // Use composite endpoint for speed
      const history = messages.slice(-20).map(m => ({ role: m.role, content: m.content }));
      const result = await aiAPI.voiceChat(audioBase64, frameBase64, history, demoMode);

      // Check for save commands
      if (SAVE_COMMANDS.test(result.transcript)) {
        handleVoiceSaveCommand();
        setVoiceState('idle');
        setIsProcessing(false);
        return;
      }

      // Store messages (hidden from UI in Default Mode, visible in History)
      addMessage({
        id: generateId(), role: 'user', content: result.transcript,
        displayMode: 'voice', timestamp: new Date(),
      });
      addMessage({
        id: generateId(), role: 'assistant', content: result.response,
        source: result.source, confidence: result.confidence as any,
        displayMode: 'voice', timestamp: new Date(),
      });

      // Play voice response
      setVoiceState('speaking');
      await playAudio(result.audio_base64);
      setVoiceState('idle');
    } catch (error: any) {
      console.error('Voice chat error:', error);
      setVoiceState('idle');
    } finally {
      setIsProcessing(false);
    }
  }, [recording, messages, demoMode, addMessage, playAudio, handleVoiceSaveCommand, setIsRecording, setIsProcessing]);

  // --- TEXT MODE: Send message ---
  const handleTextSubmit = useCallback(async () => {
    const text = inputText.trim();
    if (!text || isProcessing) return;

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
      const history = messages.slice(-20).map(m => ({ role: m.role, content: m.content }));
      const response = await aiAPI.chat(text, imageForThisMessage, history, demoMode);

      addMessage({
        id: generateId(), role: 'assistant', content: response.response,
        source: response.source, confidence: response.confidence as any,
        displayMode: 'text', timestamp: new Date(),
      });

      // NO TTS in Text Mode -- text in = text out
    } catch (error: any) {
      addMessage({
        id: generateId(), role: 'assistant',
        content: error?.message?.includes('Network') ? 'Cannot reach the server. Please check your connection.' : 'Something went wrong. Please try again.',
        displayMode: 'text', timestamp: new Date(),
      });
    } finally {
      setIsProcessing(false);
    }
  }, [inputText, isProcessing, pendingImage, messages, demoMode, addMessage, setIsProcessing]);

  // --- MODE SWITCHING ---
  const handleModeChange = useCallback((newMode: 'default' | 'text' | 'job') => {
    // Cancel in-progress work
    if (recording) {
      recording.stopAndUnloadAsync().catch(() => {});
      setRecording(null);
      setIsRecording(false);
    }
    stopAudio();
    setIsProcessing(false);
    setVoiceState('idle');

    // Clean up Job Mode
    if (interactionMode === 'job' && jobControllerRef.current) {
      jobControllerRef.current.stop();
      jobControllerRef.current = null;
    }

    // Tier gates
    if (newMode === 'job' && !tierLimits.jobMode) {
      Alert.alert('Business Plan Required', 'Job Mode is available on the Business plan.');
      return;
    }
    if (newMode === 'default' && !tierLimits.voiceOutput) {
      Alert.alert('Pro Plan Required', 'Voice mode requires the Pro plan or above.');
      return;
    }

    setInteractionMode(newMode);
  }, [recording, interactionMode, tierLimits, stopAudio, setInteractionMode, setIsRecording, setIsProcessing]);

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
        cooldownAfterSpeaking: 8000,
        cooldownAfterDismiss: 15000,
        maxAlertsPerMinute: 3,
      },
      {
        onAlert: async (message, severity) => {
          addMessage({
            id: generateId(), role: 'assistant', content: message,
            alertType: severity === 'critical' ? 'critical' : 'warning',
            source: 'Job Mode Analysis', displayMode: 'job', timestamp: new Date(),
          });
          try {
            const ttsResp = await aiAPI.textToSpeech(message, demoMode);
            if (ttsResp.audio_base64) await playAudio(ttsResp.audio_base64);
          } catch (e) {
            console.log('Job Mode TTS error:', e);
          }
        },
        onVoiceResponse: async (audioBase64) => {
          try {
            const frame = await captureFrame();
            const currentMessages = useConversationStore.getState().currentConversation?.messages || [];
            const history = currentMessages.slice(-10).map(m => ({ role: m.role, content: m.content }));
            const result = await aiAPI.voiceChat(audioBase64, frame, history, demoMode);

            addMessage({ id: generateId(), role: 'user', content: result.transcript, displayMode: 'job', timestamp: new Date() });
            addMessage({ id: generateId(), role: 'assistant', content: result.response, source: result.source, confidence: result.confidence as any, displayMode: 'job', timestamp: new Date() });

            await playAudio(result.audio_base64);
          } catch (e) {
            console.log('Job Mode voice error:', e);
          }
        },
        onStateChange: setJobAIState,
      },
      { minInterval: 3000, maxInterval: 15000, changeThreshold: 0.05, captureInterval: 2000 },
      { speechThreshold: -30, silenceThreshold: -50, speechMinDuration: 300, silenceMaxDuration: 1500, meteringInterval: 100 },
    );

    // Wire up the frame batcher to call analyzeFrame
    controller.frameBatcher['config'].onAnalyze = async (frame: string) => {
      try {
        const result = await aiAPI.analyzeFrame(frame);
        if (result.alert && result.message) {
          await controller.handleFrameAlert(result.message, result.severity || 'warning');
        }
      } catch (e) {
        console.log('Job Mode frame error:', e);
      }
    };

    controller.start(captureFrame);
    jobControllerRef.current = controller;

    return () => {
      controller.stop();
      jobControllerRef.current = null;
    };
  }, [interactionMode, permission?.granted]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- TEXT MODE: Chat show/hide effects ---
  useEffect(() => {
    if (interactionMode !== 'text') return;
    if (messages.length > 0 && !showChat) {
      setShowChat(true);
      chatSlide.setValue(1);
    }
  }, [messages.length, showChat, interactionMode, chatSlide]);

  const dismissChat = useCallback(() => {
    Animated.timing(chatSlide, { toValue: 0, duration: 250, useNativeDriver: true }).start(() => {
      setShowChat(false);
      createNewConversation();
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
  const SCREEN_WIDTH = 350;
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
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
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

            <TouchableOpacity onPress={() => createNewConversation()} style={styles.iconBtn}>
              <Ionicons name="add-circle-outline" size={24} color="#FFF" />
            </TouchableOpacity>
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
                  onPressIn={handlePTTStart}
                  onPressOut={handlePTTEnd}
                  disabled={isProcessing}
                  style={({ pressed }) => [
                    styles.pttButton,
                    pressed && styles.pttButtonActive,
                    voiceState === 'listening' && styles.pttButtonActive,
                    isProcessing && styles.pttButtonDisabled,
                  ]}
                >
                  <Ionicons
                    name={voiceState === 'listening' ? 'radio' : 'mic'}
                    size={32}
                    color="#FFF"
                  />
                </Pressable>
              </View>
            </View>
          )}

          {interactionMode === 'text' && (
            <View style={styles.modeContainer}>
              {/* Chat messages */}
              {showChat && textMessages.length > 0 ? (
                <Animated.View style={[styles.chatArea, { opacity: chatSlide, transform: [{ translateY: chatSlide.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }] }]}>
                  <FlatList
                    ref={flatListRef}
                    data={textMessages}
                    keyExtractor={(item) => item.id}
                    renderItem={({ item }) => (
                      <ChatBubble
                        message={item}
                        onSave={item.role === 'assistant' ? () => {
                          saveAnswer({
                            id: item.id, question: '', answer: item.content,
                            source: item.source, trade: currentConversation?.trade || 'General',
                            savedAt: new Date(),
                          });
                        } : undefined}
                      />
                    )}
                    contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 8 }}
                    showsVerticalScrollIndicator={false}
                    inverted={false}
                    onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
                    keyboardShouldPersistTaps="handled"
                  />

                  {/* Dismiss button */}
                  <TouchableOpacity onPress={dismissChat} style={styles.dismissBtn}>
                    <Ionicons name="chevron-down" size={20} color="rgba(255,255,255,0.6)" />
                  </TouchableOpacity>
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

              {/* Text input bar */}
              <View style={[styles.inputBar, { paddingBottom: Math.max(insets.bottom, 8) }]}>
                {/* Camera snap button */}
                <TouchableOpacity
                  onPress={async () => {
                    const frame = await captureFrame();
                    if (frame) setPendingImage(frame);
                  }}
                  style={styles.inputIconBtn}
                >
                  <Ionicons
                    name="camera"
                    size={22}
                    color={pendingImage ? Colors.accent : 'rgba(255,255,255,0.5)'}
                  />
                  {pendingImage && <View style={styles.imageBadge} />}
                </TouchableOpacity>

                <TextInput
                  style={styles.textInput}
                  value={inputText}
                  onChangeText={setInputText}
                  placeholder="Type a message..."
                  placeholderTextColor="rgba(255,255,255,0.35)"
                  editable={!isProcessing}
                  returnKeyType="send"
                  onSubmitEditing={handleTextSubmit}
                />

                {inputText.trim() ? (
                  <TouchableOpacity onPress={handleTextSubmit} style={styles.sendBtn}>
                    <Ionicons name="send" size={20} color="#FFF" />
                  </TouchableOpacity>
                ) : null}
              </View>
            </View>
          )}

          {interactionMode === 'job' && (
            <View style={styles.modeContainer}>
              <JobModeView
                aiState={jobAIState}
                onPause={() => {
                  if (jobPaused) {
                    jobControllerRef.current?.vad.resume();
                  } else {
                    jobControllerRef.current?.vad.pause();
                    jobControllerRef.current?.dismiss();
                  }
                  setJobPaused(!jobPaused);
                }}
                isPaused={jobPaused}
              />
            </View>
          )}
        </View>
      </KeyboardAvoidingView>

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
        <View style={[styles.drawerContent, { paddingTop: insets.top + 16 }]}>
          {/* Profile section */}
          <View style={styles.drawerProfile}>
            <View style={styles.drawerAvatar}>
              <Ionicons name="person" size={24} color="#FFF" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.drawerName}>{displayName}</Text>
              <Text style={styles.drawerPlan}>{(plan || 'free').charAt(0).toUpperCase() + (plan || 'free').slice(1)} Plan</Text>
            </View>
          </View>

          {/* Conversations */}
          <Text style={styles.drawerSectionTitle}>Recent Conversations</Text>
          <FlatList
            data={conversations.slice(0, 20)}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.drawerConvItem}
                onPress={() => {
                  setCurrentConversation(item);
                  toggleDrawer();
                }}
              >
                <Ionicons name="chatbubble-outline" size={16} color="rgba(255,255,255,0.5)" />
                <Text style={styles.drawerConvText} numberOfLines={1}>{item.title}</Text>
              </TouchableOpacity>
            )}
            contentContainerStyle={{ paddingHorizontal: 16 }}
            showsVerticalScrollIndicator={false}
          />

          {/* Navigation links */}
          <View style={styles.drawerNav}>
            {([
              { icon: 'bookmark-outline' as const, label: 'Saved Answers', route: '/saved-answers' },
              { icon: 'document-text-outline' as const, label: 'Manuals', route: '/manuals' },
              { icon: 'code-slash-outline' as const, label: 'Codes', route: '/codes' },
              { icon: 'calculator-outline' as const, label: 'Quick Tools', route: '/quick-tools' },
            ]).map((item) => (
              <TouchableOpacity
                key={item.route}
                style={styles.drawerNavItem}
                onPress={() => { toggleDrawer(); router.push(item.route as any); }}
              >
                <Ionicons name={item.icon} size={20} color="rgba(255,255,255,0.7)" />
                <Text style={styles.drawerNavText}>{item.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
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
    backgroundColor: Colors.recording || '#FF3B30',
    transform: [{ scale: 1.1 }],
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
  dismissBtn: {
    alignSelf: 'center',
    width: 40,
    height: 26,
    borderRadius: 13,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 6,
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
    alignItems: 'center',
    backgroundColor: Colors.glassBg || 'rgba(255,255,255,0.92)',
    borderRadius: 26,
    marginHorizontal: 12,
    paddingLeft: 6,
    paddingRight: 5,
    paddingTop: 6,
    height: 52,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 6,
  },
  inputIconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  imageBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: Colors.accent,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: Colors.text,
    paddingVertical: 0,
    paddingHorizontal: 8,
    letterSpacing: -0.2,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },

  // --- Drawer ---
  drawer: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    backgroundColor: Colors.backgroundDark || '#1C1C1E',
    zIndex: 11,
    shadowColor: '#000',
    shadowOffset: { width: 4, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 20,
  },
  drawerContent: {
    flex: 1,
    paddingHorizontal: 0,
  },
  drawerProfile: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 20,
    gap: 12,
  },
  drawerAvatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: 'rgba(255,255,255,0.12)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  drawerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
  },
  drawerPlan: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 2,
  },
  drawerSectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.4)',
    letterSpacing: 1,
    textTransform: 'uppercase',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
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
    color: 'rgba(255,255,255,0.8)',
  },
  drawerNav: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255,255,255,0.1)',
    paddingTop: 12,
    paddingBottom: 20,
    paddingHorizontal: 20,
    gap: 4,
  },
  drawerNavItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    gap: 12,
  },
  drawerNavText: {
    fontSize: 15,
    fontWeight: '500',
    color: 'rgba(255,255,255,0.8)',
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
