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

// Bug #25: Guard flag to prevent auth listener from firing during initial load
let _initializing = false;

/** Convert raw API/auth errors into user-friendly messages */
function friendlyError(raw: string): string {
  const lower = raw.toLowerCase();
  if (lower.includes('unacceptable audience')) return 'Apple Sign-In is temporarily unavailable. Please try another sign-in method.';
  if (lower.includes('invalid login credentials')) return 'Incorrect email or password. Try resetting your password.';
  if (lower.includes('email not confirmed')) return 'Please check your email and confirm your account first.';
  if (lower.includes('already registered')) return 'This email is already registered. Try signing in instead.';
  if (lower.includes('network') || lower.includes('fetch')) return 'No internet connection. Please check your network and try again.';
  if (lower.includes('rate limit') || lower.includes('too many')) return 'Too many attempts. Please wait a moment and try again.';
  if (lower.includes('expired')) return 'Your session has expired. Please sign in again.';
  if (lower.includes('token')) return 'Sign-in failed. Please try again.';
  // Fallback — don't show raw technical messages
  if (raw.length > 80 || lower.includes('error') || lower.includes('exception')) return 'Something went wrong. Please try again.';
  return raw;
}

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
  spatial_capture_consent?: boolean | null;
}

export interface Subscription {
  id: string;
  user_id: string;
  plan: 'free' | 'pro' | 'business' | 'enterprise';
  status: string;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  current_period_end?: string;
  trial_ends_at?: string;
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
  needsOnboarding: boolean;

  // Actions
  initialize: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signInWithGoogle: () => Promise<{ error?: string }>;
  signInWithApple: () => Promise<{ error?: string }>;
  completeOnboarding: (params: { firstName: string; lastName: string; email?: string; trade: string; experience: string }) => Promise<{ error?: string }>;
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
  ensureProfileExists: (user: User, overrideEmail?: string) => Promise<void>;
  getAccessToken: () => Promise<string | null>;
  updateSpatialConsent: (consent: boolean) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  user: null,
  profile: null,
  subscription: null,
  teamMembership: null,
  isLoading: true,
  isInitialized: false,
  needsOnboarding: false,

  initialize: async () => {
    // Bug #25: Prevent auth listener from processing events during initial load
    _initializing = true;
    try {
      // Bug #26: Safe optional chaining — _authSubscription may not exist on first render
      // Listen for auth state changes (clean up previous listener if re-initialized)
      (get() as any)?._authSubscription?.unsubscribe();

      // Check for existing session — use getUser() which validates against the server,
      // not getSession() which just reads cached tokens from storage
      const { data: { user: verifiedUser }, error: userError } = await supabase.auth.getUser();

      if (verifiedUser && !userError) {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          set({ session, user: session.user });
          const provider = session.user.app_metadata?.provider;
          if (provider && provider !== 'email') {
            await get().ensureProfileExists(session.user);
          }
          await get().loadProfile();
        }
      } else {
        // No valid user — clear any stale session
        console.log('[Auth] No valid session, clearing stale data');
        await supabase.auth.signOut().catch(() => {});
        set({ session: null, user: null, needsOnboarding: false });
      }

      // Bug #25: Initial load complete — allow listener to process events
      _initializing = false;

      const { data: { subscription: authSub } } = supabase.auth.onAuthStateChange(async (event, session) => {
        // Bug #25: Skip processing while initial load is in progress
        if (_initializing) return;

        set({ session, user: session?.user || null });

        if (event === 'SIGNED_IN' && session) {
          const provider = session.user.app_metadata?.provider;
          if (provider && provider !== 'email') {
            await get().ensureProfileExists(session.user);
          }
          await get().loadProfile();
        } else if (event === 'SIGNED_OUT') {
          set({
            profile: null,
            subscription: null,
            teamMembership: null,
          });
        }
      });
      (set as any)({ _authSubscription: authSub });
    } catch (error) {
      console.error('Auth init error:', error);
      _initializing = false;
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
        return { error: friendlyError(error.message) };
      }

      console.log('[Auth] Sign-in success, user:', data.user?.id);
      // Set session directly — don't rely solely on onAuthStateChange
      if (data.session) {
        set({ session: data.session, user: data.session.user });
        await get().loadProfile();
      }
      return {};
    } catch (error: any) {
      console.error('[Auth] Sign-in exception:', error);
      return { error: friendlyError(error.message || 'Sign in failed') };
    } finally {
      set({ isLoading: false });
    }
  },

  signInWithGoogle: async () => {
    try {
      set({ isLoading: true });

      // Generate redirect URI that works in both Expo Go and standalone builds.
      // Expo Go: returns exp://192.168.x.x:8081/--/auth/callback
      // Standalone: returns arrival://auth/callback
      const redirectUri = AuthSession.makeRedirectUri({
        scheme: 'arrival',
        path: 'auth/callback',
      });

      console.log('[Auth] Google OAuth — redirect URI:', redirectUri);

      // Tell Supabase to redirect directly to the app (not via website).
      // This avoids the middleman auth-callback.html which fails in Expo Go
      // because the arrival:// custom scheme isn't registered there.
      // IMPORTANT: This redirect URI must be whitelisted in Supabase Auth settings:
      //   - arrival://auth/callback (for production builds)
      //   - exp://* (for Expo Go development — add as wildcard)
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

      // Open system browser for Google OAuth.
      // openAuthSessionAsync intercepts the redirect back to redirectUri
      // and returns the full URL with tokens in the hash fragment.
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

      // Run ensureProfileExists BEFORE setting session to avoid race condition
      // where _layout routes to home before onboarding flag is set
      _initializing = true; // Block onAuthStateChange from running ensureProfileExists again

      const { error: sessionError } = await supabase.auth.setSession({
        access_token: accessToken,
        refresh_token: refreshToken || '',
      });

      if (sessionError) {
        _initializing = false;
        console.error('[Auth] Set session error:', sessionError);
        return { error: sessionError.message };
      }

      // Now run ensureProfileExists with the session active
      const { data: { session: newSession } } = await supabase.auth.getSession();
      if (newSession) {
        set({ session: newSession, user: newSession.user });
        await get().ensureProfileExists(newSession.user);
        await get().loadProfile();
      }

      _initializing = false;
      console.log('[Auth] Google sign-in success, needsOnboarding:', get().needsOnboarding);
      return {};
    } catch (error: any) {
      console.error('[Auth] Google sign-in exception:', error);
      return { error: friendlyError(error.message || 'Google sign-in failed') };
    } finally {
      set({ isLoading: false });
    }
  },

  signInWithApple: async () => {
    try {
      set({ isLoading: true });

      const AppleAuth = await import('expo-apple-authentication');

      const credential = await AppleAuth.signInAsync({
        requestedScopes: [
          AppleAuth.AppleAuthenticationScope.FULL_NAME,
          AppleAuth.AppleAuthenticationScope.EMAIL,
        ],
      });

      if (!credential.identityToken) {
        return { error: 'Apple Sign-In failed. Please try again.' };
      }

      // Block onAuthStateChange while we set up the session
      _initializing = true;

      const { data, error } = await supabase.auth.signInWithIdToken({
        provider: 'apple',
        token: credential.identityToken,
      });

      if (error) {
        _initializing = false;
        console.error('[Auth] Apple sign-in error:', error);
        return { error: friendlyError(error.message) };
      }

      if (data.session) {
        set({ session: data.session, user: data.session.user });

        // Apple only provides name + email on FIRST sign-in — store them
        const appleEmail = credential.email || '';
        const appleFirstName = credential.fullName?.givenName || '';
        const appleLastName = credential.fullName?.familyName || '';

        if (appleFirstName || appleEmail) {
          await supabase.auth.updateUser({
            data: {
              ...(appleFirstName && {
                first_name: appleFirstName,
                last_name: appleLastName,
                full_name: `${appleFirstName} ${appleLastName}`.trim(),
              }),
              ...(appleEmail && { apple_real_email: appleEmail }),
            },
          });
        }

        // Pass Apple's real email so the profile uses it instead of the relay address
        await get().ensureProfileExists(data.session.user, appleEmail || undefined);
        await get().loadProfile();
      }

      _initializing = false;
      console.log('[Auth] Apple sign-in success, needsOnboarding:', get().needsOnboarding);
      return {};
    } catch (error: any) {
      _initializing = false;
      // User cancelled — don't show error
      if (error.code === 'ERR_REQUEST_CANCELED') {
        return {};
      }
      console.error('[Auth] Apple sign-in exception:', error);
      return { error: friendlyError(error.message || 'Apple sign-in failed') };
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
        return { error: friendlyError(error.message) };
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
        account_type: 'pro',
      });

      // Bug #13: If profile insert failed, do not continue to subscription insert
      if (profileError) {
        console.error('Profile insert error:', profileError);
        return { error: 'Failed to create user profile. Please try again.' };
      }

      // 3. Insert pro subscription with 7-day trial (matches website signup)
      const trialEnd = new Date();
      trialEnd.setDate(trialEnd.getDate() + 7);
      const { error: subError } = await supabase.from('subscriptions').insert({
        user_id: userId,
        plan: 'pro',
        status: 'active',
        trial_ends_at: trialEnd.toISOString(),
      });

      if (subError) {
        console.error('Subscription insert error:', subError);
      }

      // 4. Send welcome email (fire-and-forget, matches website auth.js)
      const accessToken = data.session?.access_token;
      if (accessToken) {
        const siteUrl = process.env.EXPO_PUBLIC_SITE_URL || 'https://arrivalcompany.com';
        fetch(`${siteUrl}/.netlify/functions/send-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${accessToken}` },
          body: JSON.stringify({ to: email, template: 'welcome', args: [firstName] }),
        }).catch((err) => console.error('Welcome email error:', err));
      }

      return {};
    } catch (error: any) {
      return { error: friendlyError(error.message || 'Sign up failed') };
    } finally {
      set({ isLoading: false });
    }
  },

  resetPassword: async (email) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email);
      if (error) return { error: friendlyError(error.message) };
      return {};
    } catch (error: any) {
      return { error: friendlyError(error.message || 'Failed to send reset email') };
    }
  },

  signOut: async () => {
    // Sign out of Supabase first (before clearing state)
    await supabase.auth.signOut().catch(() => {});

    // Clear all state
    set({
      session: null,
      user: null,
      profile: null,
      subscription: null,
      teamMembership: null,
      needsOnboarding: false,
    });

    // Clear usage store on sign out
    try {
      const { useUsageStore } = await import('./usageStore');
      useUsageStore.getState().clear();
    } catch (e) {
      console.error('Failed to clear usage store:', e);
    }

    // Clear AsyncStorage
    try {
      const AsyncStorage = (await import('@react-native-async-storage/async-storage')).default;
      await AsyncStorage.multiRemove([
        'conversations',
        'saved_answers',
        'voice_output',
        'demo_mode',
        'job_mode',
        'voice_speed',
        'units',
        'text_size',
        'interaction_mode',
        'settings_v2_migrated',
      ]);
    } catch (e) {
      console.error('Failed to clear AsyncStorage on signout:', e);
    }
  },

  /**
   * Ensures a users row + subscriptions row exist for OAuth sign-ins.
   * Google OAuth doesn't go through the signup form, so we create
   * the profile on first sign-in if it doesn't exist yet.
   */
  ensureProfileExists: async (user: User, overrideEmail?: string) => {
    try {
      // Check if profile already exists by ID
      const { data: existing, error: existingError } = await supabase
        .from('users')
        .select('id, primary_trade, email')
        .eq('id', user.id)
        .maybeSingle();

      // CRITICAL: if the lookup errored, do NOT assume new user — that would
      // wrongly send existing users to onboarding on every transient network blip.
      if (existingError) {
        console.error('[Auth] ensureProfileExists lookup error — not changing onboarding state:', existingError);
        return;
      }

      if (existing) {
        // Existing profile — check if email is an Apple relay that needs fixing
        if (existing.email?.includes('privaterelay.appleid.com')) {
          // Show onboarding so user can enter their real email
          set({ needsOnboarding: true });
          return;
        }
        return;
      }

      // No row exists — genuinely new OAuth user
      const email = overrideEmail || user.email || '';
      console.log('[Auth] New OAuth user, showing onboarding:', email);
      set({ needsOnboarding: true });

      const meta = user.user_metadata || {};
      const fullName = meta.full_name || meta.name || '';
      const firstName = meta.first_name || fullName.split(' ')[0] || '';
      const lastName = meta.last_name || fullName.split(' ').slice(1).join(' ') || '';

      await supabase.from('users').upsert({
        id: user.id,
        email,
        first_name: firstName,
        last_name: lastName,
        primary_trade: 'other',
        experience_level: '1_3_years',
        account_type: 'pro',
      }, { onConflict: 'id' });

      const trialEnd = new Date();
      trialEnd.setDate(trialEnd.getDate() + 7);
      await supabase.from('subscriptions').upsert({
        user_id: user.id,
        plan: 'pro',
        status: 'active',
        trial_ends_at: trialEnd.toISOString(),
      }, { onConflict: 'user_id' });
    } catch (error) {
      console.error('[Auth] ensureProfileExists error:', error);
    }
  },

  completeOnboarding: async ({ firstName, lastName, email, trade, experience }) => {
    const { user } = get();
    if (!user) return { error: 'Not authenticated' };

    try {
      const updateData: any = {
        first_name: firstName,
        last_name: lastName,
        primary_trade: trade,
        experience_level: experience,
      };
      if (email) updateData.email = email;

      const { error } = await supabase.from('users').update(updateData).eq('id', user.id);

      if (error) {
        if (error.message.includes('users_email_key')) {
          return { error: 'This email is already linked to another account. Try a different email or sign in with that account instead.' };
        }
        return { error: friendlyError(error.message) };
      }

      set({ needsOnboarding: false });
      await get().loadProfile();
      return {};
    } catch (e: any) {
      return { error: e.message || 'Failed to save profile' };
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
      const planOrder = { enterprise: 0, business: 1, pro: 2, free: 3 };
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

      // Bug #12: Log duplicate subscriptions but do NOT auto-delete them
      if (subscriptions && subscriptions.length > 1) {
        console.warn(
          '[Auth] Multiple active subscriptions found (' + subscriptions.length + '). Using highest tier:',
          subscription?.plan,
        );
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

      // Note: onboarding check is handled by ensureProfileExists on sign-in only

      set({ profile, subscription, teamMembership });
    } catch (error) {
      console.error('Load profile error:', error);
    }
  },

  getAccessToken: async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || null;
  },

  updateSpatialConsent: async (consent: boolean) => {
    const { profile } = get();
    if (!profile) return;
    try {
      await supabase
        .from('users')
        .update({ spatial_capture_consent: consent })
        .eq('id', profile.id);
      set({ profile: { ...profile, spatial_capture_consent: consent } });
    } catch (e) {
      console.error('[authStore] Failed to update spatial consent:', e);
    }
  },
}));
