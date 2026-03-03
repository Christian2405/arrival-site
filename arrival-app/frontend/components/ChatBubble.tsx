import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, TextInput } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';
import { Message } from '../store/conversationStore';

interface ChatBubbleProps {
  message: Message;
  onSave?: () => void;
  onFeedback?: (rating: 'positive' | 'negative', feedbackText?: string) => void;
  /** The user's question that preceded this answer (for feedback logging) */
  userQuestion?: string;
}

const ALERT_COLORS = {
  warning: {
    accent: '#D4890A',
    bg: 'rgba(212, 137, 10, 0.12)',
    border: '#D4890A',
    icon: 'warning-outline' as const,
    label: 'NOTICE',
  },
  critical: {
    accent: '#C0392B',
    bg: 'rgba(192, 57, 43, 0.12)',
    border: '#C0392B',
    icon: 'alert-circle-outline' as const,
    label: 'SAFETY ALERT',
  },
};

export default function ChatBubble({ message, onSave, onFeedback, userQuestion }: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isAlert = !!message.alertType;
  const alertConfig = message.alertType ? ALERT_COLORS[message.alertType] : null;
  const [saved, setSaved] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');

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

  const handleThumbsUp = () => {
    if (feedbackGiven) return;
    setFeedbackGiven('positive');
    onFeedback?.('positive');
  };

  const handleThumbsDown = () => {
    if (feedbackGiven) return;
    setFeedbackGiven('negative');
    setShowFeedbackInput(true);
  };

  const handleSubmitFeedback = () => {
    onFeedback?.('negative', feedbackText || undefined);
    setShowFeedbackInput(false);
  };

  const handleSkipFeedback = () => {
    onFeedback?.('negative');
    setShowFeedbackInput(false);
  };

  const bubble = (
    <View
      style={[
        styles.bubble,
        isUser ? styles.userBubble : styles.assistantBubble,
        isAlert && alertConfig && {
          backgroundColor: alertConfig.bg,
          borderLeftWidth: 3,
          borderLeftColor: alertConfig.border,
          borderBottomLeftRadius: 14,
        },
      ]}
    >
      {/* Alert header */}
      {isAlert && alertConfig && (
        <View style={[styles.alertHeader, { borderBottomColor: alertConfig.border + '30' }]}>
          <Ionicons name={alertConfig.icon} size={14} color={alertConfig.accent} />
          <Text style={[styles.alertLabel, { color: alertConfig.accent }]}>
            {alertConfig.label}
          </Text>
        </View>
      )}

      <Text
        style={[
          styles.text,
          isUser ? styles.userText : styles.assistantText,
          isAlert && alertConfig && { color: alertConfig.accent },
        ]}
      >
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

      {/* Actions row — feedback thumbs + bookmark */}
      {!isUser && (onFeedback || onSave) && (
        <View style={styles.feedbackRow}>
          {onFeedback && (
            feedbackGiven ? (
              <View style={styles.feedbackDone}>
                <Ionicons
                  name={feedbackGiven === 'positive' ? 'thumbs-up' : 'thumbs-down'}
                  size={12}
                  color={Colors.textSecondary}
                />
                <Text style={styles.feedbackDoneText}>
                  {feedbackGiven === 'positive' ? 'Thanks!' : 'Noted'}
                </Text>
              </View>
            ) : (
              <>
                <TouchableOpacity onPress={handleThumbsUp} style={styles.feedbackBtn} hitSlop={8}>
                  <Ionicons name="thumbs-up-outline" size={14} color={Colors.textSecondary} />
                </TouchableOpacity>
                <TouchableOpacity onPress={handleThumbsDown} style={styles.feedbackBtn} hitSlop={8}>
                  <Ionicons name="thumbs-down-outline" size={14} color={Colors.textSecondary} />
                </TouchableOpacity>
              </>
            )
          )}
          {/* Bookmark button — visible tap target for saving */}
          {onSave && !saved && (
            <TouchableOpacity
              onPress={() => { onSave(); setSaved(true); }}
              style={[styles.feedbackBtn, { marginLeft: 'auto' }]}
              hitSlop={8}
            >
              <Ionicons name="bookmark-outline" size={14} color={Colors.textSecondary} />
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Thumbs-down feedback text input */}
      {showFeedbackInput && (
        <View style={styles.feedbackInputContainer}>
          <TextInput
            style={styles.feedbackInput}
            placeholder="What was wrong?"
            placeholderTextColor={Colors.textSecondary}
            value={feedbackText}
            onChangeText={setFeedbackText}
            multiline
            maxLength={500}
            autoFocus
          />
          <View style={styles.feedbackInputActions}>
            <TouchableOpacity onPress={handleSkipFeedback} style={styles.feedbackSkipBtn}>
              <Text style={styles.feedbackSkipText}>Skip</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={handleSubmitFeedback} style={styles.feedbackSendBtn}>
              <Text style={styles.feedbackSendText}>Send</Text>
            </TouchableOpacity>
          </View>
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
        <View
          style={[
            styles.avatar,
            isAlert && alertConfig && { backgroundColor: alertConfig.accent + '20' },
          ]}
        >
          <Ionicons
            name={isAlert && alertConfig ? alertConfig.icon : 'sparkles'}
            size={14}
            color={isAlert && alertConfig ? alertConfig.accent : Colors.accent}
          />
        </View>
      )}

      {!isUser && onSave ? (
        <TouchableOpacity onLongPress={handleLongPress} activeOpacity={0.7} delayLongPress={300}>
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
    width: 32,
    height: 32,
    borderRadius: 16,
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
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginBottom: 6,
    paddingBottom: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  alertLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
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
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  confidenceLabel: {
    fontSize: 11,
    color: Colors.textSecondary,
    textTransform: 'capitalize',
  },
  // Feedback styles
  feedbackRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 12,
  },
  feedbackBtn: {
    padding: 4,
    opacity: 0.7,
  },
  feedbackDone: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  feedbackDoneText: {
    fontSize: 11,
    color: Colors.textSecondary,
  },
  feedbackInputContainer: {
    marginTop: 8,
    backgroundColor: 'rgba(0,0,0,0.04)',
    borderRadius: 10,
    padding: 8,
  },
  feedbackInput: {
    fontSize: 13,
    color: Colors.text,
    minHeight: 36,
    maxHeight: 80,
    paddingVertical: 4,
  },
  feedbackInputActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 4,
  },
  feedbackSkipBtn: {
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  feedbackSkipText: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  feedbackSendBtn: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: Colors.accent,
    borderRadius: 6,
  },
  feedbackSendText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FFF',
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
