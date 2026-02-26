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

  const plan = subscription?.plan;
  const tierLimits = getTierLimits(plan || '');
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
    if (fileType?.includes('pdf')) return 'document-outline';
    if (fileType?.includes('image')) return 'image-outline';
    return 'book-outline';
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color="#2A2622" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Manuals</Text>
        <View style={styles.headerRight}>
          {manualDocs.length > 0 && (
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{manualDocs.length}</Text>
            </View>
          )}
        </View>
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
          <Ionicons name="search" size={16} color="#A09A93" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search manuals & guides..."
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
      {loading && !refreshing ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" color="#2A2622" />
        </View>
      ) : filteredDocs.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconWrap}>
            <Ionicons name="book-outline" size={40} color="#C7C2BC" />
          </View>
          <Text style={styles.emptyTitle}>
            {searchQuery ? 'No Results' : viewMode === 'team' ? 'No Team Manuals' : 'No Manuals Yet'}
          </Text>
          <Text style={styles.emptySubtitle}>
            {searchQuery
              ? 'Try a different search term.'
              : 'Upload equipment manuals and service\nguides on the Arrival website to\nreference them here.'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredDocs}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#2A2622" />
          }
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.manualCard} onPress={() => openDocument(item)} activeOpacity={0.6}>
              <View style={styles.manualIcon}>
                <Ionicons name={getDocIcon(item.file_type)} size={20} color="#2A2622" />
              </View>
              <View style={styles.manualInfo}>
                <Text style={styles.manualTitle} numberOfLines={1}>{item.file_name}</Text>
                <View style={styles.manualMeta}>
                  <View style={styles.categoryBadge}>
                    <Text style={styles.categoryText}>{categoryLabel(item.category)}</Text>
                  </View>
                  <Text style={styles.metaText}>{formatFileSize(item.file_size)}</Text>
                  <Text style={styles.metaDot}>&middot;</Text>
                  <Text style={styles.metaText}>{formatDate(item.created_at)}</Text>
                </View>
                {item.team_id && (
                  <View style={styles.teamTag}>
                    <Ionicons name="people-outline" size={11} color="#A09A93" />
                    <Text style={styles.teamTagText}>Team</Text>
                  </View>
                )}
              </View>
              <Ionicons name="chevron-forward" size={16} color="#C7C2BC" />
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

  // Toggle
  toggleContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  toggleBar: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#2A2622',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.12,
    shadowRadius: 3,
    elevation: 2,
  },
  toggleText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#A09A93',
  },
  toggleTextActive: {
    color: '#FFF',
  },

  // Search
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
  },

  // List
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    paddingTop: 4,
    gap: 8,
  },
  manualCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 2,
  },
  manualIcon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: '#F3F0EB',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  manualInfo: {
    flex: 1,
  },
  manualTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#2A2622',
    marginBottom: 5,
    letterSpacing: -0.2,
  },
  manualMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  categoryBadge: {
    backgroundColor: '#F3F0EB',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 5,
  },
  categoryText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#A09A93',
    letterSpacing: 0.2,
  },
  metaText: {
    fontSize: 12,
    color: '#C7C2BC',
  },
  metaDot: {
    fontSize: 12,
    color: '#C7C2BC',
  },
  teamTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 5,
  },
  teamTagText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#A09A93',
  },
});
