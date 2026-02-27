import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';

export interface VADConfig {
  speechThreshold: number;      // dB level for speech (default: -30)
  silenceThreshold: number;     // dB level for silence (default: -50)
  speechMinDuration: number;    // ms of speech before triggering (default: 300)
  silenceMaxDuration: number;   // ms of silence before ending (default: 1500)
  meteringInterval: number;     // ms between metering checks (default: 100)
  onSpeechStart: () => void;
  onSpeechEnd: (audioBase64: string) => void;
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
    if (this.recording) {
      try {
        const status = await this.recording.getStatusAsync();
        if (status.isRecording) {
          await this.recording.stopAndUnloadAsync();
        }
      } catch (_) {}
      this.recording = null;
    }
  }

  pause() {
    this.stopMetering();
    if (this.recording) {
      this.recording.stopAndUnloadAsync().catch(() => {});
      this.recording = null;
    }
    this.isSpeaking = false;
    this.speechConfirmed = false;
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
    if (!this.enabled || this.isProcessing) return;

    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') return;

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

      // Poll metering
      this.meteringTimer = setInterval(async () => {
        if (!this.recording) return;

        try {
          const status = await this.recording.getStatusAsync();
          if (!status.isRecording) return;

          const metering = status.metering ?? -160;
          const now = Date.now();

          if (metering > this.config.speechThreshold) {
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
          } else if (this.isSpeaking && this.speechConfirmed && metering < this.config.silenceThreshold) {
            // Silence after confirmed speech
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

      if (uri) {
        const audioBase64 = await FileSystem.readAsStringAsync(uri, {
          encoding: FileSystem.EncodingType.Base64,
        });
        this.config.onSpeechEnd(audioBase64);
      }
    } catch (e) {
      console.log('[VAD] speech end error:', e);
    } finally {
      this.isProcessing = false;
      // Restart listening for next utterance after a short delay
      if (this.enabled) {
        setTimeout(() => this.startListening(), 500);
      }
    }
  }
}
