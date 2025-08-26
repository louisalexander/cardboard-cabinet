const state = {
    facets: null,
    selectedMechanics: new Set(),
    filters: {},
    viewMode: 'tile', // 'tile' or 'list'
    sortColumn: null,
    sortDirection: 'asc' // 'asc' or 'desc'
  };
  
  function qs(id){ return document.getElementById(id); }
  
  function toQuery(params) {
    const p = new URLSearchParams();
    for (const [k,v] of Object.entries(params)) {
      if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length===0)) continue;
      if (Array.isArray(v)) p.set(k, v.join(","));
      else p.set(k, v);
    }
    return p.toString();
  }
  
  async function loadFacets() {
    try {
      const r = await fetch("/api/facets");
      if (!r.ok) {
        console.error("Failed to load facets:", r.status, r.statusText);
        return;
      }
      const data = await r.json();
      console.log("Loaded facets:", data);
      state.facets = data;
      renderTagCloud(data.mechanics);
      fillSelect(qs("categories"), data.categories);
      fillSelect(qs("designers"), data.designers);
      fillSelect(qs("artists"), data.artists);
      fillSelect(qs("publishers"), data.publishers);
      updateSummary();
    } catch (error) {
      console.error("Error loading facets:", error);
    }
  }
  
  function fillSelect(sel, dict) {
    sel.innerHTML = "";
    const entries = Object.entries(dict).sort((a,b)=> b[1]-a[1]);
    for (const [name, count] of entries) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = `${name} (${count})`;
      sel.appendChild(opt);
    }
  }
  
  function renderTagCloud(mechanics) {
    const cloud = qs("mechanics-cloud");
    cloud.innerHTML = "";
    const entries = Object.entries(mechanics).sort((a,b)=> b[1]-a[1]);
    const max = entries.length ? entries[0][1] : 1;
    for (const [name, count] of entries) {
      const scale = 0.85 + (count/max) * 0.9; // 0.85–1.75
      const tag = document.createElement("button");
      tag.className = "tag";
      tag.style.fontSize = `${(14*scale).toFixed(1)}px`;
      tag.innerHTML = `<span>${name}</span><span class="count">(${count})</span>`;
      tag.addEventListener("click", ()=>{
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
    return Array.from(sel.selectedOptions).map(o=>o.value);
  }
  
  function collectFilters() {
    state.filters = {
      mechanics: [...state.selectedMechanics],
      categories: getMulti(qs("categories")),
      designers:  getMulti(qs("designers")),
      artists:    getMulti(qs("artists")),
      publishers: getMulti(qs("publishers")),
      year_min:   qs("year_min").value || null,
      year_max:   qs("year_max").value || null,
      players:    qs("players").value || null,
      time_max:   qs("time_max").value || null,
      weight_min: qs("weight_min").value || null,
      weight_max: qs("weight_max").value || null,
      rating_min: qs("rating_min").value || null,
      search:     qs("search").value || null
    };
  }
  
  function updateSummary() {
    const ul = document.getElementById("summary");
    collectFilters();
    ul.innerHTML = "";
    const pairs = Object.entries(state.filters).filter(([k,v])=>{
      if (!v || (Array.isArray(v) && v.length===0)) return false;
      return true;
    });
    for (const [k,v] of pairs) {
      const li = document.createElement("li");
      li.textContent = `${k}: ${Array.isArray(v) ? v.join(", ") : v}`;
      ul.appendChild(li);
    }
  }
  
  async function applyFilters() {
    try {
      collectFilters();
      const query = toQuery(state.filters);
      console.log("Applying filters with query:", query);
      const r = await fetch(`/api/games?${query}`);
      if (!r.ok) {
        console.error("Failed to fetch games:", r.status, r.statusText);
        return;
      }
      const data = await r.json();
      console.log("Fetched games:", data.length, "games");
      renderResults(data);
    } catch (error) {
      console.error("Error applying filters:", error);
    }
  }
  
  function renderResults(games) {
    const stats = qs("stats");
    stats.textContent = `${games.length} game(s)`;
    const container = qs("results");
    container.innerHTML = "";
    
    if (state.viewMode === 'list') {
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
        <img src="${g.thumbnail || g.image || ""}" alt="">
        <div class="body">
          <div class="name clickable" data-game-id="${g.id}">${g.name}</div>
          <div class="meta">
            ${g.year || "—"} • ${g.min_players || "?"}–${g.max_players || "?"} players • ${g.playing_time || "?"} min • weight ${g.weight?.toFixed ? g.weight.toFixed(2) : (g.weight ?? "—")}
          </div>
          <div class="meta">Rating: ${g.avg_rating?.toFixed ? g.avg_rating.toFixed(2) : (g.avg_rating ?? "—")} (Bayes: ${g.bayes_rating?.toFixed ? g.bayes_rating.toFixed(2) : (g.bayes_rating ?? "—")}) • My: ${g.my_rating ?? "—"}</div>
          <div class="badges">
            ${g.mechanics.slice(0,3).map(m=>`<span class="badge clickable" data-type="mechanics" data-value="${m}">${m}</span>`).join("")}
          </div>
        </div>
      `;
      
      // Add click event listeners
      el.querySelector('.name').addEventListener('click', () => openBGGPage(g.id, g.name));
      el.querySelectorAll('.badge').forEach(badge => {
        badge.addEventListener('click', () => filterByValue(badge.dataset.type, badge.dataset.value));
      });
      
      container.appendChild(el);
    }
  }
  
  function renderListView(games, container) {
    // Sort games if a sort column is selected
    if (state.sortColumn) {
      games = [...games].sort((a, b) => {
        const aVal = getSortValue(a, state.sortColumn);
        const bVal = getSortValue(b, state.sortColumn);
        
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;
        
        let comparison = 0;
        if (typeof aVal === 'string') {
          comparison = aVal.localeCompare(bVal);
        } else {
          comparison = aVal - bVal;
        }
        
        return state.sortDirection === 'asc' ? comparison : -comparison;
      });
    }
    
    // Create table header
    const table = document.createElement("table");
    table.className = "list-table";
    
    const thead = document.createElement("thead");
    thead.innerHTML = `
      <tr>
        <th>Image</th>
        <th class="sortable" data-column="name">Name ${getSortIndicator('name')}</th>
        <th class="sortable" data-column="year">Year ${getSortIndicator('year')}</th>
        <th class="sortable" data-column="players">Players ${getSortIndicator('players')}</th>
        <th class="sortable" data-column="playing_time">Time (min) ${getSortIndicator('playing_time')}</th>
        <th class="sortable" data-column="weight">Weight ${getSortIndicator('weight')}</th>
        <th class="sortable" data-column="avg_rating">Avg Rating ${getSortIndicator('avg_rating')}</th>
        <th class="sortable" data-column="bayes_rating">Bayes Rating ${getSortIndicator('bayes_rating')}</th>
        <th class="sortable" data-column="my_rating">My Rating ${getSortIndicator('my_rating')}</th>
        <th>Mechanics</th>
        <th>Categories</th>
      </tr>
    `;
    
    // Add click event listeners to sortable headers
    thead.querySelectorAll('.sortable').forEach(th => {
      th.addEventListener('click', () => handleSort(th.dataset.column));
    });
    
    table.appendChild(thead);
    
    const tbody = document.createElement("tbody");
    for (const g of games) {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><img src="${g.thumbnail || g.image || ""}" alt="" class="list-thumbnail"></td>
        <td class="game-name clickable" data-game-id="${g.id}">${g.name}</td>
        <td>${g.year || "—"}</td>
        <td>${g.min_players || "?"}–${g.max_players || "?"}</td>
        <td>${g.playing_time || "?"}</td>
        <td>${g.weight?.toFixed ? g.weight.toFixed(2) : (g.weight ?? "—")}</td>
        <td>${g.avg_rating?.toFixed ? g.avg_rating.toFixed(2) : (g.avg_rating ?? "—")}</td>
        <td>${g.bayes_rating?.toFixed ? g.bayes_rating.toFixed(2) : (g.bayes_rating ?? "—")}</td>
        <td>${g.my_rating ?? "—"}</td>
        <td>${g.mechanics?.map(m => `<span class="badge clickable" data-type="mechanics" data-value="${m}">${m}</span>`).join(" ") || "—"}</td>
        <td>${g.categories?.map(c => `<span class="badge clickable" data-type="categories" data-value="${c}">${c}</span>`).join(" ") || "—"}</td>
      `;
      
      // Add click event listeners
      row.querySelector('.game-name').addEventListener('click', () => openBGGPage(g.id, g.name));
      row.querySelectorAll('.badge').forEach(badge => {
        badge.addEventListener('click', () => filterByValue(badge.dataset.type, badge.dataset.value));
      });
      
      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    container.appendChild(table);
  }
  
  function getSortValue(game, column) {
    switch (column) {
      case 'name':
        return game.name;
      case 'year':
        return game.year || 0;
      case 'players':
        return game.min_players || 0;
      case 'playing_time':
        return game.playing_time || 0;
      case 'weight':
        return game.weight || 0;
      case 'avg_rating':
        return game.avg_rating || 0;
      case 'bayes_rating':
        return game.bayes_rating || 0;
      case 'my_rating':
        return game.my_rating || 0;
      default:
        return null;
    }
  }
  
  function getSortIndicator(column) {
    if (state.sortColumn !== column) {
      return '↕️';
      }
    return state.sortDirection === 'asc' ? '↑' : '↓';
  }
  
  function handleSort(column) {
    if (state.sortColumn === column) {
      // Toggle direction if same column
      state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      // New column, start with ascending
      state.sortColumn = column;
      state.sortDirection = 'asc';
    }
    
    // Re-render the list view with new sorting
    applyFilters();
  }
  
  function openBGGPage(gameId, gameName) {
    const url = `https://boardgamegeek.com/boardgame/${gameId}`;
    window.open(url, '_blank');
  }
  
  function filterByValue(type, value) {
    if (type === 'mechanics') {
      // Toggle mechanics selection
      if (state.selectedMechanics.has(value)) {
        state.selectedMechanics.delete(value);
      } else {
        state.selectedMechanics.add(value);
      }
      // Update mechanics cloud visual state
      document.querySelectorAll('.tag').forEach(tag => {
        if (tag.querySelector('span').textContent === value) {
          tag.classList.toggle('active', state.selectedMechanics.has(value));
        }
      });
    } else if (type === 'categories') {
      // Set categories filter
      const categoriesSelect = qs('categories');
      if (categoriesSelect) {
        // Find and select the category option
        Array.from(categoriesSelect.options).forEach(option => {
          if (option.value === value) {
            option.selected = true;
          }
        });
      }
    }
    
    // Apply the new filters
    updateSummary();
    applyFilters();
  }
  
  function toggleView() {
    state.viewMode = state.viewMode === 'tile' ? 'list' : 'tile';
    const button = qs("view-toggle");
    if (state.viewMode === 'list') {
      button.textContent = "🎴 Tile View";
      button.classList.add("active");
    } else {
      button.textContent = "📋 List View";
      button.classList.remove("active");
    }
    // Re-render current results with new view mode
    applyFilters();
  }
  
  async function doRefresh() {
    const username = prompt("BGG username (leave blank to use server .env):", "");
    if (username === null) return; // User cancelled
    
    const refreshButton = qs("refresh");
    const originalText = refreshButton.textContent;
    
    // Show loading state with progress
    refreshButton.disabled = true;
    refreshButton.innerHTML = '<span class="rolling-dice">🎲</span> Refreshing...';
    
    // Add progress indicator
    const progressDiv = document.createElement('div');
    progressDiv.className = 'refresh-progress';
    progressDiv.innerHTML = `
      <div class="progress-bar">
        <div class="progress-fill"></div>
      </div>
      <div class="progress-text">Connecting to BGG...</div>
    `;
    refreshButton.parentNode.insertBefore(progressDiv, refreshButton.nextSibling);
    
    try {
      const url = username ? `/api/refresh?username=${encodeURIComponent(username)}` : `/api/refresh`;
      
      // Update progress
      progressDiv.querySelector('.progress-text').textContent = 'Fetching collection...';
      progressDiv.querySelector('.progress-fill').style.width = '25%';
      
      const r = await fetch(url, { method: "POST" });
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      }
      
      // Update progress
      progressDiv.querySelector('.progress-text').textContent = 'Processing games...';
      progressDiv.querySelector('.progress-fill').style.width = '75%';
      
      await loadFacets();
      await applyFilters();
      
      // Complete progress
      progressDiv.querySelector('.progress-text').textContent = 'Complete!';
      progressDiv.querySelector('.progress-fill').style.width = '100%';
      
      // Show success message
      setTimeout(() => {
        progressDiv.remove();
      }, 2000);
      
    } catch (error) {
      console.error("Refresh error:", error);
      progressDiv.querySelector('.progress-text').textContent = 'Failed: ' + error.message;
      progressDiv.querySelector('.progress-fill').style.background = 'var(--accent-4)';
      setTimeout(() => {
        progressDiv.remove();
      }, 5000);
    } finally {
      // Restore button state
      refreshButton.disabled = false;
      refreshButton.textContent = originalText;
    }
  }
  
  window.addEventListener("DOMContentLoaded", async ()=>{
    qs("apply").addEventListener("click", applyFilters);
    qs("clear").addEventListener("click", ()=>{
      state.selectedMechanics.clear();
      document.querySelectorAll(".tag.active").forEach(t=>t.classList.remove("active"));
      ["categories","designers","artists","publishers"].forEach(id=>qs(id).selectedIndex = -1);
      ["year_min","year_max","players","time_max","weight_min","weight_max","rating_min"].forEach(id=>qs(id).value="");
      updateSummary();
      applyFilters();
    });
    qs("refresh").addEventListener("click", doRefresh);
    qs("search").addEventListener("input", ()=>{ applyFilters(); });
    qs("view-toggle").addEventListener("click", toggleView);
  
    await loadFacets();
    await applyFilters();
  });