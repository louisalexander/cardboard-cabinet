import json
from pathlib import Path
from typing import List
from .models import Game

DATA_DIR = Path("data")
CACHE_FILE = DATA_DIR / "cache.json"

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_cache() -> List[Game]:
    ensure_dirs()
    if not CACHE_FILE.exists():
        return []
    data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return [Game(**g) for g in data]

def save_cache(games: List[Game]) -> None:
    ensure_dirs()
    serial = [g.model_dump() for g in games]
    CACHE_FILE.write_text(json.dumps(serial, indent=2), encoding="utf-8")
