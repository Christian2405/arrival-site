import axios from 'axios';
import { supabase } from './supabase';

// Bug #2: Guard against missing env var — warn loudly instead of silent "undefined/api"
const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
if (!BASE_URL) {
  console.error('EXPO_PUBLIC_BACKEND_URL is not set! All API calls will fail.');
}
const API_URL = (BASE_URL || '') + '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000, // 45s — real STT + Claude + TTS can take time
});

// Bug #10: Mutex for token refresh — prevents concurrent refresh race condition
let refreshPromise: Promise<any> | null = null;

// Add Supabase JWT to every request so FastAPI backend can validate
api.interceptors.request.use(async (config) => {
  let { data } = await supabase.auth.getSession();

  // If token expires within 60 seconds, refresh it
  if (data.session?.expires_at) {
    const expiresAt = data.session.expires_at * 1000;
    if (Date.now() > expiresAt - 60000) {
      // Only one concurrent refresh — others wait on the same promise
      if (!refreshPromise) {
        refreshPromise = supabase.auth.refreshSession().finally(() => {
          refreshPromise = null;
        });
      }
      const { data: refreshed } = await refreshPromise;
      if (refreshed?.session) {
        data = refreshed;
      }
    }
  }

  if (data.session?.access_token) {
    config.headers.Authorization = `Bearer ${data.session.access_token}`;
  }
  return config;
});

// --- AI API ---

export const aiAPI = {
  transcribe: async (audioBase64: string, demoMode: boolean = false) => {
    const response = await api.post(`/stt${demoMode ? '?demo=true' : ''}`, {
      audio_base64: audioBase64,
    });
    return response.data;
  },

  chat: async (
    message: string,
    imageBase64?: string,
    conversationHistory: any[] = [],
    demoMode: boolean = false
  ) => {
    const response = await api.post(`/chat${demoMode ? '?demo=true' : ''}`, {
      message,
      image_base64: imageBase64,
      conversation_history: conversationHistory,
    });
    return response.data;
  },

  textToSpeech: async (text: string, demoMode: boolean = false) => {
    const response = await api.post(`/tts${demoMode ? '?demo=true' : ''}`, {
      text,
    });
    return response.data;
  },

  analyzeFrame: async (imageBase64: string) => {
    const response = await api.post('/analyze-frame', {
      image_base64: imageBase64,
    });
    return response.data;
  },

  voiceChat: async (
    audioBase64: string,
    imageBase64?: string,
    conversationHistory: any[] = [],
    demoMode: boolean = false,
    mode: string = 'default',
  ) => {
    const response = await api.post(`/voice-chat${demoMode ? '?demo=true' : ''}`, {
      audio_base64: audioBase64,
      image_base64: imageBase64 || null,
      conversation_history: conversationHistory,
      mode: mode,
    });
    return response.data as {
      transcript: string;
      response: string;
      audio_base64: string;
      source?: string;
      confidence?: string;
    };
  },
};

// --- Documents API ---

export const documentsAPI = {
  upload: async (fileUri: string, filename: string, contentType: string) => {
    const formData = new FormData();
    formData.append('file', {
      uri: fileUri,
      name: filename,
      type: contentType,
    } as any);

    const response = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return response.data;
  },

  list: async () => {
    const response = await api.get('/documents');
    return response.data;
  },

  delete: async (documentId: string) => {
    const response = await api.delete(`/documents/${encodeURIComponent(documentId)}`);
    return response.data;
  },
};

// --- Saved Answers API ---

export const savedAnswersAPI = {
  save: async (data: {
    question: string;
    answer: string;
    source?: string;
    confidence?: string;
    trade?: string;
  }) => {
    const response = await api.post('/saved-answers', data);
    return response.data;
  },

  list: async () => {
    const response = await api.get('/saved-answers');
    return response.data;
  },

  delete: async (answerId: string) => {
    const response = await api.delete(`/saved-answers/${encodeURIComponent(answerId)}`);
    return response.data;
  },
};

export default api;
