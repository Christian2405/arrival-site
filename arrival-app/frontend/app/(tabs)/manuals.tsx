import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert,
  Linking,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { useAuthStore } from '../../store/authStore';
import { useDocumentsStore, Document, MANUAL_CATEGORIES } from '../../store/documentsStore';
import { getTierLimits } from '../../constants/Tiers';

type ViewMode = 'my' | 'team';

export default function ManualsScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('my');
  const [refreshing, setRefreshing] = useState(false);

  const { profile, subscription, teamMembership } = useAuthStore();
  const { personalDocs, teamDocs, loading, fetchDocuments, getSignedUrl } = useDocumentsStore();

  const plan = subscription?.plan || 'free';
  const tierLimits = getTierLimits(plan);
  const userId = profile?.id;
  const teamId = teamMembership?.team_id;

  // Fetch on mount
  useEffect(() => {
    if (userId) {
      fetchDocuments(userId, teamId);
    }
  }, [userId, teamId]);

  // Pull-to-refresh
  const onRefresh = useCallback(async () => {
    if (!userId) return;
    setRefreshing(true);
    await fetchDocuments(userId, teamId);
    setRefreshing(false);
  }, [userId, teamId]);

  // Filter docs by MANUAL_CATEGORIES
  const sourceList = viewMode === 'team' ? teamDocs : personalDocs;
  const manualDocs = sourceList.filter((d) =>
    MANUAL_CATEGORIES.includes(d.category)
  );

  // Apply search
  const filteredDocs = manualDocs.filter((d) =>
    d.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const openDocument = async (doc: Document) => {
    try {
      const url = await getSignedUrl(doc.storage_path);
      if (url) {
        await Linking.openURL(url);
      } else {
        Alert.alert('Error', 'Could not open document. Please try again.');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to open document.');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const categoryLabel = (cat: string) =>
    cat.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const getDocIcon = (fileType: string): keyof typeof Ionicons.glyphMap => {
    if (fileType?.includes('pdf')) return 'document';
    if (fileType?.includes('image')) return 'image';
    return 'book';
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Manuals</Text>
        <View style={styles.backBtn} />
      </View>

      {/* Team toggle (business only) */}
      {tierLimits.teamDocs && teamId && (
        <View style={styles.toggleContainer}>
          <View style={styles.toggleBar}>
            <TouchableOpacity
              style={[styles.toggleBtn, viewMode === 'my' && styles.toggleBtnActive]}
              onPress={() => setViewMode('my')}
            >
              <Text style={[styles.toggleText, viewMode === 'my' && styles.toggleTextActive]}>
                My Docs
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.toggleBtn, viewMode === 'team' && styles.toggleBtnActive]}
              onPress={() => setViewMode('team')}
            >
              <Text style={[styles.toggleText, viewMode === 'team' && styles.toggleTextActive]}>
                Team Docs
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={18} color={Colors.textSecondary} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search manuals & guides..."
            placeholderTextColor={Colors.textLight}
            value={searchQuery}
            onChangeText={setSearchQuery}
            returnKeyType="search"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={18} color={Colors.textLight} />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Content */}
      {loading && !refreshing ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" color={Colors.accent} />
        </View>
      ) : filteredDocs.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="book-outline" size={48} color={Colors.textLight} />
          </View>
          <Text style={styles.emptyTitle}>
            {searchQuery ? 'No Results' : viewMode === 'team' ? 'No Team Manuals' : 'No Manuals Yet'}
          </Text>
          <Text style={styles.emptySubtitle}>
            {searchQuery
              ? 'Try a different search term.'
              : 'Upload equipment manuals and service guides on the Arrival website to reference them here.'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredDocs}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.accent} />
          }
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.manualCard} onPress={() => openDocument(item)}>
              <View style={styles.manualIcon}>
                <Ionicons name={getDocIcon(item.file_type)} size={24} color={Colors.accent} />
              </View>
              <View style={styles.manualInfo}>
                <Text style={styles.manualTitle} numberOfLines={1}>{item.file_name}</Text>
                <View style={styles.manualMeta}>
                  <View style={styles.categoryBadge}>
                    <Text style={styles.categoryText}>{categoryLabel(item.category)}</Text>
                  </View>
                  <Text style={styles.metaText}>{formatFileSize(item.file_size)}</Text>
                </View>
                <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
                {item.team_id && (
                  <View style={styles.teamTag}>
                    <Ionicons name="people" size={10} color="#4A90D9" />
                    <Text style={styles.teamTagText}>Team</Text>
                  </View>
                )}
              </View>
              <Ionicons name="chevron-forward" size={18} color={Colors.textLight} />
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.text,
    letterSpacing: -0.3,
  },

  // Toggle
  toggleContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  toggleBar: {
    flexDirection: 'row',
    backgroundColor: '#F2F2F7',
    borderRadius: 10,
    padding: 3,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  toggleBtnActive: {
    backgroundColor: Colors.accent,
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 2,
  },
  toggleText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  toggleTextActive: {
    color: '#FFF',
  },

  // Search
  searchContainer: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 12,
    paddingHorizontal: 14,
    height: 44,
    borderWidth: 1,
    borderColor: Colors.borderLight,
    gap: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: Colors.text,
    paddingVertical: 0,
    letterSpacing: -0.2,
  },

  // Loading
  loadingWrap: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Empty
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    paddingBottom: 60,
  },
  emptyIconWrap: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 8,
    letterSpacing: -0.3,
  },
  emptySubtitle: {
    fontSize: 15,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 28,
  },

  // List
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  manualCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: Colors.borderLight,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  manualIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: Colors.accentMuted,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  manualInfo: {
    flex: 1,
  },
  manualTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: 4,
    letterSpacing: -0.2,
  },
  manualMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  categoryBadge: {
    backgroundColor: Colors.accentMuted,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  categoryText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.accent,
  },
  metaText: {
    fontSize: 12,
    color: Colors.textLight,
  },
  dateText: {
    fontSize: 12,
    color: Colors.textLight,
    marginTop: 2,
  },
  teamTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  teamTagText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#4A90D9',
  },
});
