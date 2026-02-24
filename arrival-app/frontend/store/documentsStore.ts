/**
 * Documents store — fetches and caches documents from Supabase.
 * Queries the documents table directly (same as website).
 */

import { create } from 'zustand';
import { supabase } from '../services/supabase';

export interface Document {
  id: string;
  uploaded_by: string;
  team_id: string | null;
  file_name: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  category: string;
  status: string;
  created_at: string;
}

// Category groupings (matching website's dashboard-business.js)
export const CODE_CATEGORIES = [
  'diagnostic_workflows',
  'safety_protocols',
];

export const MANUAL_CATEGORIES = [
  'equipment_manuals',
  'spec_sheets',
  'training_materials',
  'company_sops',
  'building_plans',
  'parts_lists',
];

export const MEDIA_CATEGORIES = ['photo', 'video'];

interface DocumentsState {
  personalDocs: Document[];
  teamDocs: Document[];
  loading: boolean;
  error: string | null;

  fetchDocuments: (userId: string, teamId?: string | null) => Promise<void>;
  getSignedUrl: (storagePath: string) => Promise<string | null>;
  clear: () => void;
}

export const useDocumentsStore = create<DocumentsState>((set) => ({
  personalDocs: [],
  teamDocs: [],
  loading: false,
  error: null,

  fetchDocuments: async (userId: string, teamId?: string | null) => {
    set({ loading: true, error: null });

    try {
      // Fetch personal docs (non-media)
      const { data: personal, error: personalErr } = await supabase
        .from('documents')
        .select('*')
        .eq('uploaded_by', userId)
        .is('team_id', null)
        .not('category', 'in', '("photo","video")')
        .order('created_at', { ascending: false });

      if (personalErr) {
        console.error('Fetch personal docs error:', personalErr);
      }

      // Fetch team docs if user has a team
      let teamData: Document[] = [];
      if (teamId) {
        const { data: team, error: teamErr } = await supabase
          .from('documents')
          .select('*')
          .eq('team_id', teamId)
          .not('category', 'in', '("photo","video")')
          .order('created_at', { ascending: false });

        if (teamErr) {
          console.error('Fetch team docs error:', teamErr);
        }
        teamData = (team || []) as Document[];
      }

      set({
        personalDocs: (personal || []) as Document[],
        teamDocs: teamData,
        loading: false,
      });
    } catch (error: any) {
      console.error('Fetch documents error:', error);
      set({ loading: false, error: error.message });
    }
  },

  getSignedUrl: async (storagePath: string) => {
    try {
      const { data, error } = await supabase.storage
        .from('documents')
        .createSignedUrl(storagePath, 3600); // 1 hour

      if (error) {
        console.error('Signed URL error:', error);
        return null;
      }
      return data.signedUrl;
    } catch (error) {
      console.error('Signed URL error:', error);
      return null;
    }
  },

  clear: () => {
    set({ personalDocs: [], teamDocs: [], loading: false, error: null });
  },
}));
