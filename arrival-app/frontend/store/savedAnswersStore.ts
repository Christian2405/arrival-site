/**
 * Saved Answers store — syncs bookmarked AI responses to Supabase.
 * Falls back to AsyncStorage when offline or backend is unavailable.
 * Users long-press an assistant message in chat to save it here.
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { savedAnswersAPI } from '../services/api';

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

    // Optimistically update local state + AsyncStorage
    const updated = [answer, ...answers];
    set({ answers: updated });
    await AsyncStorage.setItem('saved_answers', JSON.stringify(updated));

    // Sync to Supabase via backend (non-blocking)
    try {
      const result = await savedAnswersAPI.save({
        question: answer.question,
        answer: answer.answer,
        source: answer.source,
        confidence: answer.confidence,
        trade: answer.trade,
      });
      // Update local ID with server-generated UUID
      if (result.id && result.id !== answer.id) {
        const withServerId = updated.map((a) =>
          a.id === answer.id ? { ...a, id: result.id } : a
        );
        set({ answers: withServerId });
        await AsyncStorage.setItem('saved_answers', JSON.stringify(withServerId));
      }
    } catch (error) {
      // Supabase sync failed — local save still works
      console.log('[savedAnswers] Backend sync failed (saved locally):', error);
    }
  },

  removeAnswer: async (id) => {
    const { answers } = get();
    const updated = answers.filter((a) => a.id !== id);
    set({ answers: updated });
    await AsyncStorage.setItem('saved_answers', JSON.stringify(updated));

    // Sync deletion to Supabase (non-blocking)
    try {
      await savedAnswersAPI.delete(id);
    } catch (error) {
      console.log('[savedAnswers] Backend delete failed (removed locally):', error);
    }
  },

  loadAnswers: async () => {
    // Try loading from Supabase first (source of truth)
    try {
      const result = await savedAnswersAPI.list();
      if (result.answers) {
        const answers: SavedAnswer[] = result.answers.map((a: any) => ({
          id: a.id,
          question: a.question,
          answer: a.answer,
          source: a.source || undefined,
          confidence: a.confidence || undefined,
          savedAt: new Date(a.saved_at || a.savedAt || Date.now()),
          trade: a.trade || 'HVAC',
        }));
        set({ answers });
        // Cache to AsyncStorage for offline access
        await AsyncStorage.setItem('saved_answers', JSON.stringify(answers));
        return;
      }
    } catch (error) {
      console.log('[savedAnswers] Backend load failed, using local cache:', error);
    }

    // Fallback: load from AsyncStorage
    try {
      const stored = await AsyncStorage.getItem('saved_answers');
      if (stored) {
        const parsed = JSON.parse(stored);
        const answers = parsed.map((a: any) => ({
          ...a,
          savedAt: new Date(a.savedAt || a.saved_at || Date.now()),
        }));
        set({ answers });
      }
    } catch (error) {
      console.error('Error loading saved answers:', error);
    }
  },
}));
