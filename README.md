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

## Install as an app (PWA)

Open the live URL, then:

- **Android (Chrome):** menu ⋮ → *Add to Home screen* / *Install app*.
- **iOS (Safari):** Share → *Add to Home Screen*.

Works offline after the first load — the service worker keeps the offline copy current with the last online visit.

## Cross-device sync setup

Sync uses a **private GitHub Gist** you own. One-time setup:

1. Create a fine-grained personal access token at github.com → Settings → Developer settings → **Fine-grained tokens**, with **only the Gists permission (read/write)**. Note the expiry you choose — when it lapses, sync fails quietly (the app shows a banner after repeated failures) until you paste a fresh token.
2. In the app: **Histórico → ⬆ Backup & Sync** → paste the token, leave Gist ID blank → *Salvar e sincronizar*. The app creates the Gist and fills in its ID.
3. On another device: paste the **same token and Gist ID** → *Salvar e sincronizar*. The app pulls and merges the existing remote data before its first push, so configuring a fresh device never overwrites your history.

Data notes:

- All workout data lives in your browser's localStorage and your private Gist — nowhere else. The token/Gist ID are stored locally only and are **never** included in exports.
- Merging is per-item last-writer-wins with deletion tombstones, so devices can be used independently and converge safely.
- Recovery of last resort: the Gist's own revision history (gist.github.com → your data gist → Revisions).

## Development

No build step — `index.html` is the app.

```
python -m http.server 8742        # from the repo root
```

- Develop against `http://localhost:8742/` — `file://` breaks reloads and service workers.
- **Tests:** open `http://localhost:8742/tests/run-tests.html` — a self-contained regression suite (~90 checks) that loads the real app in an iframe and asserts against the shipped functions. Run it before every push. It wipes the origin's storage: local server only, never the live origin.
- Service-worker gotcha: if an edit doesn't seem to take effect, the SW may be serving cache — unregister it and hard-reload (the test runner does this automatically).
- Deploys are just pushes to `main` — GitHub Pages serves the repo root (~30s).

## License

[MIT](LICENSE)
