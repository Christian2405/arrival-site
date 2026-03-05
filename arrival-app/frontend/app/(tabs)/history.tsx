import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, Radius, FontSize, IconSize, Shadow } from '../../constants/Colors';
import { useConversationStore, Conversation, Message } from '../../store/conversationStore';

function formatTimeAgo(date: Date | string): string {
  // Bug #15: Defensive conversion — createdAt may be a string after deserialization
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return 'Recently';

  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTimestamp(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function getTradeBadgeColor(_trade: string): string {
  return Colors.textDark;
}

export default function HistoryScreen() {
  const router = useRouter();
  const { conversations, setCurrentConversation, createNewConversation, deleteConversation } = useConversationStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);

  const filteredConversations = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.messages.some((m) => m.content.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const openConversation = (conversation: Conversation) => {
    setSelectedConversation(conversation);
  };

  const continueConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    router.push('/(tabs)/home');
  };

  const confirmDelete = (conversation: Conversation) => {
    Alert.alert(
      'Delete Conversation',
      `Delete "${conversation.title}"? This can't be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            // If we're viewing this conversation, go back to list
            if (selectedConversation?.id === conversation.id) {
              setSelectedConversation(null);
            }
            deleteConversation(conversation.id);
          },
        },
      ]
    );
  };

  const startNewChat = () => {
    createNewConversation();
    router.push('/(tabs)/home');
  };

  // ─── Conversation Detail View ───
  if (selectedConversation) {
    return (
      <SafeAreaView style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backBtn} onPress={() => setSelectedConversation(null)}>
            <Ionicons name="chevron-back" size={IconSize.lg} color={Colors.textDark} />
          </TouchableOpacity>
          <View style={styles.detailHeaderCenter}>
            <Text style={styles.headerTitle} numberOfLines={1}>{selectedConversation.title}</Text>
            <Text style={styles.detailSubtitle}>
              {selectedConversation.messages.length} message{selectedConversation.messages.length !== 1 ? 's' : ''} · {formatTimeAgo(selectedConversation.createdAt)}
            </Text>
          </View>
          <TouchableOpacity
            style={styles.continueBtn}
            onPress={() => continueConversation(selectedConversation)}
            activeOpacity={0.7}
          >
            <Ionicons name="chatbubble-outline" size={IconSize.sm} color={Colors.accent} />
          </TouchableOpacity>
        </View>

        {/* Trade badge */}
        <View style={styles.detailBadgeRow}>
          <View style={styles.tradeBadge}>
            <Text style={styles.tradeBadgeText}>{selectedConversation.trade}</Text>
          </View>
        </View>

        {/* Messages */}
        {selectedConversation.messages.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="chatbubble-outline" size={36} color={Colors.textFaint} />
            <Text style={styles.emptyTitle}>No messages</Text>
            <Text style={styles.emptySubtitle}>This conversation is empty.</Text>
          </View>
        ) : (
          <ScrollView
            style={styles.messagesContainer}
            contentContainerStyle={styles.messagesList}
            showsVerticalScrollIndicator={false}
          >
            {selectedConversation.messages.map((msg, index) => (
              <MessageBubble key={msg.id || index} message={msg} />
            ))}
          </ScrollView>
        )}

        {/* Continue button */}
        <View style={styles.detailFooter}>
          <TouchableOpacity
            style={styles.continueConvBtn}
            onPress={() => continueConversation(selectedConversation)}
            activeOpacity={0.8}
          >
            <Ionicons name="chatbubble" size={IconSize.sm} color={Colors.card} />
            <Text style={styles.continueConvBtnText}>Continue Conversation</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ─── Conversation List View ───
  const renderItem = ({ item }: { item: Conversation }) => {
    const lastMessage = item.messages[item.messages.length - 1];
    const messageCount = item.messages.length;

    return (
      <TouchableOpacity style={styles.card} onPress={() => openConversation(item)} activeOpacity={0.6}>
        <View style={styles.cardTop}>
          <Text style={styles.cardTitle} numberOfLines={1}>
            {item.title}
          </Text>
          <View style={styles.cardTopRight}>
            <Text style={styles.cardTime}>{formatTimeAgo(item.createdAt)}</Text>
            <TouchableOpacity
              style={styles.deleteBtn}
              onPress={() => confirmDelete(item)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Ionicons name="trash-outline" size={15} color={Colors.textFaint} />
            </TouchableOpacity>
          </View>
        </View>
        {lastMessage && (
          <Text style={styles.cardPreview} numberOfLines={2}>
            {lastMessage.content}
          </Text>
        )}
        <View style={styles.cardFooter}>
          <View style={styles.tradeBadge}>
            <Text style={styles.tradeBadgeText}>{item.trade}</Text>
          </View>
          <Text style={styles.messageCount}>
            {messageCount} message{messageCount !== 1 ? 's' : ''}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.push('/(tabs)/home')}>
          <Ionicons name="chevron-back" size={IconSize.lg} color={Colors.textDark} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>History</Text>
        <TouchableOpacity style={styles.newChatBtn} onPress={startNewChat} activeOpacity={0.7}>
          <Ionicons name="add" size={IconSize.md} color={Colors.textDark} />
        </TouchableOpacity>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={IconSize.sm} color={Colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search conversations..."
            placeholderTextColor={Colors.textFaint}
            value={searchQuery}
            onChangeText={setSearchQuery}
            returnKeyType="search"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Ionicons name="close-circle" size={IconSize.sm} color={Colors.textFaint} />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Content */}
      {filteredConversations.length === 0 && searchQuery.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="chatbubbles-outline" size={40} color={Colors.textFaint} />
          </View>
          <Text style={styles.emptyTitle}>No conversations yet</Text>
          <Text style={styles.emptySubtitle}>
            Your chat history will appear here once{'\n'}you start talking to Arrival.
          </Text>
          <TouchableOpacity style={styles.startChatBtn} onPress={startNewChat} activeOpacity={0.8}>
            <Text style={styles.startChatBtnText}>Start a Conversation</Text>
          </TouchableOpacity>
        </View>
      ) : filteredConversations.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="search-outline" size={36} color={Colors.textFaint} />
          <Text style={styles.emptyTitle}>No results</Text>
          <Text style={styles.emptySubtitle}>
            Try a different search term
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredConversations}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}

// ─── Message Bubble Component ───

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <View style={[styles.messageBubbleRow, isUser && styles.messageBubbleRowUser]}>
      <View style={[styles.messageBubble, isUser ? styles.messageBubbleUser : styles.messageBubbleAssistant]}>
        <Text style={[styles.messageBubbleText, isUser && styles.messageBubbleTextUser]}>
          {message.content}
        </Text>
        <View style={styles.messageMeta}>
          {message.displayMode && (
            <View style={styles.modeTag}>
              <Ionicons
                name={message.displayMode === 'voice' ? 'mic' : message.displayMode === 'job' ? 'construct' : 'chatbubble'}
                size={10}
                color={Colors.textFaint}
              />
              <Text style={styles.modeTagText}>{message.displayMode}</Text>
            </View>
          )}
          <Text style={styles.messageTime}>{formatTimestamp(message.timestamp)}</Text>
        </View>
      </View>
    </View>
  );
}

// ─── Styles ───

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: Radius.full,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    flex: 1,
    fontSize: FontSize.xl,
    fontWeight: '800',
    color: Colors.textDark,
    letterSpacing: -0.5,
    marginLeft: Spacing.xs,
  },
  newChatBtn: {
    width: 38,
    height: 38,
    borderRadius: Radius.full,
    backgroundColor: Colors.card,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.borderWarm,
  },
  searchContainer: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.sm,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    paddingHorizontal: 14,
    height: 42,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderWarm,
  },
  searchInput: {
    flex: 1,
    fontSize: FontSize.base,
    color: Colors.textDark,
    paddingVertical: 0,
    letterSpacing: -0.2,
  },
  list: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.lg,
    paddingTop: Spacing.xs,
    gap: Spacing.sm,
  },
  card: {
    backgroundColor: Colors.card,
    borderRadius: Radius.lg,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.borderWarm,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  cardTopRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  cardTitle: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    color: Colors.textDark,
    flex: 1,
    marginRight: Spacing.md,
    letterSpacing: -0.2,
  },
  cardTime: {
    fontSize: FontSize.xs,
    color: Colors.textFaint,
    fontWeight: '500',
  },
  deleteBtn: {
    width: 28,
    height: 28,
    borderRadius: Radius.full,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardPreview: {
    fontSize: FontSize.sm,
    color: Colors.textMuted,
    lineHeight: 20,
    marginBottom: 10,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  tradeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.sm,
    backgroundColor: Colors.border,
  },
  tradeBadgeText: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.2,
    color: Colors.textMuted,
  },
  messageCount: {
    fontSize: FontSize.xs,
    color: Colors.textFaint,
    fontWeight: '500',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    paddingBottom: 80,
  },
  emptyIconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.card,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    ...Shadow.subtle,
  },
  emptyTitle: {
    fontSize: FontSize.xl,
    fontWeight: '700',
    color: Colors.textDark,
    marginBottom: Spacing.sm,
    letterSpacing: -0.3,
  },
  emptySubtitle: {
    fontSize: FontSize.base,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 28,
  },
  startChatBtn: {
    backgroundColor: Colors.tradeGeneral,
    paddingHorizontal: 28,
    paddingVertical: 15,
    borderRadius: Radius.lg,
  },
  startChatBtnText: {
    color: Colors.card,
    fontSize: FontSize.base,
    fontWeight: '600',
    letterSpacing: -0.2,
  },

  // ─── Detail View ───
  detailHeaderCenter: {
    flex: 1,
    marginLeft: Spacing.xs,
  },
  detailSubtitle: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    marginTop: 2,
  },
  continueBtn: {
    width: 38,
    height: 38,
    borderRadius: Radius.full,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailBadgeRow: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.sm,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesList: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.lg,
    paddingTop: Spacing.xs,
    gap: Spacing.sm,
  },
  detailFooter: {
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.borderWarm,
  },
  continueConvBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: Colors.accent,
    paddingVertical: 14,
    borderRadius: Radius.lg,
  },
  continueConvBtnText: {
    color: Colors.card,
    fontSize: FontSize.base,
    fontWeight: '600',
    letterSpacing: -0.2,
  },

  // ─── Message Bubbles ───
  messageBubbleRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
  },
  messageBubbleRowUser: {
    justifyContent: 'flex-end',
  },
  messageBubble: {
    maxWidth: '82%',
    borderRadius: Radius.lg,
    padding: 12,
  },
  messageBubbleAssistant: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.borderWarm,
    borderBottomLeftRadius: 4,
  },
  messageBubbleUser: {
    backgroundColor: Colors.textDark,
    borderBottomRightRadius: 4,
  },
  messageBubbleText: {
    fontSize: FontSize.sm,
    color: Colors.textDark,
    lineHeight: 20,
    letterSpacing: -0.1,
  },
  messageBubbleTextUser: {
    color: Colors.textOnDark,
  },
  messageMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    marginTop: 6,
    gap: 8,
  },
  modeTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  modeTagText: {
    fontSize: 10,
    color: Colors.textFaint,
    fontWeight: '500',
    textTransform: 'capitalize',
  },
  messageTime: {
    fontSize: 10,
    color: Colors.textFaint,
    fontWeight: '500',
  },
});
