/**
 * StreamingJobModeController — Job mode using the WebSocket streaming pipeline.
 *
 * This is the hands-free controller for trade workers:
 * - Server-side VAD (Deepgram endpointing) — works in noisy environments
 * - Audio streams in real-time instead of record-all-then-send
 * - TTS audio streams back incrementally
 * - Voice interrupt via metering: if user speaks loudly while AI is talking,
 *   the response is cancelled. No buttons to tap.
 *
 * Audio routing on iOS:
 * - Recording active = audio plays through earpiece (iOS limitation)
 * - We keep recording active at all times for voice interrupt
 * - For loudspeaker playback, we'd need to pause the mic (no voice interrupt)
 * - Trade-off: earpiece audio + voice interrupt > speaker audio + no interrupt
 *
 * FrameBatcher stays unchanged — frame analysis is a separate pipeline.
 */

import FrameBatcher, { FrameBatcherConfig } from './frameBatcher';
import StreamingVoiceClient, { StreamingState } from './streamingVoiceClient';
import StreamingAudioPlayer from './streamingAudioPlayer';
import StreamingAudioRecorder from './streamingAudioRecorder';

export type StreamingJobAIState = 'connecting' | 'monitoring' | 'listening' | 'processing' | 'speaking' | 'error';

/** Metering threshold for voice interrupt (dB).
 * While AI is speaking, if mic picks up audio louder than this, trigger interrupt.
 * Must be high enough that earpiece echo doesn't trigger it (-12 dB is loud/close speech). */
const INTERRUPT_METERING_THRESHOLD = -15;

/** Minimum consecutive loud samples before triggering interrupt (prevents blips). */
const INTERRUPT_MIN_SAMPLES = 2;

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
  private interruptLoudSamples = 0;

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
    // Recorder stays active at all times — audio streams to server continuously.
    // During AI speaking, metering is used for voice interrupt detection.
    this.recorder = new StreamingAudioRecorder({
      onAudioChunk: (base64Data) => {
        this.client.sendAudio(base64Data);
      },
      onMetering: (dB) => {
        // Voice interrupt: if loud speech detected while AI is speaking, interrupt
        if (this._state === 'speaking' && !this._interrupted) {
          if (dB > INTERRUPT_METERING_THRESHOLD) {
            this.interruptLoudSamples++;
            if (this.interruptLoudSamples >= INTERRUPT_MIN_SAMPLES) {
              console.log(`[StreamingJobMode] Voice interrupt triggered (${dB.toFixed(1)} dB)`);
              this.interrupt();
            }
          } else {
            this.interruptLoudSamples = 0;
          }
        } else {
          this.interruptLoudSamples = 0;
        }
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
        conversation_history: this.conversationHistory.slice(-6),
        image_base64: imageBase64,
      });

      // Start recording audio chunks — stays on for the entire session
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
    this.interruptLoudSamples = 0;
  }

  /**
   * Interrupt — cancel current AI response.
   * Called by voice interrupt (metering) or could be called from UI.
   */
  async interrupt(): Promise<void> {
    if (this._interrupted) return; // Already interrupted
    this._interrupted = true;

    // Stop audio playback immediately
    await this.player.stop();
    this.player.reset();

    // Tell server to cancel in-flight generation
    this.client.interrupt();

    this.currentResponseText = '';
    this.interruptLoudSamples = 0;
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
   */
  async handleFrameAlert(message: string, severity: string): Promise<void> {
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
        // NOTE: We do NOT pause the recorder here.
        // It keeps streaming audio for voice interrupt detection.
        // Audio plays through earpiece (iOS constraint with active recording).
        break;
      case 'speaking':
        this.setState('speaking');
        this.interruptLoudSamples = 0;
        break;
      case 'ready':
        // Server is ready for next turn — recorder is already running
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
    this.interruptLoudSamples = 0;
    this.setState('monitoring');
    this.callbacks.onTurnComplete?.();
  }
}
