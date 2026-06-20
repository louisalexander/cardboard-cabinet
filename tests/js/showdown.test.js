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
