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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, Radius, FontSize, IconSize, Shadow } from '../../constants/Colors';
import { useAuthStore } from '../../store/authStore';
import { useDocumentsStore, Document, CODE_CATEGORIES } from '../../store/documentsStore';
import { getTierLimits } from '../../constants/Tiers';
import { errorCodesAPI, ErrorCodeBrand, ErrorCode } from '../../services/api';

type ViewMode = 'built-in' | 'my-docs' | 'team';

export default function CodesScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('built-in');
  const [refreshing, setRefreshing] = useState(false);

  // Built-in error codes state
  const [brands, setBrands] = useState<ErrorCodeBrand[]>([]);
  const [totalCodes, setTotalCodes] = useState(0);
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [brandCodes, setBrandCodes] = useState<ErrorCode[]>([]);
  const [loadingCodes, setLoadingCodes] = useState(false);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const { profile, subscription, teamMembership } = useAuthStore();
  const { personalDocs, teamDocs, loading, fetchDocuments, getSignedUrl } = useDocumentsStore();

  const plan = subscription?.plan;
  const tierLimits = getTierLimits(plan || '');
  const userId = profile?.id;
  const teamId = teamMembership?.team_id;

  // Fetch brands on mount
  useEffect(() => {
    loadBrands();
    if (userId) {
      fetchDocuments(userId, teamId);
    }
  }, [userId, teamId]);

  const loadBrands = async () => {
    try {
      const data = await errorCodesAPI.getBrands();
      setBrands(data.brands);
      setTotalCodes(data.total_codes);
    } catch (e) {
      console.log('Failed to load brands:', e);
    }
  };

  const loadBrandCodes = async (brandId: string) => {
    if (selectedBrand === brandId) {
      setSelectedBrand(null);
      setBrandCodes([]);
      return;
    }
    setLoadingCodes(true);
    setSelectedBrand(brandId);
    try {
      const data = await errorCodesAPI.getBrandCodes(brandId);
      setBrandCodes(data.codes);
    } catch (e) {
      console.log('Failed to load codes:', e);
      setBrandCodes([]);
    }
    setLoadingCodes(false);
  };

  // Pull-to-refresh
  const onRefresh = useCallback(async () => {
    if (!userId) return;
    setRefreshing(true);
    await Promise.all([loadBrands(), fetchDocuments(userId, teamId)]);
    setRefreshing(false);
  }, [userId, teamId]);

  // Filter docs by CODE_CATEGORIES
  const sourceList = viewMode === 'team' ? teamDocs : personalDocs;
  const codeDocs = sourceList.filter((d) => CODE_CATEGORIES.includes(d.category));
  const filteredDocs = codeDocs.filter((d) =>
    d.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter built-in codes by search
  const filteredBrandCodes = searchQuery
    ? brandCodes.filter(
        (c) =>
          c.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
          c.meaning.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : brandCodes;

  const openDocument = async (doc: Document) => {
    try {
      const url = await getSignedUrl(doc.storage_path);
      if (url) {
        await Linking.openURL(url);
      } else {
        Alert.alert('Error', 'Could not open document.');
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

  // Brand icon mapping
  const getBrandIcon = (brandId: string): string => {
    const icons: Record<string, string> = {
      carrier: 'snow-outline',
      goodman: 'snow-outline',
      lennox: 'snow-outline',
      trane: 'snow-outline',
      rheem: 'flame-outline',
      rinnai: 'water-outline',
      ao_smith: 'water-outline',
      bradford_white: 'water-outline',
      daikin: 'snow-outline',
      mitsubishi: 'snow-outline',
      fujitsu: 'snow-outline',
    };
    return icons[brandId] || 'build-outline';
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={IconSize.lg} color={Colors.textDark} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Error Codes</Text>
        <View style={styles.headerRight}>
          {totalCodes > 0 && (
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{totalCodes}</Text>
            </View>
          )}
        </View>
      </View>

      {/* View mode toggle */}
      <View style={styles.toggleContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.toggleScroll}>
          <TouchableOpacity
            style={[styles.toggleChip, viewMode === 'built-in' && styles.toggleChipActive]}
            onPress={() => setViewMode('built-in')}
          >
            <Ionicons name="flash" size={14} color={viewMode === 'built-in' ? '#FFF' : Colors.textMuted} />
            <Text style={[styles.toggleChipText, viewMode === 'built-in' && styles.toggleChipTextActive]}>
              Built-in Codes
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.toggleChip, viewMode === 'my-docs' && styles.toggleChipActive]}
            onPress={() => setViewMode('my-docs')}
          >
            <Ionicons name="folder-outline" size={14} color={viewMode === 'my-docs' ? '#FFF' : Colors.textMuted} />
            <Text style={[styles.toggleChipText, viewMode === 'my-docs' && styles.toggleChipTextActive]}>
              My Docs
            </Text>
          </TouchableOpacity>
          {tierLimits.teamDocs && teamId && (
            <TouchableOpacity
              style={[styles.toggleChip, viewMode === 'team' && styles.toggleChipActive]}
              onPress={() => setViewMode('team')}
            >
              <Ionicons name="people-outline" size={14} color={viewMode === 'team' ? '#FFF' : Colors.textMuted} />
              <Text style={[styles.toggleChipText, viewMode === 'team' && styles.toggleChipTextActive]}>
                Team
              </Text>
            </TouchableOpacity>
          )}
        </ScrollView>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={16} color={Colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder={viewMode === 'built-in' ? 'Search error codes...' : 'Search documents...'}
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

      {/* BUILT-IN CODES VIEW */}
      {viewMode === 'built-in' && (
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.textDark} />}
        >
          {/* Brand grid */}
          <View style={styles.brandGrid}>
            {brands.map((brand) => (
              <TouchableOpacity
                key={brand.id}
                style={[styles.brandCard, selectedBrand === brand.id && styles.brandCardActive]}
                onPress={() => loadBrandCodes(brand.id)}
                activeOpacity={0.7}
              >
                <Ionicons
                  name={getBrandIcon(brand.id) as any}
                  size={IconSize.md}
                  color={selectedBrand === brand.id ? '#FFF' : Colors.textMuted}
                  style={{ marginBottom: Spacing.sm }}
                />
                <Text style={[styles.brandName, selectedBrand === brand.id && styles.brandNameActive]}>{brand.name}</Text>
                <Text style={[styles.brandCount, selectedBrand === brand.id && styles.brandCountActive]}>
                  {brand.code_count} codes
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Selected brand codes */}
          {selectedBrand && (
            <View style={styles.codesSection}>
              {loadingCodes ? (
                <ActivityIndicator size="small" color={Colors.textDark} style={{ paddingVertical: 20 }} />
              ) : filteredBrandCodes.length === 0 ? (
                <Text style={styles.noCodesText}>
                  {searchQuery ? 'No codes match your search.' : 'No codes available.'}
                </Text>
              ) : (
                filteredBrandCodes.map((code) => {
                  const isExpanded = expandedCode === `${selectedBrand}_${code.code}`;
                  return (
                    <TouchableOpacity
                      key={code.code}
                      style={styles.codeItem}
                      onPress={() => setExpandedCode(isExpanded ? null : `${selectedBrand}_${code.code}`)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.codeHeader}>
                        <View style={styles.codeBadge}>
                          <Text style={styles.codeBadgeText}>{code.code}</Text>
                        </View>
                        <Text style={styles.codeMeaning} numberOfLines={isExpanded ? undefined : 1}>
                          {code.meaning}
                        </Text>
                        <Ionicons
                          name={isExpanded ? 'chevron-up' : 'chevron-down'}
                          size={16}
                          color={Colors.textFaint}
                        />
                      </View>

                      {isExpanded && (
                        <View style={styles.codeDetails}>
                          {code.causes.length > 0 && (
                            <View style={styles.codeDetailBlock}>
                              <Text style={styles.codeDetailLabel}>Common Causes</Text>
                              {code.causes.map((cause, i) => (
                                <View key={i} style={styles.causeRow}>
                                  <Text style={styles.causeNumber}>{i + 1}</Text>
                                  <Text style={styles.causeText}>{cause}</Text>
                                </View>
                              ))}
                            </View>
                          )}
                          {code.fix && (
                            <View style={styles.codeDetailBlock}>
                              <Text style={styles.codeDetailLabel}>First Step</Text>
                              <Text style={styles.fixText}>{code.fix}</Text>
                            </View>
                          )}
                          <TouchableOpacity
                            style={styles.askArrivalBtn}
                            onPress={() => {
                              const brandObj = brands.find(b => b.id === selectedBrand);
                              const query = `Tell me about ${brandObj?.name || 'this'} error code ${code.code}: ${code.meaning}`;
                              router.push({ pathname: '/(tabs)/home', params: { prefill: query } } as any);
                            }}
                          >
                            <Ionicons name="chatbubble-outline" size={14} color={Colors.accent} />
                            <Text style={styles.askArrivalText}>Ask Arrival about this code</Text>
                          </TouchableOpacity>
                        </View>
                      )}
                    </TouchableOpacity>
                  );
                })
              )}
            </View>
          )}
        </ScrollView>
      )}

      {/* DOCUMENTS VIEW */}
      {(viewMode === 'my-docs' || viewMode === 'team') && (
        loading && !refreshing ? (
          <View style={styles.loadingWrap}>
            <ActivityIndicator size="large" color={Colors.textDark} />
          </View>
        ) : filteredDocs.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={styles.emptyIconWrap}>
              <Ionicons name="document-text-outline" size={40} color={Colors.textFaint} />
            </View>
            <Text style={styles.emptyTitle}>
              {searchQuery ? 'No Results' : viewMode === 'team' ? 'No Team Codes' : 'No Uploaded Codes'}
            </Text>
            <Text style={styles.emptySubtitle}>
              {searchQuery
                ? 'Try a different search term.'
                : 'Upload diagnostic workflows and code\ndocuments on the Arrival website.'}
            </Text>
          </View>
        ) : (
          <FlatList
            data={filteredDocs}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.textDark} />}
            renderItem={({ item }) => (
              <TouchableOpacity style={styles.docCard} onPress={() => openDocument(item)} activeOpacity={0.6}>
                <View style={styles.docIcon}>
                  <Ionicons name="document-text" size={20} color={Colors.textDark} />
                </View>
                <View style={styles.docInfo}>
                  <Text style={styles.docTitle} numberOfLines={1}>{item.file_name}</Text>
                  <View style={styles.docMeta}>
                    <View style={styles.categoryBadge}>
                      <Text style={styles.categoryText}>{categoryLabel(item.category)}</Text>
                    </View>
                    <Text style={styles.metaText}>{formatFileSize(item.file_size)}</Text>
                    <Text style={styles.metaDot}>&middot;</Text>
                    <Text style={styles.metaText}>{formatDate(item.created_at)}</Text>
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={16} color={Colors.textFaint} />
              </TouchableOpacity>
            )}
          />
        )
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

  // Toggle chips
  toggleContainer: {
    paddingBottom: Spacing.sm,
  },
  toggleScroll: {
    paddingHorizontal: Spacing.base,
    gap: Spacing.sm,
  },
  toggleChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.borderWarm,
  },
  toggleChipActive: {
    backgroundColor: Colors.textDark,
    borderColor: Colors.textDark,
  },
  toggleChipText: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    color: Colors.textMuted,
  },
  toggleChipTextActive: {
    color: '#FFF',
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

  // Brand grid
  brandGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: Spacing.base,
  },
  brandCard: {
    width: '31%',
    backgroundColor: Colors.card,
    borderRadius: Radius.lg,
    padding: 14,
    alignItems: 'center',
    ...Shadow.subtle,
  },
  brandCardActive: {
    backgroundColor: Colors.textDark,
  },
  brandName: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textDark,
    textAlign: 'center',
    marginBottom: 2,
  },
  brandNameActive: {
    color: '#FFF',
  },
  brandCount: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
  },
  brandCountActive: {
    color: 'rgba(255,255,255,0.6)',
  },

  // Codes list
  codesSection: {
    gap: 6,
  },
  codeItem: {
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    overflow: 'hidden',
    ...Shadow.subtle,
  },
  codeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    gap: 10,
  },
  codeBadge: {
    backgroundColor: Colors.accent,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.sm,
    minWidth: 44,
    alignItems: 'center',
  },
  codeBadgeText: {
    fontSize: FontSize.xs,
    fontWeight: '800',
    color: '#FFF',
    letterSpacing: 0.3,
  },
  codeMeaning: {
    flex: 1,
    fontSize: FontSize.sm,
    fontWeight: '500',
    color: Colors.textDark,
    letterSpacing: -0.2,
  },
  codeDetails: {
    paddingHorizontal: 14,
    paddingBottom: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.borderWarm,
    paddingTop: Spacing.md,
    gap: Spacing.md,
  },
  codeDetailBlock: {
    gap: 6,
  },
  codeDetailLabel: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  causeRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    alignItems: 'flex-start',
  },
  causeNumber: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.accent,
    width: 16,
  },
  causeText: {
    flex: 1,
    fontSize: FontSize.sm,
    color: Colors.text,
    lineHeight: 20,
  },
  fixText: {
    fontSize: FontSize.sm,
    color: Colors.text,
    lineHeight: 20,
  },
  askArrivalBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
    backgroundColor: Colors.accentMuted,
    borderRadius: Radius.sm,
    alignSelf: 'flex-start',
  },
  askArrivalText: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    color: Colors.accent,
  },
  noCodesText: {
    fontSize: FontSize.sm,
    color: Colors.textMuted,
    textAlign: 'center',
    paddingVertical: 20,
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
  },

  // Document list
  listContent: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.lg,
    paddingTop: Spacing.xs,
    gap: Spacing.sm,
  },
  docCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: Radius.lg,
    padding: 14,
    ...Shadow.medium,
  },
  docIcon: {
    width: 42,
    height: 42,
    borderRadius: Radius.md,
    backgroundColor: Colors.backgroundWarm,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: Spacing.md,
  },
  docInfo: {
    flex: 1,
  },
  docTitle: {
    fontSize: FontSize.base,
    fontWeight: '600',
    color: Colors.textDark,
    marginBottom: 5,
    letterSpacing: -0.2,
  },
  docMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  categoryBadge: {
    backgroundColor: Colors.backgroundWarm,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: Radius.sm,
  },
  categoryText: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.2,
  },
  metaText: {
    fontSize: FontSize.xs,
    color: Colors.textFaint,
  },
  metaDot: {
    fontSize: FontSize.xs,
    color: Colors.textFaint,
  },
});
