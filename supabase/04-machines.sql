-- 04 — machines collection (E2, 2026-07-29)
--
-- The app now syncs a SIXTH per-user collection: `machines` (equipment
-- instances — the specific apparatus an exercise is done on, with per-gym
-- availability and settings notes; see the vault's "Design - Movement-first
-- Library & Equipment").
--
-- user_blobs was created (01-user-blobs.sql) with a CHECK constraint admitting
-- only the original five collection names, so the machines row is rejected
-- until this widens it. The app tolerates that: it pushes the machines blob
-- in its own upsert and swallows the failure, so the five core collections
-- keep syncing normally — machines simply stay device-local (and re-attempt
-- on every push) until this migration is applied. Run once in the SQL
-- Editor; idempotent.

alter table public.user_blobs
  drop constraint if exists user_blobs_collection_check;

alter table public.user_blobs
  add constraint user_blobs_collection_check
  check (collection in ('sessions','library','plans','weights','gyms','machines'));
