/**
 * LiveKit Voice Service — connects the mobile app to the LiveKit voice agent.
 *
 * Flow:
 * 1. App requests a room token from our FastAPI backend
 * 2. App connects to LiveKit Cloud with the token
 * 3. LiveKit dispatches our voice agent to the room
 * 4. Full-duplex voice conversation via WebRTC
 *
 * The agent handles STT/LLM/TTS on the server — the client just streams audio.
 */

import { supabase } from './supabase';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Token request timeout — Render free tier can cold-start in 50s
const TOKEN_TIMEOUT_MS = 60000;

// Pre-fetched session cache — eliminates wait when entering job mode
let cachedSession: LiveKitSession | null = null;
let cacheTimestamp = 0;
const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes (token TTL is 8 hours)

export interface LiveKitSession {
  token: string;
  wsUrl: string;
  roomName: string;
}

/**
 * Request a LiveKit room token from the backend.
 * Requires authenticated Supabase session.
 * Has a 60s timeout to handle Render cold starts.
 */
export async function createLiveKitSession(
  mode: 'default' | 'job' = 'job',
  recordingConsent: boolean = false,
): Promise<LiveKitSession> {
  // Get fresh auth token — always refresh to avoid expired JWT
  const { data: refreshed } = await supabase.auth.refreshSession();
  let authToken = refreshed.session?.access_token;

  if (!authToken) {
    // Fall back to cached session
    const { data } = await supabase.auth.getSession();
    authToken = data.session?.access_token;
  }

  if (!authToken) {
    throw new Error('Not authenticated — please sign in first.');
  }

  console.log(`[LiveKitService] Requesting token from ${BACKEND_URL}/api/livekit-token (mode=${mode})`);

  // Use AbortController for timeout
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TOKEN_TIMEOUT_MS);

  try {
    const response = await fetch(`${BACKEND_URL}/api/livekit-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({ mode, recording_consent: recordingConsent }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[LiveKitService] Token request failed: ${response.status} — ${errorText}`);

      if (response.status === 401) {
        throw new Error('Auth expired — restarting session...');
      }
      throw new Error(`Token error ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log(`[LiveKitService] Token received. Room: ${result.room_name}, URL: ${result.ws_url}`);

    return {
      token: result.token,
      wsUrl: result.ws_url,
      roomName: result.room_name,
    };
  } catch (e: any) {
    if (e.name === 'AbortError') {
      throw new Error('Server is waking up (cold start). Try again in a few seconds.');
    }
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Pre-fetch a LiveKit token so job mode connects instantly.
 * Call this at app startup — silently caches the session.
 */
export async function prefetchLiveKitSession(): Promise<void> {
  try {
    const session = await createLiveKitSession('job');
    cachedSession = session;
    cacheTimestamp = Date.now();
    console.log('[LiveKitService] Pre-fetched session cached');
  } catch (e) {
    // Silent fail — will fetch on demand when entering job mode
    console.log('[LiveKitService] Pre-fetch failed (will retry on demand):', e);
  }
}

/**
 * Get a LiveKit session — uses cache if available, otherwise creates new.
 */
export async function getLiveKitSession(
  mode: 'default' | 'job' = 'job',
  recordingConsent: boolean = false,
): Promise<LiveKitSession> {
  // Always create fresh — cached session may have wrong consent/mode
  return createLiveKitSession(mode, recordingConsent);
}
