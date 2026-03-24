"""
Live integration tests that hit the real BGG API.
Run with: pytest tests/integration/test_bgg_live.py -v -s -m live
"""
import os
import pytest
import httpx
from dotenv import load_dotenv

load_dotenv()

BGG_USERNAME = os.getenv("BGG_USERNAME", "panicked_kernel")
BGG_PASSWORD = os.getenv("BGG_PASSWORD")
BASE = "https://boardgamegeek.com/xmlapi2"
# A handful of well-known public game IDs to test /thing
TEST_IDS = [13, 174430, 161936]  # Catan, Gloomhaven, Pandemic Legacy S1


@pytest.mark.live
async def test_login_sets_cookies():
    """Login returns a session and sets all three expected cookies."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        print(f"\nLogin status: {r.status_code}")
        print(f"Set-Cookie headers:")
        for h in r.headers.get_list("set-cookie"):
            print(f"  {h}")
        print(f"Parsed cookies: {dict(r.cookies)}")

        assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text}"
        assert "SessionID" in r.cookies, "No SessionID cookie returned"
        assert "bggusername" in r.cookies
        assert "bggpassword" in r.cookies


@pytest.mark.live
async def test_thing_unauthenticated():
    """Confirm /thing returns 401 without auth (baseline)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing unauthenticated status: {r.status_code}")
        print(f"Body: {r.text[:300]}")
        # We expect 401 — this documents the baseline
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"


@pytest.mark.live
async def test_thing_with_jar_cookies():
    """Login then fetch /thing using the httpx cookie jar (no manual headers)."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        # Login — cookies go into the jar automatically
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204, f"Login failed: {login.status_code}"
        print(f"\nCookies in jar after login: {dict(client.cookies)}")

        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"/thing with jar cookies status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_with_explicit_path_cookies():
    """Login, re-set cookies with path=/, then fetch /thing."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204, f"Login failed: {login.status_code}"

        # Re-set with explicit domain + path=/
        for name, value in login.cookies.items():
            client.cookies.set(name, value, domain="boardgamegeek.com", path="/")
        print(f"\nCookies after explicit set: {dict(client.cookies)}")

        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"/thing status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_with_manual_cookie_header():
    """Login, then set Cookie header explicitly on the thing request."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204, f"Login failed: {login.status_code}"

        cookies = dict(login.cookies)
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        print(f"\nCookie header to send: {cookie_header[:80]}...")

        # Use a fresh client to avoid any jar interaction
        async with httpx.AsyncClient() as fresh:
            r = await fresh.get(
                f"{BASE}/thing",
                params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
                headers={"Cookie": cookie_header},
                timeout=30,
            )
            print(f"/thing status: {r.status_code}")
            print(f"Body[:300]: {r.text[:300]}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_with_basic_auth():
    """Try HTTP Basic auth for /thing (in case BGG added basic auth requirement)."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient(auth=httpx.BasicAuth(BGG_USERNAME, BGG_PASSWORD)) as client:
        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing with Basic auth status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_cookies_plus_basic_auth():
    """Try session cookies AND Basic auth together for /thing."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient(auth=httpx.BasicAuth(BGG_USERNAME, BGG_PASSWORD)) as client:
        # Login to get session cookies
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        print(f"\nCookies: {dict(client.cookies)}")
        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"/thing status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_browser_headers():
    """Try with browser-like User-Agent + Accept headers (no cookies)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(headers=headers) as client:
        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing with browser UA (no cookies): {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")


@pytest.mark.live
async def test_thing_browser_headers_with_cookies():
    """Try with browser-like headers + session cookies."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://boardgamegeek.com/",
    }
    async with httpx.AsyncClient(headers=browser_headers) as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing with browser headers + cookies: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_response_headers():
    """Inspect the 401 response headers for auth clues (WWW-Authenticate etc)."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        r = await client.get(
            f"{BASE}/thing",
            params={"id": str(TEST_IDS[0]), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing response status: {r.status_code}")
        print(f"Response headers:")
        for k, v in r.headers.items():
            print(f"  {k}: {v}")
        print(f"Body: {r.text[:300]}")


@pytest.mark.live
async def test_thing_www_subdomain():
    """Try /thing via www.boardgamegeek.com — cookies may be domain-specific."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        r = await client.get(
            "https://www.boardgamegeek.com/xmlapi2/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing www subdomain status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_thing_follow_redirects():
    """Try /thing with follow_redirects=True — maybe Cloudflare redirects through auth."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        print(f"\nCookies after login: {dict(client.cookies)}")
        r = await client.get(
            f"{BASE}/thing",
            params={"id": ",".join(str(i) for i in TEST_IDS), "stats": 1, "type": "boardgame"},
            timeout=30,
        )
        print(f"/thing follow_redirects status: {r.status_code}")
        print(f"URL after redirect: {r.url}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_xmlapi_v1():
    """Try the older BGG XML API v1 — might have different auth rules."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        # XMLAPI v1 format
        r = await client.get(
            f"https://boardgamegeek.com/xmlapi/boardgame/{','.join(str(i) for i in TEST_IDS)}",
            params={"stats": 1},
            timeout=30,
        )
        print(f"\nXMLAPI v1 status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@pytest.mark.live
async def test_collection_detailed():
    """Check what extra data the collection API returns with stats — can we skip /thing?"""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        r = await client.get(
            f"{BASE}/collection",
            params={"username": BGG_USERNAME, "own": 1, "excludesubtype": "boardgameexpansion", "stats": 1},
            timeout=60,
        )
        assert r.status_code == 200
        # Print the first item's XML to see what fields are available
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text)
        items = root.findall("item")
        if items:
            import xml.etree.ElementTree as ET2
            print(f"\nFirst item XML (first 1500 chars):")
            print(ET.tostring(items[0], encoding="unicode")[:1500])
        print(f"\nTotal items: {len(items)}")


@pytest.mark.live
async def test_login_response_body():
    """Check the login response body — might contain a token."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        print(f"\nLogin status: {r.status_code}")
        print(f"Login body: '{r.text}'")
        print(f"Login response headers:")
        for k, v in r.headers.items():
            print(f"  {k}: {v}")


@pytest.mark.live
async def test_thing_no_stats():
    """Try /thing without stats=1 — maybe auth is only required for stats."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204
        r = await client.get(
            f"{BASE}/thing",
            params={"id": str(TEST_IDS[0]), "type": "boardgame"},
            timeout=30,
        )
        print(f"\n/thing no-stats status: {r.status_code}")
        print(f"Body[:200]: {r.text[:200]}")


@pytest.mark.live
async def test_geekitems_api():
    """Try BGG's internal geekitems API (used by the website, served via Varnish)."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient() as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204

        # Try BGG's internal geekitems API (used by the BGG Angular app)
        for gid in TEST_IDS[:1]:
            r = await client.get(
                "https://boardgamegeek.com/api/geekitems",
                params={"nosession": 1, "objecttype": "thing", "objectid": gid},
                timeout=30,
            )
            print(f"\ngeekitems status for {gid}: {r.status_code}")
            print(f"Content-Type: {r.headers.get('content-type', 'unknown')}")
            print(f"Body[:500]: {r.text[:500]}")
            print(f"Server: {r.headers.get('server', 'unknown')}")
            if r.status_code == 200:
                break


@pytest.mark.live
async def test_boardgame_angular_api():
    """Try BGG's Angular app data API."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        login = await client.post(
            "https://boardgamegeek.com/login/api/v1",
            json={"credentials": {"username": BGG_USERNAME, "password": BGG_PASSWORD}},
            timeout=30,
        )
        assert login.status_code == 204

        # Try several possible internal API paths
        endpoints = [
            f"https://boardgamegeek.com/api/thing/{TEST_IDS[0]}",
            f"https://boardgamegeek.com/geekdo-api/thing/{TEST_IDS[0]}",
            f"https://api.geekdo.com/api/thing/{TEST_IDS[0]}",
        ]
        for url in endpoints:
            r = await client.get(url, timeout=15)
            print(f"\n{url}: {r.status_code}")
            print(f"Server: {r.headers.get('server', 'unknown')}")
            print(f"Body[:200]: {r.text[:200]}")


@pytest.mark.live
async def test_geekitems_full_response():
    """Inspect full geekitems response — check for mechanics, categories, weight, etc."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://boardgamegeek.com/api/geekitems",
            params={"nosession": 1, "objecttype": "thing", "objectid": TEST_IDS[0]},
            timeout=30,
        )
        assert r.status_code == 200
        import json
        data = r.json()
        item = data.get("item", {})
        print(f"\nTop-level keys: {list(item.keys())}")
        # Print specific fields we care about
        for field in ["name", "yearpublished", "minplayers", "maxplayers",
                      "minplaytime", "maxplaytime", "playingtime", "weight",
                      "mechanics", "categories", "designers", "artists", "publishers",
                      "links", "linksobj", "stats", "average", "avgweight"]:
            if field in item:
                val = item[field]
                if isinstance(val, (list, dict)):
                    print(f"  {field}: {str(val)[:200]}")
                else:
                    print(f"  {field}: {val}")
        # Also dump the full JSON to see structure
        print(f"\nFull JSON (first 2000 chars):")
        print(json.dumps(item, indent=2)[:2000])


@pytest.mark.live
async def test_geekitems_no_auth():
    """Confirm geekitems works without auth (nosession=1 is just a hint, not a requirement)."""
    async with httpx.AsyncClient() as client:  # No login
        r = await client.get(
            "https://boardgamegeek.com/api/geekitems",
            params={"nosession": 1, "objecttype": "thing", "objectid": TEST_IDS[0]},
            timeout=30,
        )
        print(f"\ngeekitems without auth: {r.status_code}")
        assert r.status_code == 200, f"Needs auth? {r.text[:200]}"


@pytest.mark.live
async def test_geekitems_batch():
    """Test if geekitems supports multiple IDs in one request."""
    async with httpx.AsyncClient() as client:
        # Try comma-separated IDs
        r = await client.get(
            "https://boardgamegeek.com/api/geekitems",
            params={"nosession": 1, "objecttype": "thing",
                    "objectid": ",".join(str(i) for i in TEST_IDS)},
            timeout=30,
        )
        print(f"\ngeekitems batch (comma) status: {r.status_code}")
        print(f"Body[:300]: {r.text[:300]}")

        # Try repeated objectid params
        r2 = await client.get(
            "https://boardgamegeek.com/api/geekitems?nosession=1&objecttype=thing"
            + "".join(f"&objectid={i}" for i in TEST_IDS),
            timeout=30,
        )
        print(f"geekitems batch (repeated) status: {r2.status_code}")
        print(f"Body[:300]: {r2.text[:300]}")


@pytest.mark.live
async def test_full_bgg_flow():
    """End-to-end: login → collection → geekitems enrichment."""
    assert BGG_PASSWORD, "BGG_PASSWORD must be set in .env"
    from app.bgg import get_bgg_session, fetch_collection, fetch_all_games

    async with httpx.AsyncClient() as client:
        session_id = await get_bgg_session(client, BGG_USERNAME, BGG_PASSWORD)
        print(f"\nSession ID: {session_id[:20]}...")

        ids, ratings, collection_xml = await fetch_collection(client, BGG_USERNAME, session_cookie=session_id)
        print(f"Collection: {len(ids)} games")
        assert len(ids) > 0, "No games found in collection"

        # Only enrich the first 3 games to keep the test fast
        import xml.etree.ElementTree as ET
        root = ET.fromstring(collection_xml)
        items = root.findall("item") or root.findall(".//item")
        # Rebuild a minimal XML with just 3 items
        mini_root = ET.Element("items")
        for item in items[:3]:
            mini_root.append(item)
        mini_xml = ET.tostring(mini_root, encoding="unicode")

        games = await fetch_all_games(client, ids[:3], ratings, mini_xml)
        print(f"Hydrated: {len(games)} games")
        for g in games:
            print(f"  {g.name}: mechanics={g.mechanics[:2]}, categories={g.categories[:2]}")
        assert len(games) > 0, "fetch_all_games returned 0 games"
        assert any(g.mechanics for g in games), "No mechanics found in any game"
