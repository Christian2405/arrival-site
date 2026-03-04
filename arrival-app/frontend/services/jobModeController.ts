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
  cooldownAfterSpeaking: number;
  cooldownAfterDismiss: number;
  maxAlertsPerMinute: number;
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
  private operationLockTimer: ReturnType<typeof setTimeout> | null = null;
  private _interrupted: boolean = false;
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

  /** Public getter so callbacks (home.tsx) can check if interrupted before playing TTS */
  get wasInterrupted(): boolean {
    return this._interrupted;
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

  /** Acquire the operation lock with a 30s safety timeout. If the lock
   *  isn't released within 30s, force-release it so speech isn't permanently dropped. */
  private acquireLock(): boolean {
    if (this.operationLock) return false;
    this.operationLock = true;
    // Safety watchdog — force-release after 30s
    this.operationLockTimer = setTimeout(() => {
      console.warn('[JobMode] operationLock watchdog fired — force releasing after 30s');
      this.releaseLock();
      this.callbacks.onStateChange('monitoring');
      this.vad.resume();
    }, 30000);
    return true;
  }

  private releaseLock() {
    this.operationLock = false;
    if (this.operationLockTimer) {
      clearTimeout(this.operationLockTimer);
      this.operationLockTimer = null;
    }
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

    if (!this.acquireLock()) return;
    this.alertTimestamps.push(Date.now());
    await this.vad.pause();
    this.aiSpeaking = true;
    this.callbacks.onStateChange('speaking');

    try {
      await this.callbacks.onAlert(message, severity);
    } finally {
      this.aiSpeaking = false;
      this.lastSpeakTime = Date.now();

      if (this._interrupted) {
        this._interrupted = false;
        this.releaseLock();
        this.callbacks.onStateChange('monitoring');
        this.vad.resume();
      } else {
        this.scheduleTimeout(() => {
          this.callbacks.onStateChange('monitoring');
          this.vad.resume();
          this.releaseLock();
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

    // If already processing something, just drop it.
    // This is how real conversations work — you don't queue sentences.
    // The user will speak again once the mic is back on.
    if (!this.acquireLock()) return;

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

      if (this._interrupted) {
        this._interrupted = false;
        this.releaseLock();
        this.callbacks.onStateChange('monitoring');
        this.vad.resume();
      } else {
        this.scheduleTimeout(() => {
          this.callbacks.onStateChange('monitoring');
          this.vad.resume();
          this.releaseLock();
          if (this.pendingCriticalAlert) {
            const alert = this.pendingCriticalAlert;
            this.pendingCriticalAlert = null;
            this.handleFrameAlert(alert.message, alert.severity);
          }
        }, 200);
      }
    }
  }

  /**
   * Interrupt — user tapped the screen while AI is speaking/processing.
   * Like a real conversation: AI shuts up, listens for what's next.
   * No queuing. The conversation history has context so nothing is lost.
   */
  interrupt() {
    this._interrupted = true;
    // Stop audio playback immediately
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
    if (this.operationLockTimer) { clearTimeout(this.operationLockTimer); this.operationLockTimer = null; }
    this.frameBatcher.stop();
    await this.vad.stop();
    this.aiSpeaking = false;
    this.dismissed = false;
    this.alertTimestamps = [];
    this.lastSpeakTime = 0;
    this.operationLock = false;
    this._interrupted = false;
    this.pendingCriticalAlert = null;
  }
}
