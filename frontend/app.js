const state = {
    facets: null,
    selectedMechanics: new Set(),
    filters: {}
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
    const r = await fetch("/api/facets");
    if (!r.ok) return;
    const data = await r.json();
    state.facets = data;
    renderTagCloud(data.mechanics);
    fillSelect(qs("categories"), data.categories);
    fillSelect(qs("designers"), data.designers);
    fillSelect(qs("artists"), data.artists);
    fillSelect(qs("publishers"), data.publishers);
    updateSummary();
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
    collectFilters();
    const query = toQuery(state.filters);
    const r = await fetch(`/api/games?${query}`);
    const data = await r.json();
    renderResults(data);
  }
  
  function renderResults(games) {
    const stats = qs("stats");
    stats.textContent = `${games.length} game(s)`;
    const container = qs("results");
    container.innerHTML = "";
    for (const g of games) {
      const el = document.createElement("div");
      el.className = "card";
      el.innerHTML = `
        <img src="${g.thumbnail || g.image || ""}" alt="">
        <div class="body">
          <div class="name">${g.name}</div>
          <div class="meta">
            ${g.year || "—"} • ${g.min_players || "?"}–${g.max_players || "?"} players • ${g.playing_time || "?"} min • weight ${g.weight?.toFixed ? g.weight.toFixed(2) : (g.weight ?? "—")}
          </div>
          <div class="meta">Rating: ${g.avg_rating?.toFixed ? g.avg_rating.toFixed(2) : (g.avg_rating ?? "—")} (Bayes: ${g.bayes_rating?.toFixed ? g.bayes_rating.toFixed(2) : (g.bayes_rating ?? "—")}) • My: ${g.my_rating ?? "—"}</div>
          <div class="badges">
            ${g.mechanics.slice(0,3).map(m=>`<span class="badge">${m}</span>`).join("")}
          </div>
        </div>
      `;
      container.appendChild(el);
    }
  }
  
  async function doRefresh() {
    const username = prompt("BGG username (leave blank to use server .env):", "");
    const url = username ? `/api/refresh?username=${encodeURIComponent(username)}` : `/api/refresh`;
    const r = await fetch(url, { method: "POST" });
    if (!r.ok) {
      alert("Refresh failed.");
      return;
    }
    await loadFacets();
    await applyFilters();
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
  
    await loadFacets();
    await applyFilters();
  });