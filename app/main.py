import os
from contextlib import asynccontextmanager
from typing import List, Optional, Dict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Response, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx

from .models import Game, Facets, RefreshResponse, GamesResponse
from .database import get_db
from .db_storage import save_games, load_games, get_games_filtered, get_total_game_count, init_db
from .bgg import fetch_collection_ids, fetch_things, fetch_things_parallel
from .util import bucketize_minutes

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BGG Library", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")


@app.get("/")
async def read_index():
    with open(BASE_DIR / "frontend" / "index.html", "r") as f:
        return Response(content=f.read(), media_type="text/html")


@app.get("/api/test")
async def test_endpoint():
    return {"status": "ok", "message": "API is working"}


def make_facets(games: List[Game]) -> Facets:
    def add_count(d: Dict[str, int], key: Optional[str]):
        if not key:
            return
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
        for m in g.mechanics:   add_count(mechanics, m)
        for c in g.categories:  add_count(categories, c)
        for d in g.designers:   add_count(designers, d)
        for a in g.artists:     add_count(artists, a)
        for p in g.publishers:  add_count(publishers, p)

        add_count(years, str(g.year) if g.year else "Unknown")

        if g.min_players or g.max_players:
            pmin = g.min_players or g.max_players
            pmax = g.max_players or g.min_players
            add_count(player_counts, f"{pmin}–{pmax}")
        else:
            add_count(player_counts, "Unknown")

        tb = bucketize_minutes(g.playing_time if g.playing_time else None)
        add_count(time_buckets, tb)

        if g.weight is None:
            add_count(weight_buckets, "Unknown")
        else:
            w = g.weight
            key = (
                "Light (≤1.75)"          if w <= 1.75 else
                "Medium‑Light (1.76–2.5)" if w <= 2.5  else
                "Medium (2.51–3.25)"      if w <= 3.25 else
                "Medium‑Heavy (3.26–4.0)" if w <= 4.0  else
                "Heavy (>4.0)"
            )
            add_count(weight_buckets, key)

    return Facets(
        mechanics=mechanics, categories=categories,
        designers=designers, artists=artists, publishers=publishers,
        years=years, player_counts=player_counts,
        time_buckets=time_buckets, weight_buckets=weight_buckets,
    )


@app.get("/api/facets", response_model=Facets)
def get_facets(db: Session = Depends(get_db)):
    return make_facets(load_games(db))


@app.get("/api/games", response_model=GamesResponse)
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
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    games = get_games_filtered(
        db,
        mechanics=mechanics.split(",") if mechanics else None,
        categories=categories.split(",") if categories else None,
        designers=designers.split(",") if designers else None,
        artists=artists.split(",") if artists else None,
        publishers=publishers.split(",") if publishers else None,
        year_min=year_min,
        year_max=year_max,
        players=players,
        players_min=players_min,
        players_max=players_max,
        time_max=time_max,
        weight_min=weight_min,
        weight_max=weight_max,
        rating_min=rating_min,
        search=search,
    )
    total = get_total_game_count(db)
    return GamesResponse(games=games, total=total, filtered=len(games))


class RefreshRequest(BaseModel):
    username: Optional[str] = None


@app.post("/api/refresh", response_model=RefreshResponse)
async def refresh(
    body: Optional[RefreshRequest] = Body(default=None),
    db: Session = Depends(get_db),
):
    user = (body.username if body else None) or os.getenv("BGG_USERNAME")
    if not user:
        raise HTTPException(status_code=400, detail="BGG_USERNAME not configured and no username provided")

    try:
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
        timeout = httpx.Timeout(60.0, connect=10.0)

        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            print(f"Fetching collection for user: {user}")
            ids, my_ratings = await fetch_collection_ids(client, user)
            print(f"Found {len(ids)} games in collection")

            if len(ids) > 25:
                games = await fetch_things_parallel(client, ids, my_ratings)
            else:
                games = await fetch_things(client, ids, my_ratings)

            print(f"Successfully hydrated {len(games)} games")

        save_games(games, db)
        return RefreshResponse(username=user, total_in_collection=len(ids), total_hydrated=len(games), cached=True)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to refresh collection. Check server logs for details.")
