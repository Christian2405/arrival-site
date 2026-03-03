import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View } from 'react-native';
import * as Sentry from '@sentry/react-native';
import { useSettingsStore } from '../store/settingsStore';
import { useConversationStore } from '../store/conversationStore';
import { useAuthStore } from '../store/authStore';
import { useSavedAnswersStore } from '../store/savedAnswersStore';
import { Colors } from '../constants/Colors';
import OfflineBanner from '../components/OfflineBanner';

// Initialize Sentry — DSN comes from env; no-op if not set
const SENTRY_DSN = process.env.EXPO_PUBLIC_SENTRY_DSN;
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    debug: __DEV__,
    tracesSampleRate: __DEV__ ? 1.0 : 0.2,
    enableAutoSessionTracking: true,
    attachStacktrace: true,
  });
}

function RootLayout() {
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  const loadConversations = useConversationStore((s) => s.loadConversations);
  const loadAnswers = useSavedAnswersStore((s) => s.loadAnswers);
  const { initialize, session, isLoading, isInitialized } = useAuthStore();
  const router = useRouter();
  const segments = useSegments();

  // Initialize auth + load local-only data on launch
  useEffect(() => {
    initialize();
    loadSettings();
  }, []);

  // Bug #32: Load conversations and saved answers only after auth is initialized
  // Cloud sync inside loadConversations needs an active session
  useEffect(() => {
    if (isInitialized) {
      loadConversations();
      loadAnswers();
    }
  }, [isInitialized, session]);

  // Auth-gate navigation
  useEffect(() => {
    if (!isInitialized) return;

    const inAuthGroup = segments[0] === 'login' || segments[0] === 'signup';

    if (!session && !inAuthGroup) {
      // Not signed in → go to login
      router.replace('/login');
    } else if (session && segments[0] !== '(tabs)') {
      // Signed in but not on a tab screen (login/signup/index) → go to home
      router.replace('/(tabs)/home');
    }
  }, [session, isInitialized, segments]);

  // Show loading spinner while checking auth
  if (!isInitialized) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.background }}>
        <ActivityIndicator size="large" color={Colors.accent} />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="auto" />
      <OfflineBanner />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="signup" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}

// Wrap with Sentry for crash reporting (no-op if DSN not set)
export default SENTRY_DSN ? Sentry.wrap(RootLayout) : RootLayout;
