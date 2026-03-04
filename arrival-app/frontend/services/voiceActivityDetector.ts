import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';

export interface VADConfig {
  speechThreshold: number;      // dB level for speech (default: -30)
  silenceThreshold: number;     // dB level for silence (default: -38) — UNUSED now, kept for compat
  speechMinDuration: number;    // ms of speech before triggering (default: 300)
  silenceMaxDuration: number;   // ms below speechThreshold before ending (default: 1200)
  maxSpeechDuration?: number;   // ms max recording time — safety valve (default: 15000)
  meteringInterval: number;     // ms between metering checks (default: 100)
  onSpeechStart: () => void;
  onSpeechEnd: (audioBase64: string) => Promise<void>;
}

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

  constructor(config: VADConfig) {
    this.config = config;
  }

  async start() {
    this.enabled = true;
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

      const maxSpeechDuration = this.config.maxSpeechDuration ?? 15000;

      // Poll metering
      this.meteringTimer = setInterval(async () => {
        if (!this.recording) return;

        try {
          const status = await this.recording.getStatusAsync();
          if (!status.isRecording) return;

          const metering = status.metering ?? -160;
          const now = Date.now();

          if (metering > this.config.speechThreshold) {
            // Active speech detected
            this.lastSpeechTime = now;

            if (!this.isSpeaking) {
              this.speechStartTime = now;
              this.isSpeaking = true;
            }

            // Confirm speech after minimum duration
            if (!this.speechConfirmed && now - this.speechStartTime >= this.config.speechMinDuration) {
              this.speechConfirmed = true;
              this.config.onSpeechStart();
            }

            // Safety valve: force end after max duration (no one talks for 15s straight to an AI)
            if (this.speechConfirmed && now - this.speechStartTime >= maxSpeechDuration) {
              await this.handleSpeechEnd();
            }
          } else if (this.isSpeaking && this.speechConfirmed) {
            // Below speech threshold — check if silence duration met.
            // KEY FIX: We only check if metering is below speechThreshold,
            // NOT requiring absolute silence. Any drop below speech level
            // for silenceMaxDuration = end of speech. This works in noisy
            // environments where ambient noise sits between -40 and -30 dB.
            if (now - this.lastSpeechTime >= this.config.silenceMaxDuration) {
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
