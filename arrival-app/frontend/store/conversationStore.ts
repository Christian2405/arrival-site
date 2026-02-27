import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { supabase } from '../services/supabase';

// Bug #11: Collision-safe ID generator (replaces Date.now().toString())
function generateId(): string {
  return Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 10);
}

// Bug #34: Debounced save — avoids JSON.stringify on every message
let saveTimeout: ReturnType<typeof setTimeout> | null = null;
function debouncedSave(conversations: Conversation[]) {
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    AsyncStorage.setItem('conversations', JSON.stringify(conversations)).catch(console.error);
  }, 1000);
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string;
  audio?: string;
  source?: string;
  confidence?: 'high' | 'medium' | 'low';
  alertType?: 'warning' | 'critical';
  displayMode?: 'voice' | 'text' | 'job';
  timestamp: Date;
}

export interface Conversation {
  id: string;
  title: string;
  trade: string;
  messages: Message[];
  createdAt: Date;
}

interface ConversationState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  isRecording: boolean;
  isProcessing: boolean;

  setCurrentConversation: (conversation: Conversation | null) => void;
  addMessage: (message: Message) => void;
  createNewConversation: (trade?: string) => void;
  setIsRecording: (isRecording: boolean) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  loadConversations: () => Promise<void>;
  saveConversations: () => Promise<void>;
}

// ─── Supabase helpers (fire-and-forget, never block UI) ───

async function getUserId(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getUser();
    return data?.user?.id ?? null;
  } catch {
    return null;
  }
}

/** Upsert a conversation row to Supabase. */
async function syncConversationToSupabase(conv: Conversation) {
  const userId = await getUserId();
  if (!userId) return;

  try {
    await supabase.from('conversations').upsert(
      {
        id: conv.id,
        user_id: userId,
        title: conv.title,
        trade: conv.trade,
        created_at: conv.createdAt.toISOString(),
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'id' }
    );
  } catch (e) {
    console.warn('[conversations] Supabase sync error:', e);
  }
}

/** Upsert a single message row to Supabase. */
async function syncMessageToSupabase(msg: Message, conversationId: string) {
  try {
    await supabase.from('messages').upsert(
      {
        id: msg.id,
        conversation_id: conversationId,
        role: msg.role,
        content: msg.content,
        image: msg.image ?? null,
        audio: msg.audio ?? null,
        source: msg.source ?? null,
        confidence: msg.confidence ?? null,
        alert_type: msg.alertType ?? null,
        display_mode: msg.displayMode ?? null,
        timestamp: msg.timestamp.toISOString(),
      },
      { onConflict: 'id' }
    );
  } catch (e) {
    console.warn('[messages] Supabase sync error:', e);
  }
}

/** Fetch all conversations + messages from Supabase. */
async function fetchConversationsFromSupabase(): Promise<Conversation[] | null> {
  const userId = await getUserId();
  if (!userId) return null;

  try {
    // Fetch conversations ordered by most recent
    const { data: convRows, error: convErr } = await supabase
      .from('conversations')
      .select('*')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false })
      .limit(50); // keep it reasonable

    if (convErr || !convRows?.length) return convErr ? null : [];

    // Fetch all messages for these conversations in one query
    const convIds = convRows.map((c: any) => c.id);
    const { data: msgRows, error: msgErr } = await supabase
      .from('messages')
      .select('*')
      .in('conversation_id', convIds)
      .order('timestamp', { ascending: true });

    if (msgErr) return null;

    // Group messages by conversation
    const msgsByConv: Record<string, Message[]> = {};
    for (const m of msgRows || []) {
      if (!msgsByConv[m.conversation_id]) msgsByConv[m.conversation_id] = [];
      msgsByConv[m.conversation_id].push({
        id: m.id,
        role: m.role,
        content: m.content,
        image: m.image ?? undefined,
        audio: m.audio ?? undefined,
        source: m.source ?? undefined,
        confidence: m.confidence ?? undefined,
        alertType: m.alert_type ?? undefined,
        displayMode: m.display_mode ?? undefined,
        timestamp: new Date(m.timestamp),
      });
    }

    return convRows.map((c: any) => ({
      id: c.id,
      title: c.title,
      trade: c.trade,
      messages: msgsByConv[c.id] || [],
      createdAt: new Date(c.created_at),
    }));
  } catch (e) {
    console.warn('[conversations] Supabase fetch error:', e);
    return null;
  }
}

// ─── Store ───

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  isRecording: false,
  isProcessing: false,

  setCurrentConversation: (conversation) => set({ currentConversation: conversation }),
  setIsRecording: (isRecording) => set({ isRecording }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),

  createNewConversation: (trade?: string) => {
    const newConversation: Conversation = {
      id: generateId(),
      title: 'New Conversation',
      trade: trade || 'General',
      messages: [],
      createdAt: new Date(),
    };
    set({ currentConversation: newConversation });
  },

  addMessage: (message) => {
    const { currentConversation, conversations } = get();

    if (!currentConversation) {
      // Auto-create a conversation if none exists
      const newConv: Conversation = {
        id: generateId(),
        title: message.content.slice(0, 50),
        trade: 'General',
        messages: [message],
        createdAt: new Date(),
      };
      set({
        currentConversation: newConv,
        conversations: [newConv, ...conversations],
      });
      debouncedSave(get().conversations);

      // Sync to Supabase (non-blocking)
      syncConversationToSupabase(newConv).then(() =>
        syncMessageToSupabase(message, newConv.id)
      );
      return;
    }

    const updatedMessages = [...currentConversation.messages, message];
    const updatedConversation = {
      ...currentConversation,
      messages: updatedMessages,
      title: updatedMessages[0]?.content.slice(0, 50) || 'New Conversation',
    };

    set({ currentConversation: updatedConversation });

    // Update in conversations list
    const existingIndex = conversations.findIndex((c) => c.id === updatedConversation.id);
    if (existingIndex >= 0) {
      const newConversations = [...conversations];
      newConversations[existingIndex] = updatedConversation;
      set({ conversations: newConversations });
    } else {
      set({ conversations: [updatedConversation, ...conversations] });
    }

    debouncedSave(get().conversations);

    // Sync to Supabase (non-blocking)
    syncConversationToSupabase(updatedConversation).then(() =>
      syncMessageToSupabase(message, updatedConversation.id)
    );
  },

  loadConversations: async () => {
    try {
      // 1. Load from AsyncStorage immediately (fast, offline-capable)
      const stored = await AsyncStorage.getItem('conversations');
      if (stored) {
        const parsed = JSON.parse(stored);
        const localConversations = parsed.map((c: any) => ({
          ...c,
          createdAt: new Date(c.createdAt),
          messages: c.messages.map((m: any) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          })),
        }));
        set({ conversations: localConversations });
      }

      // 2. Then fetch from Supabase (cloud source of truth)
      const cloudConversations = await fetchConversationsFromSupabase();
      if (cloudConversations !== null) {
        // Merge: cloud wins for conversations that exist in both,
        // keep local-only conversations (not yet synced)
        const { conversations: localConvs } = get();
        const cloudIds = new Set(cloudConversations.map((c) => c.id));
        const localOnly = localConvs.filter((c) => !cloudIds.has(c.id));

        // Push local-only conversations to Supabase
        for (const conv of localOnly) {
          syncConversationToSupabase(conv).then(() => {
            for (const msg of conv.messages) {
              syncMessageToSupabase(msg, conv.id);
            }
          });
        }

        const merged = [...cloudConversations, ...localOnly].sort(
          (a, b) => b.createdAt.getTime() - a.createdAt.getTime()
        );

        set({ conversations: merged });
        // Update AsyncStorage cache with merged data
        await AsyncStorage.setItem('conversations', JSON.stringify(merged));
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  },

  saveConversations: async () => {
    try {
      const { conversations } = get();
      await AsyncStorage.setItem('conversations', JSON.stringify(conversations));
    } catch (error) {
      console.error('Error saving conversations:', error);
    }
  },
}));
