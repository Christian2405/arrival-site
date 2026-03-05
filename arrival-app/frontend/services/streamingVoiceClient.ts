/**
 * StreamingVoiceClient — WebSocket client for the streaming voice pipeline.
 * Manages connection lifecycle, sends audio chunks, receives events.
 * Replaces REST-based voiceChat() calls for streaming mode.
 *
 * ALL data is JSON — no binary WebSocket frames in either direction.
 * React Native's binary WebSocket support is unreliable, so audio is base64-encoded.
 */

import { supabase } from './supabase';

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Convert http(s) to ws(s)
function getWsUrl(): string {
  return BASE_URL.replace(/^http/, 'ws');
}

/** Decode a base64 string to ArrayBuffer. */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

export type StreamingState = 'connecting' | 'ready' | 'listening' | 'processing' | 'speaking' | 'disconnected' | 'error';

export interface StreamingVoiceCallbacks {
  /** Partial transcript shown in UI as user speaks */
  onTranscriptInterim?: (text: string) => void;
  /** Final confirmed transcript — add to conversation */
  onTranscriptFinal?: (text: string) => void;
  /** Claude response text chunks — accumulate for display */
  onResponseText?: (text: string, done: boolean) => void;
  /** Raw MP3 audio chunk — pass to StreamingAudioPlayer */
  onAudioChunk?: (chunk: ArrayBuffer) => void;
  /** All audio for this turn has been sent */
  onAudioEnd?: () => void;
  /** Pipeline state change */
  onStateChange?: (state: StreamingState) => void;
  /** Interrupt confirmed by server */
  onInterrupted?: () => void;
  /** Error from server or connection */
  onError?: (message: string) => void;
  /** Connection closed */
  onClose?: (reason: string) => void;
}

export default class StreamingVoiceClient {
  private ws: WebSocket | null = null;
  private callbacks: StreamingVoiceCallbacks;
  private mode: 'default' | 'job';
  private _state: StreamingState = 'disconnected';
  private reconnectAttempts = 0;
  private maxReconnects = 3;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  constructor(callbacks: StreamingVoiceCallbacks, mode: 'default' | 'job' = 'default') {
    this.callbacks = callbacks;
    this.mode = mode;
  }

  get state(): StreamingState {
    return this._state;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private setState(state: StreamingState) {
    this._state = state;
    this.callbacks.onStateChange?.(state);
  }

  /**
   * Connect to the streaming voice WebSocket.
   * Gets a fresh JWT from Supabase and opens the connection.
   */
  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.setState('connecting');

    // Get fresh JWT
    const { data } = await supabase.auth.getSession();
    let token = data.session?.access_token;

    if (!token) {
      // Try refreshing
      const { data: refreshed } = await supabase.auth.refreshSession();
      token = refreshed.session?.access_token;
    }

    if (!token) {
      this.setState('error');
      this.callbacks.onError?.('Not authenticated');
      return;
    }

    const wsUrl = `${getWsUrl()}/ws/voice-session?token=${encodeURIComponent(token)}&mode=${this.mode}`;
    console.log('[StreamingVoice] Connecting to:', wsUrl.replace(/token=[^&]+/, 'token=***'));

    return new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);

        const connectTimeout = setTimeout(() => {
          if (this.ws?.readyState !== WebSocket.OPEN) {
            this.ws?.close();
            this.setState('error');
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000);

        this.ws.onopen = () => {
          clearTimeout(connectTimeout);
          console.log('[StreamingVoice] Connected');
          this.reconnectAttempts = 0;
          this.setState('ready');
          this.startPing();
          resolve();
        };

        this.ws.onmessage = (event: MessageEvent) => {
          this.handleMessage(event);
        };

        this.ws.onerror = (event: Event) => {
          clearTimeout(connectTimeout);
          console.error('[StreamingVoice] WebSocket error:', event);
          this.callbacks.onError?.('WebSocket connection error');
        };

        this.ws.onclose = (event: CloseEvent) => {
          clearTimeout(connectTimeout);
          this.stopPing();
          console.log(`[StreamingVoice] Closed: code=${event.code} reason=${event.reason}`);

          const wasConnected = this._state !== 'connecting';
          this.setState('disconnected');
          this.ws = null;

          if (wasConnected && event.code !== 1000) {
            this.callbacks.onClose?.(`Connection lost: ${event.reason || 'unknown'}`);
          } else {
            this.callbacks.onClose?.(event.reason || 'closed');
          }
        };
      } catch (e) {
        this.setState('error');
        reject(e);
      }
    });
  }

  /**
   * Send initial config after connecting.
   * Call this once after connect() to set up the session.
   */
  sendConfig(config: {
    conversation_history?: Array<{ role: string; content: string }>;
    image_base64?: string;
  }): void {
    this.sendJSON({
      type: 'config',
      mode: this.mode,
      ...config,
    });
  }

  /**
   * Send audio data to the server as base64 JSON (forwarded to Deepgram).
   * Uses JSON instead of binary frames for React Native WebSocket compatibility.
   */
  sendAudio(base64Data: string): void {
    this.sendJSON({ type: 'audio', data: base64Data });
  }

  /**
   * Send an interrupt signal — user spoke while AI was talking.
   * Server will cancel in-flight generation and TTS.
   */
  interrupt(): void {
    this.sendJSON({ type: 'interrupt' });
  }

  /**
   * Update the current camera frame for visual context.
   */
  sendImageUpdate(imageBase64: string): void {
    this.sendJSON({ type: 'image_update', image_base64: imageBase64 });
  }

  /**
   * Gracefully end the session.
   */
  async close(): Promise<void> {
    this.stopPing();
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.sendJSON({ type: 'end_session' });
        // Brief wait for server to process
        await new Promise(r => setTimeout(r, 200));
      } catch {}
      this.ws.close(1000, 'session ended');
    }
    this.ws = null;
    this.setState('disconnected');
  }

  // --- Internals ---

  private sendJSON(data: Record<string, any>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private handleMessage(event: MessageEvent): void {
    // All messages are JSON (no binary frames — React Native can't handle them reliably)
    try {
      const msg = JSON.parse(event.data as string);
      const type = msg.type || '';

      switch (type) {
        case 'transcript_interim':
          this.callbacks.onTranscriptInterim?.(msg.text || '');
          break;

        case 'transcript_final':
          this.callbacks.onTranscriptFinal?.(msg.text || '');
          break;

        case 'response_text':
          this.callbacks.onResponseText?.(msg.text || '', !!msg.done);
          break;

        case 'audio_chunk':
          // MP3 audio as base64 — decode to ArrayBuffer for the audio player
          if (msg.data) {
            const buffer = base64ToArrayBuffer(msg.data);
            this.callbacks.onAudioChunk?.(buffer);
          }
          break;

        case 'audio_end':
          this.callbacks.onAudioEnd?.();
          break;

        case 'state':
          // Server-driven state
          const serverState = msg.state as StreamingState;
          if (serverState) this.setState(serverState);
          break;

        case 'interrupted':
          this.callbacks.onInterrupted?.();
          break;

        case 'error':
          console.error('[StreamingVoice] Server error:', msg.message);
          this.callbacks.onError?.(msg.message || 'Server error');
          break;

        default:
          console.log('[StreamingVoice] Unknown message type:', type, Object.keys(msg));
      }
    } catch (e) {
      console.warn('[StreamingVoice] Failed to parse message:', e, typeof event.data);
    }
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendJSON({ type: 'ping' });
      }
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}
