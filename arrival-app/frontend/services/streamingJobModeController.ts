/**
 * StreamingJobModeController — Job mode using the WebSocket streaming pipeline.
 *
 * Replaces the old JobModeController for streaming mode:
 * - Uses StreamingVoiceClient instead of REST API + client-side VAD
 * - Server-side VAD (Deepgram endpointing) replaces voiceActivityDetector.ts
 * - Audio streams in real-time instead of record-all-then-send
 * - TTS audio streams back incrementally instead of waiting for full response
 *
 * FrameBatcher stays unchanged — frame analysis is a separate pipeline.
 * Interrupt sends a WebSocket signal instead of just stopping playback.
 */

import FrameBatcher, { FrameBatcherConfig } from './frameBatcher';
import StreamingVoiceClient, { StreamingState } from './streamingVoiceClient';
import StreamingAudioPlayer from './streamingAudioPlayer';
import StreamingAudioRecorder from './streamingAudioRecorder';

export type StreamingJobAIState = 'connecting' | 'monitoring' | 'listening' | 'processing' | 'speaking' | 'error';

export interface StreamingJobModeCallbacks {
  /** Frame analysis alert — spoken to user */
  onAlert: (message: string, severity: string) => Promise<void>;
  /** Interim transcript — show in UI while user speaks */
  onTranscriptInterim?: (text: string) => void;
  /** Final confirmed transcript — add to conversation */
  onTranscriptFinal?: (text: string) => void;
  /** Claude response text (accumulated) — add to conversation when done */
  onResponseText?: (text: string, done: boolean) => void;
  /** State change */
  onStateChange: (state: StreamingJobAIState) => void;
  /** Called when interrupt happens */
  onInterrupt?: () => void;
  /** Error */
  onError?: (message: string) => void;
  /** Audio playback finished for this turn */
  onTurnComplete?: () => void;
}

export default class StreamingJobModeController {
  frameBatcher: FrameBatcher;

  private client: StreamingVoiceClient;
  private player: StreamingAudioPlayer;
  private recorder: StreamingAudioRecorder;
  private callbacks: StreamingJobModeCallbacks;
  private _state: StreamingJobAIState = 'connecting';
  private isRecording = false;
  private conversationHistory: Array<{ role: string; content: string }> = [];
  private currentResponseText = '';
  private _interrupted = false;

  constructor(
    callbacks: StreamingJobModeCallbacks,
    frameBatcherConfig: Omit<FrameBatcherConfig, 'onAnalyze'>,
  ) {
    this.callbacks = callbacks;

    // --- StreamingVoiceClient (WebSocket to backend) ---
    this.client = new StreamingVoiceClient({
      onTranscriptInterim: (text) => {
        this.callbacks.onTranscriptInterim?.(text);
      },

      onTranscriptFinal: (text) => {
        this.callbacks.onTranscriptFinal?.(text);
      },

      onResponseText: (text, done) => {
        this.currentResponseText += text;
        this.callbacks.onResponseText?.(this.currentResponseText, done);
      },

      onAudioChunk: (chunk) => {
        // Feed MP3 chunks to the player
        this.player.addChunk(chunk);
      },

      onAudioEnd: () => {
        // All audio for this turn received — tell player to finish
        this.player.finish(() => {
          // Playback complete — resume recording
          this.onTurnDone();
        });
      },

      onStateChange: (state) => {
        this.mapServerState(state);
      },

      onInterrupted: () => {
        this._interrupted = true;
        this.callbacks.onInterrupt?.();
      },

      onError: (msg) => {
        console.error('[StreamingJobMode] Error:', msg);
        this.callbacks.onError?.(msg);
      },

      onClose: (reason) => {
        console.log('[StreamingJobMode] Connection closed:', reason);
        if (this._state !== 'error') {
          this.setState('error');
          this.callbacks.onError?.(`Connection lost: ${reason}`);
        }
      },
    }, 'job');

    // --- StreamingAudioPlayer ---
    this.player = new StreamingAudioPlayer();

    // --- StreamingAudioRecorder ---
    this.recorder = new StreamingAudioRecorder({
      onAudioChunk: (base64Data) => {
        // Convert base64 to binary and send to server
        // The server expects raw binary frames for audio
        const binary = base64ToArrayBuffer(base64Data);
        this.client.sendAudio(binary);
      },
      onMetering: (_dB) => {
        // Could use this for UI visualization
      },
      onError: (error) => {
        console.error('[StreamingJobMode] Recorder error:', error);
      },
    });

    // --- FrameBatcher (unchanged from old controller) ---
    this.frameBatcher = new FrameBatcher({
      ...frameBatcherConfig,
      onAnalyze: async (_frame) => {
        // Will be wired up by home.tsx like before
      },
    });
  }

  get state(): StreamingJobAIState {
    return this._state;
  }

  get wasInterrupted(): boolean {
    return this._interrupted;
  }

  // --- Lifecycle ---

  /**
   * Start the streaming job mode session.
   * Connects WebSocket, starts recording, starts frame batching.
   */
  async start(
    captureFrame: () => Promise<string | undefined>,
    conversationHistory?: Array<{ role: string; content: string }>,
    imageBase64?: string,
  ): Promise<void> {
    this.conversationHistory = conversationHistory || [];
    this.setState('connecting');

    try {
      // Connect WebSocket
      await this.client.connect();

      // Send initial config
      this.client.sendConfig({
        conversation_history: this.conversationHistory.slice(-6), // Last 3 exchanges
        image_base64: imageBase64,
      });

      // Start recording audio chunks
      await this.recorder.start();
      this.isRecording = true;

      // Start frame batching
      this.frameBatcher.start(captureFrame);

      this.setState('monitoring');
    } catch (e: any) {
      console.error('[StreamingJobMode] Start failed:', e);
      this.setState('error');
      this.callbacks.onError?.(`Failed to start: ${e.message}`);
      throw e;
    }
  }

  /**
   * Stop everything and clean up.
   */
  async stop(): Promise<void> {
    this.frameBatcher.stop();
    await this.recorder.stop();
    await this.player.stop();
    await this.client.close();
    this.isRecording = false;
    this._interrupted = false;
    this.currentResponseText = '';
  }

  /**
   * Interrupt — user tapped while AI is speaking/processing.
   */
  async interrupt(): Promise<void> {
    this._interrupted = true;

    // Stop audio playback immediately
    await this.player.stop();
    this.player.reset();

    // Tell server to cancel in-flight generation
    this.client.interrupt();

    // Resume recording immediately so user can speak
    this.currentResponseText = '';
    if (!this.isRecording) {
      await this.recorder.resume();
      this.isRecording = true;
    }

    this.setState('monitoring');
    this.callbacks.onInterrupt?.();
  }

  /**
   * Update camera frame for visual context.
   */
  sendImageUpdate(imageBase64: string): void {
    this.client.sendImageUpdate(imageBase64);
  }

  /**
   * Handle a frame analysis alert (from FrameBatcher → analyzeFrame API).
   * Still uses the REST API for frame analysis (separate pipeline).
   * TTS for alerts also uses REST (short one-off utterances).
   */
  async handleFrameAlert(message: string, severity: string): Promise<void> {
    // Delegate to callback — home.tsx handles TTS for alerts via REST
    await this.callbacks.onAlert(message, severity);
  }

  // --- Internals ---

  private setState(state: StreamingJobAIState): void {
    this._state = state;
    this.callbacks.onStateChange(state);
  }

  private mapServerState(serverState: StreamingState): void {
    switch (serverState) {
      case 'listening':
        this.setState('listening');
        break;
      case 'processing':
        this.setState('processing');
        this.currentResponseText = '';
        // Pause recording while processing/speaking
        if (this.isRecording) {
          this.recorder.pause();
          this.isRecording = false;
        }
        break;
      case 'speaking':
        this.setState('speaking');
        break;
      case 'ready':
        // Server is ready for next turn
        if (!this.isRecording) {
          this.recorder.resume().then(() => { this.isRecording = true; });
        }
        this.setState('monitoring');
        break;
      case 'error':
        this.setState('error');
        break;
      default:
        break;
    }
  }

  /**
   * Called when audio playback finishes for a turn.
   */
  private async onTurnDone(): Promise<void> {
    if (this._interrupted) {
      this._interrupted = false;
      return;
    }

    this.player.reset();
    this.currentResponseText = '';

    // Resume recording for next turn
    if (!this.isRecording) {
      await this.recorder.resume();
      this.isRecording = true;
    }

    this.setState('monitoring');
    this.callbacks.onTurnComplete?.();
  }
}

// --- Utility ---

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}
