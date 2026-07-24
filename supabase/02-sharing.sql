-- ═══════════════════════════════════════════════════════════════════════════
-- 02 — Sharing features (M2): global exercise catalog + plan sharing
-- STATUS: to be applied — paste this whole file into SQL Editor and Run.
--
-- global_exercises — the admin-curated catalog. Read-only for signed-in
--   users; writes happen via the dashboard (service role bypasses RLS) until
--   M3 adds the in-app suggestion/approval flow. Ids are the same stable
--   slugs library.json ships, which is what lets a user's untouched seeded
--   exercises match catalog entries across every install.
--
-- shared_plans — in-app plan sharing, addressed BY EMAIL so a plan can be
--   sent before the recipient has ever logged in. The payload is exactly the
--   plan-export-file shape; the receiving app runs it through the same
--   untrusted-input normalization the file import uses. Rows are kept after
--   claiming (claimed_at set) rather than deleted.
--   Note, accepted at family scale: any signed-in user may send to any
--   email — there is no contact list or block mechanism at ≤10 known users.
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists public.global_exercises (
  id         text primary key,
  data       jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.global_exercises enable row level security;

create policy "catalog: signed-in read" on public.global_exercises
  for select using (auth.role() = 'authenticated');
-- no insert/update/delete policies: dashboard-only curation until M3

grant select on table public.global_exercises to authenticated;

create trigger global_exercises_touch before update on public.global_exercises
  for each row execute function public.touch_updated_at();


create table if not exists public.shared_plans (
  id         uuid primary key default gen_random_uuid(),
  from_user  uuid not null references auth.users (id) on delete cascade,
  from_email text not null,
  to_email   text not null,
  payload    jsonb not null,
  created_at timestamptz not null default now(),
  claimed_at timestamptz
);

alter table public.shared_plans enable row level security;

-- Sender: may create shares only from their own identity (both id and the
-- display email are pinned to the JWT — no spoofing another sender).
create policy "shares: send as self" on public.shared_plans
  for insert with check (
    auth.uid() = from_user
    and lower(from_email) = lower(auth.jwt()->>'email')
  );
-- Receiver: sees and claims only what is addressed to their email. There is
-- deliberately NO sender-select policy in M2 (no sent-history UI yet) — it
-- keeps the receiver's inbox query trivially clean.
create policy "shares: receive own" on public.shared_plans
  for select using (lower(to_email) = lower(auth.jwt()->>'email'));
create policy "shares: claim own" on public.shared_plans
  for update using (lower(to_email) = lower(auth.jwt()->>'email'))
  with check (lower(to_email) = lower(auth.jwt()->>'email'));

grant select, insert, update on table public.shared_plans to authenticated;


-- ── Catalog seed: the 44 curated starters (generated from library.json) ──
-- Idempotent: re-running refreshes data in place.
insert into public.global_exercises (id, data) values
  ('narrow-stance-sumo-deadlift', '{"id": "narrow-stance-sumo-deadlift", "name": "Narrow stance sumo deadlift", "type": "strength", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "hinge", "accessoryMuscles": ["hamstrings", "glutes", "quads"]}'::jsonb),
  ('wide-stance-sumo-deadlift', '{"id": "wide-stance-sumo-deadlift", "name": "Wide stance sumo deadlift", "type": "strength", "compound": true, "regime": "weighted", "mainMuscle": "glutes", "movementPattern": "hinge", "accessoryMuscles": ["hamstrings", "quads"]}'::jsonb),
  ('bent-over-barbell-row', '{"id": "bent-over-barbell-row", "name": "Bent-over barbell row", "type": "strength", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "row", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('zercher-squat', '{"id": "zercher-squat", "name": "Zercher squat", "type": "strength", "compound": true, "regime": "weighted", "mainMuscle": "quads", "movementPattern": "squat", "accessoryMuscles": ["glutes", "back"]}'::jsonb),
  ('bench-press', '{"id": "bench-press", "name": "Bench press", "type": "strength", "compound": true, "regime": "weighted", "mainMuscle": "chest", "movementPattern": "press", "accessoryMuscles": ["triceps", "shoulders"]}'::jsonb),
  ('assisted-pull-up-gravitron', '{"id": "assisted-pull-up-gravitron", "name": "Assisted pull-up (Gravitron)", "type": "strength", "compound": true, "regime": "assisted", "mainMuscle": "back", "movementPattern": "pulldown", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('dip-gravitron', '{"id": "dip-gravitron", "name": "Dip (Gravitron, leaning)", "type": "strength", "compound": true, "regime": "assisted", "mainMuscle": "chest", "movementPattern": "press", "accessoryMuscles": ["triceps", "shoulders"]}'::jsonb),
  ('dip-gravitron-upright', '{"id": "dip-gravitron-upright", "name": "Dip (Gravitron, upright)", "type": "strength", "compound": true, "regime": "assisted", "mainMuscle": "triceps", "movementPattern": "dip", "accessoryMuscles": ["chest", "shoulders"]}'::jsonb),
  ('kettlebell-swing', '{"id": "kettlebell-swing", "name": "Kettlebell swing", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "glutes", "movementPattern": "hinge", "accessoryMuscles": ["hamstrings", "back"]}'::jsonb),
  ('incline-press-machine', '{"id": "incline-press-machine", "name": "Incline press machine", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "chest", "movementPattern": "press", "accessoryMuscles": ["shoulders", "triceps"]}'::jsonb),
  ('seated-cable-row', '{"id": "seated-cable-row", "name": "Seated cable row", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "row", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('wide-grip-lat-pulldown', '{"id": "wide-grip-lat-pulldown", "name": "Wide grip lat pulldown", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "pulldown", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('wide-grip-neutral-pulldown', '{"id": "wide-grip-neutral-pulldown", "name": "Wide grip neutral pulldown", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "pulldown", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('chest-supported-high-row', '{"id": "chest-supported-high-row", "name": "Chest supported high row", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "row", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('machine-low-row', '{"id": "machine-low-row", "name": "Machine low row", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "back", "movementPattern": "row", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('v-squat-front-facing', '{"id": "v-squat-front-facing", "name": "V-squat (front-facing)", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "quads", "movementPattern": "squat", "accessoryMuscles": ["glutes"]}'::jsonb),
  ('bulgarian-split-squat', '{"id": "bulgarian-split-squat", "name": "Bulgarian split squat", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "quads", "movementPattern": "lunge", "accessoryMuscles": ["glutes", "hamstrings"]}'::jsonb),
  ('hip-thrust', '{"id": "hip-thrust", "name": "Hip thrust", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "glutes", "movementPattern": "hip_thrust", "accessoryMuscles": ["hamstrings"]}'::jsonb),
  ('cable-low-to-high-fly', '{"id": "cable-low-to-high-fly", "name": "Cable low-to-high fly", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "chest", "movementPattern": "fly", "accessoryMuscles": ["shoulders"]}'::jsonb),
  ('pec-deck-fly', '{"id": "pec-deck-fly", "name": "Pec deck fly", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "chest", "movementPattern": "fly", "accessoryMuscles": []}'::jsonb),
  ('stiff-leg-deadlift', '{"id": "stiff-leg-deadlift", "name": "Stiff-leg deadlift", "type": "hypertrophy", "compound": true, "regime": "weighted", "mainMuscle": "hamstrings", "movementPattern": "hinge", "accessoryMuscles": ["glutes", "back"]}'::jsonb),
  ('overhead-cable-triceps', '{"id": "overhead-cable-triceps", "name": "Overhead cable triceps", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "triceps", "movementPattern": "extension", "accessoryMuscles": []}'::jsonb),
  ('machine-triceps', '{"id": "machine-triceps", "name": "Machine triceps", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "triceps", "movementPattern": "extension", "accessoryMuscles": []}'::jsonb),
  ('cable-triceps-kickback', '{"id": "cable-triceps-kickback", "name": "Cable triceps kickback", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "triceps", "movementPattern": "extension", "accessoryMuscles": []}'::jsonb),
  ('rope-cable-triceps-extension', '{"id": "rope-cable-triceps-extension", "name": "Rope cable triceps extension", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "triceps", "movementPattern": "pushdown", "accessoryMuscles": []}'::jsonb),
  ('single-arm-preacher-curl', '{"id": "single-arm-preacher-curl", "name": "Single arm preacher curl", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "biceps", "movementPattern": "curl", "accessoryMuscles": []}'::jsonb),
  ('incline-deficit-curl', '{"id": "incline-deficit-curl", "name": "Incline deficit curl", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "biceps", "movementPattern": "curl", "accessoryMuscles": []}'::jsonb),
  ('hammer-curl', '{"id": "hammer-curl", "name": "Hammer curl", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "biceps", "movementPattern": "curl", "accessoryMuscles": ["forearms"]}'::jsonb),
  ('reverse-grip-ez-bar-curl', '{"id": "reverse-grip-ez-bar-curl", "name": "Reverse grip EZ bar curl", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "biceps", "movementPattern": "curl", "accessoryMuscles": ["forearms"]}'::jsonb),
  ('hammer-curl-lateral-raise', '{"id": "hammer-curl-lateral-raise", "name": "Hammer curl lateral raise", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "shoulders", "movementPattern": "raise", "accessoryMuscles": ["biceps"]}'::jsonb),
  ('lateral-raise', '{"id": "lateral-raise", "name": "Lateral raise", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "shoulders", "movementPattern": "raise", "accessoryMuscles": []}'::jsonb),
  ('crucifix-swing', '{"id": "crucifix-swing", "name": "Crucifix swing", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "shoulders", "movementPattern": "raise", "accessoryMuscles": []}'::jsonb),
  ('face-pull', '{"id": "face-pull", "name": "Face pull", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "shoulders", "movementPattern": "rear_delt", "accessoryMuscles": ["back"]}'::jsonb),
  ('seated-leg-curl', '{"id": "seated-leg-curl", "name": "Seated leg curl", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "hamstrings", "movementPattern": "curl", "accessoryMuscles": []}'::jsonb),
  ('leg-extension', '{"id": "leg-extension", "name": "Leg extension", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "quads", "movementPattern": "extension", "accessoryMuscles": []}'::jsonb),
  ('standing-leg-curl', '{"id": "standing-leg-curl", "name": "Standing leg curl", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "hamstrings", "movementPattern": "curl", "accessoryMuscles": []}'::jsonb),
  ('single-leg-45-back-extension', '{"id": "single-leg-45-back-extension", "name": "Single leg 45� back extension", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "back", "movementPattern": "extension", "accessoryMuscles": ["hamstrings", "glutes"]}'::jsonb),
  ('seated-machine-shoulder-press', '{"id": "seated-machine-shoulder-press", "name": "Seated machine shoulder press", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "shoulders", "movementPattern": "press", "accessoryMuscles": ["triceps"]}'::jsonb),
  ('hip-abduction-machine', '{"id": "hip-abduction-machine", "name": "Hip abduction machine", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "glutes", "movementPattern": "abduction", "accessoryMuscles": []}'::jsonb),
  ('hip-adduction-machine', '{"id": "hip-adduction-machine", "name": "Hip adduction machine", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "adductors", "movementPattern": "adduction", "accessoryMuscles": []}'::jsonb),
  ('calf-raise', '{"id": "calf-raise", "name": "Calf raise", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "calves", "movementPattern": "raise", "accessoryMuscles": []}'::jsonb),
  ('seated-calf-raise', '{"id": "seated-calf-raise", "name": "Seated calf raise", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "calves", "movementPattern": "raise", "accessoryMuscles": []}'::jsonb),
  ('scapular-pull-up', '{"id": "scapular-pull-up", "name": "Scapular pull-up", "type": "hypertrophy", "compound": true, "regime": "bodyweight", "mainMuscle": "back", "movementPattern": "other", "accessoryMuscles": []}'::jsonb),
  ('strict-halos', '{"id": "strict-halos", "name": "Strict halos", "type": "hypertrophy", "compound": false, "regime": "weighted", "mainMuscle": "shoulders", "movementPattern": "other", "accessoryMuscles": []}'::jsonb)
on conflict (id) do update set data = excluded.data, updated_at = now();
