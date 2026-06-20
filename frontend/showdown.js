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
