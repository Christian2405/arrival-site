import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string;
  audio?: string;
  source?: string;
  confidence?: 'high' | 'medium' | 'low';
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
  createNewConversation: () => void;
  setIsRecording: (isRecording: boolean) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  loadConversations: () => Promise<void>;
  saveConversations: () => Promise<void>;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  isRecording: false,
  isProcessing: false,

  setCurrentConversation: (conversation) => set({ currentConversation: conversation }),
  setIsRecording: (isRecording) => set({ isRecording }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),

  createNewConversation: () => {
    const newConversation: Conversation = {
      id: Date.now().toString(),
      title: 'New Conversation',
      trade: 'HVAC',
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
        id: Date.now().toString(),
        title: message.content.slice(0, 50),
        trade: 'HVAC',
        messages: [message],
        createdAt: new Date(),
      };
      set({
        currentConversation: newConv,
        conversations: [newConv, ...conversations],
      });
      get().saveConversations();
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

    get().saveConversations();
  },

  loadConversations: async () => {
    try {
      const stored = await AsyncStorage.getItem('conversations');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Restore Date objects
        const conversations = parsed.map((c: any) => ({
          ...c,
          createdAt: new Date(c.createdAt),
          messages: c.messages.map((m: any) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          })),
        }));
        set({ conversations });
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
