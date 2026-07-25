# Gym Tracker

Personal workout-tracking PWA — strength & hypertrophy, progressive-overload suggestions, offline-first, cross-device sync. Single vanilla-JS file, no framework, no build step. UI in Portuguese (pt-BR).

**Live:** https://pbbabreu.github.io/gym-tracker/

## Features

- **Treino** — log workouts from reusable plans or free-form; warm-up sets auto-generated and scaled to today's suggested working weight (compound/isolation and weighted/assisted/bodyweight regimes each have their own ramp rules).
- **Progressive overload** — set rows suggest a genuine next-session target, not a replay of last time: an exercise "graduates" to more weight only when the full prescribed set count hit the top of the rep range at one working weight. Fatigue drop-offs don't graduate; multi-session stalls get a visible nudge.
- **Histórico** — past sessions with per-set detail, volume, and edit/delete.
- **Biblioteca** — fully personal exercise library (seeded with 44 starters from `library.json`), classified by muscle group + movement pattern, filterable and searchable.
- **Planos** — ordered exercise lists to start sessions from; shareable as self-contained JSON files (exercise definitions travel with the plan).
- **Peso** — bodyweight log; feeds real-load math for assisted (bodyweight − counterweight) and bodyweight exercises.
- **Sync & backup** — cross-device sync via a private GitHub Gist; manual JSON export/import; automatic daily local snapshots (last 7 days, restorable in-app).

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
- **Tests:** open `http://localhost:8742/tests/run-tests.html` — a self-contained regression suite (100+ checks) that loads the real app in an iframe and asserts against the shipped functions. Run it before every push. It wipes the origin's storage: local server only, never the live origin.
- Service-worker gotcha: if an edit doesn't seem to take effect, the SW may be serving cache — unregister it and hard-reload (the test runner does this automatically).
- Deploys are just pushes to `main` — GitHub Pages serves the repo root (~30s).

## License

[MIT](LICENSE)
