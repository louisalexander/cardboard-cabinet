# Design: "What should we play?" — a bracket showdown

**Date:** 2026-06-20
**Status:** Approved (design); pending implementation plan

## Goal

Help two people (the user and his wife) decide what to play tonight without
drowning in their ~125-game collection. The existing app is a query/filter
browser — great for "show me 2-player games under 45 min," but it leaves a long
list and the decision unmade. This feature adds a fast "decide now" mode: set
tonight's situation in a few taps, then crown a single game through a
this-or-that single-elimination bracket.

The two frictions this targets (from brainstorming): **too many options /
paralysis** and **setting tonight's constraints fast**. Explicitly out of scope:
play-history / "haven't played in a while" freshness and "good at 2 players"
quality signals — both need play-tracking data the app does not have.

## Non-goals

- No backend, no new data, no changes to `games.json`. 100% client-side, fits
  the static Cloudflare Pages deployment.
- No play logging, no persistence of past showdowns, no accounts.
- No change to the existing filter/search/browse UI or `app.js` behavior.

## User flow

1. User taps **🎲 What should we play?** in the header → a full-screen overlay
   opens over the collection browser.
2. **Setup screen** — three chip controls (players / time / brainpower) and two
   buttons: **Deal the bracket** (uses the constraints) and **Surprise us**
   (ignores constraints, brackets the whole collection).
3. **Showdown** — the app seeds up to 8 matching games into a single-elimination
   bracket and presents head-to-head matchups. Each tap sends the chosen game
   through; the other is eliminated.
4. **Champion** — a celebratory reveal of the winning game with full details,
   plus **Run it again** (new bracket, same setup) and **Done** (close overlay).

## Components

### New: `frontend/showdown.js`
A small module holding (a) **pure bracket/seed logic** (unit-tested) and (b) the
DOM controller for the overlay. Pure functions take an injectable RNG so tests
are deterministic.

**Pure functions (exported for Node tests):**

- `setupToFilters(setup) -> filters` — maps the setup chips to the same filter
  object `queryGames` consumes:
  - **players**: `2|3|4|5` → `{players: N}` (the "5+" chip uses `players: 5`).
    Omitted/Any → no players filter.
  - **time**: `30|60|90|120` → `{time_max: N}`. Any → omitted.
  - **brainpower**: `light` → `{weight_max: 1.75}`; `medium` →
    `{weight_min: 1.76, weight_max: 3.25}`; `heavy` → `{weight_min: 3.26}`;
    Any → omitted. (Note: any non-Any brainpower excludes null-weight games, by
    the existing NULL-exclusion filter semantics — acceptable, since brainpower
    is unknown for those.)

- `dealBracket(games, rng = Math.random) -> state` — given the already-filtered
  candidate games, choose the bracket size = the largest power of 2 that is
  `<= games.length`, capped at **8** (so 8+→8, 4–7→4, 2–3→2). Randomly sample
  that many games (shuffle + take), and return the initial bracket state. If
  `games.length < 2`, return `{ insufficient: true, count: games.length }`.

- `currentMatchup(state) -> [gameA, gameB] | null` — the two games in the
  current matchup, or `null` if a champion exists.

- `chooseWinner(state, winnerId) -> state` — advance the chosen game to the next
  round and drop the other. When the current round's matchups are exhausted, the
  winners become the next round. Pure: returns a new state, does not mutate.

- `champion(state) -> game | null` — the winner when one contestant remains,
  else `null`.

- `roundLabel(roundSize) -> string` — `8 → "Quarterfinal"`, `4 → "Semifinal"`,
  `2 → "Final"`; any other size → `"Round of {n}"`.

**Bracket state shape:** `{ round: Game[], nextRound: Game[], matchupIndex:
number }`. `currentMatchup` reads `round[2*matchupIndex]` and
`round[2*matchupIndex+1]`. `chooseWinner` pushes the winner to `nextRound`,
increments `matchupIndex`; when `2*matchupIndex >= round.length`, it sets
`round = nextRound`, `nextRound = []`, `matchupIndex = 0`. Champion =
`round.length === 1`.

**DOM controller (same module):** opens/closes the overlay, renders the three
screens (setup → matchup → champion), wires taps to `chooseWinner`, and calls
`queryGames(allGames, setupToFilters(setup))` (from `data.js`) to get
candidates. Reads the collection via the existing `loadCollection()` /
`state.allGames` already loaded by `app.js`.

### Modified: `frontend/index.html`
- Add the **🎲 What should we play?** button to the header toolbar.
- Add the overlay markup (a `<div id="showdown-overlay" hidden>` with the three
  screen containers).
- Load `showdown.js` after `data.js` and `app.js` (deferred).

### Modified: `frontend/app.js`
Minimal: on startup, after the collection loads, wire the header button to
`Showdown.open(state.allGames)`. No other changes; render functions untouched.

### Modified: `frontend/styles.css`
Overlay, chip controls, the two-card matchup layout, and the champion reveal.
Follows the existing visual language (fonts, color tokens, card styling).

## Matchup card content

Each matchup card shows: cover image, name, player range (`min–max`), playing
time (`{n}m`), weight (`⚖ {n.n}`, or `⚖ —` when unknown), and average rating
(`★ {n.n}`). This mirrors the data already on the browse cards; no new fields.

## Edge cases

- **< 2 candidates:** setup screen shows "Only N games match — loosen a filter
  or hit Surprise us." No bracket dealt.
- **Odd / non-power-of-2 candidate counts:** bracket size rounds down to a power
  of 2 (handled by `dealBracket`); some matching games simply don't enter this
  bracket. **Redeal** reshuffles for a different draw.
- **Null-weight games:** included under brainpower = Any; excluded when a
  specific brainpower is chosen (existing filter semantics).
- **Surprise us with < 2 games total:** effectively impossible (collection is
  125), but the same insufficient-count guard applies.

## Controls on the showdown screens

- Matchup screen: progress line (e.g. `Quarterfinal · 2 of 4`), **↺ Redeal**
  (new bracket, same setup), and a close (✕) back to browsing.
- Champion screen: **↺ Run it again** and **Done**.

## Testing

- **Unit (Node `--test`, like `tests/js/data.test.js`):** `tests/js/showdown.test.js`
  covering `setupToFilters` mappings, `dealBracket` sizing (8+→8, 5→4, 3→2,
  1→insufficient) and determinism with a seeded RNG, `chooseWinner` round
  progression (8 → 4 → 2 → 1 across the right number of taps), `champion`, and
  `roundLabel`. Inject a deterministic RNG (e.g. a seeded generator) for sampling
  tests.
- **Smoke (manual):** serve `frontend/` statically; run a full showdown with
  constraints and with Surprise us; verify redeal, champion, run-again, and the
  insufficient-matches message.

## Risks

- **Bracket bookkeeping** (advancing rounds, exhausting matchups) is the main
  correctness risk — covered by the `chooseWinner` progression tests.
- **Filter reuse**: seeding must go through `queryGames` so showdown results stay
  consistent with the browse view; the `setupToFilters` mapping is the only new
  filter surface and is unit-tested.
