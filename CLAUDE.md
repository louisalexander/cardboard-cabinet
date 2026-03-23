# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Cardboard Cabinet** is a web app for managing and browsing board game collections from BoardGameGeek (BGG). It consists of a FastAPI backend (Python) and a vanilla JS frontend.

## Commands

### Running the app
```bash
# Set up environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure BGG username
echo "BGG_USERNAME=yourusername" > .env

# Start the server (serves frontend at http://localhost:8000)
uvicorn app.main:app --reload
```

### Testing
```bash
# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_db_storage.py

# Run a single test
pytest tests/unit/test_db_storage.py::TestGameFiltering::test_filter_by_mechanics

# Run by marker
pytest -m unit
pytest -m integration
```

### Docker
```bash
docker build -t cardboard-cabinet .
docker run -p 8000:8000 -e BGG_USERNAME=yourusername cardboard-cabinet
```

## Architecture

### Data Flow
1. `POST /api/refresh` triggers `app/bgg.py` to fetch the user's BGG collection
2. Games are saved to SQLite via `app/db_storage.py`
3. `GET /api/games` and `GET /api/facets` query the database and return filtered results
4. The frontend (`frontend/app.js`) fetches from the API and renders the UI

### Backend (`app/`)
- **`main.py`** — FastAPI app, all route handlers, filter matching logic (`matches_filters()`), facet aggregation (`make_facets()`) with bucketing for time/weight/player counts
- **`bgg.py`** — BGG XML API integration; parallel chunk fetching (20 games/chunk, 5 concurrent), polls on 202 responses
- **`db_storage.py`** — Database operations: `init_db()`, `save_games()` (full replace), `load_games()`, `get_games_filtered()` (SQLAlchemy query builder with joins)
- **`db_models.py`** — SQLAlchemy ORM: `GameDB` + 5 relationship tables (mechanics, categories, designers, artists, publishers) using composite PKs
- **`models.py`** — Pydantic models: `Game`, `Facets`, `RefreshResponse`
- **`database.py`** — SQLAlchemy engine/session setup, SQLite at `data/games.db`
- **`storage.py`** — Legacy JSON cache (superseded by database, kept for reference)

### Frontend (`frontend/`)
Vanilla JS, no build step. `app.js` calls the REST API, handles filtering/search client-side state, and toggles between tile and list views.

### Tests (`tests/`)
- `tests/unit/` — Uses in-memory SQLite; tests models and storage operations in isolation
- `tests/integration/` — Uses FastAPI `TestClient` with dependency overrides to inject a test database

### Key Design Decisions
- **Full replace on refresh**: `save_games()` deletes all rows before inserting new data
- **Filtering**: Complex filters happen in SQL (`get_games_filtered()`); facet counts happen in Python (`make_facets()`) after loading all games
- **Bucketing**: Playing time and weight are bucketed into display labels in `make_facets()` and `util.py`
- **BGG API**: Fetches collection IDs first, then games in parallel chunks; falls back to sequential if parallel fails
