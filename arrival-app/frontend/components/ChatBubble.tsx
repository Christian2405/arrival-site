import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
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

export default function ChatBubble({ message, onSave, isLatest }: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isAlert = !!message.alertType;
  const alertConfig = message.alertType ? ALERT_COLORS[message.alertType] : null;
  const [saved, setSaved] = useState(false);

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
            size={IconSize.sm}
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
});
