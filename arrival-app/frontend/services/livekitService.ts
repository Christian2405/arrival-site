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

export interface LiveKitSession {
  token: string;
  wsUrl: string;
  roomName: string;
}

/**
 * Request a LiveKit room token from the backend.
 * Requires authenticated Supabase session.
 */
export async function createLiveKitSession(
  mode: 'default' | 'job' = 'job',
): Promise<LiveKitSession> {
  // Get fresh auth token
  const { data } = await supabase.auth.getSession();
  let authToken = data.session?.access_token;

  if (!authToken) {
    const { data: refreshed } = await supabase.auth.refreshSession();
    authToken = refreshed.session?.access_token;
  }

  if (!authToken) {
    throw new Error('Not authenticated — please sign in first.');
  }

  const response = await fetch(`${BACKEND_URL}/api/livekit-token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify({ mode }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get LiveKit token: ${response.status} — ${errorText}`);
  }

  const result = await response.json();

  return {
    token: result.token,
    wsUrl: result.ws_url,
    roomName: result.room_name,
  };
}
