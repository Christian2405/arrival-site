-- ============================================
-- Migration: Create conversations + messages tables for Chat History sync
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,  -- matches client-side ID (Date.now().toString())
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    trade TEXT NOT NULL DEFAULT 'HVAC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id, updated_at DESC);

-- Auto-update updated_at
CREATE TRIGGER set_updated_at_conversations
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,  -- matches client-side ID (Date.now().toString())
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    image TEXT,
    audio TEXT,
    source TEXT,
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    alert_type TEXT CHECK (alert_type IN ('warning', 'critical')),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id, timestamp ASC);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Conversations: users can manage their own
CREATE POLICY "conversations_select_own" ON conversations
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "conversations_insert_own" ON conversations
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "conversations_update_own" ON conversations
    FOR UPDATE USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "conversations_delete_own" ON conversations
    FOR DELETE USING (user_id = auth.uid());

-- Messages: users can manage messages in their own conversations
CREATE POLICY "messages_select_own" ON messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.id = messages.conversation_id
              AND conversations.user_id = auth.uid()
        )
    );

CREATE POLICY "messages_insert_own" ON messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.id = messages.conversation_id
              AND conversations.user_id = auth.uid()
        )
    );

CREATE POLICY "messages_delete_own" ON messages
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.id = messages.conversation_id
              AND conversations.user_id = auth.uid()
        )
    );
