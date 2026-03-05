/**
 * LiveKitVoiceRoom — Full-duplex voice agent powered by LiveKit.
 *
 * This component:
 * - Connects to a LiveKit room
 * - Publishes the user's microphone audio
 * - Receives and plays agent audio via WebRTC (full-duplex)
 * - Displays connection state and agent state
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
  const audioSessionStarted = useRef(false);

  // Update parent when state changes
  const updateState = useCallback((state: AgentVoiceState) => {
    setAgentState(state);
    onStateChange?.(state);
  }, [onStateChange]);

  // Start audio session and get token
  useEffect(() => {
    if (!active) {
      setSession(null);
      setError(null);
      return;
    }

    let cancelled = false;

    const setup = async () => {
      try {
        // Start iOS audio session if not already started
        if (!audioSessionStarted.current) {
          await AudioSession.startAudioSession();
          audioSessionStarted.current = true;
        }

        updateState('connecting');

        // Get token from backend
        const lkSession = await createLiveKitSession(mode);
        if (!cancelled) {
          setSession(lkSession);
        }
      } catch (e: any) {
        console.error('[LiveKitVoice] Setup failed:', e);
        if (!cancelled) {
          const msg = e.message || 'Failed to connect';
          setError(msg);
          updateState('error');
          onError?.(msg);
        }
      }
    };

    setup();

    return () => {
      cancelled = true;
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
        <Text style={styles.statusText}>Connecting to voice agent...</Text>
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
      />
    </LiveKitRoom>
  );
}

/**
 * Inner component that has access to room context.
 */
function RoomContent({
  onStateChange,
  onAgentTranscript,
  onUserTranscript,
  onError,
}: {
  onStateChange: (state: AgentVoiceState) => void;
  onAgentTranscript?: (text: string, isFinal: boolean) => void;
  onUserTranscript?: (text: string, isFinal: boolean) => void;
  onError?: (message: string) => void;
}) {
  const connectionState = useConnectionState();
  const participants = useParticipants();

  // Map connection state to agent state
  useEffect(() => {
    switch (connectionState) {
      case ConnectionState.Connecting:
        onStateChange('connecting');
        break;
      case ConnectionState.Connected:
        // Connected — agent is idle until user speaks
        onStateChange('idle');
        break;
      case ConnectionState.Reconnecting:
        onStateChange('connecting');
        break;
      case ConnectionState.Disconnected:
        onStateChange('error');
        onError?.('Disconnected from voice agent');
        break;
    }
  }, [connectionState]);

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
