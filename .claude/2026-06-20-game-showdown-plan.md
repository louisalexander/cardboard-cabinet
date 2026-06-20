# "What should we play?" Bracket Showdown — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "decide what to play tonight" mode — set quick constraints, then crown one game through a this-or-that single-elimination bracket (up to 8 games).

**Architecture:** A new `frontend/showdown.js` holds (1) pure bracket/seed logic, unit-tested with Node, and (2) a DOM controller that renders a full-screen overlay (setup → matchups → champion). Candidate seeding reuses `queryGames` from `data.js`. 100% client-side; no backend, no `games.json` change.

**Tech Stack:** Vanilla JS (browser + Node `--test`), the existing `data.js` module, CSS in `frontend/styles.css`.

## Global Constraints

- **Client-side only.** No backend, no new data, no changes to `frontend/data/games.json`.
- **Reuse the existing filter logic:** candidate games come from `queryGames(allGames, filters)` (global from `data.js`) — do not write a second filtering implementation.
- **Pure logic must be `require()`-able under Node** (tests `require("../../frontend/showdown.js")`): no top-level browser globals; `fetch`/`window`/`document` only inside function bodies. Export pure functions via `module.exports` AND attach to `window.Showdown` in the browser.
- **Bracket size** = the largest power of 2 `<= candidate count`, capped at **8** (8+→8, 4–7→4, 2–3→2). `< 2` candidates → an "insufficient" result, no bracket.
- **Brainpower → weight mapping (exact):** `light` → `{weight_max: 1.75}`; `medium` → `{weight_min: 1.76, weight_max: 3.25}`; `heavy` → `{weight_min: 3.26}`; Any → no weight filter.
- **Round labels (exact):** size `8 → "Quarterfinal"`, `4 → "Semifinal"`, `2 → "Final"`, otherwise `"Round of {n}"`.
- **Players chip "5+" maps to `players: 5`.**
- Node test command form: `node --test tests/js/*.test.js` (bare directory form fails on Node 23+); `make test-js` runs it.
- Match the existing dark visual language in `frontend/styles.css` (cards, fonts, color tokens).

---

### Task 1: Pure bracket/seed logic + Node tests

**Files:**
- Create: `frontend/showdown.js`
- Create: `tests/js/showdown.test.js`

**Interfaces:**
- Consumes: nothing (pure module).
- Produces (on `module.exports` and `window.Showdown`):
  - `setupToFilters(setup: {players?, time?, brainpower?}) -> filters` — filters object for `queryGames`.
  - `dealBracket(games: Game[], rng = Math.random) -> state | {insufficient: true, count}` — initial bracket state.
  - `currentMatchup(state) -> [Game, Game] | null` — pair for the current matchup, `null` at champion/insufficient.
  - `chooseWinner(state, winnerId) -> state` — pure; advances the chosen game, drops the other.
  - `champion(state) -> Game | null` — winner when one remains.
  - `roundLabel(roundSize: number) -> string`.
  - State shape: `{ round: Game[], nextRound: Game[], matchupIndex: number }`.

- [ ] **Step 1: Write the failing tests**

Create `tests/js/showdown.test.js`:

```js
const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  setupToFilters, dealBracket, currentMatchup, chooseWinner, champion, roundLabel,
} = require("../../frontend/showdown.js");

const games = (n) => Array.from({ length: n }, (_, i) => ({ id: i + 1, name: "G" + (i + 1) }));
// Deterministic rng: identity-ish (always 0) → shuffle is deterministic.
const rng0 = () => 0;

test("setupToFilters maps players/time/brainpower", () => {
  assert.deepEqual(
    setupToFilters({ players: 2, time: 60, brainpower: "medium" }),
    { players: 2, time_max: 60, weight_min: 1.76, weight_max: 3.25 }
  );
  assert.deepEqual(setupToFilters({}), {});
  assert.deepEqual(setupToFilters({ brainpower: "light" }), { weight_max: 1.75 });
  assert.deepEqual(setupToFilters({ brainpower: "heavy" }), { weight_min: 3.26 });
  assert.deepEqual(setupToFilters({ players: 5 }), { players: 5 });
});

test("dealBracket sizes to largest power of 2 <= count, capped at 8", () => {
  assert.equal(dealBracket(games(10), rng0).round.length, 8);
  assert.equal(dealBracket(games(8), rng0).round.length, 8);
  assert.equal(dealBracket(games(7), rng0).round.length, 4);
  assert.equal(dealBracket(games(5), rng0).round.length, 4);
  assert.equal(dealBracket(games(3), rng0).round.length, 2);
  assert.equal(dealBracket(games(2), rng0).round.length, 2);
});

test("dealBracket reports insufficient under 2 games", () => {
  assert.deepEqual(dealBracket(games(1), rng0), { insufficient: true, count: 1 });
  assert.deepEqual(dealBracket(games(0), rng0), { insufficient: true, count: 0 });
});

test("dealBracket picks only from the input games", () => {
  const state = dealBracket(games(10), rng0);
  const ids = new Set(games(10).map((g) => g.id));
  assert.ok(state.round.every((g) => ids.has(g.id)));
  assert.equal(new Set(state.round.map((g) => g.id)).size, 8); // no duplicates
});

test("dealBracket is deterministic for a given rng", () => {
  const a = dealBracket(games(10), rng0).round.map((g) => g.id);
  const b = dealBracket(games(10), rng0).round.map((g) => g.id);
  assert.deepEqual(a, b);
});

test("currentMatchup returns the leading pair, null at champion", () => {
  const state = { round: games(4), nextRound: [], matchupIndex: 0 };
  const m = currentMatchup(state);
  assert.deepEqual([m[0].id, m[1].id], [1, 2]);
  assert.equal(currentMatchup({ round: games(1), nextRound: [], matchupIndex: 0 }), null);
});

test("chooseWinner advances rounds 8 -> 4 -> 2 -> 1 over 7 picks", () => {
  let state = { round: games(8), nextRound: [], matchupIndex: 0 };
  const sizes = [state.round.length];
  let picks = 0;
  while (!champion(state)) {
    const m = currentMatchup(state);
    state = chooseWinner(state, m[0].id); // always pick the first card
    picks += 1;
    if (currentMatchup(state) === null || state.round.length !== sizes[sizes.length - 1]) {
      sizes.push(state.round.length);
    }
    if (picks > 20) break; // guard
  }
  assert.equal(picks, 7);
  assert.equal(champion(state).id, 1); // always picking the lower index wins overall
  assert.deepEqual(sizes, [8, 4, 2, 1]);
});

test("chooseWinner with an invalid id is a no-op", () => {
  const state = { round: games(4), nextRound: [], matchupIndex: 0 };
  assert.deepEqual(chooseWinner(state, 999), state);
});

test("champion is null until one remains", () => {
  assert.equal(champion({ round: games(4), nextRound: [], matchupIndex: 0 }), null);
  assert.equal(champion({ round: games(1), nextRound: [], matchupIndex: 0 }).id, 1);
  assert.equal(champion({ insufficient: true, count: 0 }), null);
});

test("roundLabel", () => {
  assert.equal(roundLabel(8), "Quarterfinal");
  assert.equal(roundLabel(4), "Semifinal");
  assert.equal(roundLabel(2), "Final");
  assert.equal(roundLabel(6), "Round of 6");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/showdown.test.js`
Expected: FAIL — `Cannot find module '../../frontend/showdown.js'`.

- [ ] **Step 3: Implement `frontend/showdown.js` (pure logic only)**

Create `frontend/showdown.js`:

```js
(function () {
  function setupToFilters(setup) {
    const s = setup || {};
    const f = {};
    if (s.players) f.players = s.players;
    if (s.time) f.time_max = s.time;
    if (s.brainpower === "light") {
      f.weight_max = 1.75;
    } else if (s.brainpower === "medium") {
      f.weight_min = 1.76;
      f.weight_max = 3.25;
    } else if (s.brainpower === "heavy") {
      f.weight_min = 3.26;
    }
    return f;
  }

  function largestPow2AtMost(n, cap) {
    let p = 1;
    while (p * 2 <= n && p * 2 <= cap) p *= 2;
    return p;
  }

  function shuffle(arr, rng) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      const t = a[i];
      a[i] = a[j];
      a[j] = t;
    }
    return a;
  }

  function dealBracket(games, rng) {
    const r = rng || Math.random;
    if (!games || games.length < 2) {
      return { insufficient: true, count: games ? games.length : 0 };
    }
    const size = largestPow2AtMost(games.length, 8);
    const round = shuffle(games, r).slice(0, size);
    return { round, nextRound: [], matchupIndex: 0 };
  }

  function currentMatchup(state) {
    if (!state || state.insufficient || state.round.length <= 1) return null;
    const i = state.matchupIndex * 2;
    return [state.round[i], state.round[i + 1]];
  }

  function chooseWinner(state, winnerId) {
    const pair = currentMatchup(state);
    if (!pair) return state;
    const winner = pair[0].id === winnerId ? pair[0] : pair[1].id === winnerId ? pair[1] : null;
    if (!winner) return state;
    const nextRound = state.nextRound.concat([winner]);
    let matchupIndex = state.matchupIndex + 1;
    let round = state.round;
    let nr = nextRound;
    if (matchupIndex * 2 >= round.length) {
      round = nextRound;
      nr = [];
      matchupIndex = 0;
    }
    return { round, nextRound: nr, matchupIndex };
  }

  function champion(state) {
    if (!state || state.insufficient) return null;
    return state.round.length === 1 ? state.round[0] : null;
  }

  function roundLabel(roundSize) {
    if (roundSize === 8) return "Quarterfinal";
    if (roundSize === 4) return "Semifinal";
    if (roundSize === 2) return "Final";
    return "Round of " + roundSize;
  }

  const api = { setupToFilters, dealBracket, currentMatchup, chooseWinner, champion, roundLabel };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.Showdown = Object.assign(window.Showdown || {}, api);
})();
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/js/showdown.test.js`
Expected: PASS — all tests green.

- [ ] **Step 5: Run the whole JS suite (no regressions)**

Run: `make test-js`
Expected: existing `data.test.js` + new `showdown.test.js` all pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/showdown.js tests/js/showdown.test.js
git commit -m "feat: add pure bracket/seed logic for game showdown"
```

---

### Task 2: Showdown overlay UI (controller, markup, wiring, styles)

**Files:**
- Modify: `frontend/showdown.js` (append the DOM controller inside the existing IIFE, before the `const api = ...` line)
- Modify: `frontend/index.html` (header button + overlay markup + script tag)
- Modify: `frontend/app.js` (wire the header button on startup)
- Modify: `frontend/styles.css` (overlay + chips + matchup + champion styles)

**Interfaces:**
- Consumes from Task 1: `setupToFilters`, `dealBracket`, `currentMatchup`, `chooseWinner`, `champion`, `roundLabel` (in-scope within the IIFE). Also the global `queryGames(games, filters)` from `data.js`.
- Produces: `window.Showdown.open(allGames: Game[])` — opens the overlay.

- [ ] **Step 1: Add the controller to `frontend/showdown.js`**

In `frontend/showdown.js`, insert this block **immediately before** the line `const api = { setupToFilters, ... };`:

```js
  // ---- DOM controller (browser only) ----
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  const ctrl = { allGames: [], candidates: [], setup: { players: 2, time: null, brainpower: null }, state: null };

  function overlay() { return document.getElementById("showdown-overlay"); }
  function screen() { return document.getElementById("showdown-screen"); }

  function statsLine(g) {
    const players = g.min_players || g.max_players
      ? (g.min_players || g.max_players) + "–" + (g.max_players || g.min_players) : "?";
    const time = g.playing_time ? g.playing_time + "m" : "—";
    const wt = g.weight != null ? "⚖ " + g.weight.toFixed(1) : "⚖ —";
    const rating = g.avg_rating != null ? " · ★ " + g.avg_rating.toFixed(1) : "";
    return esc(players + " · " + time + " · ") + wt + rating;
  }

  function gameCard(g) {
    const img = g.image || g.thumbnail || "";
    return '<button class="sd-card" data-id="' + esc(g.id) + '">'
      + (img ? '<img src="' + esc(img) + '" alt="" loading="lazy">' : "")
      + '<div class="sd-card-body"><h3>' + esc(g.name) + "</h3>"
      + '<div class="sd-stats">' + statsLine(g) + "</div></div></button>";
  }

  function chip(group, val, label) {
    const active = String(ctrl.setup[group] == null ? "" : ctrl.setup[group]) === val ? " active" : "";
    return '<button class="sd-chip' + active + '" data-group="' + group + '" data-val="' + esc(val) + '">'
      + esc(label) + "</button>";
  }

  function renderSetup(message) {
    screen().innerHTML =
      '<div class="sd-head"><button class="sd-x" data-act="close" aria-label="Close">✕</button></div>'
      + '<h2 class="sd-q">What’s tonight like?</h2>'
      + '<div class="sd-group"><label>Players</label>'
      + chip("players", "2", "2") + chip("players", "3", "3") + chip("players", "4", "4") + chip("players", "5", "5+")
      + "</div>"
      + '<div class="sd-group"><label>Time</label>'
      + chip("time", "", "Any") + chip("time", "30", "≤30") + chip("time", "60", "≤60")
      + chip("time", "90", "≤90") + chip("time", "120", "≤120m") + "</div>"
      + '<div class="sd-group"><label>Brainpower</label>'
      + chip("brainpower", "", "Any") + chip("brainpower", "light", "Light")
      + chip("brainpower", "medium", "Medium") + chip("brainpower", "heavy", "Heavy") + "</div>"
      + '<div class="sd-actions"><button class="sd-primary" data-act="deal">Deal the bracket</button>'
      + '<button data-act="surprise">🎲 Surprise us</button></div>'
      + '<p class="sd-msg">' + esc(message || "") + "</p>";
  }

  function renderMatchup() {
    const m = currentMatchup(ctrl.state);
    if (!m) { renderChampion(); return; }
    const size = ctrl.state.round.length;
    screen().innerHTML =
      '<div class="sd-head"><button class="sd-x" data-act="close" aria-label="Close">✕</button>'
      + '<p class="sd-progress">' + esc(roundLabel(size)) + " · "
      + (ctrl.state.matchupIndex + 1) + " of " + size / 2 + "</p></div>"
      + '<h2 class="sd-q">Which sounds better tonight?</h2>'
      + '<div class="sd-matchup">' + gameCard(m[0]) + '<span class="sd-vs">VS</span>' + gameCard(m[1]) + "</div>"
      + '<button class="sd-redeal" data-act="redeal">↺ Redeal</button>';
  }

  function renderChampion() {
    const g = champion(ctrl.state);
    const img = g.image || g.thumbnail || "";
    screen().innerHTML =
      '<div class="sd-head"><button class="sd-x" data-act="close" aria-label="Close">✕</button></div>'
      + '<div class="sd-champion"><p class="sd-tonight">Tonight you’re playing</p>'
      + "<h2>" + esc(g.name) + "</h2>"
      + (img ? '<img src="' + esc(img) + '" alt="">' : "")
      + '<div class="sd-stats">' + statsLine(g) + "</div>"
      + '<div class="sd-actions"><button class="sd-primary" data-act="again">↺ Run it again</button>'
      + '<button data-act="done">Done</button></div></div>';
  }

  function deal(candidates) {
    ctrl.candidates = candidates;
    ctrl.state = dealBracket(candidates);
    if (ctrl.state.insufficient) {
      renderSetup("Only " + ctrl.state.count + " game" + (ctrl.state.count === 1 ? "" : "s")
        + " match — loosen a filter or hit Surprise us.");
      return;
    }
    renderMatchup();
  }

  function onClick(e) {
    const t = e.target.closest("[data-act], [data-id], .sd-chip");
    if (!t) return;
    if (t.classList.contains("sd-chip")) {
      const group = t.getAttribute("data-group");
      const val = t.getAttribute("data-val");
      ctrl.setup[group] = val === "" ? null : (group === "brainpower" ? val : Number(val));
      renderSetup("");
      return;
    }
    if (t.hasAttribute("data-id")) {
      ctrl.state = chooseWinner(ctrl.state, Number(t.getAttribute("data-id")));
      renderMatchup();
      return;
    }
    const act = t.getAttribute("data-act");
    if (act === "close" || act === "done") { close(); }
    else if (act === "deal") { deal(queryGames(ctrl.allGames, setupToFilters(ctrl.setup))); }
    else if (act === "surprise") { deal(ctrl.allGames.slice()); }
    else if (act === "redeal" || act === "again") { deal(ctrl.candidates); }
  }

  function open(allGames) {
    ctrl.allGames = allGames || [];
    ctrl.setup = { players: 2, time: null, brainpower: null };
    const ov = overlay();
    ov.hidden = false;
    ov.addEventListener("click", onClick);
    renderSetup("");
  }

  function close() {
    const ov = overlay();
    ov.hidden = true;
    ov.removeEventListener("click", onClick);
  }

```

Then extend the exports line to include `open`. Change:

```js
  const api = { setupToFilters, dealBracket, currentMatchup, chooseWinner, champion, roundLabel };
```
to:
```js
  const api = { setupToFilters, dealBracket, currentMatchup, chooseWinner, champion, roundLabel, open };
```

- [ ] **Step 2: Add the header button and overlay markup to `frontend/index.html`**

In `frontend/index.html`, in the `.toolbar` div, add the button after the `view-toggle` button:

```html
      <button id="play-picker" class="view-toggle">🎲 What should we play?</button>
```

Immediately before the closing `</body>` (before the `<script src="data.js" ...>` line), add the overlay markup:

```html
  <div id="showdown-overlay" hidden>
    <div class="showdown-inner" id="showdown-screen"></div>
  </div>
```

And add the script tag after `app.js`:

```html
  <script src="showdown.js" defer></script>
```

- [ ] **Step 3: Wire the button on startup in `frontend/app.js`**

In `frontend/app.js`, inside the `window.addEventListener("DOMContentLoaded", ...)` handler, after the line `qs("view-toggle").addEventListener("click", toggleView);`, add:

```js
  qs("play-picker").addEventListener("click", () => window.Showdown.open(state.allGames || []));
```

- [ ] **Step 4: Add styles to `frontend/styles.css`**

Append to `frontend/styles.css`:

```css
/* ── Game Showdown overlay ──────────────────────────────────────────────── */
#showdown-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 12, 18, 0.92);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 2rem 1rem;
}
#showdown-overlay[hidden] { display: none; }
.showdown-inner {
  width: 100%;
  max-width: 760px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.sd-head { display: flex; justify-content: space-between; align-items: center; min-height: 2rem; }
.sd-x {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--muted, #9aa);
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
}
.sd-progress { color: var(--muted, #9aa); font-size: 0.9rem; margin: 0; }
.sd-q { text-align: center; margin: 0; }
.sd-group { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
.sd-group > label { width: 100%; font-weight: 600; color: var(--muted, #9aa); font-size: 0.85rem; }
.sd-chip {
  padding: 0.5rem 0.9rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
}
.sd-chip.active { background: var(--accent, #6c8cff); border-color: var(--accent, #6c8cff); color: #fff; }
.sd-actions { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; margin-top: 0.5rem; }
.sd-actions button, .sd-redeal {
  padding: 0.6rem 1.1rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
  color: inherit;
  cursor: pointer;
  font: inherit;
}
.sd-primary { background: var(--accent, #6c8cff); border-color: var(--accent, #6c8cff); color: #fff; font-weight: 600; }
.sd-redeal { align-self: center; }
.sd-msg { text-align: center; color: var(--accent, #6c8cff); min-height: 1.2rem; margin: 0; }
.sd-matchup { display: flex; align-items: stretch; gap: 0.75rem; }
.sd-vs { align-self: center; font-weight: 700; color: var(--muted, #9aa); }
.sd-card {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  overflow: hidden;
  text-align: left;
  padding: 0;
  transition: transform 0.08s ease, border-color 0.08s ease;
}
.sd-card:hover { transform: translateY(-2px); border-color: var(--accent, #6c8cff); }
.sd-card img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; }
.sd-card-body { padding: 0.75rem; }
.sd-card-body h3 { margin: 0 0 0.35rem; font-size: 1rem; }
.sd-stats { color: var(--muted, #9aa); font-size: 0.85rem; }
.sd-champion { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 0.75rem; }
.sd-champion img { max-width: 280px; width: 100%; border-radius: 12px; }
.sd-champion h2 { font-size: 1.8rem; margin: 0; }
.sd-tonight { color: var(--muted, #9aa); margin: 0; text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.8rem; }
@media (max-width: 560px) {
  .sd-matchup { flex-direction: column; }
  .sd-vs { padding: 0.25rem 0; }
}
```

- [ ] **Step 5: Smoke-test the overlay**

Run (serves the static dir as Pages/Workers will):
```bash
cd frontend && python3 -m http.server 8788
```
Open `http://localhost:8788/`. Verify, then stop the server (Ctrl-C):
- The header shows **🎲 What should we play?**; clicking it opens the overlay with the setup screen (Players `2` preselected).
- Tapping chips toggles them (one active per group).
- **Deal the bracket** with default setup shows a head-to-head with two cards and a progress line; tapping a card advances; after the right number of taps a champion is revealed.
- **Surprise us** deals a bracket from the full collection.
- **↺ Redeal** reshuffles; **↺ Run it again** restarts from the champion; **✕** / **Done** closes the overlay back to the browser.
- Set Players to `5+` and Brainpower to `Heavy` to force few matches → the "Only N games match…" message appears on the setup screen.
- No console errors; no network calls to any `/api/*`.

- [ ] **Step 6: Commit**

```bash
git add frontend/showdown.js frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat: game showdown overlay UI (setup, bracket, champion)"
```

---

## Self-Review

**Spec coverage:**
- Entry point button + full-screen overlay → Task 2 (steps 1–3). ✓
- Setup screen with players/time/brainpower chips + Deal + Surprise us → Task 2 (`renderSetup`, `onClick`). ✓
- `setupToFilters` mapping incl. brainpower→weight, "5+"→5 → Task 1 (tested). ✓
- Seed via `queryGames`; bracket size = largest pow2 ≤ count capped at 8; <2 insufficient → Task 1 (`dealBracket`, tested) + Task 2 (`deal`). ✓
- This-or-that matchups, advance, champion → Task 1 (`currentMatchup`/`chooseWinner`/`champion`, tested) + Task 2 (`renderMatchup`/`renderChampion`). ✓
- Round labels QF/SF/Final → Task 1 (`roundLabel`, tested). ✓
- Matchup card content (cover, name, players, time, weight, rating) → Task 2 (`statsLine`/`gameCard`). ✓
- Redeal / Run again / insufficient message → Task 2 (`onClick`, `deal`). ✓
- Client-side, reuse queryGames, no games.json change → both tasks; constraints block. ✓
- Testing: pure logic Node tests + manual smoke → Task 1 (tests) + Task 2 (step 5). ✓

**Placeholder scan:** No TBD/TODO; every code step is complete. ✓

**Type consistency:** State shape `{round, nextRound, matchupIndex}` and the six pure function names are identical across Task 1 (definition + tests) and Task 2 (controller calls). `open(allGames)` defined in Task 2, called from `app.js` (Task 2 step 3) and added to `api`. `setupToFilters` consumes `{players, time, brainpower}` — the controller's `ctrl.setup` uses exactly those keys, with `players`/`time` numeric and `brainpower` a string. ✓

**Scope:** Single feature, two tasks (pure logic, then UI). Appropriate for one plan. ✓
