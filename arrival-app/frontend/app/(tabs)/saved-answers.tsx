import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSavedAnswersStore, SavedAnswer } from '../../store/savedAnswersStore';

export default function SavedAnswersScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { answers, removeAnswer, loadAnswers } = useSavedAnswersStore();

  useEffect(() => {
    loadAnswers();
  }, []);

  const filteredAnswers = answers.filter(
    (a) =>
      a.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = (item: SavedAnswer) => {
    Alert.alert(
      'Remove Saved Answer',
      'Are you sure you want to remove this bookmark?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: () => removeAnswer(item.id),
        },
      ]
    );
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Monochrome confidence: dark for high, medium gray for medium, light for low
  const getConfidenceColor = (confidence: string): string => {
    if (confidence === 'high') return '#2A2622';
    if (confidence === 'medium') return '#A09A93';
    return '#C7C2BC';
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="#2A2622" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Saved Answers</Text>
        <View style={styles.headerRight}>
          {answers.length > 0 && (
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{answers.length}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Search Bar — only show if there are answers */}
      {answers.length > 0 && (
        <View style={styles.searchContainer}>
          <View style={styles.searchBar}>
            <Ionicons name="search" size={16} color="#A09A93" />
            <TextInput
              style={styles.searchInput}
              placeholder="Search saved answers..."
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
      )}

      {/* Content */}
      {filteredAnswers.length === 0 && answers.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="bookmark-outline" size={36} color="#C7C2BC" />
          </View>
          <Text style={styles.emptyTitle}>No saved answers</Text>
          <Text style={styles.emptySubtitle}>
            Bookmark AI responses during conversations{'\n'}to find them again later.
          </Text>

          {/* How-to steps */}
          <View style={styles.stepsCard}>
            <View style={styles.step}>
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>1</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>Ask a question</Text>
                <Text style={styles.stepHint}>Chat with Arrival on the home screen</Text>
              </View>
            </View>

            <View style={styles.stepConnector} />

            <View style={styles.step}>
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>2</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>Long-press a response</Text>
                <Text style={styles.stepHint}>Hold on any AI answer you find useful</Text>
              </View>
            </View>

            <View style={styles.stepConnector} />

            <View style={styles.step}>
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>3</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>Tap "Save Answer"</Text>
                <Text style={styles.stepHint}>It will appear here for quick access</Text>
              </View>
            </View>
          </View>
        </View>
      ) : filteredAnswers.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="search-outline" size={36} color="#C7C2BC" />
          <Text style={[styles.emptyTitle, { marginTop: 16 }]}>No results</Text>
          <Text style={styles.emptySubtitle}>
            Try a different search term
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredAnswers}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => {
            const confidenceColor = getConfidenceColor(item.confidence || 'low');
            const isExpanded = expandedId === item.id;

            return (
              <TouchableOpacity
                style={styles.answerCard}
                activeOpacity={0.6}
                onPress={() => setExpandedId(isExpanded ? null : item.id)}
                onLongPress={() => handleDelete(item)}
              >
                <View style={styles.answerTop}>
                  <View style={styles.answerTopLeft}>
                    <View style={styles.answerTradeBadge}>
                      <Text style={styles.answerTradeText}>{item.trade}</Text>
                    </View>
                    <Text style={styles.answerDate}>{formatDate(item.savedAt)}</Text>
                  </View>
                  <View style={styles.answerTopRight}>
                    {item.confidence && (
                      <View style={styles.confidenceRow}>
                        <View style={[styles.confidenceDot, { backgroundColor: confidenceColor }]} />
                        <Text style={styles.confidenceText}>
                          {item.confidence}
                        </Text>
                      </View>
                    )}
                    <TouchableOpacity
                      onPress={() => handleDelete(item)}
                      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                      style={styles.deleteBtn}
                    >
                      <Ionicons name="trash-outline" size={15} color="#A09A93" />
                    </TouchableOpacity>
                  </View>
                </View>

                <Text style={styles.answerQuestion} numberOfLines={isExpanded ? undefined : 2}>
                  {item.question}
                </Text>
                <Text style={styles.answerPreview} numberOfLines={isExpanded ? undefined : 3}>
                  {item.answer}
                </Text>

                {item.source && (
                  <View style={styles.sourceRow}>
                    <Ionicons name="document-text-outline" size={11} color="#A09A93" />
                    <Text style={styles.sourceText}>{item.source}</Text>
                  </View>
                )}

                {!isExpanded && item.answer.length > 150 && (
                  <Text style={styles.readMore}>Tap to read more</Text>
                )}
              </TouchableOpacity>
            );
          }}
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
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    flex: 1,
    fontSize: 28,
    fontWeight: '800',
    color: '#2A2622',
    letterSpacing: -0.5,
    marginLeft: 4,
  },
  headerRight: {
    width: 36,
    alignItems: 'center',
  },
  countBadge: {
    backgroundColor: '#2A2622',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  countText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
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
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 28,
    paddingBottom: 60,
  },
  emptyIconWrap: {
    width: 76,
    height: 76,
    borderRadius: 38,
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
    marginBottom: 32,
  },

  // Steps card
  stepsCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    width: '100%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 1,
  },
  step: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 14,
  },
  stepNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#2A2622',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 1,
  },
  stepNumberText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  stepContent: {
    flex: 1,
    paddingTop: 2,
  },
  stepTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#2A2622',
    letterSpacing: -0.2,
    marginBottom: 2,
  },
  stepHint: {
    fontSize: 13,
    color: '#A09A93',
    lineHeight: 18,
  },
  stepConnector: {
    width: 1,
    height: 12,
    backgroundColor: '#EBE7E2',
    marginLeft: 14,
    marginVertical: 4,
  },

  // List
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    gap: 8,
  },
  answerCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 2,
  },
  answerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  answerTopLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  answerTopRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  answerTradeBadge: {
    backgroundColor: '#F3F0EB',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 5,
  },
  answerTradeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#2A2622',
    letterSpacing: 0.2,
  },
  answerDate: {
    fontSize: 11,
    color: '#A09A93',
  },
  answerQuestion: {
    fontSize: 15,
    fontWeight: '600',
    color: '#2A2622',
    marginBottom: 6,
    lineHeight: 21,
    letterSpacing: -0.2,
  },
  answerPreview: {
    fontSize: 14,
    color: '#A09A93',
    lineHeight: 20,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 4,
  },
  sourceText: {
    fontSize: 11,
    color: '#A09A93',
    fontStyle: 'italic',
  },
  readMore: {
    fontSize: 12,
    color: '#2A2622',
    fontWeight: '600',
    marginTop: 8,
  },
  confidenceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  confidenceDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  confidenceText: {
    fontSize: 11,
    color: '#A09A93',
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  deleteBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#F3F0EB',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
