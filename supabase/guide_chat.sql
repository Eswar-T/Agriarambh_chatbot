-- Chat history for the GreenPlot guide.
-- Run once in the Supabase SQL editor.
-- The Python server uses the service role key, which bypasses these policies.
-- The anon key cannot read or write these tables.

create table if not exists public.guide_sessions (
  id uuid primary key,
  language text not null default 'kn' check (language in ('kn', 'en')),
  created_at timestamptz not null default now()
);

create table if not exists public.guide_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.guide_sessions (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  text_kn text,
  text_en text,
  sources jsonb not null default '[]'::jsonb,
  suggestions_kn jsonb not null default '[]'::jsonb,
  suggestions_en jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists guide_messages_session_idx
  on public.guide_messages (session_id, created_at);

alter table public.guide_sessions enable row level security;
alter table public.guide_messages enable row level security;
