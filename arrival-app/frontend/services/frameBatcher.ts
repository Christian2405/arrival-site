/**
 * FrameBatcher - Smart frame analysis with change detection.
 * Instead of blindly analyzing every 8 seconds, it:
 * 1. Captures a frame every 2 seconds
 * 2. Compares to previous frame using base64 sampling
 * 3. Only sends to API when visual change exceeds threshold
 * 4. Has a max interval so it still checks periodically even if nothing changes
 */

export interface FrameBatcherConfig {
  minInterval: number;       // Min ms between analyses (default: 3000)
  maxInterval: number;       // Max ms without analysis even if no change (default: 15000)
  changeThreshold: number;   // Fraction of samples that must differ (default: 0.05 = 5%)
  captureInterval: number;   // How often to capture and compare (default: 2000)
  onAnalyze: (frameBase64: string) => Promise<void>;
}

export default class FrameBatcher {
  private lastFrame: string | null = null;
  private lastAnalysisTime: number = 0;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private config: FrameBatcherConfig;
  private isAnalyzing: boolean = false;
  private captureFrame: (() => Promise<string | undefined>) | null = null;

  constructor(config: FrameBatcherConfig) {
    this.config = config;
  }

  start(captureFrame: () => Promise<string | undefined>) {
    this.captureFrame = captureFrame;
    this.lastAnalysisTime = Date.now();

    this.intervalId = setInterval(async () => {
      if (this.isAnalyzing || !this.captureFrame) return;

      try {
        const frame = await this.captureFrame();
        if (!frame) return;

        const now = Date.now();
        const elapsed = now - this.lastAnalysisTime;

        // Always analyze if max interval exceeded
        if (elapsed >= this.config.maxInterval) {
          await this.analyze(frame);
          return;
        }

        // Don't analyze if min interval not met
        if (elapsed < this.config.minInterval) return;

        // Check for visual change
        if (this.hasSignificantChange(frame)) {
          await this.analyze(frame);
        }
      } catch (e) {
        console.log('[FrameBatcher] capture error:', e);
      }
    }, this.config.captureInterval);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.lastFrame = null;
    this.captureFrame = null;
  }

  private hasSignificantChange(newFrame: string): boolean {
    if (!this.lastFrame) return true;

    // Sample 100 positions in the base64 string and compare
    const sampleSize = 100;
    const minLen = Math.min(newFrame.length, this.lastFrame.length);
    if (minLen < sampleSize) return true;

    const step = Math.floor(minLen / sampleSize);
    let diffCount = 0;

    for (let i = 0; i < sampleSize; i++) {
      const pos = i * step;
      if (newFrame[pos] !== this.lastFrame[pos]) {
        diffCount++;
      }
    }

    return (diffCount / sampleSize) > this.config.changeThreshold;
  }

  private async analyze(frame: string) {
    this.isAnalyzing = true;
    this.lastFrame = frame;
    this.lastAnalysisTime = Date.now();

    try {
      await this.config.onAnalyze(frame);
    } catch (e) {
      console.log('[FrameBatcher] analysis error:', e);
    } finally {
      this.isAnalyzing = false;
    }
  }
}
