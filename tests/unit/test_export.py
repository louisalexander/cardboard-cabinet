import json
import pytest
from app.models import Game
from scripts.export_collection import games_to_json

pytestmark = pytest.mark.unit


def test_games_to_json_is_sorted_and_complete():
    games = [
        Game(id=2, name="Zebra", year=2020, mechanics=["A"]),
        Game(id=1, name="apple", year=2019, mechanics=["B", "C"]),
    ]
    out = games_to_json(games)
    data = json.loads(out)

    # Sorted case-insensitively by name.
    assert [g["name"] for g in data] == ["apple", "Zebra"]
    # Full Game shape preserved.
    assert data[0]["id"] == 1
    assert data[0]["mechanics"] == ["B", "C"]
    assert "thumbnail" in data[0]
