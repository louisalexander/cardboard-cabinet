"""Simple integration tests for the API endpoints"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


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


class TestErrorHandling:
    """Test error handling in the API"""
    
    def test_nonexistent_endpoint(self, client):
        """Test handling of nonexistent endpoints"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_http_method(self, client):
        """Test handling of invalid HTTP methods"""
        response = client.post("/api/games")
        assert response.status_code == 405  # Method not allowed


class TestAPIStructure:
    """Test that the API structure is correct"""
    
    def test_app_has_correct_title(self, client):
        """Test that the app has the correct title"""
        # This tests that the FastAPI app is properly configured
        assert app.title == "BGG Library"
    
    def test_cors_middleware_configured(self, client):
        """Test that CORS middleware is configured"""
        # Check if CORS middleware is present
        middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert "CORSMiddleware" in middleware_names
    
    def test_static_files_mounted(self, client):
        """Test that static files are mounted"""
        # Check if static files are mounted
        routes = [route.path for route in app.routes]
        assert "/static" in routes


