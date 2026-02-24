/**
 * Saved Answers store — persists bookmarked AI responses to AsyncStorage.
 * Users long-press an assistant message in chat to save it here.
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface SavedAnswer {
  id: string;
  question: string;
  answer: string;
  source?: string;
  confidence?: 'high' | 'medium' | 'low';
  savedAt: Date;
  trade: string;
}

interface SavedAnswersState {
  answers: SavedAnswer[];
  saveAnswer: (answer: SavedAnswer) => Promise<void>;
  removeAnswer: (id: string) => Promise<void>;
  loadAnswers: () => Promise<void>;
}

export const useSavedAnswersStore = create<SavedAnswersState>((set, get) => ({
  answers: [],

  saveAnswer: async (answer) => {
    const { answers } = get();
    // Don't save duplicates (same answer text)
    if (answers.some((a) => a.id === answer.id)) return;

    const updated = [answer, ...answers];
    set({ answers: updated });
    await AsyncStorage.setItem('saved_answers', JSON.stringify(updated));
  },

  removeAnswer: async (id) => {
    const { answers } = get();
    const updated = answers.filter((a) => a.id !== id);
    set({ answers: updated });
    await AsyncStorage.setItem('saved_answers', JSON.stringify(updated));
  },

  loadAnswers: async () => {
    try {
      const stored = await AsyncStorage.getItem('saved_answers');
      if (stored) {
        const parsed = JSON.parse(stored);
        const answers = parsed.map((a: any) => ({
          ...a,
          savedAt: new Date(a.savedAt),
        }));
        set({ answers });
      }
    } catch (error) {
      console.error('Error loading saved answers:', error);
    }
  },
}));
