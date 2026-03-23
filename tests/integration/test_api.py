"""Integration tests for the API endpoints"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.db_models import Base
from app.db_storage import save_games
from app.models import Game


@pytest.fixture
def test_db():
    """Create an isolated test database and wire it into the app."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    engine = create_engine(f"sqlite:///{temp_file.name}", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield temp_file.name, engine, TestSession

    app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(temp_file.name)


@pytest.fixture
def db_session(test_db):
    """Session for direct storage calls inside tests."""
    _, _, TestSession = test_db
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def sample_games():
    return [
        Game(
            id=1, name="Agricola", year=2007,
            min_players=1, max_players=5, playing_time=150, weight=3.64, avg_rating=8.0,
            mechanics=["Worker Placement", "Farming"],
            categories=["Strategy", "Euro"],
            designers=["Uwe Rosenberg"],
            artists=["Klemens Franz"],
            publishers=["Lookout Games"],
        ),
        Game(
            id=2, name="Catan", year=1995,
            min_players=3, max_players=4, playing_time=90, weight=2.3, avg_rating=7.1,
            mechanics=["Trading", "Dice Rolling"],
            categories=["Strategy", "Family"],
            designers=["Klaus Teuber"],
            artists=["Michael Menzel"],
            publishers=["Catan Studio"],
        ),
    ]


class TestBasicEndpoints:

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Cardboard Cabinet" in response.text

    def test_test_endpoint(self, client):
        response = client.get("/api/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestGamesEndpoints:

    def test_get_games_empty(self, client):
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert data["games"] == []
        assert data["total"] == 0
        assert data["filtered"] == 0

    def test_get_games_with_data(self, client, db_session, sample_games):
        save_games(sample_games, db_session)
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 2
        assert data["total"] == 2
        assert data["filtered"] == 2

    def test_get_games_filtered(self, client, db_session, sample_games):
        save_games(sample_games, db_session)

        response = client.get("/api/games?mechanics=Worker%20Placement")
        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["name"] == "Agricola"
        assert data["total"] == 2
        assert data["filtered"] == 1

        response = client.get("/api/games?categories=Family")
        assert response.json()["games"][0]["name"] == "Catan"

        response = client.get("/api/games?year_min=2000")
        assert len(response.json()["games"]) == 1

        response = client.get("/api/games?weight_max=2.5")
        assert response.json()["games"][0]["name"] == "Catan"

        response = client.get("/api/games?search=agri")
        assert response.json()["games"][0]["name"] == "Agricola"

    def test_get_games_combined_filters(self, client, db_session, sample_games):
        save_games(sample_games, db_session)
        response = client.get("/api/games?categories=Strategy&year_min=2000&weight_max=4.0")
        data = response.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["name"] == "Agricola"


class TestFacetsEndpoints:

    def test_get_facets_empty(self, client):
        response = client.get("/api/facets")
        assert response.status_code == 200
        data = response.json()
        for key in ["mechanics", "categories", "designers", "artists",
                    "publishers", "years", "player_counts", "time_buckets", "weight_buckets"]:
            assert key in data
            assert len(data[key]) == 0

    def test_get_facets_with_data(self, client, db_session, sample_games):
        save_games(sample_games, db_session)
        response = client.get("/api/facets")
        data = response.json()
        assert "Worker Placement" in data["mechanics"]
        assert "Strategy" in data["categories"]
        assert "Uwe Rosenberg" in data["designers"]
        assert "2007" in data["years"]
        assert "1–5" in data["player_counts"]
        assert "Medium‑Heavy (3.26–4.0)" in data["weight_buckets"]


class TestRefreshEndpoints:

    def test_refresh_no_username_no_env(self, client):
        """Refresh with no username and no BGG_USERNAME env returns 400."""
        import os
        env_backup = os.environ.pop("BGG_USERNAME", None)
        try:
            response = client.post("/api/refresh")
            assert response.status_code == 400
            assert "BGG_USERNAME" in response.json()["detail"]
        finally:
            if env_backup is not None:
                os.environ["BGG_USERNAME"] = env_backup

    def test_refresh_reads_username_from_json_body(self, client):
        """Username in JSON body is used (not silently ignored as query param)."""
        # We expect a 500 because we're not hitting a real BGG API,
        # but the important thing is it's NOT a 400 (username was received).
        response = client.post("/api/refresh", json={"username": "testuser"})
        assert response.status_code in [200, 500]
        if response.status_code == 500:
            # Should be a generic error, not leaking internals
            assert "detail" in response.json()

    def test_refresh_empty_body_accepted(self, client):
        """POST with no body at all should not 422 — username is optional."""
        response = client.post("/api/refresh")
        # 400 (no username configured) or 500 (BGG unreachable), never 422
        assert response.status_code in [400, 500]


class TestErrorHandling:

    def test_invalid_filter_parameters(self, client):
        response = client.get("/api/games?year_min=invalid")
        assert response.status_code == 422

        response = client.get("/api/games?weight_max=invalid")
        assert response.status_code == 422

    def test_nonexistent_endpoint(self, client):
        assert client.get("/api/nonexistent").status_code == 404

    def test_invalid_http_method(self, client):
        assert client.post("/api/games").status_code == 405
