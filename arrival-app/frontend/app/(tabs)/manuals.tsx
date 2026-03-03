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
  ScrollView,
  SectionList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { useAuthStore } from '../../store/authStore';
import { useDocumentsStore, Document, MANUAL_CATEGORIES } from '../../store/documentsStore';
import { getTierLimits } from '../../constants/Tiers';

type ViewMode = 'my' | 'team';

// Category display config
const CATEGORY_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  equipment_manuals: { icon: 'build-outline', label: 'Equipment Manuals', color: Colors.accent },
  manufacturer_manuals: { icon: 'business-outline', label: 'Manufacturer Manuals', color: '#4A90D9' },
  spec_sheets: { icon: 'document-text-outline', label: 'Spec Sheets', color: '#5B9BD5' },
  equipment_spec_sheets: { icon: 'document-text-outline', label: 'Equipment Specs', color: '#5B9BD5' },
  training_materials: { icon: 'school-outline', label: 'Training Materials', color: '#8E6BBF' },
  company_sops: { icon: 'clipboard-outline', label: 'Company SOPs', color: '#E8A84C' },
  sops: { icon: 'clipboard-outline', label: 'SOPs', color: '#E8A84C' },
  building_plans: { icon: 'map-outline', label: 'Building Plans', color: '#34C759' },
  parts_lists: { icon: 'list-outline', label: 'Parts Lists', color: '#FF9500' },
  maintenance_guides: { icon: 'construct-outline', label: 'Maintenance Guides', color: '#FF6B6B' },
  wiring_diagrams: { icon: 'flash-outline', label: 'Wiring Diagrams', color: '#E8A84C' },
};

const getCategoryConfig = (category: string) =>
  CATEGORY_CONFIG[category] || { icon: 'document-outline', label: category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()), color: Colors.textMuted };

export default function ManualsScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('my');
  const [refreshing, setRefreshing] = useState(false);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

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
  const manualDocs = sourceList.filter((d) => MANUAL_CATEGORIES.includes(d.category));

  // Apply search
  const filteredDocs = manualDocs.filter((d) =>
    d.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group by category
  const groupedDocs = filteredDocs.reduce<Record<string, Document[]>>((acc, doc) => {
    const cat = doc.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(doc);
    return acc;
  }, {});

  const sections = Object.entries(groupedDocs)
    .map(([category, data]) => ({
      title: category,
      data,
    }))
    .sort((a, b) => {
      const configA = getCategoryConfig(a.title);
      const configB = getCategoryConfig(b.title);
      return configA.label.localeCompare(configB.label);
    });

  const toggleCategory = (category: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

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

  const getDocIcon = (fileType: string): keyof typeof Ionicons.glyphMap => {
    if (fileType?.includes('pdf')) return 'document-outline';
    if (fileType?.includes('image')) return 'image-outline';
    return 'book-outline';
  };

  // Category stats for the header area
  const categoryStats = Object.entries(groupedDocs).map(([cat, docs]) => ({
    category: cat,
    count: docs.length,
    ...getCategoryConfig(cat),
  }));

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color={Colors.textDark} />
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
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.toggleScroll}>
            <TouchableOpacity
              style={[styles.toggleChip, viewMode === 'my' && styles.toggleChipActive]}
              onPress={() => setViewMode('my')}
            >
              <Ionicons name="folder-outline" size={14} color={viewMode === 'my' ? '#FFF' : Colors.textMuted} />
              <Text style={[styles.toggleChipText, viewMode === 'my' && styles.toggleChipTextActive]}>
                My Docs
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.toggleChip, viewMode === 'team' && styles.toggleChipActive]}
              onPress={() => setViewMode('team')}
            >
              <Ionicons name="people-outline" size={14} color={viewMode === 'team' ? '#FFF' : Colors.textMuted} />
              <Text style={[styles.toggleChipText, viewMode === 'team' && styles.toggleChipTextActive]}>
                Team Docs
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      )}

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={16} color={Colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search manuals & guides..."
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

      {/* Content */}
      {loading && !refreshing ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" color={Colors.textDark} />
        </View>
      ) : filteredDocs.length === 0 ? (
        <ScrollView contentContainerStyle={styles.emptyScrollContent}>
          <View style={styles.emptyState}>
            <View style={styles.emptyIconWrap}>
              <Ionicons name="book-outline" size={40} color={Colors.textFaint} />
            </View>
            <Text style={styles.emptyTitle}>
              {searchQuery ? 'No Results' : viewMode === 'team' ? 'No Team Manuals' : 'No Manuals Yet'}
            </Text>
            <Text style={styles.emptySubtitle}>
              {searchQuery
                ? 'Try a different search term.'
                : 'Upload equipment manuals and service guides\non the Arrival website to reference them here.'}
            </Text>
          </View>

          {/* Category guide — show what types can be uploaded */}
          {!searchQuery && viewMode === 'my' && (
            <View style={styles.categoryGuide}>
              <Text style={styles.categoryGuideTitle}>Supported document types</Text>
              <View style={styles.categoryGrid}>
                {[
                  { icon: 'build-outline', label: 'Equipment\nManuals', color: Colors.accent },
                  { icon: 'document-text-outline', label: 'Spec\nSheets', color: '#5B9BD5' },
                  { icon: 'flash-outline', label: 'Wiring\nDiagrams', color: '#E8A84C' },
                  { icon: 'construct-outline', label: 'Maintenance\nGuides', color: '#FF6B6B' },
                  { icon: 'clipboard-outline', label: 'Company\nSOPs', color: '#E8A84C' },
                  { icon: 'list-outline', label: 'Parts\nLists', color: '#FF9500' },
                ].map((item, i) => (
                  <View key={i} style={styles.categoryGuideItem}>
                    <View style={[styles.categoryGuideIcon, { backgroundColor: item.color + '12' }]}>
                      <Ionicons name={item.icon as any} size={20} color={item.color} />
                    </View>
                    <Text style={styles.categoryGuideLabel}>{item.label}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}
        </ScrollView>
      ) : (
        <SectionList
          sections={sections}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          stickySectionHeadersEnabled={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.textDark} />
          }
          renderSectionHeader={({ section }) => {
            const config = getCategoryConfig(section.title);
            const isCollapsed = collapsedCategories.has(section.title);
            return (
              <TouchableOpacity
                style={styles.sectionHeader}
                onPress={() => toggleCategory(section.title)}
                activeOpacity={0.7}
              >
                <View style={[styles.sectionIconWrap, { backgroundColor: config.color + '12' }]}>
                  <Ionicons name={config.icon as any} size={16} color={config.color} />
                </View>
                <Text style={styles.sectionTitle}>{config.label}</Text>
                <View style={styles.sectionCountBadge}>
                  <Text style={styles.sectionCountText}>{section.data.length}</Text>
                </View>
                <Ionicons
                  name={isCollapsed ? 'chevron-forward' : 'chevron-down'}
                  size={16}
                  color={Colors.textFaint}
                />
              </TouchableOpacity>
            );
          }}
          renderItem={({ item, section }) => {
            if (collapsedCategories.has(section.title)) return null;
            return (
              <TouchableOpacity style={styles.manualCard} onPress={() => openDocument(item)} activeOpacity={0.6}>
                <View style={styles.manualIcon}>
                  <Ionicons name={getDocIcon(item.file_type)} size={20} color={Colors.textDark} />
                </View>
                <View style={styles.manualInfo}>
                  <Text style={styles.manualTitle} numberOfLines={1}>{item.file_name}</Text>
                  <View style={styles.manualMeta}>
                    <Text style={styles.metaText}>{formatFileSize(item.file_size)}</Text>
                    <Text style={styles.metaDot}>&middot;</Text>
                    <Text style={styles.metaText}>{formatDate(item.created_at)}</Text>
                  </View>
                  {item.team_id && (
                    <View style={styles.teamTag}>
                      <Ionicons name="people-outline" size={11} color={Colors.textMuted} />
                      <Text style={styles.teamTagText}>Team</Text>
                    </View>
                  )}
                </View>
                <Ionicons name="chevron-forward" size={16} color={Colors.textFaint} />
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
    color: Colors.textDark,
    letterSpacing: -0.5,
    marginLeft: 4,
  },
  headerRight: {
    width: 44,
    alignItems: 'center',
  },
  countBadge: {
    backgroundColor: Colors.accent,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  countText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
  },

  // Toggle chips
  toggleContainer: {
    paddingBottom: 8,
  },
  toggleScroll: {
    paddingHorizontal: 16,
    gap: 8,
  },
  toggleChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.borderWarm,
  },
  toggleChipActive: {
    backgroundColor: Colors.textDark,
    borderColor: Colors.textDark,
  },
  toggleChipText: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textMuted,
  },
  toggleChipTextActive: {
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
    backgroundColor: Colors.card,
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
    color: Colors.textDark,
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
  emptyScrollContent: {
    flexGrow: 1,
    paddingBottom: 40,
  },
  emptyState: {
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    paddingTop: 60,
    paddingBottom: 32,
  },
  emptyIconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.card,
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
    color: Colors.textDark,
    marginBottom: 8,
    letterSpacing: -0.3,
  },
  emptySubtitle: {
    fontSize: 15,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 22,
  },

  // Category guide (empty state)
  categoryGuide: {
    marginHorizontal: 16,
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 1,
  },
  categoryGuideTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    marginBottom: 16,
    textAlign: 'center',
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 12,
  },
  categoryGuideItem: {
    width: '30%',
    alignItems: 'center',
  },
  categoryGuideIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 6,
  },
  categoryGuideLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 15,
  },

  // Section headers
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 4,
    marginTop: 8,
    marginBottom: 4,
    gap: 8,
  },
  sectionIconWrap: {
    width: 28,
    height: 28,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sectionTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: Colors.textDark,
    letterSpacing: -0.2,
  },
  sectionCountBadge: {
    backgroundColor: Colors.backgroundWarm,
    paddingHorizontal: 7,
    paddingVertical: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.borderWarm,
  },
  sectionCountText: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textMuted,
  },

  // List
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    paddingTop: 4,
  },
  manualCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 14,
    marginBottom: 6,
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
    backgroundColor: Colors.backgroundWarm,
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
    color: Colors.textDark,
    marginBottom: 5,
    letterSpacing: -0.2,
  },
  manualMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  metaText: {
    fontSize: 12,
    color: Colors.textFaint,
  },
  metaDot: {
    fontSize: 12,
    color: Colors.textFaint,
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
    color: Colors.textMuted,
  },
});
