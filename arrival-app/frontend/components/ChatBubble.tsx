import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';
import { Message } from '../store/conversationStore';

interface ChatBubbleProps {
  message: Message;
  onSave?: () => void;
}

export default function ChatBubble({ message, onSave }: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const [saved, setSaved] = useState(false);

  const handleLongPress = () => {
    if (isUser || !onSave) return;
    Alert.alert(
      'Save Answer',
      'Bookmark this response for quick access later?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Save',
          onPress: () => {
            onSave();
            setSaved(true);
          },
        },
      ]
    );
  };

  const bubble = (
    <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
      <Text style={[styles.text, isUser ? styles.userText : styles.assistantText]}>
        {message.content}
      </Text>

      {/* Source & Confidence */}
      {message.source && (
        <View style={styles.metaRow}>
          <Ionicons name="document-text-outline" size={11} color={Colors.textSecondary} />
          <Text style={styles.sourceText}>{message.source}</Text>
        </View>
      )}
      {message.confidence && (
        <View style={styles.metaRow}>
          <View
            style={[
              styles.confidenceDot,
              {
                backgroundColor:
                  message.confidence === 'high'
                    ? Colors.confidenceHigh
                    : message.confidence === 'medium'
                    ? Colors.confidenceMedium
                    : Colors.confidenceLow,
              },
            ]}
          />
          <Text style={styles.confidenceLabel}>
            {message.confidence} confidence
          </Text>
        </View>
      )}

      {/* Saved badge */}
      {saved && (
        <View style={styles.savedBadge}>
          <Ionicons name="bookmark" size={10} color={Colors.accent} />
          <Text style={styles.savedText}>Saved</Text>
        </View>
      )}
    </View>
  );

  return (
    <View style={[styles.container, isUser ? styles.userContainer : styles.assistantContainer]}>
      {/* Avatar */}
      {!isUser && (
        <View style={styles.avatar}>
          <Ionicons name="sparkles" size={14} color={Colors.accent} />
        </View>
      )}

      {!isUser && onSave ? (
        <TouchableOpacity onLongPress={handleLongPress} activeOpacity={0.8} delayLongPress={400}>
          {bubble}
        </TouchableOpacity>
      ) : (
        bubble
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: 4,
    paddingHorizontal: 14,
    alignItems: 'flex-end',
  },
  userContainer: {
    justifyContent: 'flex-end',
  },
  assistantContainer: {
    justifyContent: 'flex-start',
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
    marginBottom: 2,
  },
  bubble: {
    maxWidth: '78%',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
  },
  userBubble: {
    backgroundColor: Colors.accent,
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: Colors.glassBg,
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  text: {
    fontSize: 15,
    lineHeight: 21,
    letterSpacing: -0.2,
  },
  userText: {
    color: '#FFFFFF',
  },
  assistantText: {
    color: Colors.text,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    gap: 4,
  },
  sourceText: {
    fontSize: 11,
    color: Colors.textSecondary,
    fontStyle: 'italic',
    flex: 1,
  },
  confidenceDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  confidenceLabel: {
    fontSize: 11,
    color: Colors.textSecondary,
  },
  savedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    gap: 4,
  },
  savedText: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.accent,
  },
});
