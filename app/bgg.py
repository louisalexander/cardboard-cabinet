import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
from .models import Game
from .util import rate_limit_sleep

BASE = "https://boardgamegeek.com/xmlapi2"
CHUNK_SIZE = 10

async def fetch_collection_ids(client: httpx.AsyncClient, username: str) -> Tuple[List[int], Optional[float]]:
    """
    Returns list of game ids and your per-game ratings (dict by id) from the collection.
    """
    params = {"username": username, "own": 1, "excludesubtype": "boardgameexpansion", "stats": 1}
    # BGG collection can return 202 (accepted) first; poll until ready
    ratings: Dict[int, Optional[float]] = {}
    ids: List[int] = []

    while True:
        r = await client.get(f"{BASE}/collection", params=params, timeout=60)
        if r.status_code == 202:
            rate_limit_sleep(1.5)
            continue
        r.raise_for_status()
        root = ET.fromstring(r.text)
        for item in root.findall("item"):
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
                    except:
                        my = None
            ratings[gid] = my
        break

    return ids, ratings  # ratings are per game in collection

def _text(elem, path, attr=None, cast=None):
    node = elem.find(path)
    if node is None:
        return None
    if attr:
        val = node.attrib.get(attr)
    else:
        val = node.text
    if val is None:
        return None
    if cast:
        try:
            return cast(val)
        except:
            return None
    return val

def parse_thing_xml(x: str, my_ratings: Dict[int, Optional[float]]) -> List[Game]:
    root = ET.fromstring(x)
    games: List[Game] = []
    for item in root.findall("item"):
        gid = int(item.attrib["id"])
        name_node = None
        # pick the primary name
        for n in item.findall("name"):
            if n.attrib.get("type") == "primary":
                name_node = n
                break
        if name_node is None:
            name_node = item.find("name")

        name = name_node.attrib.get("value") if name_node is not None else f"Game {gid}"

        year = _text(item, "yearpublished", "value", int)
        image = _text(item, "image")
        thumb = _text(item, "thumbnail")

        min_players = _text(item, "minplayers", "value", int)
        max_players = _text(item, "maxplayers", "value", int)
        playing_time = _text(item, "playingtime", "value", int)

        stats = item.find("statistics")
        avg_rating = bayes = weight = None
        if stats is not None:
            ratings = stats.find("ratings")
            if ratings is not None:
                avg_rating = _text(ratings, "average", "value", float)
                bayes     = _text(ratings, "bayesaverage", "value", float)
                weight    = _text(ratings, "averageweight", "value", float)

        def links_of(t: str) -> List[str]:
            return [ln.attrib.get("value") for ln in item.findall(f"link[@type='{t}']")]

        mechanics  = links_of("boardgamemechanic")
        categories = links_of("boardgamecategory")
        designers  = links_of("boardgamedesigner")
        artists    = links_of("boardgameartist")
        publishers = links_of("boardgamepublisher")

        g = Game(
            id=gid, name=name, year=year, image=image, thumbnail=thumb,
            min_players=min_players, max_players=max_players, playing_time=playing_time,
            weight=weight, avg_rating=avg_rating, bayes_rating=bayes,
            my_rating=my_ratings.get(gid),
            mechanics=mechanics, categories=categories, designers=designers,
            artists=artists, publishers=publishers
        )
        games.append(g)
    return games

async def fetch_things(client: httpx.AsyncClient, ids: List[int], my_ratings: Dict[int, Optional[float]]) -> List[Game]:
    games: List[Game] = []
    for i in range(0, len(ids), CHUNK_SIZE):
        chunk = ids[i:i+CHUNK_SIZE]
        params = {"id": ",".join(map(str, chunk)), "stats": 1, "type": "boardgame"}
        try:
            r = await client.get(f"{BASE}/thing", params=params, timeout=60)
            r.raise_for_status()
            games.extend(parse_thing_xml(r.text, my_ratings))
            rate_limit_sleep(2.0)
        except Exception as e:
            print(f"Error fetching chunk {chunk}: {e}")
            # Continue with other chunks instead of failing completely
            continue
    return games