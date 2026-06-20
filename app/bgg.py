import httpx
import xml.etree.ElementTree as ET
import asyncio
from typing import List, Dict, Tuple, Optional
from .models import Game
from .util import rate_limit_sleep

BASE = "https://boardgamegeek.com/xmlapi2"
GEEKITEMS = "https://boardgamegeek.com/api/geekitems"
# Community weight (complexity) lives in BGG's dynamic stats API. The xmlapi2
# /thing endpoint now rejects cookie auth (401), so we read it from here.
DYNAMICINFO = "https://api.geekdo.com/api/dynamicinfo"
MAX_CONCURRENT = 5
REDUCED_DELAY = 0.3
MAX_POLL_RETRIES = 30


async def get_bgg_session(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Login to BGG and return the SessionID cookie value."""
    r = await client.post(
        "https://boardgamegeek.com/login/api/v1",
        json={"credentials": {"username": username, "password": password}},
        timeout=30,
    )
    if r.status_code == 400:
        raise ValueError("Invalid BGG username or password.")
    r.raise_for_status()
    session_id = r.cookies.get("SessionID")
    if not session_id:
        raise RuntimeError("BGG login succeeded but no session cookie was returned.")
    return session_id


async def fetch_collection(
    client: httpx.AsyncClient,
    username: str,
    session_cookie: Optional[str] = None,
) -> Tuple[List[int], Dict[int, Optional[float]], str]:
    """
    Returns (game_ids, user_ratings_by_id, raw_xml) from the BGG collection.
    Authenticated via httpx cookie jar (session_cookie param kept for compat).
    """
    params = {"username": username, "own": 1, "stats": 1}
    ratings: Dict[int, Optional[float]] = {}
    ids: List[int] = []
    poll_attempts = 0

    while True:
        r = await client.get(f"{BASE}/collection", params=params, timeout=60)

        if r.status_code == 202:
            poll_attempts += 1
            if poll_attempts >= MAX_POLL_RETRIES:
                raise TimeoutError(f"BGG collection API not ready after {MAX_POLL_RETRIES} attempts")
            await asyncio.sleep(1.0)
            continue

        if r.status_code == 401:
            raise PermissionError(
                "BGG requires a password to access your collection. "
                "Enter your BGG password in the refresh form."
            )
        if r.status_code == 404:
            raise LookupError(f"BGG username '{username}' not found.")
        if r.status_code == 429:
            raise RuntimeError("BGG rate limit reached. Try again in a few minutes.")
        if r.status_code in (502, 503, 504):
            raise RuntimeError("BoardGameGeek is temporarily unavailable. Try again in a few minutes.")

        r.raise_for_status()

        root = ET.fromstring(r.text)
        items = root.findall("item") or root.findall(".//item")

        for item in items:
            gid = int(item.attrib.get("objectid"))
            ids.append(gid)
            stats = item.find("stats")
            my = None
            if stats is not None:
                rating = stats.find("rating")
                if rating is not None:
                    val = rating.attrib.get("value")
                    try:
                        my = float(val) if val not in (None, "N/A") else None
                    except (ValueError, TypeError):
                        my = None
            ratings[gid] = my
        break

    return ids, ratings, r.text


# Alias for backward compatibility with tests
async def fetch_collection_ids(
    client: httpx.AsyncClient,
    username: str,
    session_cookie: Optional[str] = None,
) -> Tuple[List[int], Dict[int, Optional[float]]]:
    ids, ratings, _ = await fetch_collection(client, username, session_cookie)
    return ids, ratings


def _parse_collection_item(item: ET.Element, my_ratings: Dict[int, Optional[float]]) -> Game:
    """Extract all available fields from a collection <item> element."""
    gid = int(item.attrib.get("objectid"))

    name_node = item.find("name")
    name = name_node.text if name_node is not None else f"Game {gid}"

    def text(path):
        n = item.find(path)
        return n.text if n is not None else None

    def intval(path):
        try:
            v = text(path)
            return int(v) if v else None
        except (ValueError, TypeError):
            return None

    year = intval("yearpublished")
    image = text("image")
    thumb = text("thumbnail")

    stats = item.find("stats")
    min_players = max_players = playing_time = avg_rating = bayes = None
    if stats is not None:
        min_players = int(stats.attrib.get("minplayers") or 0) or None
        max_players = int(stats.attrib.get("maxplayers") or 0) or None
        playing_time = int(stats.attrib.get("playingtime") or 0) or None
        rating = stats.find("rating")
        if rating is not None:
            try:
                avg_rating = float(rating.find("average").attrib.get("value") or 0) or None
            except Exception:
                avg_rating = None
            try:
                bayes = float(rating.find("bayesaverage").attrib.get("value") or 0) or None
            except Exception:
                bayes = None

    return Game(
        id=gid, name=name, year=year, image=image, thumbnail=thumb,
        min_players=min_players, max_players=max_players, playing_time=playing_time,
        weight=None, avg_rating=avg_rating, bayes_rating=bayes,
        my_rating=my_ratings.get(gid),
        mechanics=[], categories=[], designers=[], artists=[], publishers=[],
    )


def _parse_avgweight(payload: dict) -> Optional[float]:
    """Extract the community average weight from a dynamicinfo JSON payload.

    Returns None for missing, zero (no votes), or malformed values.
    """
    stats = ((payload.get("item") or {}).get("stats") or {})
    try:
        w = float(stats.get("avgweight"))
    except (TypeError, ValueError):
        return None
    return w or None


async def fetch_weight(client: httpx.AsyncClient, game_id: int) -> Optional[float]:
    """Fetch a game's community weight from BGG's dynamicinfo API (no auth)."""
    try:
        r = await client.get(
            DYNAMICINFO,
            params={"objectid": game_id, "objecttype": "thing"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        return _parse_avgweight(r.json())
    except Exception as e:
        print(f"Error fetching weight for game {game_id}: {e}")
        return None


async def fetch_game_links(
    client: httpx.AsyncClient,
    game: Game,
) -> Game:
    """
    Fetch mechanics, categories, designers, artists, publishers for a game
    from BGG's internal geekitems API (no auth required).
    Returns an updated Game with those fields populated.
    """
    try:
        r = await client.get(
            GEEKITEMS,
            params={"nosession": 1, "objecttype": "thing", "objectid": game.id},
            timeout=30,
        )
        if r.status_code != 200:
            return game
        item = r.json().get("item", {})
        links = item.get("links", {})

        def names(key):
            return [e["name"] for e in links.get(key, []) if e.get("name")]

        # Use better image from geekitems if available and collection had none
        image = game.image or item.get("imageurl")
        thumb = game.thumbnail or (item.get("images") or {}).get("thumb")

        return Game(
            id=game.id, name=game.name, year=game.year,
            image=image, thumbnail=thumb,
            min_players=game.min_players, max_players=game.max_players,
            playing_time=game.playing_time,
            weight=None,
            avg_rating=game.avg_rating, bayes_rating=game.bayes_rating,
            my_rating=game.my_rating,
            mechanics=names("boardgamemechanic"),
            categories=names("boardgamecategory"),
            designers=names("boardgamedesigner"),
            artists=names("boardgameartist"),
            publishers=names("boardgamepublisher"),
        )
    except Exception as e:
        print(f"Error fetching geekitems for game {game.id}: {e}")
        return game


async def fetch_all_games(
    auth_client: httpx.AsyncClient,
    ids: List[int],
    my_ratings: Dict[int, Optional[float]],
    collection_xml: str,
) -> List[Game]:
    """
    Given the collection XML (already fetched), parse basic game data,
    then enrich each game with links from the geekitems API in parallel.
    """
    root = ET.fromstring(collection_xml)
    items = root.findall("item") or root.findall(".//item")
    seen: set = set()
    unique_items = []
    for item in items:
        gid = int(item.attrib.get("objectid"))
        if gid not in seen:
            seen.add(gid)
            unique_items.append(item)
    games = [_parse_collection_item(item, my_ratings) for item in unique_items]
    print(f"Parsed {len(games)} games from collection, fetching links...")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def enrich(game: Game) -> Game:
        async with semaphore:
            result = await fetch_game_links(auth_client, game)
            result.weight = await fetch_weight(auth_client, game.id)
            await asyncio.sleep(REDUCED_DELAY)
            return result

    tasks = [enrich(g) for g in games]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    for r in results:
        if isinstance(r, Exception):
            print(f"Game enrichment failed: {r}")
        else:
            enriched.append(r)

    return enriched
