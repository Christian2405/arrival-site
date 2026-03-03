import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
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

// --- Retry interceptor for Render cold starts ---
// Render free tier sleeps after 15min of inactivity; first request after
// sleeping gets a network error or 502/503 while the server boots (~30-60s).
// Auto-retry up to 2 times with increasing delays so the user doesn't see
// "Cannot reach server" on cold starts.
interface RetryConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined;
    if (!config || (config._retryCount ?? 0) >= 2) {
      return Promise.reject(error);
    }

    // Retry on network errors (cold start) or 502/503 (Render proxy can't reach server).
    // Safe for ALL methods here because 502/503 and network errors mean the server
    // never received/processed the request — no risk of duplicate side effects.
    const isNetworkError = !error.response && (
      error.code === 'ECONNABORTED' ||
      error.code === 'ERR_NETWORK' ||
      error.message?.includes('Network') ||
      error.message?.includes('timeout')
    );
    const isServerStarting = error.response?.status === 502 || error.response?.status === 503;

    if (isNetworkError || isServerStarting) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      const delay = config._retryCount * 3000; // 3s first retry, 6s second
      console.log(`[API] Retry ${config._retryCount}/2 after ${delay}ms (server may be waking up)...`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return api(config);
    }

    return Promise.reject(error);
  },
);

// --- AI API ---

export const aiAPI = {
  /** Fire-and-forget ping to wake up Render free tier server */
  warmup: async () => {
    try { await api.get('/health'); } catch { /* silent — just waking the server */ }
  },

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

  analyzeFrame: async (imageBase64: string, previousAlerts?: string[]) => {
    const response = await api.post('/analyze-frame', {
      image_base64: imageBase64,
      previous_alerts: previousAlerts || [],
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

// --- Feedback API ---

export const feedbackAPI = {
  submit: async (data: {
    question: string;
    answer: string;
    rating: 'positive' | 'negative';
    feedback_text?: string;
    source?: string;
    conversation_id?: string;
  }) => {
    const response = await api.post('/feedback', data);
    return response.data;
  },
};

// --- Job Context API ---

export interface JobContext {
  equipment_type: string;
  brand?: string | null;
  model?: string | null;
}

export interface JobContextOptions {
  equipment_types: string[];
  brands: string[];
}

export const jobContextAPI = {
  set: async (data: {
    equipment_type: string;
    brand?: string;
    model?: string;
  }): Promise<JobContext> => {
    const response = await api.post('/job-context', data);
    return response.data;
  },

  get: async (): Promise<JobContext | null> => {
    const response = await api.get('/job-context');
    return response.data;
  },

  clear: async () => {
    const response = await api.delete('/job-context');
    return response.data;
  },

  getOptions: async (): Promise<JobContextOptions> => {
    const response = await api.get('/job-context/options');
    return response.data;
  },
};

// --- Usage API ---

export interface UsageData {
  plan: string;
  queries_today: number;
  query_limit: number;   // -1 = unlimited
  documents_count: number;
  document_limit: number; // -1 = unlimited
  job_mode: boolean;
}

export const usageAPI = {
  getUsage: async (): Promise<UsageData> => {
    const response = await api.get('/usage');
    return response.data;
  },
};

// --- Error Codes API (public, no auth needed) ---

export interface ErrorCodeBrand {
  id: string;
  name: string;
  code_count: number;
}

export interface ErrorCode {
  code: string;
  meaning: string;
  causes: string[];
  fix: string;
}

export const errorCodesAPI = {
  getBrands: async (): Promise<{ brands: ErrorCodeBrand[]; total_codes: number }> => {
    const response = await api.get('/error-codes');
    return response.data;
  },
  getBrandCodes: async (brandId: string): Promise<{ brand: string; brand_id: string; codes: ErrorCode[] }> => {
    const response = await api.get(`/error-codes/${brandId}`);
    return response.data;
  },
};

export default api;
