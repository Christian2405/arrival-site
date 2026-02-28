/**
 * Usage store — tracks query and document usage against tier limits.
 * Fetches from GET /api/usage and provides display helpers.
 */

import { create } from 'zustand';
import { usageAPI } from '../services/api';
import { supabase } from '../services/supabase';

interface UsageState {
  // Data from server
  plan: string;
  queriesToday: number;
  queryLimit: number;   // -1 = unlimited
  documentsCount: number;
  documentLimit: number; // -1 = unlimited
  jobMode: boolean;

  // Loading / error
  isLoaded: boolean;
  lastFetchedAt: number;

  // Actions
  fetchUsage: () => Promise<void>;
  incrementQueryCount: () => void;
  clear: () => void;
}

const DEBOUNCE_MS = 10_000; // Don't re-fetch within 10 seconds

export const useUsageStore = create<UsageState>((set, get) => ({
  plan: 'free',
  queriesToday: 0,
  queryLimit: 10,
  documentsCount: 0,
  documentLimit: 0,
  jobMode: false,
  isLoaded: false,
  lastFetchedAt: 0,

  fetchUsage: async () => {
    // Debounce — skip if fetched recently
    const now = Date.now();
    if (now - get().lastFetchedAt < DEBOUNCE_MS) return;

    // Skip if not authenticated — avoids 401 on cold launch before auth completes
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
    } catch {
      return;
    }

    try {
      const data = await usageAPI.getUsage();
      set({
        plan: data.plan,
        queriesToday: data.queries_today,
        queryLimit: data.query_limit,
        documentsCount: data.documents_count,
        documentLimit: data.document_limit,
        jobMode: data.job_mode,
        isLoaded: true,
        lastFetchedAt: now,
      });
    } catch (error) {
      console.log('[usageStore] Failed to fetch usage:', error);
      // Don't clear existing data on error — keep stale values
    }
  },

  incrementQueryCount: () => {
    set((state) => ({ queriesToday: state.queriesToday + 1 }));
  },

  clear: () => {
    set({
      plan: 'free',
      queriesToday: 0,
      queryLimit: 10,
      documentsCount: 0,
      documentLimit: 0,
      jobMode: false,
      isLoaded: false,
      lastFetchedAt: 0,
    });
  },
}));

// --- Helpers (read from store snapshot, no hooks needed) ---

export function isQueryLimitReached(): boolean {
  const { queryLimit, queriesToday } = useUsageStore.getState();
  if (queryLimit === -1) return false; // unlimited
  return queriesToday >= queryLimit;
}

export function isDocumentLimitReached(): boolean {
  const { documentLimit, documentsCount } = useUsageStore.getState();
  if (documentLimit === -1) return false; // unlimited
  return documentsCount >= documentLimit;
}

export function queryDisplayText(): string {
  const { queryLimit, queriesToday } = useUsageStore.getState();
  if (queryLimit === -1) return 'Unlimited';
  return `${queriesToday}/${queryLimit} today`;
}

export function documentDisplayText(): string {
  const { documentLimit, documentsCount } = useUsageStore.getState();
  if (documentLimit === -1) return 'Unlimited';
  return `${documentsCount}/${documentLimit}`;
}
