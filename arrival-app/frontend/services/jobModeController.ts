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
  private operationLock: boolean = false;                             // BUG 7 FIX: mutex for concurrent operations
  private dismissTimeout: ReturnType<typeof setTimeout> | null = null; // BUG 10 FIX: track dismiss timeout
  private pendingTimeouts: ReturnType<typeof setTimeout>[] = [];       // BUG 11 FIX: track all pending timeouts

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
      onSpeechEnd: async (audioBase64) => {
        await this.handleUserSpeech(audioBase64);
      },
    });
  }

  // BUG 13 FIX: shared pruning method used at the top of both handlers
  private pruneAlertTimestamps() {
    const now = Date.now();
    this.alertTimestamps = this.alertTimestamps.filter(t => now - t < 60000);
  }

  canSpeak(): boolean {
    const now = Date.now();

    if (now - this.lastSpeakTime < this.config.cooldownAfterSpeaking) return false;
    if (this.dismissed && now - this.dismissTime < this.config.cooldownAfterDismiss) return false;

    // Prune old timestamps and check rate limit
    this.pruneAlertTimestamps();
    if (this.alertTimestamps.length >= this.config.maxAlertsPerMinute) return false;

    if (this.aiSpeaking) return false;

    return true;
  }

  // BUG 11 FIX: helper to schedule timeouts and track them for cleanup
  private scheduleTimeout(fn: () => void, ms: number): ReturnType<typeof setTimeout> {
    const id = setTimeout(() => {
      this.pendingTimeouts = this.pendingTimeouts.filter(t => t !== id);
      fn();
    }, ms);
    this.pendingTimeouts.push(id);
    return id;
  }

  async handleFrameAlert(message: string, severity: string) {
    // BUG 13 FIX: prune timestamps before any check
    this.pruneAlertTimestamps();

    // BUG 7 FIX: mutex guard against concurrent operations
    if (this.operationLock) return;

    // BUG 8 FIX: even critical alerts must check if AI is already speaking
    if (severity === 'critical') {
      if (this.aiSpeaking) return;
    } else {
      if (!this.canSpeak()) return;
    }

    this.operationLock = true;

    this.alertTimestamps.push(Date.now());
    await this.vad.pause();
    this.aiSpeaking = true;
    this.callbacks.onStateChange('speaking');

    try {
      await this.callbacks.onAlert(message, severity);
    } finally {
      this.aiSpeaking = false;
      this.lastSpeakTime = Date.now();
      this.callbacks.onStateChange('monitoring');
      // BUG 11 FIX: use tracked timeout
      this.scheduleTimeout(() => this.vad.resume(), 500);
      this.operationLock = false;
    }
  }

  async handleUserSpeech(audioBase64: string) {
    // BUG 13 FIX: prune timestamps before any check
    this.pruneAlertTimestamps();

    // BUG 7 FIX: mutex guard against concurrent operations
    if (this.operationLock) return;
    this.operationLock = true;

    await this.vad.pause();
    this.aiSpeaking = true;
    this.callbacks.onStateChange('processing');

    try {
      // BUG 9 FIX: set 'speaking' state BEFORE the voice response (which includes TTS playback)
      this.callbacks.onStateChange('speaking');
      await this.callbacks.onVoiceResponse(audioBase64);
    } catch (e) {
      console.log('[JobMode] voice response error:', e);
    } finally {
      this.aiSpeaking = false;
      this.lastSpeakTime = Date.now();
      // BUG 11 FIX: use tracked timeout
      this.scheduleTimeout(() => {
        this.callbacks.onStateChange('monitoring');
        this.vad.resume();
      }, 500);
      this.operationLock = false;
    }
  }

  dismiss() {
    this.dismissed = true;
    this.dismissTime = Date.now();
    // BUG 10 FIX: store the timeout so it can be cleared in stop()
    if (this.dismissTimeout) {
      clearTimeout(this.dismissTimeout);
    }
    this.dismissTimeout = this.scheduleTimeout(() => {
      this.dismissed = false;
      this.dismissTimeout = null;
    }, this.config.cooldownAfterDismiss);
  }

  async start(captureFrame: () => Promise<string | undefined>) {
    this.frameBatcher.start(captureFrame);
    await this.vad.start();
    this.callbacks.onStateChange('monitoring');
  }

  async stop() {
    // BUG 11 FIX: clear all pending timeouts so nothing fires on a stopped controller
    for (const id of this.pendingTimeouts) {
      clearTimeout(id);
    }
    this.pendingTimeouts = [];

    // BUG 10 FIX: clear dismiss timeout
    if (this.dismissTimeout) {
      clearTimeout(this.dismissTimeout);
      this.dismissTimeout = null;
    }

    this.frameBatcher.stop();
    await this.vad.stop();

    // BUG 12 FIX: reset all internal state
    this.aiSpeaking = false;
    this.dismissed = false;
    this.alertTimestamps = [];
    this.lastSpeakTime = 0;
    this.operationLock = false;
  }
}
