-- ═══════════════════════════════════════════════════════════════════════════
-- 01 — Per-user blob storage (M1 foundation)
-- STATUS: applied to the live project on 2026-07-23 (in two parts, via chat).
-- Kept in-repo as the canonical record and for standing up a fresh project.
-- Safe to re-run only on a FRESH database: CREATE POLICY has no IF NOT
-- EXISTS, so duplicates error (harmlessly — nothing is dropped or changed).
--
-- One row per user per collection; content carries the exact same
-- { schema, <items>, tombstones, lastModified } payload a Gist file holds.
-- The app's client-side merge (per-item LWW + tombstones + schema guard)
-- is the conflict layer — this table is deliberately a dumb store.
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists public.user_blobs (
  user_id    uuid not null references auth.users (id) on delete cascade,
  collection text not null check (collection in ('sessions','library','plans','weights','gyms')),
  content    jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, collection)
);

alter table public.user_blobs enable row level security;

create policy "own rows: select" on public.user_blobs
  for select using (auth.uid() = user_id);
create policy "own rows: insert" on public.user_blobs
  for insert with check (auth.uid() = user_id);
create policy "own rows: update" on public.user_blobs
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
-- Deliberately NO delete policy: RLS default-denies what has no policy, and
-- deletions live INSIDE content as tombstones — rows never disappear.

-- This project generation grants NOTHING to anon/authenticated by default
-- (locked-down defaults that ship with publishable-key projects) — RLS
-- policies alone don't open access; the role needs table-level grants too.
-- anon deliberately gets nothing at all.
grant select, insert, update on table public.user_blobs to authenticated;

-- Keep updated_at honest on every write. search_path pinned so the
-- Advisor's function linter stays green.
create or replace function public.touch_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end $$;

create trigger user_blobs_touch before update on public.user_blobs
  for each row execute function public.touch_updated_at();
