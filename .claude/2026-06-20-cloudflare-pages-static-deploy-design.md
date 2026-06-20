# Design: Static Cardboard Cabinet on Cloudflare Pages

**Date:** 2026-06-20
**Status:** Approved (design); pending implementation plan

## Goal

Deploy Cardboard Cabinet to Cloudflare Pages. Because Pages serves only static
assets + JS Workers (not a Python/FastAPI server), convert the app to a fully
static single-page site: ship the collection as a JSON file and do all
filtering, faceting, search, and sorting client-side. Collection data is
refreshed locally and redeployed.

## Non-goals

- Live "Refresh from BGG" from the deployed site (no backend on Pages).
- Porting `bgg.py` / the FastAPI API to Workers or D1.
- Multi-user support. This is a single-user (one BGG account) collection browser.
- Deleting the existing FastAPI app — it stays for local use and tests.

## Architecture

```
Build/refresh (local):  bgg.py → frontend/data/games.json  →  git commit/push
Runtime (browser):      games.json → in-memory filter/facet/render (no server)
```

The deployed site is 100% static files on Cloudflare's CDN: `index.html`,
`app.js`, `data.js`, `styles.css`, and `data/games.json`. The browser fetches
`games.json` once on load and keeps the full collection in memory. Every filter,
facet count, search, and sort runs in JS against that in-memory array.

## Components

### New: `frontend/data/games.json`
The full collection serialized as a JSON array of game objects, matching the
Pydantic `Game` shape (`id, name, year, image, thumbnail, min_players,
max_players, playing_time, weight, avg_rating, bayes_rating, my_rating,
mechanics[], categories[], designers[], artists[], publishers[]`). ~100–200KB;
served gzipped by Cloudflare.

### New: `frontend/data.js`
Client module mirroring the Python logic. Exposes (loaded before `app.js`):

- `loadCollection()` → fetch `data/games.json` once, cache the array in memory,
  return it. Subsequent calls return the cache.
- `queryGames(filters)` → port of `get_games_filtered()` in `db_storage.py`:
  - **mechanics / categories / designers / artists / publishers**: a game matches
    if it has **any** of the selected values (OR within a facet — mirrors SQL
    `.in_()` + join + `distinct()`). Across different facets the conditions are
    AND-ed.
  - **year_min / year_max**: inclusive bounds on `year`.
  - **players** (supported): `(min_players is None or min_players <= players)`
    AND `(max_players is None or max_players >= players)`.
  - **time_max**: `playing_time <= time_max` — games with null `playing_time`
    are **excluded** when this bound is active.
  - **weight_min / weight_max**: inclusive; null `weight` **excluded** when a
    bound is active.
  - **rating_min**: `avg_rating >= rating_min`; null excluded when active.
  - **search**: case-insensitive substring match on `name` (equivalent to SQL
    `ilike %term%`; literal match, no glob).
  - Returns the filtered array.
- `computeFacets(games)` → port of `make_facets()` + `bucketize_minutes()`
  (`util.py`) + the inline weight buckets in `main.py`. Returns the `Facets`
  shape: `{mechanics, categories, designers, artists, publishers, years,
  player_counts, time_buckets, weight_buckets}` as `{label: count}` maps.
  - Time buckets: `≤30 min`, `31–60 min`, `61–90 min`, `91–120 min`,
    `120+ min`, `Unknown`.
  - Weight buckets: `Light (≤1.75)`, `Medium‑Light (1.76–2.5)`,
    `Medium (2.51–3.25)`, `Medium‑Heavy (3.26–4.0)`, `Heavy (>4.0)`, `Unknown`.
  - Player counts: `"{min}–{max}"` using the present value when one side is null,
    else `Unknown`.
  - Years: `str(year)` or `Unknown`.

### Modified: `frontend/app.js`
Only the two network call sites change; render code is untouched.
- `loadFacets()`: replace `fetch("/api/facets")` with
  `computeFacets(await loadCollection())`.
- `applyFilters()`: replace `fetch("/api/games?…")` with
  `queryGames(state.filters)`, then build `{games, total, filtered}` locally
  (`total` = full collection length, `filtered` = result length) and pass to the
  existing `renderResults()`.
- Keep the `AbortController`/loading-bar UX or simplify it (filtering is now
  synchronous and instant). Acceptable to keep the structure and resolve
  immediately.

### Modified: `frontend/index.html`
- `/static/styles.css` → `styles.css`; `/static/app.js` → `app.js` (Pages serves
  from root; there is no `/static` mount).
- Add `<script src="data.js" defer></script>` before `app.js`.
- Hide the "🔄 Refresh from BGG" button (no live backend). Keep the markup but
  `hidden`, or remove it. Decision: hide it.

### New: `scripts/export_collection.py`
Runs the existing async BGG fetch (`fetch_collection` + `fetch_all_games` from
`bgg.py`, with optional auth via `get_bgg_session`) using `BGG_USERNAME` /
`BGG_PASSWORD` from `.env`, and writes the resulting games to
`frontend/data/games.json` (pretty-printed, stable key order). Wired as a
Makefile target (e.g. `make export`).

### New: deploy config / docs
A Cloudflare Pages project with **build output directory = `frontend/`** and **no
build command** (pure static). Document both paths:
- Dashboard Git integration (auto-deploy on push to `main`).
- `wrangler pages deploy frontend` from the CLI.

## What stays / what is retired
- Retired from deploy (kept in repo for local dev/tests): `app/main.py`,
  `app/db_storage.py`, `app/database.py`, `app/db_models.py`, `Dockerfile`.
- Reused by the export script: `app/bgg.py`, `app/models.py`, `app/util.py`.

## Testing
- **Parity check:** verify JS `queryGames` / `computeFacets` produce the same
  results as the Python API for the same dataset across a handful of filter
  combinations (single facet, multi-value facet, bounded numeric, search,
  combined). At minimum, manual parity checks; a small automated comparison is a
  bonus.
- **Smoke test:** serve `frontend/` statically (`python -m http.server` from the
  `frontend/` dir) and confirm load, facets render, each filter type works,
  search, sort, and tile/list view toggle all behave against `games.json`.

## Risks
- **Filter parity** is the primary risk. The Python code in `db_storage.py` /
  `main.py` / `util.py` is the authoritative spec; mirror it exactly, especially
  (a) OR-within-facet semantics and (b) NULL exclusion when a numeric bound is
  active.
- **Stale data**: deployed data is only as fresh as the last `make export` +
  deploy. Acceptable per the single-user, rarely-changing-collection assumption.
