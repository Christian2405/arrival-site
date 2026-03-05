/**
 * StreamingJobModeController — Job mode using the WebSocket streaming pipeline.
 *
 * This is the hands-free controller for trade workers:
 * - Server-side VAD (Deepgram endpointing) — works in noisy environments
 * - Audio streams in real-time instead of record-all-then-send
 * - TTS audio streams back incrementally
 *
 * Audio routing on iOS (critical fix):
 * - Recording active = iOS routes audio through EARPIECE (not speaker)
 * - When AI speaks: recorder PAUSES → audio routes to LOUDSPEAKER
 * - When AI finishes: recorder RESUMES → back to listening
 * - This trades voice interrupt for audible output — required for job sites
 *
 * FrameBatcher stays unchanged — frame analysis is a separate pipeline.
 */

import FrameBatcher, { FrameBatcherConfig } from './frameBatcher';
import StreamingVoiceClient, { StreamingState } from './streamingVoiceClient';
import StreamingAudioPlayer from './streamingAudioPlayer';
import StreamingAudioRecorder from './streamingAudioRecorder';

export type StreamingJobAIState = 'connecting' | 'monitoring' | 'listening' | 'processing' | 'speaking' | 'error';

/** Safety timeout: if recorder stays paused > 20s, something went wrong — force resume */
const SPEAKING_SAFETY_TIMEOUT_MS = 20000;

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
  private speakingSafetyTimer: ReturnType<typeof setTimeout> | null = null;

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
    // Recorder streams audio to server. PAUSED during AI speaking for loudspeaker output.
    this.recorder = new StreamingAudioRecorder({
      onAudioChunk: (base64Data) => {
        this.client.sendAudio(base64Data);
      },
      onMetering: (_dB) => {
        // Metering not used for interrupt (recorder is paused during speaking).
        // Could be used for UI visualization in the future.
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
    this.clearSpeakingSafetyTimer();
    this.frameBatcher.stop();
    await this.recorder.stop();
    await this.player.stop();
    await this.client.close();
    this.isRecording = false;
    this._interrupted = false;
    this.currentResponseText = '';
  }

  /**
   * Interrupt — cancel current AI response.
   * Called from UI tap or could be called programmatically.
   */
  async interrupt(): Promise<void> {
    if (this._interrupted) return; // Already interrupted
    this._interrupted = true;

    this.clearSpeakingSafetyTimer();

    // Stop audio playback immediately
    await this.player.stop();
    this.player.reset();

    // Tell server to cancel in-flight generation
    this.client.interrupt();

    this.currentResponseText = '';

    // Resume recording (may have been paused for speaking)
    await this.recorder.resume();
    this.isRecording = true;

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
   * Handle a frame analysis alert (from FrameBatcher -> analyzeFrame API).
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
        break;
      case 'speaking':
        this.setState('speaking');
        this._interrupted = false;
        // CRITICAL FIX: Pause recorder so iOS routes audio to LOUDSPEAKER.
        // Without this, allowsRecordingIOS=true forces audio through earpiece.
        // recorder.pause() sets allowsRecordingIOS=false → speaker output.
        this.recorder.pause().catch(e =>
          console.warn('[StreamingJobMode] Pause recorder error:', e)
        );
        this.isRecording = false;
        // Safety timeout: force-resume if something goes wrong
        this.startSpeakingSafetyTimer();
        break;
      case 'ready':
        // Server says it's ready for the next turn.
        // Don't resume recorder here — player may still be playing audio.
        // The recorder resumes in onTurnDone() when playback actually finishes.
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
   * Resume recording so the mic is live for the next utterance.
   */
  private async onTurnDone(): Promise<void> {
    this.clearSpeakingSafetyTimer();

    if (this._interrupted) {
      this._interrupted = false;
      return;
    }

    this.player.reset();
    this.currentResponseText = '';

    // Resume recording — switches audio mode back to recording
    // (earpiece for mic, but no audio is playing now so it doesn't matter)
    await this.recorder.resume();
    this.isRecording = true;

    this.setState('monitoring');
    this.callbacks.onTurnComplete?.();
  }

  private startSpeakingSafetyTimer(): void {
    this.clearSpeakingSafetyTimer();
    this.speakingSafetyTimer = setTimeout(async () => {
      console.warn('[StreamingJobMode] Speaking safety timeout — force resuming recorder');
      await this.player.stop();
      this.player.reset();
      await this.recorder.resume();
      this.isRecording = true;
      this.setState('monitoring');
    }, SPEAKING_SAFETY_TIMEOUT_MS);
  }

  private clearSpeakingSafetyTimer(): void {
    if (this.speakingSafetyTimer) {
      clearTimeout(this.speakingSafetyTimer);
      this.speakingSafetyTimer = null;
    }
  }
}
