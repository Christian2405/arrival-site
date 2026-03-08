-- Migration 005: Add DELETE RLS policy for documents table
-- Run this in Supabase SQL Editor
--
-- The documents table likely has INSERT and SELECT policies but no DELETE policy.
-- Without this, users can't delete their own documents through the API.

-- Enable RLS if not already enabled
ALTER TABLE IF EXISTS documents ENABLE ROW LEVEL SECURITY;

-- Allow users to delete their own documents
CREATE POLICY IF NOT EXISTS "Users can delete own documents"
  ON documents
  FOR DELETE
  USING (auth.uid() = uploaded_by);

-- Also ensure UPDATE policy exists (for edit functionality)
CREATE POLICY IF NOT EXISTS "Users can update own documents"
  ON documents
  FOR UPDATE
  USING (auth.uid() = uploaded_by)
  WITH CHECK (auth.uid() = uploaded_by);
