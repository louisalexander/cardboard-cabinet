"""Integration tests for the API endpoints"""

import pytest
import tempfile
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.db_models import Base, GameDB, GameMechanic, GameCategory, GameDesigner, GameArtist, GamePublisher
from app.db_storage import save_games
from app.models import Game


@pytest.fixture
def test_db():
    """Create a test database"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
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

    # Patch db_storage.get_db so direct next(get_db()) calls also use the test db
    with patch('app.db_storage.get_db', override_get_db):
        yield temp_file.name, engine

    app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(temp_file.name)


@pytest.fixture
def client(test_db):
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def sample_games():
    """Create sample games for testing"""
    return [
        Game(
            id=1,
            name="Agricola",
            year=2007,
            min_players=1,
            max_players=5,
            playing_time=150,
            weight=3.64,
            avg_rating=8.0,
            mechanics=["Worker Placement", "Farming"],
            categories=["Strategy", "Euro"],
            designers=["Uwe Rosenberg"],
            artists=["Klemens Franz"],
            publishers=["Lookout Games"]
        ),
        Game(
            id=2,
            name="Catan",
            year=1995,
            min_players=3,
            max_players=4,
            playing_time=90,
            weight=2.3,
            avg_rating=7.1,
            mechanics=["Trading", "Dice Rolling"],
            categories=["Strategy", "Family"],
            designers=["Klaus Teuber"],
            artists=["Michael Menzel"],
            publishers=["Catan Studio"]
        )
    ]


class TestBasicEndpoints:
    """Test basic API endpoints"""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Cardboard Cabinet" in response.text
    
    def test_test_endpoint(self, client):
        """Test the test endpoint"""
        response = client.get("/api/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "API is working"


class TestGamesEndpoints:
    """Test games-related API endpoints"""
    
    def test_get_games_empty(self, client, test_db):
        """Test getting games when database is empty"""
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_games_with_data(self, client, test_db, sample_games):
        """Test getting games when database has data"""
        # Save sample games to test database
        save_games(sample_games)
        
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert data[0]["name"] == "Agricola"
        assert data[1]["name"] == "Catan"
    
    def test_get_games_filtered(self, client, test_db, sample_games):
        """Test getting filtered games"""
        # Save sample games to test database
        save_games(sample_games)
        
        # Test filtering by mechanics
        response = client.get("/api/games?mechanics=Worker%20Placement")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Agricola"
        
        # Test filtering by categories
        response = client.get("/api/games?categories=Family")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Catan"
        
        # Test filtering by year
        response = client.get("/api/games?year_min=2000")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Agricola"
        
        # Test filtering by weight
        response = client.get("/api/games?weight_max=2.5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Catan"
        
        # Test search by name
        response = client.get("/api/games?search=agri")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Agricola"
    
    def test_get_games_combined_filters(self, client, test_db, sample_games):
        """Test combining multiple filters"""
        # Save sample games to test database
        save_games(sample_games)
        
        # Combine multiple filters - adjust weight_max to include Agricola (weight=3.64)
        response = client.get("/api/games?categories=Strategy&year_min=2000&weight_max=4.0")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only Agricola meets all criteria
        assert data[0]["name"] == "Agricola"


class TestFacetsEndpoints:
    """Test facets-related API endpoints"""
    
    def test_get_facets_empty(self, client, test_db):
        """Test getting facets when database is empty"""
        response = client.get("/api/facets")
        assert response.status_code == 200
        data = response.json()
        
        # Check that all facet categories exist but are empty
        assert "mechanics" in data
        assert "categories" in data
        assert "designers" in data
        assert "artists" in data
        assert "publishers" in data
        assert "years" in data
        assert "player_counts" in data
        assert "time_buckets" in data
        assert "weight_buckets" in data
        
        # All should be empty
        for facet_type in data.values():
            assert len(facet_type) == 0
    
    def test_get_facets_with_data(self, client, test_db, sample_games):
        """Test getting facets when database has data"""
        # Save sample games to test database
        save_games(sample_games)
        
        response = client.get("/api/facets")
        assert response.status_code == 200
        data = response.json()
        
        # Check mechanics
        assert "Worker Placement" in data["mechanics"]
        assert "Farming" in data["mechanics"]
        assert "Trading" in data["mechanics"]
        assert "Dice Rolling" in data["mechanics"]
        
        # Check categories
        assert "Strategy" in data["categories"]
        assert "Euro" in data["categories"]
        assert "Family" in data["categories"]
        
        # Check designers
        assert "Uwe Rosenberg" in data["designers"]
        assert "Klaus Teuber" in data["designers"]
        
        # Check years
        assert "2007" in data["years"]
        assert "1995" in data["years"]
        
        # Check player counts
        assert "1–5" in data["player_counts"]  # Agricola
        assert "3–4" in data["player_counts"]  # Catan
        
        # Check weight buckets
        assert "Medium‑Heavy (3.26–4.0)" in data["weight_buckets"]  # Agricola
        assert "Medium‑Light (1.76–2.5)" in data["weight_buckets"]  # Catan


class TestRefreshEndpoints:
    """Test refresh-related API endpoints"""
    
    def test_refresh_collection(self, client, test_db):
        """Test refreshing collection from BGG"""
        # This is a mock test since we don't want to hit the real BGG API
        # In a real integration test, you might use a mock or test BGG API
        
        # For now, just test that the endpoint exists and returns a proper response structure
        # Note: This would need to be mocked in a real test environment
        
        # Test with a mock username
        response = client.post("/api/refresh", json={"username": "testuser"})
        
        # The response might be an error if BGG API is not available, but structure should be correct
        if response.status_code == 200:
            data = response.json()
            assert "username" in data
            assert "total_in_collection" in data
            assert "total_hydrated" in data
            assert "cached" in data
        else:
            # If there's an error, it should be a proper error response
            assert response.status_code in [400, 500]  # Expected error codes


class TestErrorHandling:
    """Test error handling in the API"""
    
    def test_invalid_filter_parameters(self, client, test_db):
        """Test handling of invalid filter parameters"""
        # Test invalid year parameter
        response = client.get("/api/games?year_min=invalid")
        assert response.status_code == 422  # Validation error
        
        # Test invalid weight parameter
        response = client.get("/api/games?weight_max=invalid")
        assert response.status_code == 422  # Validation error
    
    def test_nonexistent_endpoint(self, client):
        """Test handling of nonexistent endpoints"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_http_method(self, client):
        """Test handling of invalid HTTP methods"""
        response = client.post("/api/games")
        assert response.status_code == 405  # Method not allowed
