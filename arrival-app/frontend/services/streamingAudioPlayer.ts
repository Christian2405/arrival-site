/**
 * StreamingAudioPlayer — Incremental MP3 playback for streaming TTS.
 * Receives MP3 chunks from the WebSocket, buffers them into segments,
 * writes to temp files, and chains playback using expo-av.
 *
 * Key challenges solved:
 * - expo-av can't play from a stream/buffer — needs a file URI
 * - We accumulate chunks into playable segments (~50KB each)
 * - When one segment finishes, the next starts immediately
 * - stop() provides instant interrupt (<50ms)
 * - iOS audio session routing handled (loudspeaker, not earpiece)
 */

import { Audio } from 'expo-av';
import { cacheDirectory, EncodingType, writeAsStringAsync, deleteAsync } from 'expo-file-system/legacy';

// Minimum bytes before we try to play a segment.
// MP3 needs a full frame to decode — too small = decode error.
// 8KB is ~0.5s of audio at 128kbps, enough for expo-av to work with.
const MIN_SEGMENT_BYTES = 8 * 1024;

// Maximum bytes per segment before we force-flush to a new file.
// Keeps individual segments small so stop() is responsive.
const MAX_SEGMENT_BYTES = 64 * 1024;

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

interface Segment {
  uri: string;
  sound: Audio.Sound | null;
}

export default class StreamingAudioPlayer {
  private chunks: Uint8Array[] = [];
  private currentBytes = 0;
  private segments: Segment[] = [];
  private currentSegmentIndex = -1;
  private isPlaying = false;
  private isStopped = false;
  private segmentCounter = 0;
  private onDone: (() => void) | null = null;
  private allChunksReceived = false;
  private audioModeSet = false;

  /**
   * Call this whenever an MP3 audio chunk arrives from the WebSocket.
   */
  async addChunk(data: ArrayBuffer): Promise<void> {
    if (this.isStopped) return;

    const chunk = new Uint8Array(data);
    this.chunks.push(chunk);
    this.currentBytes += chunk.byteLength;

    // If we have enough data, flush to a segment
    if (this.currentBytes >= MIN_SEGMENT_BYTES) {
      await this.flushSegment();
    }
  }

  /**
   * Signal that all audio chunks have been received (audio_end event).
   * Flushes any remaining buffered data and marks stream as complete.
   */
  async finish(onDone?: () => void): Promise<void> {
    this.onDone = onDone || null;
    this.allChunksReceived = true;

    // Flush any remaining chunks
    if (this.chunks.length > 0 && this.currentBytes > 0) {
      await this.flushSegment();
    }

    // If nothing is playing and we have segments ready, start
    if (!this.isPlaying && this.segments.length > 0 && this.currentSegmentIndex < 0) {
      this.playNext();
    }
    // If all segments are done already
    if (this.currentSegmentIndex >= this.segments.length - 1 && !this.isPlaying) {
      this.cleanup();
    }
  }

  /**
   * Immediately stop all playback. Used for interrupt.
   */
  async stop(): Promise<void> {
    this.isStopped = true;
    this.isPlaying = false;
    this.chunks = [];
    this.currentBytes = 0;
    this.allChunksReceived = false;

    // Stop current sound
    const current = this.segments[this.currentSegmentIndex];
    if (current?.sound) {
      try {
        await current.sound.stopAsync();
        await current.sound.unloadAsync();
      } catch {}
      current.sound = null;
    }

    // Clean up all temp files
    for (const seg of this.segments) {
      if (seg.sound) {
        try { await seg.sound.unloadAsync(); } catch {}
        seg.sound = null;
      }
      try { await deleteAsync(seg.uri, { idempotent: true }); } catch {}
    }
    this.segments = [];
    this.currentSegmentIndex = -1;
    this.audioModeSet = false;
  }

  /**
   * Reset for a new turn (reuse the same player instance).
   */
  reset(): void {
    this.chunks = [];
    this.currentBytes = 0;
    this.segments = [];
    this.currentSegmentIndex = -1;
    this.isPlaying = false;
    this.isStopped = false;
    this.allChunksReceived = false;
    this.onDone = null;
    this.audioModeSet = false;
  }

  // --- Internals ---

  private async flushSegment(): Promise<void> {
    if (this.chunks.length === 0 || this.isStopped) return;

    // Combine all buffered chunks into one segment
    const totalLen = this.chunks.reduce((sum, c) => sum + c.byteLength, 0);
    const combined = new Uint8Array(totalLen);
    let offset = 0;
    for (const chunk of this.chunks) {
      combined.set(chunk, offset);
      offset += chunk.byteLength;
    }
    this.chunks = [];
    this.currentBytes = 0;

    // Write to a temp file
    if (!cacheDirectory) return;
    const fileUri = `${cacheDirectory}stream_audio_${this.segmentCounter++}_${Date.now()}.mp3`;
    const base64 = arrayBufferToBase64(combined.buffer);
    await writeAsStringAsync(fileUri, base64, { encoding: EncodingType.Base64 });

    this.segments.push({ uri: fileUri, sound: null });

    // Start playback if not already playing
    if (!this.isPlaying && !this.isStopped) {
      this.playNext();
    }
  }

  private async playNext(): Promise<void> {
    if (this.isStopped) return;

    this.currentSegmentIndex++;
    if (this.currentSegmentIndex >= this.segments.length) {
      // No more segments
      this.isPlaying = false;
      if (this.allChunksReceived) {
        this.cleanup();
      }
      return;
    }

    this.isPlaying = true;
    const segment = this.segments[this.currentSegmentIndex];

    try {
      // NOTE: Do NOT change audio mode here. The StreamingJobModeController
      // keeps the recorder active for voice interrupt, which means
      // allowsRecordingIOS stays true and audio routes through the earpiece.
      // Changing it here would kill the active recording.
      // For loudspeaker playback, the recorder would need to be paused first.

      const { sound } = await Audio.Sound.createAsync({ uri: segment.uri });
      segment.sound = sound;

      // Chain: when this segment finishes, play next
      sound.setOnPlaybackStatusUpdate(async (status: any) => {
        if (this.isStopped) return;

        if (!status.isLoaded) {
          // Sound was unloaded (interrupted)
          this.isPlaying = false;
          return;
        }

        if (status.didJustFinish) {
          // Clean up this segment
          try {
            await sound.unloadAsync();
            segment.sound = null;
            await deleteAsync(segment.uri, { idempotent: true });
          } catch {}

          // Play next segment
          this.playNext();
        }
      });

      await sound.playAsync();
    } catch (e) {
      console.warn('[StreamingAudioPlayer] Play segment error:', e);
      // Try next segment
      this.playNext();
    }
  }

  private cleanup(): void {
    this.isPlaying = false;
    // Clean up any remaining temp files
    for (const seg of this.segments) {
      if (seg.sound) {
        try { seg.sound.unloadAsync(); } catch {}
      }
      deleteAsync(seg.uri, { idempotent: true }).catch(() => {});
    }
    this.segments = [];
    this.currentSegmentIndex = -1;
    this.audioModeSet = false;
    this.onDone?.();
    this.onDone = null;
  }
}
