-- ============================================
-- TextArrival Initial Schema Migration
-- Paste this into Supabase SQL Editor and run
-- ============================================

-- Enable UUID generation
create extension if not exists "pgcrypto";

-- ============================================
-- TABLES
-- ============================================

-- Users
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  first_name text,
  last_name text,
  primary_trade text check (primary_trade in ('hvac', 'plumbing', 'electrical', 'general_construction', 'appliance_repair', 'other')),
  experience_level text check (experience_level in ('apprentice', '1_3_years', '3_10_years', '10_plus_years', 'diy_homeowner')),
  account_type text not null default 'free' check (account_type in ('free', 'pro', 'business', 'enterprise')),
  preferred_units text not null default 'imperial',
  explanation_depth text not null default 'standard',
  voice_output boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Teams
create table public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  primary_trade text,
  address text,
  employee_count integer,
  owner_id uuid not null references public.users(id) on delete cascade,
  max_seats integer not null default 10,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Team Members
create table public.team_members (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  user_id uuid references public.users(id) on delete cascade,
  email text not null,
  role text not null check (role in ('admin', 'manager', 'technician')),
  status text not null check (status in ('active', 'invited', 'deactivated')),
  invited_at timestamptz,
  joined_at timestamptz,
  unique (team_id, email)
);

-- Documents
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  uploaded_by uuid not null references public.users(id) on delete cascade,
  team_id uuid references public.teams(id) on delete cascade,
  file_name text not null,
  file_type text not null,
  file_size bigint not null,
  storage_path text not null,
  category text not null check (category in (
    'equipment_manuals', 'manufacturer_manuals', 'wiring_diagrams', 'parts_lists',
    'technical_bulletins', 'warranty_docs', 'spec_sheets', 'equipment_spec_sheets',
    'building_plans', 'engineering_reports', 'site_surveys', 'permits',
    'inspection_reports', 'project_specs', 'scope_of_work', 'material_specs',
    'local_codes', 'safety_data_sheets', 'osha_docs', 'inspection_checklists',
    'sops', 'company_sops', 'safety_protocols', 'diagnostic_workflows',
    'installation_checklists', 'training_materials', 'maintenance_guides',
    'client_docs', 'service_reports', 'site_requirements', 'photo', 'video'
  )),
  project_tag text,
  notes text,
  status text not null default 'ready' check (status in ('uploading', 'processing', 'ready', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Subscriptions
create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  team_id uuid references public.teams(id) on delete cascade,
  plan text not null default 'free' check (plan in ('free', 'pro', 'business', 'enterprise')),
  status text not null default 'active' check (status in ('active', 'cancelled', 'past_due', 'trial_expired')),
  trial_ends_at timestamptz,
  current_period_start timestamptz,
  current_period_end timestamptz,
  stripe_customer_id text,
  stripe_subscription_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ============================================
-- INDEXES
-- ============================================

create index idx_team_members_team_id on public.team_members(team_id);
create index idx_team_members_user_id on public.team_members(user_id);
create index idx_documents_uploaded_by on public.documents(uploaded_by);
create index idx_documents_team_id on public.documents(team_id);
create index idx_subscriptions_user_id on public.subscriptions(user_id);
create index idx_subscriptions_stripe_customer_id on public.subscriptions(stripe_customer_id);

-- ============================================
-- AUTO-UPDATE updated_at TRIGGER
-- ============================================

create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger set_updated_at_users
  before update on public.users
  for each row execute function public.handle_updated_at();

create trigger set_updated_at_teams
  before update on public.teams
  for each row execute function public.handle_updated_at();

create trigger set_updated_at_team_members
  before update on public.team_members
  for each row execute function public.handle_updated_at();

create trigger set_updated_at_documents
  before update on public.documents
  for each row execute function public.handle_updated_at();

create trigger set_updated_at_subscriptions
  before update on public.subscriptions
  for each row execute function public.handle_updated_at();

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

alter table public.users enable row level security;
alter table public.teams enable row level security;
alter table public.team_members enable row level security;
alter table public.documents enable row level security;
alter table public.subscriptions enable row level security;

-- -------------------------
-- USERS policies
-- -------------------------

-- Users can read their own row
create policy "users_select_own"
  on public.users for select
  using (auth.uid() = id);

-- Users can update their own row
create policy "users_update_own"
  on public.users for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Users can insert their own row (for sign-up)
create policy "users_insert_own"
  on public.users for insert
  with check (auth.uid() = id);

-- -------------------------
-- TEAMS policies
-- -------------------------

-- Team members can read their team
create policy "teams_select_member"
  on public.teams for select
  using (
    exists (
      select 1 from public.team_members
      where team_members.team_id = teams.id
        and team_members.user_id = auth.uid()
        and team_members.status = 'active'
    )
  );

-- Team owner can insert teams
create policy "teams_insert_owner"
  on public.teams for insert
  with check (auth.uid() = owner_id);

-- Team owner can update their team
create policy "teams_update_owner"
  on public.teams for update
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

-- -------------------------
-- TEAM_MEMBERS policies
-- -------------------------

-- Active team members can read their own team's membership
create policy "team_members_select_team"
  on public.team_members for select
  using (
    exists (
      select 1 from public.team_members as my_membership
      where my_membership.team_id = team_members.team_id
        and my_membership.user_id = auth.uid()
        and my_membership.status = 'active'
    )
  );

-- Only team admins can insert team members
create policy "team_members_insert_admin"
  on public.team_members for insert
  with check (
    exists (
      select 1 from public.team_members as admin_check
      where admin_check.team_id = team_members.team_id
        and admin_check.user_id = auth.uid()
        and admin_check.role = 'admin'
        and admin_check.status = 'active'
    )
  );

-- Only team admins can update team members
create policy "team_members_update_admin"
  on public.team_members for update
  using (
    exists (
      select 1 from public.team_members as admin_check
      where admin_check.team_id = team_members.team_id
        and admin_check.user_id = auth.uid()
        and admin_check.role = 'admin'
        and admin_check.status = 'active'
    )
  );

-- Only team admins can delete team members
create policy "team_members_delete_admin"
  on public.team_members for delete
  using (
    exists (
      select 1 from public.team_members as admin_check
      where admin_check.team_id = team_members.team_id
        and admin_check.user_id = auth.uid()
        and admin_check.role = 'admin'
        and admin_check.status = 'active'
    )
  );

-- -------------------------
-- DOCUMENTS policies
-- -------------------------

-- Personal docs: only uploader can read
-- Team docs: any active team member can read
create policy "documents_select"
  on public.documents for select
  using (
    case
      when team_id is null then uploaded_by = auth.uid()
      else exists (
        select 1 from public.team_members
        where team_members.team_id = documents.team_id
          and team_members.user_id = auth.uid()
          and team_members.status = 'active'
      )
    end
  );

-- Anyone can insert their own personal documents (team_id is null)
create policy "documents_insert_personal"
  on public.documents for insert
  with check (
    uploaded_by = auth.uid()
    and team_id is null
  );

-- Team admins and managers can insert team documents
create policy "documents_insert_team"
  on public.documents for insert
  with check (
    uploaded_by = auth.uid()
    and team_id is not null
    and exists (
      select 1 from public.team_members
      where team_members.team_id = documents.team_id
        and team_members.user_id = auth.uid()
        and team_members.role in ('admin', 'manager')
        and team_members.status = 'active'
    )
  );

-- Uploader can update their own personal documents
create policy "documents_update_personal"
  on public.documents for update
  using (uploaded_by = auth.uid() and team_id is null)
  with check (uploaded_by = auth.uid() and team_id is null);

-- Team admins and managers can update team documents
create policy "documents_update_team"
  on public.documents for update
  using (
    team_id is not null
    and exists (
      select 1 from public.team_members
      where team_members.team_id = documents.team_id
        and team_members.user_id = auth.uid()
        and team_members.role in ('admin', 'manager')
        and team_members.status = 'active'
    )
  );

-- Uploader can delete their own personal documents
create policy "documents_delete_personal"
  on public.documents for delete
  using (uploaded_by = auth.uid() and team_id is null);

-- Team admins and managers can delete team documents
create policy "documents_delete_team"
  on public.documents for delete
  using (
    team_id is not null
    and exists (
      select 1 from public.team_members
      where team_members.team_id = documents.team_id
        and team_members.user_id = auth.uid()
        and team_members.role in ('admin', 'manager')
        and team_members.status = 'active'
    )
  );

-- -------------------------
-- SUBSCRIPTIONS policies
-- -------------------------

-- Users can read their own subscriptions
create policy "subscriptions_select_own"
  on public.subscriptions for select
  using (auth.uid() = user_id);

-- Users can insert their own subscriptions
create policy "subscriptions_insert_own"
  on public.subscriptions for insert
  with check (auth.uid() = user_id);

-- Users can update their own subscriptions
create policy "subscriptions_update_own"
  on public.subscriptions for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
