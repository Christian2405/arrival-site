import FrameBatcher, { FrameBatcherConfig } from './frameBatcher';
import VoiceActivityDetector, { VADConfig } from './voiceActivityDetector';

export interface JobModeCallbacks {
  onAlert: (message: string, severity: string) => Promise<void>;
  onVoiceResponse: (audioBase64: string) => Promise<void>;
  onStateChange: (state: 'monitoring' | 'listening' | 'processing' | 'speaking') => void;
  /** Called when user taps to interrupt — stops audio playback */
  onInterrupt?: () => void;
}

export interface JobModeConfig {
  cooldownAfterSpeaking: number;   // ms after AI speaks (default: 2000)
  cooldownAfterDismiss: number;    // ms after user dismisses (default: 5000)
  maxAlertsPerMinute: number;      // Rate limit (default: 4)
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
  private operationLock: boolean = false;
  private interrupted: boolean = false;                                     // Interrupt flag
  private pendingSpeech: string | null = null;                              // Queued speech during processing
  private pendingCriticalAlert: { message: string; severity: string } | null = null;
  private dismissTimeout: ReturnType<typeof setTimeout> | null = null;
  private pendingTimeouts: ReturnType<typeof setTimeout>[] = [];

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

  private pruneAlertTimestamps() {
    const now = Date.now();
    this.alertTimestamps = this.alertTimestamps.filter(t => now - t < 60000);
  }

  canSpeak(): boolean {
    const now = Date.now();
    if (now - this.lastSpeakTime < this.config.cooldownAfterSpeaking) return false;
    if (this.dismissed && now - this.dismissTime < this.config.cooldownAfterDismiss) return false;
    this.pruneAlertTimestamps();
    if (this.alertTimestamps.length >= this.config.maxAlertsPerMinute) return false;
    if (this.aiSpeaking) return false;
    return true;
  }

  private scheduleTimeout(fn: () => void, ms: number): ReturnType<typeof setTimeout> {
    const id = setTimeout(() => {
      this.pendingTimeouts = this.pendingTimeouts.filter(t => t !== id);
      fn();
    }, ms);
    this.pendingTimeouts.push(id);
    return id;
  }

  async handleFrameAlert(message: string, severity: string) {
    this.pruneAlertTimestamps();

    if (this.operationLock) {
      if (severity === 'critical') {
        this.pendingCriticalAlert = { message, severity };
      }
      return;
    }

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

      if (this.interrupted) {
        // Interrupted — resume immediately
        this.interrupted = false;
        this.operationLock = false;
        this.callbacks.onStateChange('monitoring');
        this.vad.resume();
      } else {
        this.scheduleTimeout(() => {
          this.callbacks.onStateChange('monitoring');
          this.vad.resume();
          this.operationLock = false;
          if (this.pendingCriticalAlert) {
            const alert = this.pendingCriticalAlert;
            this.pendingCriticalAlert = null;
            this.handleFrameAlert(alert.message, alert.severity);
          }
        }, 300);
      }
    }
  }

  async handleUserSpeech(audioBase64: string) {
    this.pruneAlertTimestamps();

    // If locked (processing another voice or alert), QUEUE instead of dropping
    if (this.operationLock) {
      this.pendingSpeech = audioBase64;
      return;
    }
    this.operationLock = true;

    await this.vad.pause();
    this.aiSpeaking = true;
    this.callbacks.onStateChange('processing');

    try {
      await this.callbacks.onVoiceResponse(audioBase64);
    } catch (e) {
      console.log('[JobMode] voice response error:', e);
    } finally {
      this.aiSpeaking = false;
      this.lastSpeakTime = Date.now();

      if (this.interrupted) {
        // Interrupted — resume immediately, process queued speech
        this.interrupted = false;
        this.operationLock = false;
        this.callbacks.onStateChange('monitoring');
        this.vad.resume();
        this.processQueuedSpeech();
      } else {
        this.scheduleTimeout(() => {
          this.callbacks.onStateChange('monitoring');
          this.vad.resume();
          this.operationLock = false;
          // Process queued speech or pending critical alert
          if (this.pendingSpeech) {
            this.processQueuedSpeech();
          } else if (this.pendingCriticalAlert) {
            const alert = this.pendingCriticalAlert;
            this.pendingCriticalAlert = null;
            this.handleFrameAlert(alert.message, alert.severity);
          }
        }, 200);
      }
    }
  }

  private processQueuedSpeech() {
    if (this.pendingSpeech) {
      const speech = this.pendingSpeech;
      this.pendingSpeech = null;
      // Process the queued speech after a tiny delay
      setTimeout(() => this.handleUserSpeech(speech), 50);
    }
  }

  /**
   * Interrupt the AI — called when user taps the screen during speaking.
   * Sets a flag that the finally block in handleUserSpeech/handleFrameAlert
   * checks to resume immediately instead of waiting.
   */
  interrupt() {
    this.interrupted = true;
    // Tell home.tsx to stop audio playback
    this.callbacks.onInterrupt?.();
  }

  dismiss() {
    this.dismissed = true;
    this.dismissTime = Date.now();
    if (this.dismissTimeout) { clearTimeout(this.dismissTimeout); }
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
    for (const id of this.pendingTimeouts) { clearTimeout(id); }
    this.pendingTimeouts = [];
    if (this.dismissTimeout) { clearTimeout(this.dismissTimeout); this.dismissTimeout = null; }
    this.frameBatcher.stop();
    await this.vad.stop();
    this.aiSpeaking = false;
    this.dismissed = false;
    this.alertTimestamps = [];
    this.lastSpeakTime = 0;
    this.operationLock = false;
    this.interrupted = false;
    this.pendingSpeech = null;
    this.pendingCriticalAlert = null;
  }
}
