import os
from typing import List, Optional, Dict
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from .models import Game, Facets, RefreshResponse
from .storage import load_cache, save_cache
from .bgg import fetch_collection_ids, fetch_things, fetch_things_parallel
from .util import bucketize_minutes

load_dotenv()
app = FastAPI(title="BGG Library")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve the main HTML file at root
@app.get("/")
async def read_index():
    with open("frontend/index.html", "r") as f:
        return Response(content=f.read(), media_type="text/html")

@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint to verify the API is working."""
    return {"status": "ok", "message": "API is working"}

def make_facets(games: List[Game]) -> Facets:
    def add_count(d: Dict[str,int], key: Optional[str]):
        if not key: return
        d[key] = d.get(key, 0) + 1

    mechanics: Dict[str, int] = {}
    categories: Dict[str, int] = {}
    designers: Dict[str, int] = {}
    artists: Dict[str, int] = {}
    publishers: Dict[str, int] = {}
    years: Dict[str, int] = {}
    player_counts: Dict[str, int] = {}
    time_buckets: Dict[str, int] = {}
    weight_buckets: Dict[str, int] = {}

    for g in games:
        for m in g.mechanics:  add_count(mechanics, m)
        for c in g.categories: add_count(categories, c)
        for d in g.designers:  add_count(designers, d)
        for a in g.artists:    add_count(artists, a)
        for p in g.publishers: add_count(publishers, p)

        add_count(years, str(g.year) if g.year else "Unknown")

        # players distribution as exact ranges "X–Y"
        if g.min_players or g.max_players:
            pmin = g.min_players or g.max_players
            pmax = g.max_players or g.min_players
            add_count(player_counts, f"{pmin}–{pmax}")
        else:
            add_count(player_counts, "Unknown")

        # time buckets
        tb = bucketize_minutes(g.playing_time if g.playing_time else None)
        add_count(time_buckets, tb)

        # weight buckets
        if g.weight is None:
            add_count(weight_buckets, "Unknown")
        else:
            w = g.weight
            key = (
                "Light (≤1.75)" if w <= 1.75 else
                "Medium‑Light (1.76–2.5)" if w <= 2.5 else
                "Medium (2.51–3.25)" if w <= 3.25 else
                "Medium‑Heavy (3.26–4.0)" if w <= 4.0 else
                "Heavy (>4.0)"
            )
            add_count(weight_buckets, key)

    return Facets(
        mechanics=mechanics, categories=categories,
        designers=designers, artists=artists, publishers=publishers,
        years=years, player_counts=player_counts,
        time_buckets=time_buckets, weight_buckets=weight_buckets
    )

def matches_filters(g: Game, q: dict) -> bool:
    def include_str_list(field_vals: List[str], targets: Optional[List[str]]) -> bool:
        if not targets: return True
        svals = set(v.lower() for v in field_vals)
        return all(t.lower() in svals for t in targets)

    if not include_str_list(g.mechanics, q.get("mechanics")): return False
    if not include_str_list(g.categories, q.get("categories")): return False
    if not include_str_list(g.designers, q.get("designers")): return False
    if not include_str_list(g.artists, q.get("artists")): return False
    if not include_str_list(g.publishers, q.get("publishers")): return False

    ymn, ymx = q.get("year_min"), q.get("year_max")
    if ymn and (g.year or 0) < ymn: return False
    if ymx and (g.year or 9999) > ymx: return False

    players = q.get("players")
    if players:
        # Ensure players fits in min/max range
        if g.min_players and players < g.min_players: return False
        if g.max_players and players > g.max_players: return False

    pmin, pmax = q.get("players_min"), q.get("players_max")
    if pmin and (g.max_players or 0) < pmin: return False
    if pmax and (g.min_players or 9999) > pmax: return False

    tmax = q.get("time_max")
    if tmax and (g.playing_time or 99999) > tmax: return False

    wmin, wmax = q.get("weight_min"), q.get("weight_max")
    if wmin and (g.weight or 0) < wmin: return False
    if wmax and (g.weight or 9999) > wmax: return False

    rmin = q.get("rating_min")
    if rmin and (g.avg_rating or 0) < rmin: return False

    search = q.get("search")
    if search and search.lower() not in g.name.lower(): return False

    return True

@app.get("/api/facets", response_model=Facets)
def get_facets():
    games = load_cache()
    return make_facets(games)

@app.get("/api/games", response_model=List[Game])
def get_games(
    mechanics: Optional[str] = None,
    categories: Optional[str] = None,
    designers: Optional[str] = None,
    artists: Optional[str] = None,
    publishers: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    players: Optional[int] = None,
    players_min: Optional[int] = None,
    players_max: Optional[int] = None,
    time_max: Optional[int] = None,
    weight_min: Optional[float] = None,
    weight_max: Optional[float] = None,
    rating_min: Optional[float] = None,
    search: Optional[str] = None
):
    games = load_cache()
    q = {
        "mechanics": mechanics.split(",") if mechanics else None,
        "categories": categories.split(",") if categories else None,
        "designers": designers.split(",") if designers else None,
        "artists": artists.split(",") if artists else None,
        "publishers": publishers.split(",") if publishers else None,
        "year_min": year_min, "year_max": year_max,
        "players": players, "players_min": players_min, "players_max": players_max,
        "time_max": time_max, "weight_min": weight_min, "weight_max": weight_max,
        "rating_min": rating_min, "search": search
    }
    return [g for g in games if matches_filters(g, q)]

@app.post("/api/refresh", response_model=RefreshResponse)
async def refresh(username: Optional[str] = None):
    user = username or os.getenv("BGG_USERNAME")
    if not user:
        return Response(status_code=400, content="BGG_USERNAME not configured and no username provided")

    try:
        # Use connection pooling and keep-alive for better performance
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
        timeout = httpx.Timeout(60.0, connect=10.0)
        
        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            print(f"Fetching collection for user: {user}")
            ids, my_ratings = await fetch_collection_ids(client, user)
            print(f"Found {len(ids)} games in collection")
            
            # Use parallel fetching for much faster performance
            if len(ids) > 25:  # Use parallel for larger collections
                print("Using parallel fetching for faster performance...")
                games = await fetch_things_parallel(client, ids, my_ratings)
            else:
                print("Using sequential fetching for smaller collection...")
                games = await fetch_things(client, ids, my_ratings)
                
            print(f"Successfully hydrated {len(games)} games")
            
            # Debug: Check if games have content
            if games:
                print(f"First game: {games[0].name if games[0] else 'None'}")
                print(f"Total games fetched: {len(games)}")
            else:
                print("WARNING: No games were fetched!")
                
        save_cache(games)
        return RefreshResponse(username=user, total_in_collection=len(ids), total_hydrated=len(games), cached=True)
    except Exception as e:
        print(f"Error in refresh: {e}")
        import traceback
        traceback.print_exc()
        return Response(status_code=500, content=f"Error refreshing collection: {str(e)}")