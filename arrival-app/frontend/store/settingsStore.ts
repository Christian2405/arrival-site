import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface SettingsState {
  voiceOutput: boolean;
  jobMode: boolean;
  interactionMode: 'default' | 'text' | 'job';
  voiceSpeed: 'slow' | 'normal' | 'fast';
  units: 'imperial' | 'metric';
  textSize: 'small' | 'medium' | 'large';
  useStreamingVoice: boolean; // Streaming pipeline toggle (WebSocket vs REST)
  useLiveKit: boolean; // LiveKit voice agent (full-duplex WebRTC) — needs native build

  setVoiceOutput: (value: boolean) => void;
  setJobMode: (value: boolean) => void;
  setInteractionMode: (value: 'default' | 'text' | 'job') => void;
  setVoiceSpeed: (value: 'slow' | 'normal' | 'fast') => void;
  setUnits: (value: 'imperial' | 'metric') => void;
  setTextSize: (value: 'small' | 'medium' | 'large') => void;
  setUseStreamingVoice: (value: boolean) => void;
  setUseLiveKit: (value: boolean) => void;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  voiceOutput: true,
  jobMode: false,
  interactionMode: 'default',
  voiceSpeed: 'normal',
  units: 'imperial',
  textSize: 'medium',
  useStreamingVoice: false, // OFF — WebSocket streaming unreliable, use REST pipeline
  useLiveKit: true, // ON — LiveKit full-duplex WebRTC (needs EAS dev client build)

  setVoiceOutput: (value) => {
    set({ voiceOutput: value });
    AsyncStorage.setItem('voice_output', value.toString()).catch(console.error);
  },
  setJobMode: (value) => {
    set({ jobMode: value, interactionMode: value ? 'job' : 'default' });
    AsyncStorage.setItem('job_mode', value.toString()).catch(console.error);
    AsyncStorage.setItem('interaction_mode', value ? 'job' : 'default').catch(console.error);
  },
  setInteractionMode: (value) => {
    set({ interactionMode: value, jobMode: value === 'job' });
    AsyncStorage.setItem('interaction_mode', value).catch(console.error);
    AsyncStorage.setItem('job_mode', (value === 'job').toString()).catch(console.error);
  },
  setVoiceSpeed: (value) => {
    set({ voiceSpeed: value });
    AsyncStorage.setItem('voice_speed', value).catch(console.error);
  },
  setUnits: (value) => {
    set({ units: value });
    AsyncStorage.setItem('units', value).catch(console.error);
  },
  setTextSize: (value) => {
    set({ textSize: value });
    AsyncStorage.setItem('text_size', value).catch(console.error);
  },
  setUseStreamingVoice: (value) => {
    set({ useStreamingVoice: value });
    AsyncStorage.setItem('use_streaming_voice', value.toString()).catch(console.error);
  },
  setUseLiveKit: (value) => {
    set({ useLiveKit: value });
    AsyncStorage.setItem('use_livekit', value.toString()).catch(console.error);
  },
  loadSettings: async () => {
    try {
      // Force LiveKit ON — EAS dev client now includes native WebRTC
      const lkMigrated3 = await AsyncStorage.getItem('settings_lk_v3_on');
      if (!lkMigrated3) {
        await AsyncStorage.setItem('use_livekit', 'true');
        await AsyncStorage.setItem('settings_lk_v3_on', 'true');
      }

      // Force streaming OFF — WebSocket pipeline is unreliable, use REST
      const streamMigrated = await AsyncStorage.getItem('settings_stream_v1_off');
      if (!streamMigrated) {
        await AsyncStorage.setItem('use_streaming_voice', 'false');
        await AsyncStorage.setItem('settings_stream_v1_off', 'true');
      }

      const voiceOutput = await AsyncStorage.getItem('voice_output');
      const jobMode = await AsyncStorage.getItem('job_mode');
      const interactionMode = await AsyncStorage.getItem('interaction_mode');
      const voiceSpeed = await AsyncStorage.getItem('voice_speed');
      const units = await AsyncStorage.getItem('units');
      const textSize = await AsyncStorage.getItem('text_size');
      const useLiveKit = await AsyncStorage.getItem('use_livekit');

      set({
        voiceOutput: voiceOutput !== 'false',
        jobMode: jobMode === 'true',
        interactionMode: (['default', 'text', 'job'].includes(interactionMode || '') ? interactionMode : 'default') as 'default' | 'text' | 'job',
        voiceSpeed: (voiceSpeed as any) || 'normal',
        units: (units as any) || 'imperial',
        textSize: (textSize as any) || 'medium',
        useStreamingVoice: false, // REST pipeline — streaming disabled until debugged
        useLiveKit: useLiveKit !== 'false', // ON by default — LiveKit is the primary voice pipeline
      });
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  },
}));
