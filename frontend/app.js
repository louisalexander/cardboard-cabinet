function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const state = {
  facets: null,
  selectedMechanics: new Set(),
  filters: {},
  viewMode: "tile",
  sortColumn: null,
  sortDirection: "asc",
  lastGames: null,   // cached result for view toggle (M6.4)
  totalGames: 0,     // unfiltered collection size (M5.6)
};

function qs(id) { return document.getElementById(id); }

function toQuery(params) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) continue;
    if (Array.isArray(v)) p.set(k, v.join(","));
    else p.set(k, v);
  }
  return p.toString();
}

// ── Error / state display ──────────────────────────────────────────────────

function showResultsError(message) {
  const container = qs("results");
  container.innerHTML = `
    <div class="empty-state">
      <span class="empty-icon" aria-hidden="true">⚠</span>
      <h3>${escapeHtml(message)}</h3>
      <p>Check your connection and try again.</p>
      <button type="button" class="ghost-btn" id="retry-results">Retry</button>
    </div>
  `;
  container.querySelector("#retry-results").addEventListener("click", applyFilters);
  container.setAttribute("tabindex", "-1");
  container.focus();
}

function showFacetsError() {
  const existing = document.getElementById("facets-error-banner");
  if (existing) existing.remove();

  const banner = document.createElement("div");
  banner.id = "facets-error-banner";
  banner.className = "error-banner";
  banner.innerHTML = `
    <span>⚠ Filter options failed to load — filters may be incomplete.</span>
    <span class="banner-actions">
      <button type="button" class="ghost-btn-sm" id="retry-facets">Retry</button>
      <button type="button" class="banner-close" aria-label="Dismiss" id="dismiss-facets-error">×</button>
    </span>
  `;
  const header = document.querySelector("header");
  header.after(banner);

  banner.querySelector("#retry-facets").addEventListener("click", () => {
    banner.remove();
    loadFacets();
  });
  banner.querySelector("#dismiss-facets-error").addEventListener("click", () => {
    banner.remove();
    qs("search").focus();
  });
}

function showOnboarding() {
  const main = document.querySelector("main");
  main.classList.remove("grid");
  main.innerHTML = `
    <div class="onboarding-card panel">
      <span class="onboarding-icon" aria-hidden="true">🎲</span>
      <h2>Your cabinet is empty</h2>
      <p>Connect your BoardGameGeek account to import your collection. It only takes a few seconds.</p>
      <button type="button" id="onboarding-connect" class="primary-btn" autofocus>Connect BGG Account</button>
      <p class="hint">Your BGG username is stored only in your browser.</p>
    </div>
  `;
  main.querySelector("#onboarding-connect").addEventListener("click", () => {
    showUsernameForm(true);
  });
}

function restoreMainLayout() {
  const main = document.querySelector("main");
  if (!main.classList.contains("grid")) {
    main.className = "container grid";
    main.innerHTML = `
      <section class="panel" id="sidebar">
        <h2>Mechanics</h2>
        <div id="mechanics-cloud" class="tag-cloud"></div>
        <div id="filter-summary"></div>
        <h2>Filters</h2>
        <div class="filters" id="filters-panel">
          <label>Categories</label>
          <select id="categories" multiple></select>
          <p class="filter-hint">Hold Ctrl (or Cmd on Mac) to select multiple</p>

          <label>Designers</label>
          <select id="designers" multiple></select>
          <p class="filter-hint">Hold Ctrl (or Cmd on Mac) to select multiple</p>

          <label>Artists</label>
          <select id="artists" multiple></select>
          <p class="filter-hint">Hold Ctrl (or Cmd on Mac) to select multiple</p>

          <label>Publishers</label>
          <select id="publishers" multiple></select>
          <p class="filter-hint">Hold Ctrl (or Cmd on Mac) to select multiple</p>

          <div class="row">
            <div>
              <label>Year Min</label>
              <input id="year_min" type="number" placeholder="e.g. 2000" />
            </div>
            <div>
              <label>Year Max</label>
              <input id="year_max" type="number" placeholder="e.g. 2025" />
            </div>
          </div>

          <div class="row">
            <div>
              <label>Players supported</label>
              <input id="players" type="number" placeholder="e.g. 4" />
            </div>
            <div>
              <label>Time ≤ (min)</label>
              <input id="time_max" type="number" placeholder="e.g. 90" />
            </div>
          </div>

          <div class="row">
            <div>
              <label>Weight min</label>
              <input id="weight_min" type="number" step="0.01" placeholder="e.g. 2.0" />
            </div>
            <div>
              <label>Weight max</label>
              <input id="weight_max" type="number" step="0.01" placeholder="e.g. 3.5" />
            </div>
          </div>

          <div>
            <label>Avg rating ≥</label>
            <input id="rating_min" type="number" step="0.1" placeholder="e.g. 7.0" />
          </div>

          <div class="actions">
            <button type="button" id="clear">Clear</button>
          </div>
        </div>
      </section>

      <section>
        <h2>Results</h2>
        <div id="stats"></div>
        <div id="results" class="cards"></div>
      </section>
    `;
    bindFilterListeners();
  }
}

// ── Facets / filters ───────────────────────────────────────────────────────

async function loadFacets() {
  try {
    const r = await fetch("/api/facets");
    if (!r.ok) { showFacetsError(); return; }
    const data = await r.json();
    state.facets = data;
    renderTagCloud(data.mechanics);
    fillSelect(qs("categories"), data.categories);
    fillSelect(qs("designers"), data.designers);
    fillSelect(qs("artists"), data.artists);
    fillSelect(qs("publishers"), data.publishers);
    updateSummary();
  } catch {
    showFacetsError();
  }
}

function fillSelect(sel, dict) {
  if (!sel) return;
  sel.innerHTML = "";
  const entries = Object.entries(dict).sort((a, b) => b[1] - a[1]);
  for (const [name, count] of entries) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = `${name} (${count})`;
    sel.appendChild(opt);
  }
}

function renderTagCloud(mechanics) {
  const cloud = qs("mechanics-cloud");
  if (!cloud) return;
  cloud.innerHTML = "";
  const entries = Object.entries(mechanics).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? entries[0][1] : 1;
  for (const [name, count] of entries) {
    const scale = 0.85 + (count / max) * 0.9;
    const tag = document.createElement("button");
    tag.type = "button";
    tag.className = "tag";
    tag.style.fontSize = `${(14 * scale).toFixed(1)}px`;
    tag.setAttribute("aria-label", `Filter by mechanic: ${name}`);
    tag.innerHTML = `<span>${escapeHtml(name)}</span><span class="count">(${count})</span>`;
    tag.addEventListener("click", () => {
      if (state.selectedMechanics.has(name)) state.selectedMechanics.delete(name);
      else state.selectedMechanics.add(name);
      tag.classList.toggle("active");
      updateSummary();
      applyFilters();
    });
    cloud.appendChild(tag);
  }
}

function getMulti(sel) {
  if (!sel) return [];
  return Array.from(sel.selectedOptions).map(o => o.value);
}

function collectFilters() {
  state.filters = {
    mechanics:  [...state.selectedMechanics],
    categories: getMulti(qs("categories")),
    designers:  getMulti(qs("designers")),
    artists:    getMulti(qs("artists")),
    publishers: getMulti(qs("publishers")),
    year_min:   qs("year_min")?.value || null,
    year_max:   qs("year_max")?.value || null,
    players:    qs("players")?.value || null,
    time_max:   qs("time_max")?.value || null,
    weight_min: qs("weight_min")?.value || null,
    weight_max: qs("weight_max")?.value || null,
    rating_min: qs("rating_min")?.value || null,
    search:     qs("search")?.value || null,
  };
}

function updateSummary() {
  const container = qs("filter-summary");
  if (!container) return;
  collectFilters();

  const chips = [];

  for (const m of state.selectedMechanics) {
    chips.push({ label: escapeHtml(m), type: "mechanic", value: m });
  }

  const labelMap = {
    year_min: v => `From ${v}`,
    year_max: v => `Until ${v}`,
    players:  v => `Players: ${v}`,
    time_max: v => `Time ≤ ${v} min`,
    weight_min: v => `Weight ≥ ${v}`,
    weight_max: v => `Weight ≤ ${v}`,
    rating_min: v => `Rating ≥ ${v}`,
    search:   v => `Search: "${v}"`,
  };

  for (const [key, fn] of Object.entries(labelMap)) {
    const v = state.filters[key];
    if (v) chips.push({ label: escapeHtml(fn(v)), type: key, value: v });
  }

  for (const cat of state.filters.categories || [])
    chips.push({ label: escapeHtml(cat), type: "category", value: cat });
  for (const d of state.filters.designers || [])
    chips.push({ label: escapeHtml(d), type: "designer", value: d });
  for (const a of state.filters.artists || [])
    chips.push({ label: escapeHtml(a), type: "artist", value: a });
  for (const p of state.filters.publishers || [])
    chips.push({ label: escapeHtml(p), type: "publisher", value: p });

  if (chips.length === 0) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = `
    <div class="filter-chips">
      ${chips.map(c => `
        <button type="button" class="filter-chip" data-type="${escapeHtml(c.type)}" data-value="${escapeHtml(c.value)}">
          ${c.label} <span aria-hidden="true">×</span><span class="sr-only">Remove filter</span>
        </button>`).join("")}
    </div>`;

  container.querySelectorAll(".filter-chip").forEach(chip => {
    chip.addEventListener("click", () => removeFilterChip(chip.dataset.type, chip.dataset.value));
  });
}

function removeFilterChip(type, value) {
  if (type === "mechanic") {
    state.selectedMechanics.delete(value);
    document.querySelectorAll(".tag").forEach(tag => {
      if (tag.querySelector("span")?.textContent === value) tag.classList.remove("active");
    });
  } else if (type === "search") {
    const s = qs("search");
    if (s) s.value = "";
  } else if (type === "category") {
    const sel = qs("categories");
    if (sel) Array.from(sel.options).forEach(o => { if (o.value === value) o.selected = false; });
  } else if (type === "designer") {
    const sel = qs("designers");
    if (sel) Array.from(sel.options).forEach(o => { if (o.value === value) o.selected = false; });
  } else if (type === "artist") {
    const sel = qs("artists");
    if (sel) Array.from(sel.options).forEach(o => { if (o.value === value) o.selected = false; });
  } else if (type === "publisher") {
    const sel = qs("publishers");
    if (sel) Array.from(sel.options).forEach(o => { if (o.value === value) o.selected = false; });
  } else {
    const input = qs(type);
    if (input) input.value = "";
  }
  updateSummary();
  applyFilters();
}

// ── Games fetch / render ───────────────────────────────────────────────────

let filterAbortController = null;
let searchTimer = null;

async function applyFilters() {
  if (filterAbortController) filterAbortController.abort();
  filterAbortController = new AbortController();
  const signal = filterAbortController.signal;

  const resultsEl = qs("results");
  let loadingBar = null;
  let showBarTimer = null;

  // Show in-flight indicator after 150ms (skip for very fast responses)
  showBarTimer = setTimeout(() => {
    if (resultsEl && resultsEl.querySelector(".card")) {
      resultsEl.style.opacity = "0.5";
    }
    loadingBar = document.createElement("div");
    loadingBar.className = "filter-loading-bar";
    loadingBar.innerHTML = `<div class="filter-loading-fill"></div>`;
    const statsEl = qs("stats");
    if (statsEl) statsEl.after(loadingBar);
  }, 150);

  try {
    collectFilters();
    const query = toQuery(state.filters);
    const r = await fetch(`/api/games?${query}`, { signal });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    state.lastGames = data.games;
    state.totalGames = data.total;
    renderResults(data.games, data.total, data.filtered);
  } catch (err) {
    if (err.name === "AbortError") return;
    showResultsError("Could not load games.");
  } finally {
    clearTimeout(showBarTimer);
    if (loadingBar) loadingBar.remove();
    if (resultsEl) resultsEl.style.opacity = "";
  }
}

function renderResults(games, total, filtered) {
  const stats = qs("stats");
  if (stats) {
    const hasFilters = Object.entries(state.filters).some(([, v]) =>
      v && (Array.isArray(v) ? v.length > 0 : true)
    );
    const gameWord = total === 1 ? "game" : "games";
    if (hasFilters && total !== filtered) {
      const activeCount = Object.entries(state.filters).filter(([, v]) =>
        v && (Array.isArray(v) ? v.length > 0 : true)
      ).length;
      stats.innerHTML = `${filtered} of ${total} ${gameWord} <span class="filter-count-badge">${activeCount} filter${activeCount !== 1 ? "s" : ""} active</span>`;
    } else {
      stats.textContent = `${total} ${gameWord}`;
    }
  }

  const container = qs("results");
  if (!container) return;
  container.innerHTML = "";

  if (games.length === 0 && total > 0) {
    const searchVal = qs("search")?.value;
    const searchHint = searchVal
      ? ` Search is also active — clear it above to search by name only.`
      : "";
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon" aria-hidden="true">🔍</span>
        <h3>No games match your filters</h3>
        <p>Try removing a filter or broadening your search.${escapeHtml(searchHint)}</p>
        <button type="button" class="ghost-btn" id="clear-from-empty">Clear all filters</button>
      </div>
    `;
    container.querySelector("#clear-from-empty").addEventListener("click", clearAll);
    return;
  }

  if (state.viewMode === "list") {
    renderListView(games, container);
  } else {
    renderTileView(games, container);
  }
}

function renderTileView(games, container) {
  for (const g of games) {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `
      <img src="${escapeHtml(g.thumbnail || g.image || "")}" alt="${escapeHtml(g.name)} box art">
      <div class="body">
        <a class="name" href="https://boardgamegeek.com/boardgame/${escapeHtml(String(g.id))}"
           target="_blank" rel="noopener noreferrer">${escapeHtml(g.name)}</a>
        <div class="meta">
          ${escapeHtml(String(g.year || "—"))} •
          ${escapeHtml(String(g.min_players || "?"))}–${escapeHtml(String(g.max_players || "?"))} players •
          ${escapeHtml(String(g.playing_time || "?"))} min •
          weight ${escapeHtml(String(g.weight?.toFixed ? g.weight.toFixed(2) : (g.weight ?? "—")))}
        </div>
        <div class="meta">
          Rating: ${escapeHtml(String(g.avg_rating?.toFixed ? g.avg_rating.toFixed(2) : (g.avg_rating ?? "—")))}
          (Bayes: ${escapeHtml(String(g.bayes_rating?.toFixed ? g.bayes_rating.toFixed(2) : (g.bayes_rating ?? "—")))}) •
          My: ${escapeHtml(String(g.my_rating ?? "—"))}
        </div>
        <div class="badges">
          ${g.mechanics.slice(0, 3).map(m =>
            `<button type="button" class="badge" data-type="mechanics" data-value="${escapeHtml(m)}"
              aria-label="Filter by mechanic: ${escapeHtml(m)}">${escapeHtml(m)}</button>`
          ).join("")}
        </div>
      </div>
    `;
    el.querySelectorAll(".badge").forEach(badge => {
      badge.addEventListener("click", () => filterByValue(badge.dataset.type, badge.dataset.value));
    });
    container.appendChild(el);
  }
}

function renderListView(games, container) {
  if (state.sortColumn) {
    games = [...games].sort((a, b) => {
      const aVal = getSortValue(a, state.sortColumn);
      const bVal = getSortValue(b, state.sortColumn);
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = typeof aVal === "string" ? aVal.localeCompare(bVal) : aVal - bVal;
      return state.sortDirection === "asc" ? cmp : -cmp;
    });
  }

  const wrapper = document.createElement("div");
  wrapper.className = "table-scroll";

  const table = document.createElement("table");
  table.className = "list-table";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>Image</th>
      ${["name","year","players","playing_time","weight","avg_rating","bayes_rating","my_rating"]
        .map(col => {
          const labels = { name:"Name", year:"Year", players:"Players", playing_time:"Time (min)",
            weight:"Weight", avg_rating:"Avg Rating", bayes_rating:"Bayes Rating", my_rating:"My Rating" };
          const ariaSort = state.sortColumn === col
            ? (state.sortDirection === "asc" ? "ascending" : "descending")
            : "none";
          return `<th class="sortable" data-column="${col}" role="columnheader" aria-sort="${ariaSort}">
            ${labels[col]} <span class="sort-indicator" aria-hidden="true">${getSortIndicator(col)}</span>
          </th>`;
        }).join("")}
      <th>Mechanics</th>
      <th>Categories</th>
    </tr>
  `;
  thead.querySelectorAll(".sortable").forEach(th => {
    th.addEventListener("click", () => handleSort(th.dataset.column));
  });
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const g of games) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><img src="${escapeHtml(g.thumbnail || g.image || "")}" alt="${escapeHtml(g.name)} box art" class="list-thumbnail"></td>
      <td class="game-name">
        <a href="https://boardgamegeek.com/boardgame/${escapeHtml(String(g.id))}"
           target="_blank" rel="noopener noreferrer">${escapeHtml(g.name)}</a>
      </td>
      <td>${escapeHtml(String(g.year || "—"))}</td>
      <td>${escapeHtml(String(g.min_players || "?"))}–${escapeHtml(String(g.max_players || "?"))}</td>
      <td>${escapeHtml(String(g.playing_time || "?"))}</td>
      <td>${escapeHtml(String(g.weight?.toFixed ? g.weight.toFixed(2) : (g.weight ?? "—")))}</td>
      <td>${escapeHtml(String(g.avg_rating?.toFixed ? g.avg_rating.toFixed(2) : (g.avg_rating ?? "—")))}</td>
      <td>${escapeHtml(String(g.bayes_rating?.toFixed ? g.bayes_rating.toFixed(2) : (g.bayes_rating ?? "—")))}</td>
      <td>${escapeHtml(String(g.my_rating ?? "—"))}</td>
      <td>${g.mechanics?.map(m =>
        `<button type="button" class="badge" data-type="mechanics" data-value="${escapeHtml(m)}"
          aria-label="Filter by mechanic: ${escapeHtml(m)}">${escapeHtml(m)}</button>`
      ).join(" ") || "—"}</td>
      <td>${g.categories?.map(c =>
        `<button type="button" class="badge" data-type="categories" data-value="${escapeHtml(c)}"
          aria-label="Filter by category: ${escapeHtml(c)}">${escapeHtml(c)}</button>`
      ).join(" ") || "—"}</td>
    `;
    row.querySelectorAll(".badge").forEach(badge => {
      badge.addEventListener("click", () => filterByValue(badge.dataset.type, badge.dataset.value));
    });
    tbody.appendChild(row);
  }
  table.appendChild(tbody);
  wrapper.appendChild(table);
  container.appendChild(wrapper);
}

function getSortValue(game, column) {
  const map = {
    name: game.name,
    year: game.year || 0,
    players: game.min_players || 0,
    playing_time: game.playing_time || 0,
    weight: game.weight || 0,
    avg_rating: game.avg_rating || 0,
    bayes_rating: game.bayes_rating || 0,
    my_rating: game.my_rating || 0,
  };
  return map[column] ?? null;
}

function getSortIndicator(column) {
  if (state.sortColumn !== column) return "⇅";
  return state.sortDirection === "asc" ? "↑" : "↓";
}

function handleSort(column) {
  if (state.sortColumn === column) {
    state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
  } else {
    state.sortColumn = column;
    state.sortDirection = "asc";
  }
  if (state.lastGames) {
    renderResults(state.lastGames, state.totalGames,
      state.lastGames.length); // re-render from cache
  } else {
    applyFilters();
  }
}

function filterByValue(type, value) {
  if (type === "mechanics") {
    if (state.selectedMechanics.has(value)) state.selectedMechanics.delete(value);
    else state.selectedMechanics.add(value);
    document.querySelectorAll(".tag").forEach(tag => {
      if (tag.querySelector("span")?.textContent === value)
        tag.classList.toggle("active", state.selectedMechanics.has(value));
    });
  } else if (type === "categories") {
    const sel = qs("categories");
    if (sel) Array.from(sel.options).forEach(o => { if (o.value === value) o.selected = true; });
  }
  updateSummary();
  applyFilters();
}

function toggleView() {
  state.viewMode = state.viewMode === "tile" ? "list" : "tile";
  const button = qs("view-toggle");
  if (state.viewMode === "list") {
    button.textContent = "List view";
    button.setAttribute("aria-label", "Switch to tile view");
    button.classList.add("active");
    // Apply default sort on first entry to list view
    if (state.sortColumn === null) {
      state.sortColumn = "avg_rating";
      state.sortDirection = "desc";
    }
  } else {
    button.textContent = "Tile view";
    button.setAttribute("aria-label", "Switch to list view");
    button.classList.remove("active");
  }
  // Use cached games if available; avoid redundant API call
  if (state.lastGames) {
    renderResults(state.lastGames, state.totalGames, state.lastGames.length);
  } else {
    applyFilters();
  }
}

function clearAll() {
  state.selectedMechanics.clear();
  document.querySelectorAll(".tag.active").forEach(t => t.classList.remove("active"));
  ["categories", "designers", "artists", "publishers"].forEach(id => {
    const el = qs(id);
    if (el) el.selectedIndex = -1;
  });
  ["year_min","year_max","players","time_max","weight_min","weight_max","rating_min"].forEach(id => {
    const el = qs(id);
    if (el) el.value = "";
  });
  const search = qs("search");
  if (search) search.value = "";
  updateSummary();
  applyFilters();
  if (search) search.focus();
}

// ── Inline username form (replaces window.prompt) ─────────────────────────

function showUsernameForm(fromOnboarding = false) {
  const stored = localStorage.getItem("bgg_username") || "";

  if (fromOnboarding) {
    // Self-contained form inside onboarding card
    const card = document.querySelector(".onboarding-card");
    if (!card) { doRefreshWithUsername(stored || null); return; }
    card.innerHTML = `
      <span class="onboarding-icon" aria-hidden="true">🎲</span>
      <h2>Connect BGG Account</h2>
      <form id="bgg-form" class="username-form">
        <input id="bgg-username-input" type="text" placeholder="BGG username"
               autocomplete="username" value="${escapeHtml(stored)}" />
        <button type="submit" class="primary-btn">Sync Collection</button>
        <button type="button" class="ghost-btn" id="cancel-onboarding">Cancel</button>
      </form>
      <p class="hint">Your username is stored in your browser for next time.</p>
    `;
    card.querySelector("#cancel-onboarding").addEventListener("click", showOnboarding);
    card.querySelector("#bgg-form").addEventListener("submit", e => {
      e.preventDefault();
      const username = card.querySelector("#bgg-username-input").value.trim() || null;
      doRefreshWithUsername(username);
    });
    card.querySelector("#bgg-username-input").focus();
    return;
  }

  // Expand header toolbar
  const toolbar = document.querySelector(".toolbar");
  const refreshBtn = qs("refresh");
  refreshBtn.style.display = "none";

  const form = document.createElement("form");
  form.id = "bgg-inline-form";
  form.className = "username-form";
  form.innerHTML = `
    <input id="bgg-username-input" type="text" placeholder="BGG username"
           autocomplete="username" value="${escapeHtml(stored)}" />
    <button type="submit" class="primary-btn" id="sync-btn">Sync Collection</button>
    <button type="button" class="ghost-btn" id="cancel-sync">Cancel</button>
  `;
  toolbar.appendChild(form);

  form.querySelector("#bgg-username-input").focus();
  form.querySelector("#cancel-sync").addEventListener("click", () => {
    form.remove();
    refreshBtn.style.display = "";
    refreshBtn.focus();
  });
  form.addEventListener("submit", e => {
    e.preventDefault();
    const username = form.querySelector("#bgg-username-input").value.trim() || null;
    form.remove();
    refreshBtn.style.display = "";
    doRefreshWithUsername(username);
  });
}

async function doRefreshWithUsername(username) {
  if (username) {
    try { localStorage.setItem("bgg_username", username); } catch {}
  }

  const refreshBtn = qs("refresh");
  const originalText = refreshBtn ? refreshBtn.textContent : "";
  if (refreshBtn) {
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '<span class="rolling-dice" aria-hidden="true">🎲</span> Syncing…';
  }

  // Progress block
  const progressDiv = document.createElement("div");
  progressDiv.className = "refresh-progress";
  progressDiv.innerHTML = `
    <div class="progress-bar"><div class="progress-fill indeterminate"></div></div>
    <div class="progress-text">Syncing with BoardGameGeek…</div>
  `;
  const toolbar = document.querySelector(".toolbar");
  if (toolbar) toolbar.after(progressDiv);

  const preRefreshTotal = state.totalGames;

  try {
    const body = username ? JSON.stringify({ username }) : "{}";
    const r = await fetch("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    const data = await r.json();

    // Store last synced timestamp
    try { localStorage.setItem("bgg_last_synced", new Date().toISOString()); } catch {}

    // Complete progress
    const fill = progressDiv.querySelector(".progress-fill");
    fill.classList.remove("indeterminate");
    fill.style.width = "100%";

    const newCount = data.total_hydrated;
    const diff = newCount - preRefreshTotal;
    const diffText = preRefreshTotal > 0 && diff !== 0
      ? ` (${diff > 0 ? "+" : ""}${diff} since last sync)`
      : "";

    if (newCount === 0) {
      progressDiv.querySelector(".progress-text").innerHTML =
        `<span style="color:var(--accent-3)">⚠</span> Sync completed but no games were found. Check that your BGG collection is public.`;
    } else {
      progressDiv.querySelector(".progress-text").innerHTML =
        `<span style="color:var(--accent-2)" aria-hidden="true">✓</span> Synced successfully — ${newCount} games imported${escapeHtml(diffText)}.`;
    }

    // Invalidate cache, reload
    state.lastGames = null;
    restoreMainLayout();
    await loadFacets();
    await applyFilters();
    updateLastSynced();

    setTimeout(() => progressDiv.remove(), 4000);
  } catch (err) {
    const fill = progressDiv.querySelector(".progress-fill");
    fill.classList.remove("indeterminate");
    fill.style.width = "100%";
    fill.style.background = "var(--accent-4)";
    progressDiv.querySelector(".progress-text").textContent = `Failed: ${err.message}`;
    const hint = document.createElement("p");
    hint.className = "progress-hint";
    hint.textContent = "If this keeps happening, check that your BGG username is correct.";
    progressDiv.appendChild(hint);
    setTimeout(() => progressDiv.remove(), 8000);
  } finally {
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.textContent = originalText;
    }
  }
}

function updateLastSynced() {
  const footer = document.querySelector("footer small");
  if (!footer) return;
  try {
    const raw = localStorage.getItem("bgg_last_synced");
    if (!raw) {
      footer.textContent = "Never synced — use the Refresh button to import your collection.";
      return;
    }
    const date = new Date(raw);
    if (isNaN(date)) { footer.textContent = "Last synced: unknown via BoardGameGeek"; return; }
    const secs = Math.floor((Date.now() - date) / 1000);
    let rel;
    if (secs < 60) rel = "just now";
    else if (secs < 3600) rel = `${Math.floor(secs / 60)} minutes ago`;
    else if (secs < 86400) rel = `${Math.floor(secs / 3600)} hours ago`;
    else rel = `${Math.floor(secs / 86400)} days ago`;
    footer.textContent = `Last synced: ${rel} via BoardGameGeek`;
  } catch {
    footer.textContent = "Last synced: unknown via BoardGameGeek";
  }
}

// ── Event binding ──────────────────────────────────────────────────────────

function bindFilterListeners() {
  const clearBtn = qs("clear");
  if (clearBtn) clearBtn.addEventListener("click", clearAll);

  ["categories","designers","artists","publishers"].forEach(id => {
    const el = qs(id);
    if (el) el.addEventListener("change", applyFilters);
  });

  ["year_min","year_max","rating_min"].forEach(id => {
    const el = qs(id);
    if (el) el.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(applyFilters, 500);
    });
  });

  ["players","time_max","weight_min","weight_max"].forEach(id => {
    const el = qs(id);
    if (el) el.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(applyFilters, 500);
    });
  });
}

window.addEventListener("DOMContentLoaded", async () => {
  updateLastSynced();

  qs("refresh").addEventListener("click", () => showUsernameForm(false));
  qs("view-toggle").addEventListener("click", toggleView);

  // Debounced search (M5.3)
  qs("search").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(applyFilters, 300);
  });
  qs("search").addEventListener("keydown", e => {
    if (e.key === "Enter") {
      clearTimeout(searchTimer);
      applyFilters();
    }
  });

  bindFilterListeners();

  // Show skeleton while loading
  const results = qs("results");
  results.innerHTML = Array(3).fill(`
    <div class="card skeleton">
      <div class="skeleton-img"></div>
      <div class="body">
        <div class="skeleton-line wide"></div>
        <div class="skeleton-line narrow"></div>
      </div>
    </div>
  `).join("");

  await loadFacets();
  const r = await fetch("/api/games").catch(() => null);
  if (!r || !r.ok) {
    results.innerHTML = "";
    showResultsError("Could not load games.");
    return;
  }
  const data = await r.json();

  if (data.total === 0) {
    showOnboarding();
  } else {
    state.lastGames = data.games;
    state.totalGames = data.total;
    renderResults(data.games, data.total, data.filtered);
  }
});
