create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.tenants (
  id text primary key,
  name text not null,
  slug text not null unique,
  logo_url text,
  brand_colors jsonb not null default '{}'::jsonb,
  custom_domain text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.users (
  id text primary key,
  tenant_id text not null references public.tenants(id) on delete cascade,
  role text not null default 'member',
  email text not null,
  name text,
  avatar_url text,
  api_key text unique,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.credits (
  tenant_id text primary key references public.tenants(id) on delete cascade,
  balance integer not null default 0,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.credit_packs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  credits integer not null,
  price_cents integer not null,
  stripe_price_id text not null unique,
  active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references public.tenants(id) on delete cascade,
  user_id text references public.users(id) on delete set null,
  title text not null default 'Untitled video',
  status text not null default 'draft',
  workflow text not null,
  config jsonb not null default '{}'::jsonb,
  output_video_url text,
  thumbnail_url text,
  duration_seconds double precision,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  tenant_id text not null references public.tenants(id) on delete cascade,
  status text not null default 'queued',
  worker_id text,
  locked_at timestamptz,
  attempt_count integer not null default 0,
  progress integer not null default 0,
  error_message text,
  script_text text,
  scenes jsonb,
  pipeline_state jsonb not null default '{}'::jsonb,
  voice_url text,
  media_urls jsonb,
  output_video_url text,
  credits_charged integer not null default 0,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.credit_transactions (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references public.tenants(id) on delete cascade,
  type text not null,
  amount integer not null,
  description text not null,
  job_id uuid references public.jobs(id) on delete set null,
  stripe_payment_id text,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references public.tenants(id) on delete cascade,
  project_id uuid references public.projects(id) on delete set null,
  type text not null,
  url text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.voice_catalog (
  id text primary key,
  name text not null,
  category text not null,
  preview_url text,
  labels jsonb not null default '{}'::jsonb,
  cached_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.music_tracks (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  url text not null,
  duration_seconds double precision,
  genre text,
  mood text,
  active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.media_presets (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  description text,
  style_prompt text,
  active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.caption_presets (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  font_family text,
  font_size integer,
  color text,
  background_color text,
  animation text,
  position text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_users_tenant_id on public.users (tenant_id);
create index if not exists idx_projects_tenant_id on public.projects (tenant_id);
create index if not exists idx_jobs_tenant_id on public.jobs (tenant_id);
create index if not exists idx_jobs_project_id on public.jobs (project_id);
create index if not exists idx_credit_transactions_tenant_id on public.credit_transactions (tenant_id);
create index if not exists idx_assets_tenant_id on public.assets (tenant_id);

drop trigger if exists trg_tenants_set_updated_at on public.tenants;
create trigger trg_tenants_set_updated_at
before update on public.tenants
for each row
execute function public.set_updated_at();

drop trigger if exists trg_users_set_updated_at on public.users;
create trigger trg_users_set_updated_at
before update on public.users
for each row
execute function public.set_updated_at();

drop trigger if exists trg_credits_set_updated_at on public.credits;
create trigger trg_credits_set_updated_at
before update on public.credits
for each row
execute function public.set_updated_at();

drop trigger if exists trg_credit_packs_set_updated_at on public.credit_packs;
create trigger trg_credit_packs_set_updated_at
before update on public.credit_packs
for each row
execute function public.set_updated_at();

drop trigger if exists trg_projects_set_updated_at on public.projects;
create trigger trg_projects_set_updated_at
before update on public.projects
for each row
execute function public.set_updated_at();

drop trigger if exists trg_jobs_set_updated_at on public.jobs;
create trigger trg_jobs_set_updated_at
before update on public.jobs
for each row
execute function public.set_updated_at();

drop trigger if exists trg_music_tracks_set_updated_at on public.music_tracks;
create trigger trg_music_tracks_set_updated_at
before update on public.music_tracks
for each row
execute function public.set_updated_at();

drop trigger if exists trg_media_presets_set_updated_at on public.media_presets;
create trigger trg_media_presets_set_updated_at
before update on public.media_presets
for each row
execute function public.set_updated_at();

drop trigger if exists trg_caption_presets_set_updated_at on public.caption_presets;
create trigger trg_caption_presets_set_updated_at
before update on public.caption_presets
for each row
execute function public.set_updated_at();

grant usage on schema public to service_role;
grant all privileges on all tables in schema public to service_role;
grant all privileges on all sequences in schema public to service_role;
alter default privileges in schema public grant all on tables to service_role;
alter default privileges in schema public grant all on sequences to service_role;
