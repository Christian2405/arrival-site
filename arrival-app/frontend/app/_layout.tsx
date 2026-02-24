import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View } from 'react-native';
import { useSettingsStore } from '../store/settingsStore';
import { useConversationStore } from '../store/conversationStore';
import { useAuthStore } from '../store/authStore';
import { useSavedAnswersStore } from '../store/savedAnswersStore';
import { Colors } from '../constants/Colors';

export default function RootLayout() {
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  const loadConversations = useConversationStore((s) => s.loadConversations);
  const loadAnswers = useSavedAnswersStore((s) => s.loadAnswers);
  const { initialize, session, isLoading, isInitialized } = useAuthStore();
  const router = useRouter();
  const segments = useSegments();

  // Initialize auth + load local data on launch
  useEffect(() => {
    initialize();
    loadSettings();
    loadConversations();
    loadAnswers();
  }, []);

  // Auth-gate navigation
  useEffect(() => {
    if (!isInitialized) return;

    const inAuthGroup = segments[0] === 'login' || segments[0] === 'signup';

    if (!session && !inAuthGroup) {
      // Not signed in → go to login
      router.replace('/login');
    } else if (session && inAuthGroup) {
      // Signed in but on login/signup → go to home
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
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="signup" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}
