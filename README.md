# Board Game Library (FastAPI + Vanilla JS)

A slick, filterable, visual view of your BoardGameGeek collection: -
Pulls your *owned* collection from BGG
(`/collection?username=...&own=1`) - Hydrates deep attributes via BGG
XML API2 `/thing?id=...&stats=1` - Caches locally (JSON) to avoid
hammering BGG - Facets: mechanics, categories, designers, artists,
publishers, year, player counts, play time, weight (complexity),
ratings - UI: tag cloud for mechanics, live filtering, search, and
result grid

## Quick start

``` bash
# 1) Create environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Configure your username
cp .env.sample .env
# edit .env and set BGG_USERNAME

# 4) Run
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000

## Refreshing data

Use the UI's "Refresh from BGG" button, or:

    POST /api/refresh            (uses BGG_USERNAME from .env)
    POST /api/refresh?username=YourBGGName

## API (selected)

-   `GET /api/games` --- all games (with optional filters via query
    string)
-   `GET /api/facets` --- computed facets & counts
-   `POST /api/refresh` --- fetch collection + hydrate details; caches
    to `data/cache.json`

### Filtering params (all optional; comma-separated lists allowed)

-   `mechanics, categories, designers, artists, publishers`
-   `year_min, year_max`
-   `players` (exact), `players_min`, `players_max`
-   `time_max` (minutes), `weight_min`, `weight_max`, `rating_min`,
    `search` (substring on name)

## Deploy (Render)

1.  Push this repo to GitHub.
2.  Create a new **Web Service** on Render:
    -   Environment: **Python 3**
    -   Build Command: `pip install -r requirements.txt`
    -   Start Command:
        `uvicorn app.main:app --host 0.0.0.0 --port 10000`
    -   Add environment variable `BGG_USERNAME=your_name`
3.  Set **Auto deploy** on.
4.  Visit the service URL.

## Notes

-   BGG XML API2 is rate-limited; we batch in chunks and sleep between
    calls to be polite.
-   If you want a DB later, swap the JSON cache with SQLite easily (see
    `storage.py`).
-   Front end is plain HTML/JS/CSS for zero-build hosting; upgrade to
    React any time.
