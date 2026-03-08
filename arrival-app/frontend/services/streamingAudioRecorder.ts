/**
 * StreamingAudioRecorder — Chunked audio capture for streaming STT.
 *
 * expo-av doesn't support true PCM streaming. Workaround:
 * - Start a recording
 * - Every 200ms, stop it, read the file, send the data, start a new one
 * - This gives us ~200ms PCM chunks to stream to the server
 *
 * IMPORTANT: expo-av records to compressed formats (m4a/aac) by default.
 * We configure it for WAV (LINEAR PCM) to get raw audio that Deepgram can consume.
 * The server-side Deepgram config expects: linear16, 16kHz, mono.
 *
 * Alternative approach: We send the chunks as-is and let the server handle
 * format detection. Deepgram's WebSocket accepts raw PCM bytes directly.
 */

import { Audio, InterruptionModeIOS, InterruptionModeAndroid } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';

const CHUNK_INTERVAL_MS = 200; // 200ms chunks

// Recording options for PCM-compatible audio
// expo-av on iOS records to .caf with linearPCM, on Android to .wav
const RECORDING_OPTIONS: Audio.RecordingOptions = {
  isMeteringEnabled: true,
  android: {
    extension: '.wav',
    outputFormat: Audio.AndroidOutputFormat.DEFAULT,
    audioEncoder: Audio.AndroidAudioEncoder.DEFAULT,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
  },
  ios: {
    extension: '.wav',
    outputFormat: Audio.IOSOutputFormat.LINEARPCM,
    audioQuality: Audio.IOSAudioQuality.LOW,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {
    mimeType: 'audio/wav',
    bitsPerSecond: 256000,
  },
};

export interface StreamingRecorderCallbacks {
  /** Called with each audio chunk (base64 encoded). Server will decode. */
  onAudioChunk: (base64Data: string) => void;
  /** Called when metering data is available — can be used for UI visualization */
  onMetering?: (dB: number) => void;
  /** Called on error */
  onError?: (error: string) => void;
}

export default class StreamingAudioRecorder {
  private recording: Audio.Recording | null = null;
  private chunkTimer: ReturnType<typeof setInterval> | null = null;
  private callbacks: StreamingRecorderCallbacks;
  private isRunning = false;
  private isCapturing = false; // Guard against overlapping captures
  private hasPermission = false;

  constructor(callbacks: StreamingRecorderCallbacks) {
    this.callbacks = callbacks;
  }

  /**
   * Start capturing audio in chunks.
   * Sets audio mode for recording (routes to earpiece on iOS — expected).
   */
  async start(): Promise<void> {
    if (this.isRunning) return;

    if (!this.hasPermission) {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        this.callbacks.onError?.('Microphone permission not granted');
        return;
      }
      this.hasPermission = true;
    }

    // Set audio mode for recording
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
      interruptionModeIOS: InterruptionModeIOS.DoNotMix,
      interruptionModeAndroid: InterruptionModeAndroid.DoNotMix,
    });

    this.isRunning = true;
    await this.startNewRecording();

    // Chunk timer — stop current recording, send data, start new one
    this.chunkTimer = setInterval(async () => {
      if (!this.isRunning || this.isCapturing) return;
      await this.captureChunk();
    }, CHUNK_INTERVAL_MS);
  }

  /**
   * Stop recording and clean up.
   */
  async stop(): Promise<void> {
    this.isRunning = false;

    if (this.chunkTimer) {
      clearInterval(this.chunkTimer);
      this.chunkTimer = null;
    }

    if (this.recording) {
      try {
        const status = await this.recording.getStatusAsync();
        if (status.isRecording) {
          await this.recording.stopAndUnloadAsync();
        }
      } catch {}
      this.recording = null;
    }

    // Don't reset audio mode here — let the player handle it once
    // Reducing category switches prevents iOS volume/route resets
  }

  /**
   * Pause recording (e.g., while AI is speaking).
   * Stops the mic but does NOT reset audio mode — the audio player
   * will set it once before playback to avoid volume reset.
   */
  async pause(): Promise<void> {
    this.isRunning = false;

    if (this.chunkTimer) {
      clearInterval(this.chunkTimer);
      this.chunkTimer = null;
    }

    if (this.recording) {
      try {
        await this.recording.stopAndUnloadAsync();
      } catch {}
      this.recording = null;
    }
    // Don't reset audio mode here — reduces iOS audio session switches
    // which cause volume to reset
  }

  /**
   * Resume recording after pause.
   */
  async resume(): Promise<void> {
    if (this.isRunning) return;
    await this.start();
  }

  // --- Internals ---

  private async startNewRecording(): Promise<void> {
    try {
      // Audio mode already set in start() — don't re-set per chunk
      // Reducing setAudioModeAsync calls prevents iOS volume resets
      const { recording } = await Audio.Recording.createAsync(RECORDING_OPTIONS);
      this.recording = recording;
    } catch (e) {
      console.error('[StreamingRecorder] Start recording error:', e);
      this.callbacks.onError?.(`Recording failed: ${e}`);
    }
  }

  private async captureChunk(): Promise<void> {
    if (!this.recording || !this.isRunning) return;
    this.isCapturing = true;

    try {
      // Get metering before stopping
      const status = await this.recording.getStatusAsync();
      if (status.isRecording && status.metering !== undefined) {
        this.callbacks.onMetering?.(status.metering);
      }

      // Stop current recording
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      this.recording = null;

      // Start a new recording immediately (minimize gap)
      if (this.isRunning) {
        await this.startNewRecording();
      }

      // Read and send the captured chunk
      if (uri) {
        try {
          const base64 = await FileSystem.readAsStringAsync(uri, {
            encoding: FileSystem.EncodingType.Base64,
          });

          // Only send non-empty chunks
          if (base64 && base64.length > 100) {
            this.callbacks.onAudioChunk(base64);
          }

          // Clean up temp file
          await FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => {});
        } catch (readError) {
          // File might not exist if recording was too short
          console.log('[StreamingRecorder] Read chunk error:', readError);
        }
      }
    } catch (e) {
      console.warn('[StreamingRecorder] Capture chunk error:', e);
      // Try to start a fresh recording
      if (this.isRunning) {
        try { await this.startNewRecording(); } catch {}
      }
    } finally {
      this.isCapturing = false;
    }
  }
}
