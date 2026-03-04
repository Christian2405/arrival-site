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
import { Colors, Spacing, Radius, FontSize, IconSize, Shadow } from '../../constants/Colors';
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

  const formatDate = (date: Date | string) => {
    // Defensive: date may arrive as a string from AsyncStorage deserialization
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getConfidenceStyle = (confidence: string) => {
    if (confidence === 'high') return { color: Colors.confidenceHigh, label: 'High' };
    if (confidence === 'medium') return { color: Colors.confidenceMedium, label: 'Medium' };
    return { color: Colors.confidenceLow, label: 'Low' };
  };

  const getTradeColor = (trade: string) => {
    const lower = trade?.toLowerCase() || '';
    if (lower.includes('hvac') || lower.includes('heating') || lower.includes('cooling')) return Colors.tradeHvac;
    if (lower.includes('electric')) return Colors.tradeElectrical;
    if (lower.includes('plumb')) return Colors.tradePlumbing;
    return Colors.tradeGeneral;
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={IconSize.lg} color={Colors.textDark} />
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
            <Ionicons name="search" size={16} color={Colors.textMuted} />
            <TextInput
              style={styles.searchInput}
              placeholder="Search saved answers..."
              placeholderTextColor={Colors.textFaint}
              value={searchQuery}
              onChangeText={setSearchQuery}
              returnKeyType="search"
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Ionicons name="close-circle" size={16} color={Colors.textFaint} />
              </TouchableOpacity>
            )}
          </View>
        </View>
      )}

      {/* Content */}
      {filteredAnswers.length === 0 && answers.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="bookmark-outline" size={36} color={Colors.accent} />
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
              <View style={[styles.stepNumber, { backgroundColor: Colors.accent }]}>
                <Text style={styles.stepNumberText}>2</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>Tap the bookmark icon</Text>
                <Text style={styles.stepHint}>
                  Each AI response has a{' '}
                  <Ionicons name="bookmark-outline" size={12} color={Colors.textMuted} />
                  {' '}icon at the bottom
                </Text>
              </View>
            </View>

            <View style={styles.stepConnector} />

            <View style={styles.step}>
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>3</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>Find it here</Text>
                <Text style={styles.stepHint}>Saved answers appear on this page for quick access</Text>
              </View>
            </View>
          </View>
        </View>
      ) : filteredAnswers.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="search-outline" size={36} color={Colors.textFaint} />
          </View>
          <Text style={styles.emptyTitle}>No results</Text>
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
            const confidenceStyle = getConfidenceStyle(item.confidence || 'low');
            const tradeColor = getTradeColor(item.trade || '');
            const isExpanded = expandedId === item.id;

            return (
              <TouchableOpacity
                style={styles.answerCard}
                activeOpacity={0.6}
                onPress={() => setExpandedId(isExpanded ? null : item.id)}
              >
                {/* Top row: trade badge + date + confidence + delete */}
                <View style={styles.answerTop}>
                  <View style={styles.answerTopLeft}>
                    <View style={[styles.answerTradeBadge, { backgroundColor: tradeColor + '12' }]}>
                      <Text style={[styles.answerTradeText, { color: tradeColor }]}>{item.trade}</Text>
                    </View>
                    <Text style={styles.answerDate}>{formatDate(item.savedAt)}</Text>
                  </View>
                  <View style={styles.answerTopRight}>
                    {item.confidence && (
                      <View style={styles.confidenceRow}>
                        <View style={[styles.confidenceDot, { backgroundColor: confidenceStyle.color }]} />
                        <Text style={styles.confidenceText}>
                          {confidenceStyle.label}
                        </Text>
                      </View>
                    )}
                    <TouchableOpacity
                      onPress={() => handleDelete(item)}
                      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                      style={styles.deleteBtn}
                    >
                      <Ionicons name="trash-outline" size={15} color={Colors.textMuted} />
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Question */}
                <Text style={styles.answerQuestion} numberOfLines={isExpanded ? undefined : 2}>
                  {item.question}
                </Text>

                {/* Answer preview/full */}
                <View style={[styles.answerBody, isExpanded && styles.answerBodyExpanded]}>
                  <Text style={styles.answerPreview} numberOfLines={isExpanded ? undefined : 3}>
                    {item.answer}
                  </Text>
                </View>

                {/* Source */}
                {item.source && (
                  <View style={styles.sourceRow}>
                    <Ionicons name="document-text-outline" size={11} color={Colors.textMuted} />
                    <Text style={styles.sourceText}>{item.source}</Text>
                  </View>
                )}

                {/* Expand hint */}
                {!isExpanded && item.answer.length > 150 && (
                  <View style={styles.readMoreRow}>
                    <Text style={styles.readMore}>Tap to read more</Text>
                    <Ionicons name="chevron-down" size={14} color={Colors.accent} />
                  </View>
                )}

                {/* Collapsed indicator */}
                {isExpanded && item.answer.length > 150 && (
                  <View style={styles.readMoreRow}>
                    <Text style={styles.readMore}>Tap to collapse</Text>
                    <Ionicons name="chevron-up" size={14} color={Colors.accent} />
                  </View>
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
    backgroundColor: Colors.backgroundWarm,
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
  headerRight: {
    width: 44,
    alignItems: 'center',
  },
  countBadge: {
    backgroundColor: Colors.accent,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: Radius.md,
  },
  countText: {
    color: '#FFF',
    fontSize: FontSize.xs,
    fontWeight: '700',
  },

  // Search
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
    ...Shadow.subtle,
  },
  searchInput: {
    flex: 1,
    fontSize: FontSize.base,
    color: Colors.textDark,
    paddingVertical: 0,
    letterSpacing: -0.2,
  },

  // Empty
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
    marginBottom: Spacing.xl,
  },

  // Steps card
  stepsCard: {
    backgroundColor: Colors.card,
    borderRadius: Radius.lg,
    padding: 20,
    width: '100%',
    ...Shadow.subtle,
  },
  step: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 14,
  },
  stepNumber: {
    width: 28,
    height: 28,
    borderRadius: Radius.lg,
    backgroundColor: Colors.textDark,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 1,
  },
  stepNumberText: {
    fontSize: FontSize.sm,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  stepContent: {
    flex: 1,
    paddingTop: 2,
  },
  stepTitle: {
    fontSize: FontSize.base,
    fontWeight: '600',
    color: Colors.textDark,
    letterSpacing: -0.2,
    marginBottom: 2,
  },
  stepHint: {
    fontSize: FontSize.sm,
    color: Colors.textMuted,
    lineHeight: 18,
  },
  stepConnector: {
    width: 1,
    height: 12,
    backgroundColor: Colors.borderWarm,
    marginLeft: 14,
    marginVertical: Spacing.xs,
  },

  // List
  listContent: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.lg,
    gap: 10,
  },
  answerCard: {
    backgroundColor: Colors.card,
    borderRadius: Radius.lg,
    padding: Spacing.base,
    ...Shadow.medium,
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
    gap: Spacing.sm,
  },
  answerTopRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  answerTradeBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.sm,
  },
  answerTradeText: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  answerDate: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
  },
  answerQuestion: {
    fontSize: FontSize.base,
    fontWeight: '600',
    color: Colors.textDark,
    marginBottom: 6,
    lineHeight: 21,
    letterSpacing: -0.2,
  },
  answerBody: {
    paddingLeft: 0,
  },
  answerBodyExpanded: {
    backgroundColor: 'rgba(0,0,0,0.015)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginHorizontal: -4,
  },
  answerPreview: {
    fontSize: FontSize.sm,
    color: Colors.textMuted,
    lineHeight: 20,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
    gap: Spacing.xs,
    paddingTop: Spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.borderWarm,
  },
  sourceText: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    fontStyle: 'italic',
    flex: 1,
  },
  readMoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    marginTop: Spacing.sm,
    justifyContent: 'center',
  },
  readMore: {
    fontSize: FontSize.xs,
    color: Colors.accent,
    fontWeight: '600',
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
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    fontWeight: '600',
  },
  deleteBtn: {
    width: 32,
    height: 32,
    borderRadius: Radius.lg,
    backgroundColor: Colors.backgroundWarm,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
