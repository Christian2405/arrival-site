import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface SettingsState {
  voiceOutput: boolean;
  demoMode: boolean;
  jobMode: boolean;
  interactionMode: 'default' | 'text' | 'job';
  voiceSpeed: 'slow' | 'normal' | 'fast';
  units: 'imperial' | 'metric';
  textSize: 'small' | 'medium' | 'large';

  setVoiceOutput: (value: boolean) => void;
  setDemoMode: (value: boolean) => void;
  setJobMode: (value: boolean) => void;
  setInteractionMode: (value: 'default' | 'text' | 'job') => void;
  setVoiceSpeed: (value: 'slow' | 'normal' | 'fast') => void;
  setUnits: (value: 'imperial' | 'metric') => void;
  setTextSize: (value: 'small' | 'medium' | 'large') => void;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  voiceOutput: true,
  demoMode: false, // Real API keys are configured — use live mode
  jobMode: false,
  interactionMode: 'default',
  voiceSpeed: 'normal',
  units: 'imperial',
  textSize: 'medium',

  setVoiceOutput: (value) => {
    set({ voiceOutput: value });
    AsyncStorage.setItem('voice_output', value.toString()).catch(console.error);
  },
  setDemoMode: (value) => {
    set({ demoMode: value });
    AsyncStorage.setItem('demo_mode', value.toString()).catch(console.error);
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
  loadSettings: async () => {
    try {
      // One-time migration: force demo mode OFF now that real API keys are set
      const migrated = await AsyncStorage.getItem('settings_v2_migrated');
      if (!migrated) {
        await AsyncStorage.setItem('demo_mode', 'false');
        await AsyncStorage.setItem('settings_v2_migrated', 'true');
      }

      const voiceOutput = await AsyncStorage.getItem('voice_output');
      const demoMode = await AsyncStorage.getItem('demo_mode');
      const jobMode = await AsyncStorage.getItem('job_mode');
      const interactionMode = await AsyncStorage.getItem('interaction_mode');
      const voiceSpeed = await AsyncStorage.getItem('voice_speed');
      const units = await AsyncStorage.getItem('units');
      const textSize = await AsyncStorage.getItem('text_size');

      set({
        voiceOutput: voiceOutput !== 'false',
        demoMode: demoMode === 'true', // Only enable if explicitly set
        jobMode: jobMode === 'true',
        interactionMode: (['default', 'text', 'job'].includes(interactionMode || '') ? interactionMode : 'default') as 'default' | 'text' | 'job',
        voiceSpeed: (voiceSpeed as any) || 'normal',
        units: (units as any) || 'imperial',
        textSize: (textSize as any) || 'medium',
      });
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  },
}));
