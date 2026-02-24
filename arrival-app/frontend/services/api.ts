import axios from 'axios';
import { supabase } from './supabase';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000, // 45s — real STT + Claude + TTS can take time
});

// Add Supabase JWT to every request so FastAPI backend can validate
api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
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

export default api;
