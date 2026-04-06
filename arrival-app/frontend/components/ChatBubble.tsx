import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, Keyboard } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Radius, FontSize, IconSize } from '../constants/Colors';
import { Message } from '../store/conversationStore';

interface ChatBubbleProps {
  message: Message;
  onSave?: () => void;
  onFeedback?: (rating: 'positive' | 'negative', feedbackText?: string) => void;
  userQuestion?: string;
  /** Set to true for the most recent assistant message to enable typing animation */
  isLatest?: boolean;
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

// Characters revealed per tick for typewriter effect
const CHARS_PER_TICK = 3;
const TICK_MS = 16; // ~60fps

export default function ChatBubble({ message, onSave, onFeedback, isLatest }: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isAlert = !!message.alertType;
  const alertConfig = message.alertType ? ALERT_COLORS[message.alertType] : null;
  const [saved, setSaved] = useState(false);

  // Feedback state
  const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(
    message.feedbackRating || null
  );
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [commentText, setCommentText] = useState('');

  // Typewriter effect for assistant messages
  const [displayedText, setDisplayedText] = useState(
    // Only animate the latest assistant message; show full text for all others
    (!isUser && isLatest) ? '' : message.content
  );
  const animatingRef = useRef(false);

  useEffect(() => {
    // Only animate the latest assistant message in text mode
    if (isUser || !isLatest || !message.content) {
      setDisplayedText(message.content);
      return;
    }

    // If we already showed the full text, don't re-animate
    if (displayedText === message.content) return;

    animatingRef.current = true;
    let charIndex = 0;

    const interval = setInterval(() => {
      charIndex += CHARS_PER_TICK;
      if (charIndex >= message.content.length) {
        setDisplayedText(message.content);
        animatingRef.current = false;
        clearInterval(interval);
      } else {
        setDisplayedText(message.content.slice(0, charIndex));
      }
    }, TICK_MS);

    return () => {
      clearInterval(interval);
      // If unmounting while animating, show full text
      animatingRef.current = false;
    };
  }, [message.content, isLatest]);

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
          <Ionicons name={alertConfig.icon} size={IconSize.sm} color={alertConfig.accent} />
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
        {displayedText}
      </Text>

      {/* Confidence badge — only show for high ("Verified") and low ("Best guess") */}
      {!isUser && message.confidence === 'high' && (
        <View style={styles.confidenceBadge}>
          <View style={[styles.confidenceDot, { backgroundColor: Colors.confidenceHigh }]} />
          <Text style={[styles.confidenceText, { color: Colors.confidenceHigh }]}>Verified</Text>
        </View>
      )}
      {!isUser && message.confidence === 'low' && (
        <View style={styles.confidenceBadge}>
          <View style={[styles.confidenceDot, { backgroundColor: Colors.warning }]} />
          <Text style={[styles.confidenceText, { color: Colors.warning }]}>Best guess</Text>
        </View>
      )}

      {/* Saved badge */}
      {saved && (
        <View style={styles.savedBadge}>
          <Ionicons name="bookmark" size={10} color={Colors.accent} />
          <Text style={styles.savedText}>Saved</Text>
        </View>
      )}

      {/* Action row: save + feedback */}
      {!isUser && (onFeedback || onSave) && !showCommentInput && (
        <View style={styles.feedbackRow}>
          {/* Save button — always visible for assistant messages */}
          {onSave && !saved && (
            <TouchableOpacity
              onPress={() => { onSave(); setSaved(true); }}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              style={styles.actionBtn}
            >
              <Ionicons name="bookmark-outline" size={14} color={Colors.textMuted} />
            </TouchableOpacity>
          )}
          {/* Feedback thumbs */}
          {onFeedback && !feedbackGiven && (
            <>
              <TouchableOpacity
                onPress={() => {
                  setFeedbackGiven('positive');
                  onFeedback('positive');
                }}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                style={styles.actionBtn}
              >
                <Ionicons name="thumbs-up-outline" size={14} color={Colors.textMuted} />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => setShowCommentInput(true)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                style={styles.actionBtn}
              >
                <Ionicons name="thumbs-down-outline" size={14} color={Colors.textMuted} />
              </TouchableOpacity>
            </>
          )}
        </View>
      )}

      {/* Feedback: comment input for negative rating */}
      {!isUser && showCommentInput && !feedbackGiven && (
        <View style={styles.commentContainer}>
          <TextInput
            style={styles.commentInput}
            placeholder="What was wrong? (optional)"
            placeholderTextColor={Colors.textMuted}
            value={commentText}
            onChangeText={setCommentText}
            maxLength={200}
            multiline
            autoFocus
          />
          <View style={styles.commentActions}>
            <TouchableOpacity
              onPress={() => {
                setShowCommentInput(false);
                setCommentText('');
              }}
            >
              <Text style={styles.commentCancel}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => {
                setFeedbackGiven('negative');
                setShowCommentInput(false);
                onFeedback?.('negative', commentText.trim() || undefined);
                setCommentText('');
                Keyboard.dismiss();
              }}
            >
              <Text style={styles.commentSubmit}>Submit</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Feedback: confirmation icon */}
      {!isUser && feedbackGiven && (
        <View style={styles.feedbackRow}>
          <Ionicons
            name={feedbackGiven === 'positive' ? 'thumbs-up' : 'thumbs-down'}
            size={14}
            color={feedbackGiven === 'positive' ? Colors.accent : Colors.textMuted}
          />
          <Text style={[styles.feedbackConfirm, feedbackGiven === 'positive' && { color: Colors.accent }]}>
            {feedbackGiven === 'positive' ? 'Thanks!' : 'Noted'}
          </Text>
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
            size={IconSize.sm}
            color={isAlert && alertConfig ? alertConfig.accent : Colors.accent}
          />
        </View>
      )}

      {bubble}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: Spacing.xs,
    paddingHorizontal: Spacing.base,
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
    borderRadius: Radius.lg,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: Spacing.sm,
    marginBottom: 2,
  },
  bubble: {
    maxWidth: '92%',
    paddingHorizontal: Spacing.base,
    paddingVertical: 10,
    borderRadius: Radius.lg,
  },
  userBubble: {
    backgroundColor: Colors.accent,
    borderBottomRightRadius: 4,
    maxWidth: '80%',
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
    gap: Spacing.xs,
    marginBottom: 6,
    paddingBottom: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  alertLabel: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  text: {
    fontSize: FontSize.base,
    lineHeight: 22,
    letterSpacing: -0.2,
  },
  userText: {
    color: '#FFFFFF',
  },
  assistantText: {
    color: Colors.text,
  },
  confidenceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    gap: 4,
  },
  confidenceDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  confidenceText: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  savedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    gap: Spacing.xs,
  },
  savedText: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.accent,
  },
  feedbackRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 14,
  },
  actionBtn: {
    padding: 2,
  },
  feedbackConfirm: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.textMuted,
  },
  commentContainer: {
    marginTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255,255,255,0.1)',
    paddingTop: 8,
  },
  commentInput: {
    fontSize: 12,
    color: Colors.text,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: Radius.sm,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minHeight: 32,
    maxHeight: 60,
  },
  commentActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 6,
  },
  commentCancel: {
    fontSize: 11,
    color: Colors.textMuted,
    fontWeight: '500',
  },
  commentSubmit: {
    fontSize: 11,
    color: Colors.accent,
    fontWeight: '600',
  },
});
