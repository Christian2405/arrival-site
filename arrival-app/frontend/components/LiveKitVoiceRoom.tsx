/**
 * LiveKitVoiceRoom — Full-duplex voice agent powered by LiveKit.
 *
 * This component:
 * - Connects to a LiveKit room with auto-retry (up to 3 attempts)
 * - Publishes the user's microphone audio
 * - Receives and plays agent audio via WebRTC (full-duplex)
 * - Handles vision requests from the agent via data channel
 * - Handles disconnect/reconnect gracefully
 * - Handles cleanup on unmount
 *
 * Vision Architecture (data channel mediated):
 * Agent sends "vision_request" via data channel → This component captures a
 * fresh frame from the camera → Calls /api/analyze-frame with the frame →
 * Sends the text analysis back to the agent via data channel.
 * This avoids all cross-process issues between the agent and FastAPI.
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import {
  LiveKitRoom,
  AudioSession,
  useConnectionState,
  useParticipants,
  useRoomContext,
  useTracks,
  registerGlobals,
} from '@livekit/react-native';
import { ConnectionState, RoomEvent, Track } from 'livekit-client';
import { createLiveKitSession, type LiveKitSession } from '../services/livekitService';
import { supabase } from '../services/supabase';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Register LiveKit globals — must be called once before any LK usage
registerGlobals();

export type AgentVoiceState = 'connecting' | 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

export interface EquipmentContext {
  equipment_type: string;
  brand?: string;
  model?: string;
}

interface LiveKitVoiceRoomProps {
  /** "job" or "default" mode */
  mode: 'default' | 'job';
  /** Whether the room should be active */
  active: boolean;
  /** Camera capture function — returns base64 JPEG */
  captureFrame?: () => Promise<string | undefined>;
  /** Callback with agent state changes */
  onStateChange?: (state: AgentVoiceState) => void;
  /** Callback when voice agent connects/disconnects */
  onVoiceConnected?: (connected: boolean) => void;
  /** Callback when agent speaks (for transcript display) */
  onAgentTranscript?: (text: string, isFinal: boolean) => void;
  /** Callback when user speaks (for transcript display) */
  onUserTranscript?: (text: string, isFinal: boolean) => void;
  /** Error callback */
  onError?: (message: string) => void;
  /** Equipment context to send to agent */
  equipmentContext?: EquipmentContext | null;
  /** Exposes a function to send data channel messages to the agent */
  onSendMessageReady?: (sendFn: ((msg: Record<string, any>) => void) | null) => void;
  /** Exposes the local camera track ref for rendering at the root level */
  onLocalVideoTrack?: (trackRef: any | null) => void;
}

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

export default function LiveKitVoiceRoom({
  mode,
  active,
  captureFrame,
  onStateChange,
  onVoiceConnected,
  onAgentTranscript,
  onUserTranscript,
  onError,
  equipmentContext,
  onSendMessageReady,
  onLocalVideoTrack,
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
        // Start audio session if not already started
        if (!audioSessionStarted.current) {
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

  // Show subtle status while getting token — not blocking, just informational
  if (!session) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="rgba(255,255,255,0.4)" />
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
      video={true}
      options={{
        adaptiveStream: false,
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        videoCaptureDefaults: {
          facingMode: 'environment',
          resolution: { width: 1280, height: 720, frameRate: 24 },
        },
      }}
    >
      <RoomContent
        onStateChange={updateState}
        onVoiceConnected={onVoiceConnected}
        onAgentTranscript={onAgentTranscript}
        onUserTranscript={onUserTranscript}
        onRetry={retry}
        unmountedRef={unmounted}
        captureFrame={captureFrame}
        roomName={session.roomName}
        equipmentContext={equipmentContext}
        onSendMessageReady={onSendMessageReady}
        onLocalVideoTrack={onLocalVideoTrack}
      />
    </LiveKitRoom>
  );
}

/**
 * Inner component that has access to room context.
 * Handles:
 * - Connection state tracking
 * - Frame upload loop (every 5s)
 * - Vision request handling from agent (data channel)
 */
function RoomContent({
  onStateChange,
  onVoiceConnected,
  onAgentTranscript,
  onUserTranscript,
  onRetry,
  unmountedRef,
  captureFrame,
  roomName,
  equipmentContext,
  onSendMessageReady,
  onLocalVideoTrack,
}: {
  onStateChange: (state: AgentVoiceState) => void;
  onVoiceConnected?: (connected: boolean) => void;
  onAgentTranscript?: (text: string, isFinal: boolean) => void;
  onUserTranscript?: (text: string, isFinal: boolean) => void;
  onRetry: () => void;
  unmountedRef: React.MutableRefObject<boolean>;
  captureFrame?: () => Promise<string | undefined>;
  roomName?: string;
  equipmentContext?: EquipmentContext | null;
  onSendMessageReady?: (sendFn: ((msg: Record<string, any>) => void) | null) => void;
  onLocalVideoTrack?: (trackRef: any | null) => void;
}) {
  const connectionState = useConnectionState();
  const participants = useParticipants();
  const room = useRoomContext();
  const tracks = useTracks([Track.Source.Camera]);
  const hasStartedConnecting = useRef(false);
  const wasConnected = useRef(false);
  const [roomError, setRoomError] = useState<string | null>(null);
  // Track captureFrame in a ref so the data listener always has the latest
  const captureFrameRef = useRef(captureFrame);
  captureFrameRef.current = captureFrame;
  const roomNameRef = useRef(roomName);
  roomNameRef.current = roomName;

  // Send equipment context to agent whenever it changes
  useEffect(() => {
    if (connectionState !== ConnectionState.Connected || !room || !equipmentContext) return;
    try {
      const msg = JSON.stringify({
        type: 'equipment_context',
        equipment_type: equipmentContext.equipment_type,
        brand: equipmentContext.brand || '',
        model: equipmentContext.model || '',
      });
      room.localParticipant.publishData(
        new TextEncoder().encode(msg),
        { reliable: true },
      );
      console.log(`[LiveKitVoice] Equipment context sent: ${equipmentContext.equipment_type}`);
    } catch (e: any) {
      console.debug(`[LiveKitVoice] Equipment context send failed: ${e?.message}`);
    }
  }, [connectionState, room, equipmentContext]);

  // -----------------------------------------------------------------------
  // Vision request handler — agent asks us to capture + analyze via data channel
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (connectionState !== ConnectionState.Connected || !room) return;

    const handleDataReceived = async (
      payload: Uint8Array,
      participant: any,
      _kind?: any,
      _topic?: string,
    ) => {
      // Ignore our own messages
      if (participant?.isLocal) return;

      try {
        const text = new TextDecoder().decode(payload);
        const msg = JSON.parse(text);

        if (msg.type === 'vision_request') {
          console.log(`[LiveKitVoice] ★ Agent requested vision analysis: "${msg.question?.substring(0, 60)}..."`);

          // Step 1: Capture a fresh frame from the camera
          let frame: string | undefined;
          if (captureFrameRef.current) {
            try {
              frame = await captureFrameRef.current();
              if (frame) {
                console.log(`[LiveKitVoice] Frame captured for vision (${Math.round(frame.length / 1024)}KB)`);
              } else {
                console.warn('[LiveKitVoice] captureFrame returned empty for vision request');
              }
            } catch (e: any) {
              console.error('[LiveKitVoice] Frame capture failed for vision:', e?.message);
            }
          } else {
            console.warn('[LiveKitVoice] No captureFrame function available');
          }

          // Step 2: Get auth token
          const { data } = await supabase.auth.getSession();
          const token = data.session?.access_token;
          if (!token) {
            console.warn('[LiveKitVoice] No auth token for vision request');
            // Send error back to agent
            const errorMsg = JSON.stringify({ type: 'vision_error', error: 'No auth token' });
            try {
              await room.localParticipant.publishData(
                new TextEncoder().encode(errorMsg),
                { reliable: true },
              );
            } catch {}
            return;
          }

          // Step 3: Call /api/livekit-analyze with inline frame (bypasses frame store)
          const analyzeUrl = `${BACKEND_URL}/api/livekit-analyze`;
          const currentRoomName = msg.room_name || roomNameRef.current || '';
          console.log(`[LiveKitVoice] Calling ${analyzeUrl} (room=${currentRoomName})`);

          try {
            const resp = await fetch(analyzeUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
              },
              body: JSON.stringify({
                room_name: currentRoomName,
                question: msg.question || 'What do you see?',
                frame: frame || undefined,  // Send fresh frame inline if we have one
              }),
            });

            if (resp.ok) {
              const result = await resp.json();
              const analysis = result.analysis || '';
              console.log(`[LiveKitVoice] ✓ Vision analysis received (${analysis.length} chars)`);

              // Step 4: Send result back to agent via data channel
              const resultMsg = JSON.stringify({
                type: 'vision_result',
                analysis: analysis,
              });
              await room.localParticipant.publishData(
                new TextEncoder().encode(resultMsg),
                { reliable: true },
              );
              console.log('[LiveKitVoice] ✓ Vision result sent to agent');
            } else {
              const errorText = await resp.text().catch(() => '');
              console.error(`[LiveKitVoice] Vision API failed: ${resp.status} ${errorText}`);

              // Send error back to agent so it doesn't hang
              const errorMsg = JSON.stringify({
                type: 'vision_error',
                error: `API ${resp.status}: ${errorText.substring(0, 100)}`,
              });
              await room.localParticipant.publishData(
                new TextEncoder().encode(errorMsg),
                { reliable: true },
              );
            }
          } catch (e: any) {
            console.error(`[LiveKitVoice] Vision request failed: ${e?.message}`);
            // Send error back to agent
            const errorMsg = JSON.stringify({
              type: 'vision_error',
              error: e?.message || 'Network error',
            });
            try {
              await room.localParticipant.publishData(
                new TextEncoder().encode(errorMsg),
                { reliable: true },
              );
            } catch {}
          }
        }
      } catch {
        // Not JSON or not a vision request — ignore
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);
    console.log('[LiveKitVoice] ✓ Vision request handler registered');

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [connectionState, room]);

  // Camera is published via video={true} + videoCaptureDefaults on LiveKitRoom.
  // No need for setCameraEnabled — LiveKit handles back camera via WebRTC natively,
  // bypassing expo-camera which iOS kills when LiveKit's audio session activates.

  // HTTP frame upload fallback — uses captureFrame from expo-camera if available
  // This only works BEFORE LiveKit connects (first frame). After that, the video
  // track above handles frame delivery.
  useEffect(() => {
    if (connectionState !== ConnectionState.Connected || !captureFrame || !roomName) {
      return;
    }

    let active = true;

    // Single initial capture before LiveKit kills the camera
    const initialCapture = async () => {
      if (!active) return;
      try {
        const frame = await captureFrame();
        if (!frame) return;
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;
        if (!token) return;
        await fetch(`${BACKEND_URL}/api/livekit-frame`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ room_name: roomName, frame }),
        });
        console.log('[LiveKitVoice] Initial HTTP frame uploaded');
      } catch {}
    };

    // Capture once immediately, before LiveKit's audio session kills the camera
    initialCapture();

    return () => { active = false; };
  }, [connectionState, captureFrame, roomName]);

  // -----------------------------------------------------------------------
  // Connection state tracking
  // -----------------------------------------------------------------------
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
  }, [participants]);

  // Check if agent is in the room
  const agentConnected = participants.some(p => !p.isLocal);

  // Notify parent when voice agent connects/disconnects
  useEffect(() => {
    onVoiceConnected?.(agentConnected);
  }, [agentConnected, onVoiceConnected]);

  // Expose send function to parent when connected — allows guidance start/stop via data channel
  useEffect(() => {
    if (connectionState === ConnectionState.Connected && room?.localParticipant) {
      const sendFn = (msg: Record<string, any>) => {
        try {
          room.localParticipant.publishData(
            new TextEncoder().encode(JSON.stringify(msg)),
            { reliable: true },
          );
        } catch (e: any) {
          console.warn('[LiveKitVoice] sendMessage failed:', e?.message);
        }
      };
      onSendMessageReady?.(sendFn);
    } else {
      onSendMessageReady?.(null);
    }
    return () => onSendMessageReady?.(null);
  }, [connectionState, room, onSendMessageReady]);

  // Agent connection timeout — if agent doesn't join within 20s, show error
  const agentTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const agentConnectedRef = useRef(agentConnected);
  const [agentTimedOut, setAgentTimedOut] = useState(false);

  // Keep ref in sync with state
  useEffect(() => {
    agentConnectedRef.current = agentConnected;
  }, [agentConnected]);

  useEffect(() => {
    if (connectionState === ConnectionState.Connected && !agentConnected) {
      // Start timeout — agent should join within 20s
      if (!agentTimeoutRef.current) {
        agentTimeoutRef.current = setTimeout(() => {
          if (!agentConnectedRef.current) {
            setAgentTimedOut(true);
            onStateChange('error');
          }
        }, 20000);
      }
    }

    if (agentConnected) {
      // Agent joined — clear timeout
      if (agentTimeoutRef.current) {
        clearTimeout(agentTimeoutRef.current);
        agentTimeoutRef.current = null;
      }
      setAgentTimedOut(false);
    }

    return () => {
      if (agentTimeoutRef.current) {
        clearTimeout(agentTimeoutRef.current);
        agentTimeoutRef.current = null;
      }
    };
  }, [connectionState, agentConnected]);

  // Agent timed out — show retry
  if (agentTimedOut) {
    return (
      <TouchableOpacity style={styles.errorContainer} onPress={() => {
        setAgentTimedOut(false);
        onRetry();
      }} activeOpacity={0.7}>
        <Text style={styles.errorText}>Voice agent unavailable</Text>
        <View style={styles.retryBadge}>
          <Text style={styles.retryText}>Retry</Text>
        </View>
      </TouchableOpacity>
    );
  }

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

  // Show subtle status while connecting or waiting for agent
  if (connectionState === ConnectionState.Connecting || connectionState === ConnectionState.Reconnecting) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="rgba(255,255,255,0.4)" />
        <Text style={styles.statusText}>Connecting...</Text>
      </View>
    );
  }

  if (connectionState === ConnectionState.Connected && !agentConnected) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="rgba(255,255,255,0.4)" />
        <Text style={styles.statusText}>Waiting for voice agent...</Text>
      </View>
    );
  }

  // Pass local camera track up to parent for rendering at root level
  const localCameraTrack = tracks.find(t => t.participant.isLocal) ?? null;
  useEffect(() => {
    onLocalVideoTrack?.(localCameraTrack);
    return () => onLocalVideoTrack?.(null);
  }, [localCameraTrack, onLocalVideoTrack]);

  // Connected and agent is present — voice is live, no UI needed
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
