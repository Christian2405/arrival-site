import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { useConversationStore, Conversation } from '../../store/conversationStore';

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getTradeBadgeColor(trade: string): string {
  switch (trade.toLowerCase()) {
    case 'hvac': return '#4A90D9';
    case 'electrical': return '#E8A84C';
    case 'plumbing': return '#5B9BD5';
    default: return '#7C736A';
  }
}

export default function HistoryScreen() {
  const router = useRouter();
  const { conversations, setCurrentConversation, createNewConversation } = useConversationStore();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.messages.some((m) => m.content.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const openConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    router.push('/(tabs)/home');
  };

  const startNewChat = () => {
    createNewConversation();
    router.push('/(tabs)/home');
  };

  const renderItem = ({ item }: { item: Conversation }) => {
    const lastMessage = item.messages[item.messages.length - 1];
    const messageCount = item.messages.length;
    const badgeColor = getTradeBadgeColor(item.trade);

    return (
      <TouchableOpacity style={styles.card} onPress={() => openConversation(item)} activeOpacity={0.6}>
        <View style={styles.cardTop}>
          <Text style={styles.cardTitle} numberOfLines={1}>
            {item.title}
          </Text>
          <Text style={styles.cardTime}>{formatTimeAgo(item.createdAt)}</Text>
        </View>
        {lastMessage && (
          <Text style={styles.cardPreview} numberOfLines={2}>
            {lastMessage.content}
          </Text>
        )}
        <View style={styles.cardFooter}>
          <View style={[styles.tradeBadge, { backgroundColor: badgeColor + '12' }]}>
            <View style={[styles.tradeDot, { backgroundColor: badgeColor }]} />
            <Text style={[styles.tradeBadgeText, { color: badgeColor }]}>{item.trade}</Text>
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
        <Text style={styles.headerTitle}>History</Text>
        <TouchableOpacity style={styles.newChatBtn} onPress={startNewChat} activeOpacity={0.7}>
          <Ionicons name="add" size={20} color="#2A2622" />
        </TouchableOpacity>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={16} color="#A09A93" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search conversations..."
            placeholderTextColor="#C7C2BC"
            value={searchQuery}
            onChangeText={setSearchQuery}
            returnKeyType="search"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Ionicons name="close-circle" size={16} color="#C7C2BC" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Content */}
      {filteredConversations.length === 0 && searchQuery.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="chatbubbles-outline" size={40} color="#C7C2BC" />
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
          <Ionicons name="search-outline" size={36} color="#C7C2BC" />
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F0EB',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#2A2622',
    letterSpacing: -0.5,
  },
  newChatBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
  },
  searchContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 14,
    height: 42,
    gap: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 1,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: '#2A2622',
    paddingVertical: 0,
    letterSpacing: -0.2,
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    paddingTop: 4,
    gap: 8,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2A2622',
    flex: 1,
    marginRight: 12,
    letterSpacing: -0.2,
  },
  cardTime: {
    fontSize: 12,
    color: '#C7C2BC',
    fontWeight: '500',
  },
  cardPreview: {
    fontSize: 14,
    color: '#A09A93',
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
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    gap: 5,
  },
  tradeDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
  },
  tradeBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  messageCount: {
    fontSize: 12,
    color: '#C7C2BC',
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
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 1,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#2A2622',
    marginBottom: 8,
    letterSpacing: -0.3,
  },
  emptySubtitle: {
    fontSize: 15,
    color: '#A09A93',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 28,
  },
  startChatBtn: {
    backgroundColor: '#2A2622',
    paddingHorizontal: 28,
    paddingVertical: 15,
    borderRadius: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 8,
    elevation: 4,
  },
  startChatBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
    letterSpacing: -0.2,
  },
});
