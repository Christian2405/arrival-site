import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';

export interface VADConfig {
  speechThreshold: number;      // dB level for speech (default: -30)
  silenceThreshold: number;     // dB level for silence (default: -50)
  speechMinDuration: number;    // ms of speech before triggering (default: 300)
  silenceMaxDuration: number;   // ms of silence before ending (default: 1500)
  meteringInterval: number;     // ms between metering checks (default: 100)
  onSpeechStart: () => void;
  onSpeechEnd: (audioBase64: string) => Promise<void>; // BUG 2 FIX: returns Promise
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
  private isPausing: boolean = false;    // BUG 1 FIX: guard against pause/resume race
  private hasPermission: boolean = false; // BUG 5 FIX: cache permission result

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
    // BUG 6 FIX: defensively access recording in a try block
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

  // BUG 1 FIX: pause is now async, awaits stop before nulling
  async pause() {
    this.isPausing = true;
    this.stopMetering();
    if (this.recording) {
      try {
        await this.recording.stopAndUnloadAsync();
      } catch (_) {}
      this.recording = null;
    }
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
    // BUG 1 FIX: don't start if a pause is in progress
    if (!this.enabled || this.isProcessing || this.isPausing) return;

    try {
      // BUG 5 FIX: only request permission if not already cached
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

      // BUG 4 FIX: reset audio mode so TTS plays through speaker, not earpiece
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      }).catch(() => {});

      if (uri) {
        const audioBase64 = await FileSystem.readAsStringAsync(uri, {
          encoding: FileSystem.EncodingType.Base64,
        });

        // BUG 3 FIX: clean up temp audio file
        await FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => {});

        // BUG 2 FIX: await onSpeechEnd so restart delay begins after pipeline completes
        await this.config.onSpeechEnd(audioBase64);
      }
    } catch (e) {
      console.log('[VAD] speech end error:', e);
    } finally {
      this.isProcessing = false;
      // Restart listening — fast restart for responsive feel
      if (this.enabled) {
        setTimeout(() => this.startListening(), 200);
      }
    }
  }
}
