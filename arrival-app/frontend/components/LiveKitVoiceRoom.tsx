/**
 * LiveKitVoiceRoom — Full-duplex voice agent powered by LiveKit.
 *
 * This component:
 * - Connects to a LiveKit room with auto-retry (up to 3 attempts)
 * - Publishes the user's microphone audio
 * - Receives and plays agent audio via WebRTC (full-duplex)
 * - Handles disconnect/reconnect gracefully
 * - Handles cleanup on unmount
 *
 * The heavy lifting (STT, LLM, TTS, turn detection, interruption)
 * all happens server-side in the LiveKit agent. This client just
 * streams audio and shows status.
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import {
  LiveKitRoom,
  AudioSession,
  useConnectionState,
  useParticipants,
  registerGlobals,
} from '@livekit/react-native';
import { ConnectionState, RoomEvent, DataPacket_Kind } from 'livekit-client';
import { createLiveKitSession, type LiveKitSession } from '../services/livekitService';

// Register LiveKit globals — must be called once before any LK usage
registerGlobals();

export type AgentVoiceState = 'connecting' | 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

interface LiveKitVoiceRoomProps {
  /** "job" or "default" mode */
  mode: 'default' | 'job';
  /** Whether the room should be active */
  active: boolean;
  /** Callback with agent state changes */
  onStateChange?: (state: AgentVoiceState) => void;
  /** Callback when agent speaks (for transcript display) */
  onAgentTranscript?: (text: string, isFinal: boolean) => void;
  /** Callback when user speaks (for transcript display) */
  onUserTranscript?: (text: string, isFinal: boolean) => void;
  /** Error callback */
  onError?: (message: string) => void;
}

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

export default function LiveKitVoiceRoom({
  mode,
  active,
  onStateChange,
  onAgentTranscript,
  onUserTranscript,
  onError,
}: LiveKitVoiceRoomProps) {
  const [session, setSession] = useState<LiveKitSession | null>(null);
  const [agentState, setAgentState] = useState<AgentVoiceState>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>('Connecting to voice agent...');
  const audioSessionStarted = useRef(false);
  const retryCount = useRef(0);
  const unmounted = useRef(false);

  // Update parent when state changes
  const updateState = useCallback((state: AgentVoiceState) => {
    setAgentState(state);
    onStateChange?.(state);
  }, [onStateChange]);

  // Start audio session and get token (with retry)
  useEffect(() => {
    unmounted.current = false;

    if (!active) {
      setSession(null);
      setError(null);
      retryCount.current = 0;
      return;
    }

    let cancelled = false;

    const setup = async (attempt: number) => {
      if (cancelled) return;

      try {
        // Start iOS audio session if not already started
        if (!audioSessionStarted.current) {
          await AudioSession.startAudioSession();
          audioSessionStarted.current = true;
        }

        updateState('connecting');
        if (attempt > 0) {
          setStatusMsg(`Retrying connection (${attempt}/${MAX_RETRIES})...`);
        } else {
          setStatusMsg('Connecting to voice agent...');
        }

        // Get token from backend
        console.log(`[LiveKitVoice] Getting token (attempt ${attempt + 1})...`);
        const lkSession = await createLiveKitSession(mode);
        console.log(`[LiveKitVoice] Token received. Room: ${lkSession.roomName}, URL: ${lkSession.wsUrl}`);

        if (!cancelled) {
          setSession(lkSession);
          setError(null);
          retryCount.current = 0;
        }
      } catch (e: any) {
        console.error(`[LiveKitVoice] Setup failed (attempt ${attempt + 1}):`, e.message);
        if (cancelled) return;

        if (attempt < MAX_RETRIES - 1) {
          // Retry after delay
          const delay = RETRY_DELAY_MS * (attempt + 1);
          console.log(`[LiveKitVoice] Retrying in ${delay}ms...`);
          setStatusMsg(`Connection failed, retrying in ${Math.round(delay / 1000)}s...`);
          setTimeout(() => {
            if (!cancelled) setup(attempt + 1);
          }, delay);
        } else {
          // All retries exhausted
          const msg = `Failed after ${MAX_RETRIES} attempts: ${e.message || 'Unknown error'}`;
          console.error(`[LiveKitVoice] ${msg}`);
          setError(msg);
          updateState('error');
          onError?.(msg);
        }
      }
    };

    setup(0);

    return () => {
      cancelled = true;
      unmounted.current = true;
    };
  }, [active, mode]);

  // Cleanup audio session on unmount
  useEffect(() => {
    return () => {
      if (audioSessionStarted.current) {
        AudioSession.stopAudioSession();
        audioSessionStarted.current = false;
      }
    };
  }, []);

  if (!active) {
    return null;
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  if (!session) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="#F97316" />
        <Text style={styles.statusText}>{statusMsg}</Text>
      </View>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={session.wsUrl}
      token={session.token}
      connect={true}
      audio={true}
      video={false}
      options={{
        adaptiveStream: false,
      }}
    >
      <RoomContent
        onStateChange={updateState}
        onAgentTranscript={onAgentTranscript}
        onUserTranscript={onUserTranscript}
        onError={onError}
        unmountedRef={unmounted}
      />
    </LiveKitRoom>
  );
}

/**
 * Inner component that has access to room context.
 * Tracks whether we ever successfully connected to distinguish
 * "never connected" from "was connected then disconnected".
 */
function RoomContent({
  onStateChange,
  onAgentTranscript,
  onUserTranscript,
  onError,
  unmountedRef,
}: {
  onStateChange: (state: AgentVoiceState) => void;
  onAgentTranscript?: (text: string, isFinal: boolean) => void;
  onUserTranscript?: (text: string, isFinal: boolean) => void;
  onError?: (message: string) => void;
  unmountedRef: React.MutableRefObject<boolean>;
}) {
  const connectionState = useConnectionState();
  const participants = useParticipants();
  const hasStartedConnecting = useRef(false);
  const wasConnected = useRef(false);

  // Map connection state to agent state
  useEffect(() => {
    console.log(`[LiveKitVoice] Connection state: ${connectionState}`);

    switch (connectionState) {
      case ConnectionState.Connecting:
        hasStartedConnecting.current = true;
        onStateChange('connecting');
        break;
      case ConnectionState.Connected:
        wasConnected.current = true;
        console.log('[LiveKitVoice] Connected to LiveKit room');
        onStateChange('idle');
        break;
      case ConnectionState.Reconnecting:
        console.log('[LiveKitVoice] Reconnecting...');
        onStateChange('connecting');
        break;
      case ConnectionState.Disconnected:
        // Ignore the initial Disconnected state (before connecting starts)
        if (!hasStartedConnecting.current) break;
        // Ignore clean unmount
        if (unmountedRef.current) break;

        if (wasConnected.current) {
          console.warn('[LiveKitVoice] Disconnected after being connected');
          onStateChange('error');
          onError?.('Voice connection lost. Switch modes and back to reconnect.');
        } else {
          console.warn('[LiveKitVoice] Failed to connect to LiveKit room');
          onStateChange('error');
          onError?.('Could not connect to voice server. Check your internet connection.');
        }
        break;
    }
  }, [connectionState]);

  // Log participant changes
  useEffect(() => {
    const remoteCount = participants.filter(p => !p.isLocal).length;
    console.log(`[LiveKitVoice] Participants: ${participants.length} total, ${remoteCount} remote`);
    participants.forEach(p => {
      if (!p.isLocal) {
        console.log(`[LiveKitVoice] Remote participant: ${p.identity} (${p.name || 'unnamed'})`);
      }
    });
  }, [participants]);

  // Check if agent is in the room
  const agentConnected = participants.some(p => p.identity?.startsWith('agent-'));

  // Show minimal status
  if (connectionState === ConnectionState.Connecting) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="#F97316" />
        <Text style={styles.statusText}>Connecting...</Text>
      </View>
    );
  }

  if (connectionState === ConnectionState.Reconnecting) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="#F97316" />
        <Text style={styles.statusText}>Reconnecting...</Text>
      </View>
    );
  }

  if (connectionState === ConnectionState.Connected && !agentConnected) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="#F97316" />
        <Text style={styles.statusText}>Waiting for voice agent...</Text>
      </View>
    );
  }

  // Connected and agent is present — voice is live
  // The actual audio streaming happens automatically via WebRTC
  // No UI needed for the voice part — it's all handled by LiveKit
  return null;
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    gap: 8,
  },
  statusText: {
    color: '#9CA3AF',
    fontSize: 13,
    fontWeight: '500',
  },
  errorText: {
    color: '#EF4444',
    fontSize: 13,
    fontWeight: '500',
  },
});
