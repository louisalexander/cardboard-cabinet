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
    // A <div role="button"> rather than a <button>: Safari does not lay out the
    // flex children of a <button> (image + text), so the card box renders but its
    // contents stay blank. Taps still work via the data-id click delegation.
    return '<div class="sd-card" role="button" data-id="' + esc(g.id) + '">'
      + (img ? '<img src="' + esc(img) + '" alt="">' : "")
      + '<div class="sd-card-body"><h3>' + esc(g.name) + "</h3>"
      + '<div class="sd-stats">' + statsLine(g) + "</div></div></div>";
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
    forceRepaint();
  }

  // iOS Safari can leave the image cards inside the position:fixed overlay
  // unpainted on first render (blank until a repaint is forced, e.g. by rotating
  // the device). Promoting them to their own compositing layer forces the paint.
  function forceRepaint() {
    requestAnimationFrame(function () {
      var els = screen().querySelectorAll(".sd-card, .sd-champion img");
      for (var i = 0; i < els.length; i++) els[i].style.transform = "translateZ(0)";
    });
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
    forceRepaint();
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

  function onKeydown(e) {
    if (e.key === "Escape") close();
  }

  function open(allGames) {
    ctrl.allGames = allGames || [];
    ctrl.setup = { players: 2, time: null, brainpower: null };
    ctrl.candidates = [];
    ctrl.state = null;
    const ov = overlay();
    ov.hidden = false;
    ov.addEventListener("click", onClick);
    document.addEventListener("keydown", onKeydown);
    renderSetup("");
  }

  function close() {
    const ov = overlay();
    ov.hidden = true;
    ov.removeEventListener("click", onClick);
    document.removeEventListener("keydown", onKeydown);
  }

  const api = { setupToFilters, dealBracket, currentMatchup, chooseWinner, champion, roundLabel, open };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.Showdown = Object.assign(window.Showdown || {}, api);
})();
