"""Fetch the BGG collection and write it to frontend/data/games.json.

Reuses app/bgg.py so the static site ships the same data the FastAPI app
would serve. Run locally, then commit + deploy.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import List

import httpx
from dotenv import load_dotenv

from app.bgg import fetch_collection, get_bgg_session, fetch_all_games
from app.models import Game

load_dotenv()

OUT_PATH = Path(__file__).resolve().parent.parent / "frontend" / "data" / "games.json"


def games_to_json(games: List[Game]) -> str:
    """Serialize games to deterministic, name-sorted, pretty JSON."""
    data = [g.model_dump() for g in games]
    data.sort(key=lambda d: (d["name"] or "").lower())
    return json.dumps(data, ensure_ascii=False, indent=2)


async def export() -> int:
    user = os.getenv("BGG_USERNAME")
    if not user:
        raise SystemExit("BGG_USERNAME not configured in .env")
    password = os.getenv("BGG_PASSWORD")

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        session_cookie = await get_bgg_session(client, user, password) if password else None
        print(f"Fetching collection for user: {user}")
        ids, my_ratings, collection_xml = await fetch_collection(
            client, user, session_cookie=session_cookie
        )
        print(f"Found {len(ids)} games; hydrating…")
        games = await fetch_all_games(client, ids, my_ratings, collection_xml)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(games_to_json(games), encoding="utf-8")
    print(f"Wrote {len(games)} games to {OUT_PATH}")
    return len(games)


if __name__ == "__main__":
    asyncio.run(export())
