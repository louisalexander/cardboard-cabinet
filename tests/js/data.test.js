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
