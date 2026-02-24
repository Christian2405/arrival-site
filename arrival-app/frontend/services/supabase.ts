/**
 * Supabase client for React Native.
 * Uses AsyncStorage for session persistence (same project as the website).
 */

import { createClient } from '@supabase/supabase-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || '';

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.warn(
    '⚠️ Supabase env vars not loaded! Restart Expo with: npx expo start --clear',
    { SUPABASE_URL: SUPABASE_URL ? '✓' : '✗', SUPABASE_ANON_KEY: SUPABASE_ANON_KEY ? '✓' : '✗' }
  );
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false, // important for React Native
  },
});
