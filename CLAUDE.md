# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
py app.py          # starts Flask dev server on http://localhost:5000
```

No build step, no test suite. The SQLite database (`instance/drums.db`) and `static/uploads/` folder are created automatically on first run via `db.create_all()` + `_seed()` inside an `app.app_context()` block at module level.

For production the app is served via Passenger WSGI (`passenger_wsgi.py` exposes `application = app`).

## Architecture

Single-file Flask app (`app.py`) with Jinja2 templates and vanilla JS. No blueprints.

**Models (SQLAlchemy / SQLite)**
- `Song` — core entity: title, artist, BPM, style, difficulty (1–5), status (`learning`/`mastered`/`on_hold`), optional TikTok URL/ID, optional PDF tablature path.
- `PracticeSession` — FK to `Song`; records duration, rating, notes. Cascade-deleted with the song.
- `User` — single admin user, seeded by `_seed()` (username `admin`).
- `SongSuggestion` — visitor-submitted suggestions, no FK.
- `TikTokConfig` / `TikTokToken` — one-row tables storing OAuth client credentials and the active bearer token.

**Route groups**
| Prefix | Auth | Purpose |
|---|---|---|
| `/`, `/practice`, `/stats`, `/suggestion` | Public | Visitor-facing pages |
| `/api/songs`, `/api/practice/log` | Public | JSON API consumed by frontend JS |
| `/admin/*` | `@login_required` (session cookie) | CRUD for songs, suggestions, TikTok |

**TikTok OAuth flow**  
`/admin/tiktok/connect` → TikTok authorize (PKCE, S256) → `/admin/tiktok/callback` (exchanges code for token, stores in `TikTokToken`) → `/admin/tiktok/sync` (POST to `video/list`, imports new videos as `Song` rows).

**Frontend JS**
- `dashboard.js` — pure DOM filtering of `.song-card` elements by style/difficulty/status/BPM/search; no API call, all data is already in the rendered HTML.
- `practice.js` — logs a practice session via `POST /api/practice/log`.
- `stats.js` — Chart.js charts (doughnut, bar, line); data injected as JS globals (`MASTERED`, `STYLE_DATA`, `DAILY_DATA`, etc.) by the Jinja2 template.
- `suggestion.js` — suggestion form helper.

**Templates**  
All extend `templates/base.html`. Admin templates live under `templates/admin/`. Chart.js is loaded from CDN in `templates/stats.html`.

**PDF uploads**  
Stored in `static/uploads/`, named `{Artist}_{Title}.pdf`. Served via `/uploads/<filename>`.

## Key constants / globals

- `STYLES` — `['Rock', 'Metal', 'Pop', 'Jazz', 'Funk', 'Autre']` — used in forms and chart coloring.
- `STATUSES` — `[('learning', …), ('mastered', …), ('on_hold', …)]` — passed to every song form template.
- `TIKTOK_USERNAME = "drmbvs"` — informational only; the actual sync uses the OAuth token.
- TikTok client key/secret are seeded into `TikTokConfig` at startup; edit `_seed()` to change them.
