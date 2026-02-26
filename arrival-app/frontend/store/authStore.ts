/**
 * Auth store — manages Supabase session, user profile, subscription, and team.
 * Mirrors the website's auth flow exactly so users work on both platforms.
 */

import { create } from 'zustand';
import { Session, User } from '@supabase/supabase-js';
import { supabase } from '../services/supabase';
import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';

// Required so the browser dismisses properly on iOS
WebBrowser.maybeCompleteAuthSession();

export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  primary_trade: string;
  experience_level: string;
  account_type: string;
  preferred_units?: string;
  voice_output?: boolean;
}

export interface Subscription {
  id: string;
  user_id: string;
  plan: 'free' | 'pro' | 'business';
  status: string;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  current_period_end?: string;
}

export interface TeamMembership {
  team_id: string;
  role: string;
  status: string;
  team?: {
    id: string;
    name: string;
    owner_id: string;
    max_seats: number;
  };
}

interface AuthState {
  // State
  session: Session | null;
  user: User | null;
  profile: UserProfile | null;
  subscription: Subscription | null;
  teamMembership: TeamMembership | null;
  isLoading: boolean;
  isInitialized: boolean;

  // Actions
  initialize: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signInWithGoogle: () => Promise<{ error?: string }>;
  signUp: (params: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
    trade: string;
    experience: string;
  }) => Promise<{ error?: string; needsConfirmation?: boolean }>;
  resetPassword: (email: string) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
  loadProfile: () => Promise<void>;
  ensureProfileExists: (user: User) => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  user: null,
  profile: null,
  subscription: null,
  teamMembership: null,
  isLoading: true,
  isInitialized: false,

  initialize: async () => {
    try {
      // Check for existing session
      const { data: { session } } = await supabase.auth.getSession();

      if (session) {
        set({ session, user: session.user });
        await get().ensureProfileExists(session.user);
        await get().loadProfile();
      }

      // Listen for auth state changes
      supabase.auth.onAuthStateChange(async (event, session) => {
        set({ session, user: session?.user || null });

        if (event === 'SIGNED_IN' && session) {
          await get().ensureProfileExists(session.user);
          await get().loadProfile();
        } else if (event === 'SIGNED_OUT') {
          set({
            profile: null,
            subscription: null,
            teamMembership: null,
          });
        }
      });
    } catch (error) {
      console.error('Auth init error:', error);
    } finally {
      set({ isLoading: false, isInitialized: true });
    }
  },

  signIn: async (email, password) => {
    try {
      set({ isLoading: true });

      const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL || '';
      console.log('[Auth] Signing in:', email, '| URL:', supabaseUrl.substring(0, 30), '| Key:', process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ? 'set' : 'MISSING');

      if (!supabaseUrl) {
        return { error: 'App not configured. Restart with: npx expo start --clear' };
      }

      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        console.error('[Auth] Sign-in error:', error.message, '| status:', error.status, '| code:', (error as any).code);
        return { error: error.message };
      }

      console.log('[Auth] Sign-in success, user:', data.user?.id);
      return {};
    } catch (error: any) {
      console.error('[Auth] Sign-in exception:', error);
      return { error: error.message || 'Sign in failed' };
    } finally {
      set({ isLoading: false });
    }
  },

  signInWithGoogle: async () => {
    try {
      set({ isLoading: true });

      // Build the redirect URI using Expo's scheme
      const redirectUri = AuthSession.makeRedirectUri({
        scheme: 'arrival',
        path: 'auth/callback',
      });

      console.log('[Auth] Google OAuth redirect URI:', redirectUri);

      // Use Supabase's signInWithOAuth to get the authorization URL
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectUri,
          skipBrowserRedirect: true,
          queryParams: {
            prompt: 'select_account',
          },
        },
      });

      if (error || !data.url) {
        console.error('[Auth] Google OAuth URL error:', error);
        return { error: error?.message || 'Failed to start Google sign-in' };
      }

      // Open the browser for Google OAuth
      const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUri);

      if (result.type !== 'success') {
        console.log('[Auth] Google OAuth cancelled or failed:', result.type);
        // Don't show error for user cancellation
        return result.type === 'cancel' ? {} : { error: 'Google sign-in failed' };
      }

      // Extract tokens from the redirect URL
      const url = result.url;
      const parsedUrl = new URL(url);

      // Supabase returns tokens in the hash fragment
      const hashParams = new URLSearchParams(parsedUrl.hash.substring(1));
      const accessToken = hashParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token');

      if (!accessToken) {
        // Try query params as fallback (PKCE flow uses code)
        const code = parsedUrl.searchParams.get('code');
        if (code) {
          const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
          if (exchangeError) {
            console.error('[Auth] Code exchange error:', exchangeError);
            return { error: exchangeError.message };
          }
          return {};
        }
        return { error: 'No authentication tokens received' };
      }

      // Set the session manually with the tokens
      const { error: sessionError } = await supabase.auth.setSession({
        access_token: accessToken,
        refresh_token: refreshToken || '',
      });

      if (sessionError) {
        console.error('[Auth] Set session error:', sessionError);
        return { error: sessionError.message };
      }

      console.log('[Auth] Google sign-in success');
      return {};
    } catch (error: any) {
      console.error('[Auth] Google sign-in exception:', error);
      return { error: error.message || 'Google sign-in failed' };
    } finally {
      set({ isLoading: false });
    }
  },

  signUp: async ({ email, password, firstName, lastName, trade, experience }) => {
    try {
      set({ isLoading: true });

      // 1. Create auth user (mirrors website auth.js handleSignup)
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { first_name: firstName, last_name: lastName },
        },
      });

      if (error) {
        return { error: error.message };
      }

      // If email confirmation required
      if (!data.session) {
        return { needsConfirmation: true };
      }

      const userId = data.user!.id;

      // 2. Insert user profile (same as website)
      const { error: profileError } = await supabase.from('users').insert({
        id: userId,
        email,
        first_name: firstName,
        last_name: lastName,
        primary_trade: trade,
        experience_level: experience,
        account_type: 'free',
      });

      if (profileError) {
        console.error('Profile insert error:', profileError);
      }

      // 3. Insert free subscription (same as website)
      const { error: subError } = await supabase.from('subscriptions').insert({
        user_id: userId,
        plan: 'free',
        status: 'active',
      });

      if (subError) {
        console.error('Subscription insert error:', subError);
      }

      return {};
    } catch (error: any) {
      return { error: error.message || 'Sign up failed' };
    } finally {
      set({ isLoading: false });
    }
  },

  resetPassword: async (email) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email);
      if (error) return { error: error.message };
      return {};
    } catch (error: any) {
      return { error: error.message || 'Failed to send reset email' };
    }
  },

  signOut: async () => {
    await supabase.auth.signOut();
    set({
      session: null,
      user: null,
      profile: null,
      subscription: null,
      teamMembership: null,
    });
  },

  /**
   * Ensures a users row + subscriptions row exist for OAuth sign-ins.
   * Google OAuth doesn't go through the signup form, so we create
   * the profile on first sign-in if it doesn't exist yet.
   */
  ensureProfileExists: async (user: User) => {
    try {
      // Check if profile already exists
      const { data: existing } = await supabase
        .from('users')
        .select('id')
        .eq('id', user.id)
        .maybeSingle();

      if (existing) return; // Already exists

      // Also check if subscription exists (prevent duplicates)
      const { data: existingSub } = await supabase
        .from('subscriptions')
        .select('id')
        .eq('user_id', user.id)
        .limit(1);

      if (existingSub && existingSub.length > 0) return; // Has subscription, profile might just be RLS-blocked

      // Extract name from Google metadata
      const meta = user.user_metadata || {};
      const fullName = meta.full_name || meta.name || '';
      const firstName = meta.first_name || fullName.split(' ')[0] || '';
      const lastName = meta.last_name || fullName.split(' ').slice(1).join(' ') || '';
      const email = user.email || '';

      console.log('[Auth] Creating profile for OAuth user:', email);

      // Insert user profile
      await supabase.from('users').upsert({
        id: user.id,
        email,
        first_name: firstName,
        last_name: lastName,
        primary_trade: 'other',
        experience_level: '1_3_years',
        account_type: 'free',
      }, { onConflict: 'id', ignoreDuplicates: true });

      // Insert free subscription only if none exists
      await supabase.from('subscriptions').insert({
        user_id: user.id,
        plan: 'free',
        status: 'active',
      });
    } catch (error) {
      console.error('[Auth] ensureProfileExists error:', error);
    }
  },

  loadProfile: async () => {
    const { user } = get();
    if (!user) return;

    try {
      // Load user profile
      const { data: profile, error: profileError } = await supabase
        .from('users')
        .select('*')
        .eq('id', user.id)
        .single();

      if (profileError) {
        console.error('[Auth] Profile load error:', profileError.message, profileError.code);
      }
      console.log('[Auth] Profile loaded:', profile?.email || 'NULL', '| account_type:', profile?.account_type || 'NULL');

      // Load active subscription — order so highest plan wins if duplicates exist
      const planOrder = { business: 1, enterprise: 1, pro: 2, free: 3 };
      const { data: subscriptions, error: subError } = await supabase
        .from('subscriptions')
        .select('*')
        .eq('user_id', user.id)
        .eq('status', 'active');

      if (subError) {
        console.error('[Auth] Subscription load error:', subError.message, subError.code);
      }

      // Pick the highest-tier subscription if multiple exist
      const subscription = subscriptions && subscriptions.length > 0
        ? subscriptions.sort((a: any, b: any) =>
            (planOrder[a.plan as keyof typeof planOrder] || 99) -
            (planOrder[b.plan as keyof typeof planOrder] || 99)
          )[0]
        : null;

      console.log('[Auth] Subscription loaded:', subscription?.plan || 'NULL', '| rows:', subscriptions?.length || 0);

      // Clean up duplicate subscriptions — keep only the highest-tier one
      if (subscriptions && subscriptions.length > 1 && subscription) {
        const dupes = subscriptions.filter((s: any) => s.id !== subscription.id);
        for (const dupe of dupes) {
          console.log('[Auth] Removing duplicate subscription:', dupe.plan, dupe.id);
          await supabase.from('subscriptions').delete().eq('id', dupe.id);
        }
      }

      // Load team membership (with team details)
      const { data: membership } = await supabase
        .from('team_members')
        .select('team_id, role, status, teams(id, name, owner_id, max_seats)')
        .eq('user_id', user.id)
        .eq('status', 'active')
        .single();

      let teamMembership: TeamMembership | null = null;
      if (membership) {
        teamMembership = {
          team_id: membership.team_id,
          role: membership.role,
          status: membership.status,
          team: (membership as any).teams || undefined,
        };
      }

      set({ profile, subscription, teamMembership });
    } catch (error) {
      console.error('Load profile error:', error);
    }
  },

  getAccessToken: async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || null;
  },
}));
