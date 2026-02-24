import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ScrollView,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  Platform,
  Alert,
  Animated,
  Dimensions,
  Keyboard,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { cacheDirectory, readAsStringAsync, writeAsStringAsync, EncodingType } from 'expo-file-system/legacy';

import { Colors } from '../../constants/Colors';
import { useConversationStore, Message } from '../../store/conversationStore';
import { useSettingsStore } from '../../store/settingsStore';
import { useAuthStore } from '../../store/authStore';
import { useSavedAnswersStore } from '../../store/savedAnswersStore';
import { getTierLimits } from '../../constants/Tiers';
import { aiAPI } from '../../services/api';
import ChatBubble from '../../components/ChatBubble';
import ArrivalLogo from '../../components/ArrivalLogo';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const DRAWER_WIDTH = SCREEN_WIDTH * 0.78;

type IoniconsName = keyof typeof Ionicons.glyphMap;

interface DrawerItem {
  icon: IoniconsName;
  label: string;
  route: string;
  badge?: number;
}

const DRAWER_ITEMS: DrawerItem[] = [
  { icon: 'document-text-outline', label: 'Codes', route: '/(tabs)/codes' },
  { icon: 'book-outline', label: 'Manuals', route: '/(tabs)/manuals' },
  { icon: 'build-outline', label: 'Quick Tools', route: '/(tabs)/quick-tools' },
  { icon: 'bookmark-outline', label: 'Saved Answers', route: '/(tabs)/saved-answers' },
  { icon: 'time-outline', label: 'History', route: '/(tabs)/history' },
  { icon: 'settings-outline', label: 'Settings', route: '/(tabs)/settings' },
];

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerAnim = useRef(new Animated.Value(0)).current;

  // Camera
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [flashOn, setFlashOn] = useState(false);

  // Audio recording
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const recordingPulse = useRef(new Animated.Value(1)).current;

  // Chat state
  const [inputText, setInputText] = useState('');
  const [showChat, setShowChat] = useState(false);
  const flatListRef = useRef<FlatList>(null);
  const chatSlide = useRef(new Animated.Value(0)).current;

  // Stores
  const {
    currentConversation,
    isRecording,
    isProcessing,
    addMessage,
    createNewConversation,
    setIsRecording,
    setIsProcessing,
  } = useConversationStore();

  const { demoMode, voiceOutput, jobMode, setJobMode } = useSettingsStore();
  const { saveAnswer } = useSavedAnswersStore();

  // Auth + tier data for drawer footer and Job Mode gating
  const { profile, subscription, teamMembership } = useAuthStore();
  const plan = subscription?.plan || 'free';
  const tierLimits = getTierLimits(plan);
  const displayName = profile
    ? `${profile.first_name} ${profile.last_name}`
    : 'Arrival User';
  const planLabel = plan.charAt(0).toUpperCase() + plan.slice(1) + ' Plan';
  const planColor =
    plan === 'business' ? '#4A90D9' : plan === 'pro' ? Colors.accent : Colors.textSecondary;

  const messages = currentConversation?.messages || [];

  // --- Keyboard height (instant, no animation) ---
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';

    const showSub = Keyboard.addListener(showEvent, (e) => {
      setKeyboardHeight(e.endCoordinates.height);
    });
    const hideSub = Keyboard.addListener(hideEvent, () => {
      setKeyboardHeight(0);
    });

    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  // --- Drawer ---
  const openDrawer = useCallback(() => {
    setDrawerOpen(true);
    Animated.spring(drawerAnim, {
      toValue: 1,
      useNativeDriver: true,
      damping: 24,
      stiffness: 200,
    }).start();
  }, []);

  const closeDrawer = useCallback(() => {
    Animated.timing(drawerAnim, {
      toValue: 0,
      duration: 200,
      useNativeDriver: true,
    }).start(() => setDrawerOpen(false));
  }, []);

  const navigateFromDrawer = (route: string) => {
    closeDrawer();
    setTimeout(() => router.push(route as any), 250);
  };

  // Show chat when messages exist — instant, no animation delay
  useEffect(() => {
    if (messages.length > 0 && !showChat) {
      setShowChat(true);
      chatSlide.setValue(1);
    }
  }, [messages.length]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0 && flatListRef.current) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages.length, isProcessing]);

  // Recording pulse animation
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
  }, [isRecording]);

  // --- Dismiss chat ---
  const dismissChat = useCallback(() => {
    Animated.timing(chatSlide, {
      toValue: 0,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      setShowChat(false);
    });
  }, []);

  // --- Camera Frame Capture ---
  const captureFrame = async (): Promise<string | undefined> => {
    if (!cameraRef.current) return undefined;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.3,
        exif: false,
      });
      return photo?.base64 || undefined;
    } catch (error) {
      console.log('Camera capture failed:', error);
      return undefined;
    }
  };

  // --- Audio Recording (PTT) ---
  const startRecording = async () => {
    try {
      // Clean up any stale recording first
      if (recording) {
        try { await recording.stopAndUnloadAsync(); } catch (_) {}
        setRecording(null);
      }

      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission needed', 'Microphone access is required for voice input.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(rec);
      setIsRecording(true);
    } catch (error: any) {
      console.error('Failed to start recording:', error);
      Alert.alert('Mic Error', error?.message || 'Could not start recording. Check microphone permissions in Settings.');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    setIsRecording(false);
    setIsProcessing(true);
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) { setIsProcessing(false); return; }
      const audioBase64 = await readAsStringAsync(uri, { encoding: EncodingType.Base64 });
      const { text } = await aiAPI.transcribe(audioBase64, demoMode);
      if (text) {
        await sendMessage(text);
      } else {
        setIsProcessing(false);
        Alert.alert('Could not hear you', 'Tap the mic, speak clearly, then tap again to send.');
      }
    } catch (error: any) {
      console.error('Recording failed:', error);
      setIsProcessing(false);
      const msg = error?.message?.includes('Network')
        ? 'Cannot reach the server. Make sure the backend is running.'
        : 'Voice recording failed. Please try again.';
      Alert.alert('Voice Error', msg);
    }
  };

  // --- Send Message ---
  const sendMessage = async (text: string) => {
    if (!text.trim()) return;
    Keyboard.dismiss();
    setInputText('');
    setIsProcessing(true);

    if (!currentConversation) createNewConversation();

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };
    addMessage(userMessage);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const response = await aiAPI.chat(text.trim(), undefined, history, demoMode);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        source: response.source,
        confidence: response.confidence,
        timestamp: new Date(),
      };
      addMessage(assistantMessage);

      if (voiceOutput && response.response) {
        try {
          const ttsResponse = await aiAPI.textToSpeech(response.response, demoMode);
          if (ttsResponse.audio_base64) await playAudio(ttsResponse.audio_base64);
        } catch (e) {
          console.log('TTS error:', e);
          // Voice output failed silently — text response still visible
        }
      }
    } catch (error: any) {
      console.error('Chat failed:', error);
      const isNetwork = error?.message?.includes('Network') || error?.code === 'ECONNABORTED';
      addMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: isNetwork
          ? 'Cannot reach the server. Check that the backend is running and you\'re on the same WiFi network.'
          : 'Sorry, I had trouble processing that. Please try again.',
        confidence: 'low',
        timestamp: new Date(),
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // --- Audio Playback ---
  const playAudio = async (audioBase64: string) => {
    try {
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      const fileUri = cacheDirectory + 'tts_response.mp3';
      await writeAsStringAsync(fileUri, audioBase64, { encoding: EncodingType.Base64 });
      const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
      await sound.playAsync();
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) sound.unloadAsync();
      });
    } catch (error) { console.log('Audio playback error:', error); }
  };

  const handleSubmit = () => {
    if (inputText.trim() && !isProcessing) sendMessage(inputText);
  };

  // --- Permission screen ---
  if (!permission) return <View style={styles.container} />;
  if (!permission.granted) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: Colors.background }]}>
        <View style={styles.permIconWrap}>
          <Ionicons name="camera-outline" size={48} color={Colors.accent} />
        </View>
        <Text style={styles.permTitle}>Camera Access</Text>
        <Text style={styles.permSubtitle}>
          Arrival uses your camera to see equipment and help diagnose issues in real-time.
        </Text>
        <TouchableOpacity style={styles.permButton} onPress={requestPermission}>
          <Ionicons name="lock-open-outline" size={18} color="#FFF" />
          <Text style={styles.permButtonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const drawerTranslateX = drawerAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [-DRAWER_WIDTH, 0],
  });

  const overlayOpacity = drawerAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 0.5],
  });

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
    <View style={styles.container}>
      {/* Camera Background */}
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="back"
        enableTorch={flashOn}
      />

      {/* Subtle overlay */}
      <View style={[StyleSheet.absoluteFill, styles.cameraOverlay]} />

      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        {/* ===== TOP BAR ===== */}
        <View style={styles.topBar}>
          {/* Left: Hamburger */}
          <TouchableOpacity style={styles.topIconBtn} onPress={openDrawer}>
            <Ionicons name="menu" size={24} color="#FFF" />
          </TouchableOpacity>

          {/* Center: Job Mode toggle */}
          <TouchableOpacity
            style={[styles.recordingPill, jobMode && styles.recordingPillActive]}
            onPress={() => {
              if (!tierLimits.jobMode && !jobMode) {
                Alert.alert(
                  'Business Feature',
                  'Job Mode continuous recording is available on the Business plan. Upgrade on arrivalcompany.com to unlock this feature.',
                  [{ text: 'OK' }]
                );
                return;
              }
              setJobMode(!jobMode);
            }}
            activeOpacity={0.8}
          >
            <View style={[styles.recordDot, jobMode && styles.recordDotActive]} />
            <Text style={styles.recordText}>
              {jobMode ? 'Job Mode ON' : 'Job Mode'}
            </Text>
            {!tierLimits.jobMode && (
              <Ionicons name="lock-closed" size={12} color="rgba(255,255,255,0.5)" />
            )}
          </TouchableOpacity>

          {/* Right: Flash */}
          <TouchableOpacity style={styles.topIconBtn} onPress={() => setFlashOn(!flashOn)}>
            <Ionicons name={flashOn ? 'flash' : 'flash-outline'} size={22} color="#FFF" />
          </TouchableOpacity>
        </View>

        {/* Demo badge */}
        {demoMode && (
          <View style={styles.demoBadge}>
            <Text style={styles.demoBadgeText}>DEMO MODE</Text>
          </View>
        )}

        {/* ===== CHAT AREA ===== */}
        <View style={[styles.chatArea, { paddingBottom: keyboardHeight > 0 ? keyboardHeight - insets.bottom : 0 }]}>

          {/* Empty state */}
          {!showChat && messages.length === 0 && (
            <View style={styles.emptyState}>
              <View style={styles.emptyIconWrap}>
                <Ionicons name="chatbubble-ellipses" size={32} color="rgba(255,255,255,0.6)" />
              </View>
              <Text style={styles.emptyTitle}>How can I help you today?</Text>
              <Text style={styles.emptySubtitle}>
                Point your camera at equipment and ask a question
              </Text>
            </View>
          )}

          {/* Messages */}
          {(showChat || messages.length > 0) && (
            <Animated.View
              style={[
                styles.messagesContainer,
                {
                  opacity: chatSlide,
                  transform: [{ translateY: chatSlide.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }],
                },
              ]}
            >
              {/* Dismiss button */}
              <TouchableOpacity style={styles.dismissBtn} onPress={dismissChat}>
                <Ionicons name="chevron-down" size={20} color="rgba(255,255,255,0.7)" />
              </TouchableOpacity>

              <FlatList
                ref={flatListRef}
                data={messages}
                keyExtractor={(item) => item.id}
                renderItem={({ item, index }) => (
                  <ChatBubble
                    message={item}
                    onSave={item.role === 'assistant' ? () => {
                      // Find the preceding user message as the "question"
                      const prevMessages = messages.slice(0, index);
                      const userMsg = [...prevMessages].reverse().find((m) => m.role === 'user');
                      saveAnswer({
                        id: item.id,
                        question: userMsg?.content || 'Voice question',
                        answer: item.content,
                        source: item.source,
                        confidence: item.confidence,
                        savedAt: new Date(),
                        trade: profile?.trade || 'General',
                      });
                    } : undefined}
                  />
                )}
                style={styles.messagesScroll}
                contentContainerStyle={styles.messagesContent}
                keyboardShouldPersistTaps="handled"
                showsVerticalScrollIndicator={true}
                onContentSizeChange={() => {
                  flatListRef.current?.scrollToEnd({ animated: true });
                }}
                ListFooterComponent={
                  isProcessing ? (
                    <View style={styles.thinkingRow}>
                      <View style={styles.thinkingDot} />
                      <ActivityIndicator color={Colors.accent} size="small" />
                      <Text style={styles.thinkingText}>Thinking...</Text>
                    </View>
                  ) : null
                }
              />
            </Animated.View>
          )}

          {/* ===== INPUT BAR ===== */}
          <View style={[styles.inputBarWrap, { paddingBottom: Math.max(insets.bottom, 8) }]}>
            <View style={styles.inputBar}>
              {/* Camera snap button */}
              <TouchableOpacity style={styles.inputIconBtn} onPress={captureFrame}>
                <Ionicons name="camera-outline" size={22} color={Colors.textSecondary} />
              </TouchableOpacity>

              {/* Text input */}
              <TextInput
                style={styles.textInput}
                placeholder="Ask anything..."
                placeholderTextColor={Colors.textLight}
                value={inputText}
                onChangeText={setInputText}
                onSubmitEditing={handleSubmit}
                returnKeyType="send"
                editable={!isProcessing}
                multiline={false}
              />

              {/* Send or Mic */}
              {inputText.trim() ? (
                <TouchableOpacity style={styles.sendBtn} onPress={handleSubmit} disabled={isProcessing}>
                  <Ionicons name="arrow-up" size={20} color="#FFF" />
                </TouchableOpacity>
              ) : (
                <Animated.View style={{ transform: [{ scale: isRecording ? recordingPulse : 1 }] }}>
                  <TouchableOpacity
                    style={[styles.micBtn, isRecording && styles.micBtnActive]}
                    onPress={isRecording ? stopRecording : startRecording}
                    disabled={isProcessing}
                    activeOpacity={0.7}
                  >
                    <Ionicons
                      name={isRecording ? 'radio' : 'mic'}
                      size={22}
                      color={isRecording ? '#FFF' : Colors.accent}
                    />
                  </TouchableOpacity>
                </Animated.View>
              )}
            </View>
          </View>
        </View>
      </SafeAreaView>

      {/* ===== DRAWER OVERLAY ===== */}
      {drawerOpen && (
        <TouchableWithoutFeedback onPress={closeDrawer}>
          <Animated.View style={[styles.drawerOverlay, { opacity: overlayOpacity }]} />
        </TouchableWithoutFeedback>
      )}

      {/* ===== DRAWER ===== */}
      {drawerOpen && (
        <Animated.View
          style={[
            styles.drawer,
            {
              width: DRAWER_WIDTH,
              transform: [{ translateX: drawerTranslateX }],
            },
          ]}
        >
          <SafeAreaView style={styles.drawerSafe}>
            {/* Drawer Header — Arrival Logo */}
            <View style={styles.drawerHeader}>
              <ArrivalLogo width={140} color={Colors.text} />
            </View>

            <View style={styles.drawerDivider} />

            {/* Drawer Items */}
            <ScrollView style={styles.drawerScroll} showsVerticalScrollIndicator={false}>
              {DRAWER_ITEMS.map((item) => (
                <TouchableOpacity
                  key={item.route}
                  style={styles.drawerItem}
                  onPress={() => navigateFromDrawer(item.route)}
                  activeOpacity={0.6}
                >
                  <View style={styles.drawerItemIcon}>
                    <Ionicons name={item.icon} size={20} color={Colors.text} />
                  </View>
                  <Text style={styles.drawerItemLabel}>{item.label}</Text>
                  {item.badge !== undefined && item.badge > 0 && (
                    <View style={styles.drawerBadge}>
                      <Text style={styles.drawerBadgeText}>{item.badge}</Text>
                    </View>
                  )}
                  <Ionicons name="chevron-forward" size={16} color={Colors.textLight} />
                </TouchableOpacity>
              ))}
            </ScrollView>

            {/* Drawer Footer */}
            <View style={styles.drawerFooter}>
              <View style={styles.drawerDivider} />
              <View style={styles.drawerFooterContent}>
                <View style={[styles.drawerAvatar, { backgroundColor: planColor + '20' }]}>
                  <Ionicons name="person" size={18} color={planColor} />
                </View>
                <View style={styles.drawerFooterInfo}>
                  <Text style={styles.drawerFooterName}>{displayName}</Text>
                  <Text style={[styles.drawerFooterPlan, { color: planColor }]}>{planLabel}</Text>
                </View>
              </View>
            </View>
          </SafeAreaView>
        </Animated.View>
      )}
    </View>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  centered: { justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40 },
  cameraOverlay: { backgroundColor: 'rgba(0,0,0,0.08)' },
  safeArea: { flex: 1 },

  // --- Top Bar ---
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  topIconBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: Colors.glassDark,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordingPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.glassDark,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    gap: 8,
  },
  recordingPillActive: {
    backgroundColor: Colors.recording,
  },
  recordDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.4)',
  },
  recordDotActive: {
    backgroundColor: '#FFF',
  },
  recordText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
    letterSpacing: -0.2,
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

  // --- Chat area ---
  chatArea: { flex: 1, justifyContent: 'flex-end' },

  // --- Empty state ---
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 80,
  },
  emptyIconWrap: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(255,255,255,0.12)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 18,
  },
  emptyTitle: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 26,
    fontWeight: '700',
    letterSpacing: -0.5,
    textAlign: 'center',
  },
  emptySubtitle: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 15,
    marginTop: 8,
    textAlign: 'center',
    paddingHorizontal: 40,
    lineHeight: 22,
  },

  // --- Messages ---
  messagesContainer: {
    flex: 1,
  },
  dismissBtn: {
    alignSelf: 'center',
    width: 40,
    height: 26,
    borderRadius: 13,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 6,
  },
  messagesScroll: { flex: 1 },
  messagesContent: {
    paddingVertical: 8,
    paddingBottom: 4,
  },
  thinkingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    gap: 8,
  },
  thinkingDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.accentMuted,
  },
  thinkingText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 14,
  },

  // --- Input Bar ---
  inputBarWrap: {
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.glassBg,
    borderRadius: 26,
    paddingLeft: 6,
    paddingRight: 5,
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
  micBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
  },
  micBtnActive: {
    backgroundColor: Colors.recording,
    shadowColor: Colors.recording,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 4,
  },

  // --- Permission ---
  permIconWrap: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  permTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 8,
    textAlign: 'center',
    letterSpacing: -0.3,
  },
  permSubtitle: {
    fontSize: 15,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 28,
  },
  permButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.accent,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 14,
    gap: 8,
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  permButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },

  // --- Drawer ---
  drawerOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#000',
    zIndex: 10,
  },
  drawer: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    backgroundColor: Colors.background,
    zIndex: 11,
    shadowColor: '#000',
    shadowOffset: { width: 4, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 20,
  },
  drawerSafe: {
    flex: 1,
  },
  drawerHeader: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 18,
  },
  drawerDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: Colors.border,
    marginHorizontal: 20,
  },
  drawerScroll: {
    flex: 1,
    paddingTop: 8,
  },
  drawerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  drawerItemIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#F2F2F7',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  drawerItemLabel: {
    flex: 1,
    fontSize: 16,
    fontWeight: '500',
    color: Colors.text,
    letterSpacing: -0.2,
  },
  drawerBadge: {
    backgroundColor: Colors.accent,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginRight: 8,
  },
  drawerBadgeText: {
    color: '#FFF',
    fontSize: 11,
    fontWeight: '700',
  },
  drawerFooter: {
    paddingBottom: 16,
  },
  drawerFooterContent: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 12,
  },
  drawerAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  drawerFooterInfo: {
    flex: 1,
  },
  drawerFooterName: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
  },
  drawerFooterPlan: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginTop: 1,
  },
});
