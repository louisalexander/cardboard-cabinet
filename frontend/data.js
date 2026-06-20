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
