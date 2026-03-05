import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';

export interface VADConfig {
  speechThreshold: number;      // Fallback fixed threshold (only used before calibration)
  silenceThreshold: number;     // UNUSED — kept for compat
  speechMinDuration: number;    // ms of speech before triggering (default: 300)
  silenceMaxDuration: number;   // ms below threshold before ending speech (default: 800)
  maxSpeechDuration?: number;   // ms max recording time — absolute safety valve (default: 10000)
  meteringInterval: number;     // ms between metering checks (default: 100)
  onSpeechStart: () => void;
  onSpeechEnd: (audioBase64: string) => Promise<void>;
}

/**
 * Adaptive Voice Activity Detector.
 *
 * Instead of a fixed dB threshold (which fails in noisy environments),
 * this VAD continuously tracks the ambient noise floor and requires
 * speech to be significantly louder than background.
 *
 * How it works:
 * - First ~1s: calibration phase, measures ambient noise baseline
 * - After calibration: speech threshold = baseline + SPEECH_BOOST_DB
 * - Baseline only updates during non-speech periods (so talking doesn't raise it)
 * - Works on quiet job sites AND next to running compressors
 */
export default class VoiceActivityDetector {
  private recording: Audio.Recording | null = null;
  private meteringTimer: ReturnType<typeof setInterval> | null = null;
  private config: VADConfig;
  private isSpeaking: boolean = false;
  private speechConfirmed: boolean = false;
  private speechStartTime: number = 0;
  private lastSpeechTime: number = 0;
  private isProcessing: boolean = false;
  private enabled: boolean = false;
  private isPausing: boolean = false;
  private hasPermission: boolean = false;

  // --- Adaptive threshold state ---
  /** Exponential moving average of ambient noise level (dB). */
  private noiseFloor: number = -45;
  /** Number of metering samples collected — used to detect calibration complete. */
  private sampleCount: number = 0;
  /** Minimum samples before adaptive threshold kicks in (~1s at 100ms interval). */
  private static readonly CALIBRATION_SAMPLES = 10;
  /** Speech must be this many dB above the noise floor to trigger. */
  private static readonly SPEECH_BOOST_DB = 8;
  /** How fast the noise floor adapts (0-1). Lower = slower, more stable. */
  private static readonly NOISE_ADAPT_RATE = 0.08;
  /** Absolute floor — never set threshold below this (very quiet room). */
  private static readonly MIN_THRESHOLD = -35;
  /** Absolute ceiling — never set threshold above this (extremely loud site). */
  private static readonly MAX_THRESHOLD = -12;

  constructor(config: VADConfig) {
    this.config = config;
  }

  async start() {
    this.enabled = true;
    this.noiseFloor = -45;
    this.sampleCount = 0;
    await this.startListening();
  }

  async stop() {
    this.enabled = false;
    this.stopMetering();
    const rec = this.recording;
    this.recording = null;
    if (rec) {
      try {
        const status = await rec.getStatusAsync();
        if (status.isRecording) {
          await rec.stopAndUnloadAsync();
        }
      } catch (_) {}
    }
  }

  async pause() {
    this.isPausing = true;
    this.stopMetering();
    if (this.recording) {
      try {
        await this.recording.stopAndUnloadAsync();
      } catch (_) {}
      this.recording = null;
    }
    // Reset iOS audio session to playback mode so TTS routes to loudspeaker.
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
    }).catch(() => {});
    this.isSpeaking = false;
    this.speechConfirmed = false;
    this.isPausing = false;
  }

  async resume() {
    if (this.enabled && !this.isProcessing) {
      await this.startListening();
    }
  }

  private stopMetering() {
    if (this.meteringTimer) {
      clearInterval(this.meteringTimer);
      this.meteringTimer = null;
    }
  }

  /**
   * Get the current speech threshold based on ambient noise calibration.
   * During calibration (first ~1s), uses the config fallback threshold.
   * After calibration, uses noiseFloor + boost, clamped to reasonable range.
   */
  private getSpeechThreshold(): number {
    if (this.sampleCount < VoiceActivityDetector.CALIBRATION_SAMPLES) {
      // Still calibrating — use config fallback
      return this.config.speechThreshold;
    }
    const adaptive = this.noiseFloor + VoiceActivityDetector.SPEECH_BOOST_DB;
    return Math.max(
      VoiceActivityDetector.MIN_THRESHOLD,
      Math.min(VoiceActivityDetector.MAX_THRESHOLD, adaptive),
    );
  }

  private async startListening() {
    if (!this.enabled || this.isProcessing || this.isPausing) return;

    try {
      if (!this.hasPermission) {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') return;
        this.hasPermission = true;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        {
          ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
          isMeteringEnabled: true,
        }
      );
      this.recording = recording;
      this.isSpeaking = false;
      this.speechConfirmed = false;

      const maxSpeechDuration = this.config.maxSpeechDuration ?? 10000;

      // Poll metering
      this.meteringTimer = setInterval(async () => {
        if (!this.recording) return;

        try {
          const status = await this.recording.getStatusAsync();
          if (!status.isRecording) return;

          const metering = status.metering ?? -160;
          const now = Date.now();

          // --- Adaptive noise floor tracking ---
          // Only update when NOT speaking (so speech doesn't raise the floor)
          if (!this.isSpeaking) {
            this.sampleCount++;
            this.noiseFloor += (metering - this.noiseFloor) * VoiceActivityDetector.NOISE_ADAPT_RATE;
          }

          const threshold = this.getSpeechThreshold();

          // --- Unconditional safety valve ---
          // Force end if speech has been going too long — prevents infinite "listening"
          if (this.speechConfirmed && now - this.speechStartTime >= maxSpeechDuration) {
            console.log(`[VAD] Safety valve: forcing end after ${maxSpeechDuration}ms (floor=${this.noiseFloor.toFixed(1)} thresh=${threshold.toFixed(1)})`);
            await this.handleSpeechEnd();
            return;
          }

          if (metering > threshold) {
            // Active speech detected (louder than ambient + boost)
            this.lastSpeechTime = now;

            if (!this.isSpeaking) {
              this.speechStartTime = now;
              this.isSpeaking = true;
            }

            // Confirm speech after minimum duration
            if (!this.speechConfirmed && now - this.speechStartTime >= this.config.speechMinDuration) {
              this.speechConfirmed = true;
              console.log(`[VAD] Speech confirmed (floor=${this.noiseFloor.toFixed(1)} thresh=${threshold.toFixed(1)} meter=${metering.toFixed(1)})`);
              this.config.onSpeechStart();
            }
          } else if (this.isSpeaking && this.speechConfirmed) {
            // Below threshold — check if silence duration met
            if (now - this.lastSpeechTime >= this.config.silenceMaxDuration) {
              console.log(`[VAD] Silence detected — ending speech (${this.config.silenceMaxDuration}ms quiet)`);
              await this.handleSpeechEnd();
            }
          } else if (this.isSpeaking && !this.speechConfirmed) {
            // Brief noise that didn't last long enough — reset
            if (now - this.lastSpeechTime >= 500) {
              this.isSpeaking = false;
            }
          }
        } catch (e) {
          // Metering may fail if recording was stopped externally
        }
      }, this.config.meteringInterval);
    } catch (e) {
      console.log('[VAD] start listening error:', e);
    }
  }

  private async handleSpeechEnd() {
    if (!this.recording) return;
    this.isProcessing = true;
    this.isSpeaking = false;
    this.speechConfirmed = false;
    this.stopMetering();

    try {
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      this.recording = null;

      // Reset audio mode so TTS plays through speaker, not earpiece
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      }).catch(() => {});

      if (uri) {
        const audioBase64 = await FileSystem.readAsStringAsync(uri, {
          encoding: FileSystem.EncodingType.Base64,
        });

        await FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => {});
        await this.config.onSpeechEnd(audioBase64);
      }
    } catch (e) {
      console.log('[VAD] speech end error:', e);
    } finally {
      this.isProcessing = false;
      if (this.enabled) {
        setTimeout(() => this.startListening(), 200);
      }
    }
  }
}
