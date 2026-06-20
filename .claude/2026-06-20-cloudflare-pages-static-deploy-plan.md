# Static Cardboard Cabinet on Cloudflare Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Cardboard Cabinet to a fully static site (all filtering/faceting/search in client-side JS over a shipped `games.json`) and deploy it to Cloudflare Pages.

**Architecture:** The browser fetches a static `frontend/data/games.json` once and keeps the collection in memory. A new `frontend/data.js` module ports the Python filter/facet logic to pure JS functions. `app.js` calls those functions instead of the FastAPI API. A local Python script (`scripts/export_collection.py`) reuses `app/bgg.py` to regenerate `games.json`; deploy = commit + push (or `wrangler pages deploy`).

**Tech Stack:** Vanilla JS (browser + Node `--test` for unit tests), Python 3.11 (existing `bgg.py`/`models.py` for the export script), Cloudflare Pages (static hosting), Wrangler CLI.

## Global Constraints

- **Filter parity is authoritative:** `app/db_storage.py::get_games_filtered`, `app/main.py::make_facets`, and `app/util.py::bucketize_minutes` define the exact semantics. Mirror them, especially: (a) **OR within a facet** for mechanics/categories/designers/artists/publishers (a game matches if it has *any* selected value); (b) **NULL exclusion** — a game with a null numeric field is excluded when a bound on that field is active (`time_max`, `weight_min/max`, `rating_min`, `year_min/max`).
- **Bucket labels must be byte-for-byte identical** to the Python source, including the en-dash `–` (U+2013) and non-breaking hyphen `‑` (U+2011) used in weight labels. Copy them verbatim; do not retype with ASCII `-`.
- **Game object shape** matches the Pydantic `Game` model: `id, name, year, image, thumbnail, min_players, max_players, playing_time, weight, avg_rating, bayes_rating, my_rating, mechanics[], categories[], designers[], artists[], publishers[]`.
- **Single-user, no backend on Pages.** The deployed site makes no API calls.
- `data.js` must be `require()`-able under Node (no top-level browser globals); browser-only code (`fetch`, `window`) runs only inside function bodies guarded by environment checks.
- Makefile variables: `PYTHON := .venv/bin/python`, `PYTEST := .venv/bin/pytest`. New targets follow the existing `<name>: install` pattern.

---

### Task 1: `data.js` — pure filter/facet logic + Node unit tests

**Files:**
- Create: `frontend/data.js`
- Create: `tests/js/fixtures/sample.json`
- Create: `tests/js/data.test.js`

**Interfaces:**
- Consumes: nothing (first task).
- Produces (all attached to `window` in browser and exported via `module.exports` in Node):
  - `bucketizeMinutes(minutes: number|null) -> string`
  - `weightBucket(weight: number|null) -> string`
  - `queryGames(games: Game[], filters: object) -> Game[]`
  - `computeFacets(games: Game[]) -> Facets`
  - `loadCollection() -> Promise<Game[]>` (browser-only fetch; defined here, exercised in Task 3)

- [ ] **Step 1: Create the test fixture**

Create `tests/js/fixtures/sample.json`:

```json
[
  {
    "id": 1, "name": "Azul", "year": 2017, "image": null, "thumbnail": null,
    "min_players": 2, "max_players": 4, "playing_time": 45, "weight": 1.77,
    "avg_rating": 7.8, "bayes_rating": 7.7, "my_rating": 8.0,
    "mechanics": ["Tile Placement", "Pattern Building"],
    "categories": ["Abstract Strategy"], "designers": ["Michael Kiesling"],
    "artists": ["Chris Quilliams"], "publishers": ["Plan B Games"]
  },
  {
    "id": 2, "name": "Gloomhaven", "year": 2017, "image": null, "thumbnail": null,
    "min_players": 1, "max_players": 4, "playing_time": 120, "weight": 3.9,
    "avg_rating": 8.6, "bayes_rating": 8.4, "my_rating": null,
    "mechanics": ["Hand Management", "Cooperative Game"],
    "categories": ["Adventure", "Fighting"], "designers": ["Isaac Childres"],
    "artists": ["Alexandr Elichev"], "publishers": ["Cephalofair Games"]
  },
  {
    "id": 3, "name": "Patchwork", "year": 2014, "image": null, "thumbnail": null,
    "min_players": 2, "max_players": 2, "playing_time": 30, "weight": null,
    "avg_rating": 7.6, "bayes_rating": 7.5, "my_rating": 7.0,
    "mechanics": ["Tile Placement"],
    "categories": ["Abstract Strategy"], "designers": ["Uwe Rosenberg"],
    "artists": ["Klemens Franz"], "publishers": ["Lookout Games"]
  }
]
```

- [ ] **Step 2: Write the failing tests**

Create `tests/js/data.test.js`:

```js
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { queryGames, computeFacets, bucketizeMinutes, weightBucket } = require("../../frontend/data.js");

const games = JSON.parse(
  fs.readFileSync(path.join(__dirname, "fixtures", "sample.json"), "utf8")
);
const names = (gs) => gs.map((g) => g.name).sort();

test("no filters returns all games", () => {
  assert.deepEqual(names(queryGames(games, {})), ["Azul", "Gloomhaven", "Patchwork"]);
});

test("mechanics filter is OR-within-facet", () => {
  const r = queryGames(games, { mechanics: ["Tile Placement"] });
  assert.deepEqual(names(r), ["Azul", "Patchwork"]);
});

test("multiple selected mechanics union their matches", () => {
  const r = queryGames(games, { mechanics: ["Tile Placement", "Hand Management"] });
  assert.deepEqual(names(r), ["Azul", "Gloomhaven", "Patchwork"]);
});

test("different facets are AND-ed", () => {
  const r = queryGames(games, { mechanics: ["Tile Placement"], categories: ["Abstract Strategy"] });
  assert.deepEqual(names(r), ["Azul", "Patchwork"]);
});

test("weight bound excludes null-weight games", () => {
  const r = queryGames(games, { weight_min: "1.5", weight_max: "3.0" });
  assert.deepEqual(names(r), ["Azul"]); // Patchwork(null) excluded, Gloomhaven(3.9) excluded
});

test("time_max excludes null and over-bound", () => {
  const r = queryGames(games, { time_max: "60" });
  assert.deepEqual(names(r), ["Azul", "Patchwork"]);
});

test("players supported filter", () => {
  const r = queryGames(games, { players: "1" });
  assert.deepEqual(names(r), ["Gloomhaven"]);
});

test("year bounds inclusive", () => {
  const r = queryGames(games, { year_min: "2015", year_max: "2017" });
  assert.deepEqual(names(r), ["Azul", "Gloomhaven"]);
});

test("rating_min excludes below bound", () => {
  const r = queryGames(games, { rating_min: "8.0" });
  assert.deepEqual(names(r), ["Gloomhaven"]);
});

test("search is case-insensitive substring", () => {
  assert.deepEqual(names(queryGames(games, { search: "patch" })), ["Patchwork"]);
});

test("bucketizeMinutes labels", () => {
  assert.equal(bucketizeMinutes(null), "Unknown");
  assert.equal(bucketizeMinutes(30), "≤30 min");
  assert.equal(bucketizeMinutes(45), "31–60 min");
  assert.equal(bucketizeMinutes(200), "120+ min");
});

test("weightBucket labels", () => {
  assert.equal(weightBucket(null), "Unknown");
  assert.equal(weightBucket(1.5), "Light (≤1.75)");
  assert.equal(weightBucket(1.77), "Medium‑Light (1.76–2.5)");
  assert.equal(weightBucket(3.9), "Medium‑Heavy (3.26–4.0)");
  assert.equal(weightBucket(5), "Heavy (>4.0)");
});

test("computeFacets counts and buckets", () => {
  const f = computeFacets(games);
  assert.equal(f.mechanics["Tile Placement"], 2);
  assert.equal(f.categories["Abstract Strategy"], 2);
  assert.equal(f.years["2017"], 2);
  assert.equal(f.player_counts["2–4"], 1);
  assert.equal(f.player_counts["1–4"], 1);
  assert.equal(f.player_counts["2–2"], 1);
  assert.equal(f.time_buckets["≤30 min"], 1);
  assert.equal(f.weight_buckets["Unknown"], 1);
  assert.equal(f.weight_buckets["Light (≤1.75)"], undefined); // 1.77 is Medium‑Light
  assert.equal(f.weight_buckets["Medium‑Light (1.76–2.5)"], 1);
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `node --test tests/js/`
Expected: FAIL — `Cannot find module '../../frontend/data.js'`.

- [ ] **Step 4: Implement `frontend/data.js`**

Create `frontend/data.js`. **Copy the en-dash `–` and non-breaking hyphen `‑` characters exactly from `app/util.py` / `app/main.py`** — do not retype them as ASCII.

```js
(function () {
  function toNum(v) {
    if (v === undefined || v === null || v === "") return null;
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  }

  function asArray(v) {
    return Array.isArray(v) ? v : (v == null || v === "" ? [] : [v]);
  }

  function bucketizeMinutes(minutes) {
    if (minutes === null || minutes === undefined) return "Unknown";
    if (minutes <= 30) return "≤30 min";
    if (minutes <= 60) return "31–60 min";
    if (minutes <= 90) return "61–90 min";
    if (minutes <= 120) return "91–120 min";
    return "120+ min";
  }

  function weightBucket(w) {
    if (w === null || w === undefined) return "Unknown";
    if (w <= 1.75) return "Light (≤1.75)";
    if (w <= 2.5) return "Medium‑Light (1.76–2.5)";
    if (w <= 3.25) return "Medium (2.51–3.25)";
    if (w <= 4.0) return "Medium‑Heavy (3.26–4.0)";
    return "Heavy (>4.0)";
  }

  function queryGames(games, filters) {
    const f = filters || {};
    const mech = asArray(f.mechanics);
    const cats = asArray(f.categories);
    const desi = asArray(f.designers);
    const arts = asArray(f.artists);
    const pubs = asArray(f.publishers);
    const yearMin = toNum(f.year_min);
    const yearMax = toNum(f.year_max);
    const players = toNum(f.players);
    const timeMax = toNum(f.time_max);
    const weightMin = toNum(f.weight_min);
    const weightMax = toNum(f.weight_max);
    const ratingMin = toNum(f.rating_min);
    const search = (f.search || "").toString().trim().toLowerCase();

    const hasAny = (gameList, selected) => selected.some((s) => gameList.includes(s));

    return games.filter((g) => {
      if (mech.length && !hasAny(g.mechanics, mech)) return false;
      if (cats.length && !hasAny(g.categories, cats)) return false;
      if (desi.length && !hasAny(g.designers, desi)) return false;
      if (arts.length && !hasAny(g.artists, arts)) return false;
      if (pubs.length && !hasAny(g.publishers, pubs)) return false;

      if (yearMin !== null && !(g.year != null && g.year >= yearMin)) return false;
      if (yearMax !== null && !(g.year != null && g.year <= yearMax)) return false;

      if (players !== null) {
        const okMin = g.min_players == null || g.min_players <= players;
        const okMax = g.max_players == null || g.max_players >= players;
        if (!(okMin && okMax)) return false;
      }

      if (timeMax !== null && !(g.playing_time != null && g.playing_time <= timeMax)) return false;
      if (weightMin !== null && !(g.weight != null && g.weight >= weightMin)) return false;
      if (weightMax !== null && !(g.weight != null && g.weight <= weightMax)) return false;
      if (ratingMin !== null && !(g.avg_rating != null && g.avg_rating >= ratingMin)) return false;

      if (search && !(g.name || "").toLowerCase().includes(search)) return false;

      return true;
    });
  }

  function computeFacets(games) {
    const mechanics = {}, categories = {}, designers = {}, artists = {}, publishers = {};
    const years = {}, playerCounts = {}, timeBuckets = {}, weightBuckets = {};
    const add = (d, key) => { if (key) d[key] = (d[key] || 0) + 1; };

    for (const g of games) {
      (g.mechanics || []).forEach((m) => add(mechanics, m));
      (g.categories || []).forEach((c) => add(categories, c));
      (g.designers || []).forEach((d) => add(designers, d));
      (g.artists || []).forEach((a) => add(artists, a));
      (g.publishers || []).forEach((p) => add(publishers, p));

      add(years, g.year ? String(g.year) : "Unknown");

      if (g.min_players || g.max_players) {
        const pmin = g.min_players || g.max_players;
        const pmax = g.max_players || g.min_players;
        add(playerCounts, `${pmin}–${pmax}`);
      } else {
        add(playerCounts, "Unknown");
      }

      add(timeBuckets, bucketizeMinutes(g.playing_time != null ? g.playing_time : null));
      add(weightBuckets, weightBucket(g.weight != null ? g.weight : null));
    }

    return {
      mechanics, categories, designers, artists, publishers,
      years, player_counts: playerCounts,
      time_buckets: timeBuckets, weight_buckets: weightBuckets,
    };
  }

  async function loadCollection() {
    if (loadCollection._cache) return loadCollection._cache;
    const r = await fetch("data/games.json");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    loadCollection._cache = await r.json();
    return loadCollection._cache;
  }

  const api = { bucketizeMinutes, weightBucket, queryGames, computeFacets, loadCollection };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") Object.assign(window, api);
})();
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `node --test tests/js/`
Expected: PASS — all tests green.

- [ ] **Step 6: Commit**

```bash
git add frontend/data.js tests/js/
git commit -m "feat: add client-side filter/facet module with parity tests"
```

---

### Task 2: Export script — regenerate `games.json` from BGG

**Files:**
- Create: `scripts/export_collection.py`
- Create: `scripts/__init__.py` (empty, so the module imports cleanly under pytest)
- Create: `tests/unit/test_export.py`
- Modify: `Makefile` (add `export` target + `.PHONY`)

**Interfaces:**
- Consumes: `app.bgg.fetch_collection`, `app.bgg.get_bgg_session`, `app.bgg.fetch_all_games`, `app.models.Game`.
- Produces: `scripts.export_collection.games_to_json(games: list[Game]) -> str` (deterministic, name-sorted, indent=2 JSON); writes `frontend/data/games.json` when run as `__main__`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_export.py`:

```python
import json
import pytest
from app.models import Game
from scripts.export_collection import games_to_json

pytestmark = pytest.mark.unit


def test_games_to_json_is_sorted_and_complete():
    games = [
        Game(id=2, name="Zebra", year=2020, mechanics=["A"]),
        Game(id=1, name="apple", year=2019, mechanics=["B", "C"]),
    ]
    out = games_to_json(games)
    data = json.loads(out)

    # Sorted case-insensitively by name.
    assert [g["name"] for g in data] == ["apple", "Zebra"]
    # Full Game shape preserved.
    assert data[0]["id"] == 1
    assert data[0]["mechanics"] == ["B", "C"]
    assert "thumbnail" in data[0]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `make test-file FILE=tests/unit/test_export.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'`.

- [ ] **Step 3: Implement the script**

Create empty `scripts/__init__.py`.

Create `scripts/export_collection.py`:

```python
"""Fetch the BGG collection and write it to frontend/data/games.json.

Reuses app/bgg.py so the static site ships the same data the FastAPI app
would serve. Run locally, then commit + deploy.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import List

import httpx
from dotenv import load_dotenv

from app.bgg import fetch_collection, get_bgg_session, fetch_all_games
from app.models import Game

load_dotenv()

OUT_PATH = Path(__file__).resolve().parent.parent / "frontend" / "data" / "games.json"


def games_to_json(games: List[Game]) -> str:
    """Serialize games to deterministic, name-sorted, pretty JSON."""
    data = [g.model_dump() for g in games]
    data.sort(key=lambda d: (d["name"] or "").lower())
    return json.dumps(data, ensure_ascii=False, indent=2)


async def export() -> int:
    user = os.getenv("BGG_USERNAME")
    if not user:
        raise SystemExit("BGG_USERNAME not configured in .env")
    password = os.getenv("BGG_PASSWORD")

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        session_cookie = await get_bgg_session(client, user, password) if password else None
        print(f"Fetching collection for user: {user}")
        ids, my_ratings, collection_xml = await fetch_collection(
            client, user, session_cookie=session_cookie
        )
        print(f"Found {len(ids)} games; hydrating…")
        games = await fetch_all_games(client, ids, my_ratings, collection_xml)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(games_to_json(games), encoding="utf-8")
    print(f"Wrote {len(games)} games to {OUT_PATH}")
    return len(games)


if __name__ == "__main__":
    asyncio.run(export())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `make test-file FILE=tests/unit/test_export.py`
Expected: PASS.

- [ ] **Step 5: Add the Makefile `export` target**

In `Makefile`, add `export` to the `.PHONY` line (append after `db-reset`), and add this target after the `db-reset` block:

```makefile
# ── Static export ─────────────────────────────────────────────────────────────

# Fetch the BGG collection and write frontend/data/games.json for the static site.
export: install
	$(PYTHON) scripts/export_collection.py
```

- [ ] **Step 6: Generate real data**

Run: `make export`
Expected: prints "Wrote N games to …/frontend/data/games.json" and the file exists.
If credentials/network are unavailable, copy a known-good collection JSON to `frontend/data/games.json` manually instead — the file must exist and be a JSON array matching the `Game` shape for Tasks 3–4.

- [ ] **Step 7: Commit**

```bash
git add scripts/ tests/unit/test_export.py Makefile frontend/data/games.json
git commit -m "feat: add BGG export script and generated games.json"
```

---

### Task 3: Wire the frontend to `data.js` (no API), fix paths, hide refresh

**Files:**
- Modify: `frontend/index.html` (asset paths, script tag, hide refresh button)
- Modify: `frontend/app.js` (`loadFacets`, `applyFilters`, startup data load)

**Interfaces:**
- Consumes from Task 1: `loadCollection()`, `queryGames(games, filters)`, `computeFacets(games)` (global functions).
- Produces: a fully static frontend that renders entirely from `data/games.json`.

- [ ] **Step 1: Fix `index.html` asset paths and script order**

In `frontend/index.html`:

Change line 10 from:
```html
  <link rel="stylesheet" href="/static/styles.css" />
```
to:
```html
  <link rel="stylesheet" href="styles.css" />
```

Change the script line (101) from:
```html
  <script src="/static/app.js" defer></script>
```
to:
```html
  <script src="data.js" defer></script>
  <script src="app.js" defer></script>
```

- [ ] **Step 2: Hide the "Refresh from BGG" button**

In `frontend/index.html`, change line 17 from:
```html
      <button id="refresh">🔄 Refresh from BGG</button>
```
to:
```html
      <button id="refresh" hidden>🔄 Refresh from BGG</button>
```

- [ ] **Step 3: Add a startup collection load in `app.js`**

In `frontend/app.js`, add this helper near the top of the file (after the `state` object, around line 20). It loads the collection once and caches it on `state`:

```js
async function ensureCollection() {
  if (state.allGames) return state.allGames;
  state.allGames = await loadCollection();
  state.totalGames = state.allGames.length;
  return state.allGames;
}
```

Add `allGames: null,` to the `state` object literal (around line 18, alongside `lastGames`).

- [ ] **Step 4: Replace the API call in `loadFacets()`**

In `frontend/app.js`, replace the body of `loadFacets()` (lines ~80–95) so it computes facets locally:

```js
async function loadFacets() {
  try {
    const games = await ensureCollection();
    state.facets = computeFacets(games);
    renderTagCloud(state.facets.mechanics);
    fillSelect(qs("categories"), state.facets.categories);
    fillSelect(qs("designers"), state.facets.designers);
    fillSelect(qs("artists"), state.facets.artists);
    fillSelect(qs("publishers"), state.facets.publishers);
    updateSummary();
  } catch {
    showFacetsError();
  }
}
```

- [ ] **Step 5: Replace the API call in `applyFilters()`**

In `frontend/app.js`, replace the `try` block inside `applyFilters()` (lines ~266–282) so it filters in-memory. Keep the loading-bar scaffolding above it unchanged:

```js
  try {
    collectFilters();
    const games = await ensureCollection();
    const filtered = queryGames(games, state.filters);
    state.lastGames = filtered;
    state.totalGames = games.length;
    renderResults(filtered, games.length, filtered.length);
  } catch (err) {
    showResultsError("Could not load games.");
  } finally {
    clearTimeout(showBarTimer);
    if (loadingBar) loadingBar.remove();
    if (resultsEl) resultsEl.style.opacity = "";
  }
```

(The `signal`/`AbortController` lines above remain; aborting a synchronous in-memory filter is harmless and keeps the existing fast-typing UX intact.)

- [ ] **Step 6: Smoke-test the static site**

Run (serves the static dir exactly as Pages will):
```bash
cd frontend && python3 -m http.server 8787
```
Open `http://localhost:8787/`. Verify, then stop the server (Ctrl-C):
- Page loads with no console errors and no network calls to `/api/*`.
- Mechanics tag cloud + Categories/Designers/Artists/Publishers selects populate.
- Selecting a mechanic filters results; clearing restores them.
- Numeric filters (year/players/time/weight/rating) and search work.
- Tile/List view toggle works.

Expected: all interactions work against `data/games.json` with zero backend.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/app.js
git commit -m "feat: render static site from games.json instead of the API"
```

---

### Task 4: Cloudflare Pages deploy config + docs

**Files:**
- Create: `DEPLOY.md`
- Modify: `Makefile` (add `deploy` target + `.PHONY`)
- Modify: `.gitignore` (ensure `frontend/data/games.json` is NOT ignored)

**Interfaces:**
- Consumes: a populated `frontend/data/games.json` (Task 2) and the static frontend (Task 3).
- Produces: a documented, repeatable deploy.

- [ ] **Step 1: Ensure the data file is committed, not ignored**

Run: `git check-ignore frontend/data/games.json || echo "not ignored — good"`
If it prints the path (ignored), add a negation to `.gitignore`:
```
!frontend/data/games.json
```
Expected: the file is tracked (it was committed in Task 2).

- [ ] **Step 2: Add a `deploy` Makefile target**

In `Makefile`, add `deploy` to the `.PHONY` line, and add after the `export` target:

```makefile
# ── Deploy ────────────────────────────────────────────────────────────────────

# Deploy the static frontend to Cloudflare Pages via Wrangler.
# Requires: npx wrangler login (one-time). PROJECT defaults to cardboard-cabinet.
PROJECT ?= cardboard-cabinet
deploy:
	npx wrangler@latest pages deploy frontend --project-name=$(PROJECT)
```

- [ ] **Step 3: Write `DEPLOY.md`**

Create `DEPLOY.md`:

````markdown
# Deploying Cardboard Cabinet to Cloudflare Pages

The deployed site is fully static — it serves `frontend/` and reads
`frontend/data/games.json` in the browser. There is no backend on Cloudflare.

## Update the collection data

```bash
make export      # fetches your BGG collection -> frontend/data/games.json
```

Commit the regenerated file. Data is only as fresh as your last export.

## Option A — Git integration (recommended)

1. Push this repo to GitHub (already at `origin`).
2. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git** → select `cardboard-cabinet`.
3. Build settings:
   - **Framework preset:** None
   - **Build command:** *(leave empty)*
   - **Build output directory:** `frontend`
4. Save and deploy. Every push to `main` auto-deploys.

## Option B — Wrangler CLI

```bash
npx wrangler login                 # one-time
make deploy                        # = wrangler pages deploy frontend
```

The first `deploy` will offer to create the `cardboard-cabinet` Pages project.

## Notes

- The "🔄 Refresh from BGG" button is hidden — refresh is `make export` + redeploy.
- To preview the production build locally: `cd frontend && python3 -m http.server 8787`.
````

- [ ] **Step 4: Validate the deploy command (dry run)**

Run: `npx wrangler@latest pages deploy frontend --project-name=cardboard-cabinet --dry-run 2>&1 | head -20`
Expected: Wrangler validates the directory and reports the files it would upload (or prompts for login — that confirms the command path is correct). Do NOT do a real deploy unless the user asks.

- [ ] **Step 5: Commit**

```bash
git add DEPLOY.md Makefile .gitignore
git commit -m "docs: add Cloudflare Pages deploy config and instructions"
```

---

## Self-Review

**Spec coverage:**
- `games.json` data file → Task 2. ✓
- `data.js` (`loadCollection`/`queryGames`/`computeFacets`) → Task 1. ✓
- `app.js` swaps both fetch sites → Task 3 (steps 4–5). ✓
- `index.html` path fixes + script tag + hidden refresh → Task 3 (steps 1–2). ✓
- Export script reusing `bgg.py` + Makefile target → Task 2. ✓
- Deploy config/docs (dashboard + wrangler) → Task 4. ✓
- Testing: parity (Task 1 Node tests + Task 2 serialization test) + smoke (Task 3 step 6). ✓
- Risk notes (OR-within-facet, NULL exclusion, exact bucket labels) → Global Constraints + Task 1 tests. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code. Task 2 step 6 documents the credentials-unavailable fallback explicitly. ✓

**Type consistency:** `queryGames(games, filters)` and `computeFacets(games)` signatures are identical across Task 1 (definition), Task 1 tests, and Task 3 (callers). `loadCollection()` defined in Task 1, called via `ensureCollection()` in Task 3. `games_to_json(games)` consistent across Task 2 script and test. Facet keys (`player_counts`, `time_buckets`, `weight_buckets`) match `app/models.py::Facets`. ✓

**Scope:** Single subsystem (static conversion + deploy). One plan is appropriate. ✓
