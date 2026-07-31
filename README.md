# Gym Tracker

Personal workout-tracking PWA — strength & hypertrophy, progressive-overload suggestions, offline-first, cross-device sync. Single vanilla-JS file, no framework, no build step. UI in Portuguese (pt-BR).

**Live:** https://pbbabreu.github.io/gym-tracker/

## Features

- **Treino** — log workouts from reusable plans or free-form; adding an exercise opens a **movement-first picker** (browse movements grouped by muscle — "Supino reto", "Puxada" — then that movement's variants grouped by equipment class, with bilingual search reaching both movements and exact variant names; new variants created inside a movement inherit its classification and a chosen equipment class). Warm-up sets are auto-generated and scaled to today's suggested working weight (a first-ever exercise asks for an estimate and prefills warm-ups *and* work loads from it; barbell warm-ups never drop below the empty bar). Strength/hypertrophy is a per-session tracking mode — each exercise defaults to the mode of its *last* session, not a stored label. Exercise blocks collapse into a focus mode: an exercise-level ✓ (or checking every set) folds the finished block and opens the next one. The in-progress session survives closing the tab, the Back button, or the OS killing the page — it's continuously mirrored locally and restored on the next open; tapping a prefilled reps/kg field clears it for fresh typing (leaving without typing restores it), and the browser Back button closes open dialogs instead of leaving the app.
- **Equipment & machines** — every session block carries a 🔧 chip naming the *specific* apparatus: machines/cables are **calibrated** (suggestions prefer that same machine's history — numbers from one unit never masquerade as another's; a save-time nudge asks about unidentified machines, never blocking), while free-weight equipment is **descriptive** (the bar tells you what you did the movement with; progression stays one story). Machines remember settings notes ("banco 7, pegada aberta"), belong to gyms with one-tap reuse elsewhere, and auto-attach from last time. Barbell blocks add a ⚖ setup: bar weight + how loads are typed — **Total, Por lado, or Anilhas** — with a computed Total column, "barra vazia" at zero, and storage always as the grand total so history and charts never change units.
- **Rest timer** — checking a set starts a countdown sized by the transition (warm-up→warm-up / warm-up→work / work→work), with presets and custom values resolving per exercise → per plan → per exercise default → device defaults. Beep on expiry; vibration too on Chromium-based Android browsers (Chrome, Edge, Samsung Internet — Firefox removed the Vibration API in 2024, and iOS never had it).
- **Progressive overload** — set rows suggest a genuine next-session target, not a replay of last time: an exercise "graduates" to more weight only when the full prescribed set count hit the top of the rep range at one working weight (strength 3×3–5, hypertrophy 1×6–10/12). Fatigue drop-offs don't graduate; multi-session stalls get a visible nudge.
- **Gym profiles** — mark which gyms have which exercises; starting a plan at a gym flags what's unavailable and suggests equivalent swaps (same muscle + movement pattern). A ⇄ on every session block swaps any exercise for an equivalent, gym-aware when a gym is selected.
- **Plans ↔ sessions** — plans carry per-exercise rest timings; a session started from a plan can drift freely, and saving offers to update the plan, fork a new one, or keep the plan untouched. Any saved session (or a free workout, at save time) can be turned into a plan.
- **Sharing** — send a plan to another user by e-mail in-app (appears under *Planos recebidos*), or as a self-contained JSON file; pull curated exercises from the shared catalog (Biblioteca → ⟳ Catálogo).
- **Histórico** — past sessions with per-set detail, volume, gym tag, and edit/delete/extract-to-plan.
- **Biblioteca** — fully personal exercise library (seeded from a curated, PT-BR-primary starter set with English names and aliases kept searchable), classified by muscle group + movement pattern + **movement** (the family a variant belongs to), and with a detail view carrying cues, common errors and known machines. Duplicate entries are prevented at creation (matching Portuguese *and* English names) and, if any exist, can be reviewed and merged — duplicates split an exercise's history, which quietly degrades suggestions and progress charts.
- **Peso** — bodyweight log; feeds real-load math for assisted (bodyweight − counterweight) and bodyweight exercises.
- **Sync & backup** — invite-only account sync (magic link / code); manual JSON export/import; automatic daily local snapshots (last 7 days, restorable in-app); a factory reset that wipes everything and rebuilds the library clean across devices; legacy GitHub Gist driver for pre-account installs.

## Using it

Just open the live URL in your browser — that's the supported way to use it, on every platform. It works offline after the first load (the service worker keeps the offline copy current with your last online visit), and a home-screen shortcut that opens a browser tab is a perfectly good "app icon".

> Installing as a standalone PWA also works on Android, but is deliberately not the recommended path for now: on iOS, login e-mail links open in Safari — *outside* a standalone app — which strands the session. Browser usage sidesteps that entirely. (A type-in login code that fixes standalone iOS exists in the app and activates once custom SMTP is configured for the project.)

## Cross-device sync setup

**Account sync (default):** open **Histórico → ⬆ Backup & Sync**, enter your e-mail, and tap the magic link that arrives — no password exists. (The app also has a 6-digit-code field, which activates once the project's login e-mails carry a code — pending custom SMTP setup.) Your data syncs to a private per-user store (Supabase, guarded by row-level security); logging in on another device pulls and merges your history before anything is ever pushed, so a fresh phone can never overwrite it. Accounts are invite-only: the instance owner adds new users.

**Onboarding a new user:** the owner invites their e-mail (Supabase dashboard → Authentication → Users → Invite). The person opens the app URL in their browser, goes to Backup & Sync, enters that e-mail, and taps the login link they receive. From there they can be sent workout plans in-app (✉ on any plan → appears under *Planos recebidos*) and pull curated exercises from the shared catalog (Biblioteca → ⟳ Catálogo).

**Legacy Gist sync:** earlier installs synced via a private GitHub Gist (fine-grained PAT with gists-only scope). That driver still works and remains available on devices that configured it, until they migrate to an account. New installs never see it.

Data notes:

- All workout data lives in your browser's localStorage and your own private sync store — nowhere else. Login/config state is stored locally only and is **never** included in exports.
- Merging is per-item last-writer-wins with deletion tombstones, so devices can be used independently — even offline — and converge safely.
- The app additionally keeps rolling daily local snapshots (last 7 days), restorable from the Backup & Sync modal.

## Development

No build step — `index.html` is the app.

```
python -m http.server 8742        # from the repo root
```

- Develop against `http://localhost:8742/` — `file://` breaks reloads and service workers.
- **Tests:** open `http://localhost:8742/tests/run-tests.html` — a self-contained regression suite (430+ checks) that loads the real app in an iframe and asserts against the shipped functions. Run it before every push. It wipes the origin's storage: local server only, never the live origin.
- Service-worker gotcha: if an edit doesn't seem to take effect, the SW may be serving cache — unregister it and hard-reload (the test runner does this automatically).
- `supabase/` holds the canonical database SQL (01 = per-user storage, 02 = sharing tables, 03 = generated catalog seed, 04 = machines-collection migration); `.github/workflows/keepalive.yml` pings the project weekly so the free tier never pauses.
- **The exercise catalog is not authored in this repo.** `library.json`, `supabase/03-catalog-seed.sql` and `SEED_CLASSIFICATION` are build output of `python tools/build-library.py`, which reads curated exercise notes from a separate Obsidian vault. Run `python tools/build-library.py --check` before pushing — it validates the catalog and fails if the committed artifacts drift from their source.
- Deploys are just pushes to `main` — GitHub Pages serves the repo root (~30s).

## License

[MIT](LICENSE)
