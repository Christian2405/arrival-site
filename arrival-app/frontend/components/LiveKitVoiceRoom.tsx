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
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import {
  LiveKitRoom,
  AudioSession,
  useConnectionState,
  useParticipants,
  useRoomContext,
  registerGlobals,
} from '@livekit/react-native';
import { ConnectionState, RoomEvent } from 'livekit-client';
import { createLiveKitSession, type LiveKitSession } from '../services/livekitService';

// Register LiveKit globals — must be called once before any LK usage
registerGlobals();

/** Convert a string to Uint8Array (ASCII-safe, no TextEncoder needed) */
function strToBytes(str: string): Uint8Array {
  const buf = new Uint8Array(str.length);
  for (let i = 0; i < str.length; i++) buf[i] = str.charCodeAt(i) & 0xff;
  return buf;
}

export type AgentVoiceState = 'connecting' | 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

interface LiveKitVoiceRoomProps {
  /** "job" or "default" mode */
  mode: 'default' | 'job';
  /** Whether the room should be active */
  active: boolean;
  /** Camera capture function — returns base64 JPEG */
  captureFrame?: () => Promise<string | undefined>;
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
  captureFrame,
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
  const setupRef = useRef<((attempt: number) => void) | null>(null);

  // Update parent when state changes
  const updateState = useCallback((state: AgentVoiceState) => {
    setAgentState(state);
    onStateChange?.(state);
  }, [onStateChange]);

  // Retry function — can be called from error UI or from RoomContent on disconnect
  const retry = useCallback(() => {
    setError(null);
    setSession(null);
    retryCount.current = 0;
    // Trigger re-setup by bumping a counter
    setRetryTrigger(prev => prev + 1);
  }, []);

  const [retryTrigger, setRetryTrigger] = useState(0);

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
        // Start iOS audio session with voiceChat mode for echo cancellation
        if (!audioSessionStarted.current) {
          await AudioSession.configureAudio({
            android: {
              audioTypeOptions: {
                audioMode: 'inCommunication',
              },
            },
            ios: {
              defaultOutput: 'speaker',
            },
          });
          // Set iOS to voiceChat mode for better echo cancellation
          await AudioSession.setAppleAudioConfiguration({
            audioCategory: 'playAndRecord',
            audioCategoryOptions: ['allowBluetooth', 'defaultToSpeaker'],
            audioMode: 'voiceChat',
          });
          await AudioSession.startAudioSession();
          audioSessionStarted.current = true;
        }

        updateState('connecting');
        setError(null);
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
          // All retries exhausted — show error with retry button
          const shortMsg = e.message?.includes('cold start')
            ? 'Server is starting up. Tap to retry.'
            : e.message?.includes('Not authenticated')
            ? 'Please sign in and try again.'
            : 'Connection failed. Tap to retry.';
          console.error(`[LiveKitVoice] All retries exhausted: ${e.message}`);
          setError(shortMsg);
          updateState('error');
          // Notify parent but DON'T add to conversation — error is shown inline
          onError?.(shortMsg);
        }
      }
    };

    setupRef.current = setup;
    setup(0);

    return () => {
      cancelled = true;
      unmounted.current = true;
    };
  }, [active, mode, retryTrigger]);

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
      <TouchableOpacity style={styles.errorContainer} onPress={retry} activeOpacity={0.7}>
        <Text style={styles.errorText}>{error}</Text>
        <View style={styles.retryBadge}>
          <Text style={styles.retryText}>Retry</Text>
        </View>
      </TouchableOpacity>
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
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      }}
    >
      <RoomContent
        onStateChange={updateState}
        onAgentTranscript={onAgentTranscript}
        onUserTranscript={onUserTranscript}
        onRetry={retry}
        unmountedRef={unmounted}
        captureFrame={captureFrame}
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
  onRetry,
  unmountedRef,
  captureFrame,
}: {
  onStateChange: (state: AgentVoiceState) => void;
  onAgentTranscript?: (text: string, isFinal: boolean) => void;
  onUserTranscript?: (text: string, isFinal: boolean) => void;
  onRetry: () => void;
  unmountedRef: React.MutableRefObject<boolean>;
  captureFrame?: () => Promise<string | undefined>;
}) {
  const connectionState = useConnectionState();
  const participants = useParticipants();
  const room = useRoomContext();
  const hasStartedConnecting = useRef(false);
  const wasConnected = useRef(false);
  const [roomError, setRoomError] = useState<string | null>(null);

  // Send camera frames to agent via data channel (every 5s when connected)
  useEffect(() => {
    if (connectionState !== ConnectionState.Connected || !captureFrame || !room) return;

    let active = true;
    const sendFrame = async () => {
      if (!active) return;
      try {
        const frame = await captureFrame();
        if (frame && room.localParticipant) {
          const data = strToBytes(JSON.stringify({ type: 'camera_frame', image: frame }));
          await room.localParticipant.publishData(data, { reliable: true });
        }
      } catch (e) {
        // Silent fail — frame sending is best-effort
      }
    };

    // Send initial frame immediately, then every 5 seconds
    sendFrame();
    const interval = setInterval(sendFrame, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [connectionState, captureFrame, room]);

  // Map connection state to agent state
  useEffect(() => {
    console.log(`[LiveKitVoice] Connection state: ${connectionState}`);

    switch (connectionState) {
      case ConnectionState.Connecting:
        hasStartedConnecting.current = true;
        setRoomError(null);
        onStateChange('connecting');
        break;
      case ConnectionState.Connected:
        wasConnected.current = true;
        setRoomError(null);
        console.log('[LiveKitVoice] Connected to LiveKit room');
        onStateChange('idle');
        break;
      case ConnectionState.Reconnecting:
        console.log('[LiveKitVoice] Reconnecting...');
        setRoomError(null);
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
          setRoomError('Voice connection lost. Tap to reconnect.');
        } else {
          console.warn('[LiveKitVoice] Failed to connect to LiveKit room');
          onStateChange('error');
          setRoomError('Could not connect. Tap to retry.');
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

  // Check if agent is in the room — accept any non-local participant as the agent
  // LiveKit Agents SDK may use different identity formats (agent-xxx, or custom)
  const agentConnected = participants.some(p => !p.isLocal);

  // Room-level error with retry
  if (roomError) {
    return (
      <TouchableOpacity style={styles.errorContainer} onPress={onRetry} activeOpacity={0.7}>
        <Text style={styles.errorText}>{roomError}</Text>
        <View style={styles.retryBadge}>
          <Text style={styles.retryText}>Retry</Text>
        </View>
      </TouchableOpacity>
    );
  }

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
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    gap: 10,
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
  retryBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: 'rgba(239, 68, 68, 0.12)',
  },
  retryText: {
    color: '#EF4444',
    fontSize: 12,
    fontWeight: '600',
  },
});
