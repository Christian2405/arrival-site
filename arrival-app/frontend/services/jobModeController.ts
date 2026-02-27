import FrameBatcher, { FrameBatcherConfig } from './frameBatcher';
import VoiceActivityDetector, { VADConfig } from './voiceActivityDetector';

export interface JobModeCallbacks {
  onAlert: (message: string, severity: string) => Promise<void>;
  onVoiceResponse: (audioBase64: string) => Promise<void>;
  onStateChange: (state: 'monitoring' | 'listening' | 'processing' | 'speaking') => void;
}

export interface JobModeConfig {
  cooldownAfterSpeaking: number;   // ms after AI speaks (default: 8000)
  cooldownAfterDismiss: number;    // ms after user dismisses (default: 15000)
  maxAlertsPerMinute: number;      // Rate limit (default: 3)
}

export default class JobModeController {
  frameBatcher: FrameBatcher;
  vad: VoiceActivityDetector;

  private config: JobModeConfig;
  private callbacks: JobModeCallbacks;
  private lastSpeakTime: number = 0;
  private alertTimestamps: number[] = [];
  private aiSpeaking: boolean = false;
  private dismissed: boolean = false;
  private dismissTime: number = 0;

  constructor(
    config: JobModeConfig,
    callbacks: JobModeCallbacks,
    frameBatcherConfig: Omit<FrameBatcherConfig, 'onAnalyze'>,
    vadConfig: Omit<VADConfig, 'onSpeechStart' | 'onSpeechEnd'>,
  ) {
    this.config = config;
    this.callbacks = callbacks;

    this.frameBatcher = new FrameBatcher({
      ...frameBatcherConfig,
      onAnalyze: async (frame) => {
        // The callback from home.tsx calls analyzeFrame API and then handleFrameAlert
      },
    });

    this.vad = new VoiceActivityDetector({
      ...vadConfig,
      onSpeechStart: () => {
        this.callbacks.onStateChange('listening');
      },
      onSpeechEnd: (audioBase64) => {
        this.handleUserSpeech(audioBase64);
      },
    });
  }

  canSpeak(): boolean {
    const now = Date.now();

    if (now - this.lastSpeakTime < this.config.cooldownAfterSpeaking) return false;
    if (this.dismissed && now - this.dismissTime < this.config.cooldownAfterDismiss) return false;

    // Prune old timestamps and check rate limit
    this.alertTimestamps = this.alertTimestamps.filter(t => now - t < 60000);
    if (this.alertTimestamps.length >= this.config.maxAlertsPerMinute) return false;

    if (this.aiSpeaking) return false;

    return true;
  }

  async handleFrameAlert(message: string, severity: string) {
    // Critical alerts ALWAYS get through (safety first)
    if (severity !== 'critical' && !this.canSpeak()) return;

    this.alertTimestamps.push(Date.now());
    this.vad.pause();
    this.aiSpeaking = true;
    this.callbacks.onStateChange('speaking');

    try {
      await this.callbacks.onAlert(message, severity);
    } finally {
      this.aiSpeaking = false;
      this.lastSpeakTime = Date.now();
      this.callbacks.onStateChange('monitoring');
      setTimeout(() => this.vad.resume(), 1000);
    }
  }

  async handleUserSpeech(audioBase64: string) {
    this.vad.pause();
    this.aiSpeaking = true;
    this.callbacks.onStateChange('processing');

    try {
      await this.callbacks.onVoiceResponse(audioBase64);
      this.callbacks.onStateChange('speaking');
    } catch (e) {
      console.log('[JobMode] voice response error:', e);
      this.callbacks.onStateChange('monitoring');
    } finally {
      this.aiSpeaking = false;
      this.lastSpeakTime = Date.now();
      setTimeout(() => {
        this.callbacks.onStateChange('monitoring');
        this.vad.resume();
      }, 1000);
    }
  }

  dismiss() {
    this.dismissed = true;
    this.dismissTime = Date.now();
    setTimeout(() => { this.dismissed = false; }, this.config.cooldownAfterDismiss);
  }

  async start(captureFrame: () => Promise<string | undefined>) {
    this.frameBatcher.start(captureFrame);
    await this.vad.start();
    this.callbacks.onStateChange('monitoring');
  }

  async stop() {
    this.frameBatcher.stop();
    await this.vad.stop();
  }
}
