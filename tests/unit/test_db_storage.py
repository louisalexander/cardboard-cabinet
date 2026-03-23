"""Unit tests for database storage operations"""

import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db_models import Base
from app.db_storage import save_games, load_games, get_games_filtered, init_db
from app.models import Game


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    # Create engine for the temp file
    engine = create_engine(f"sqlite:///{temp_file.name}", echo=False)
    Base.metadata.create_all(bind=engine)
    
    yield temp_file.name, engine
    
    # Cleanup
    engine.dispose()
    os.unlink(temp_file.name)


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
        ),
        Game(
            id=3,
            name="Pandemic",
            year=2008,
            min_players=2,
            max_players=4,
            playing_time=45,
            weight=2.4,
            avg_rating=7.6,
            mechanics=["Cooperative", "Hand Management"],
            categories=["Strategy", "Thematic"],
            designers=["Matt Leacock"],
            artists=["Josh Cappel"],
            publishers=["Z-Man Games"]
        )
    ]


class TestDatabaseOperations:
    """Test basic database operations"""
    
    def test_init_db(self, temp_db):
        """Test database initialization"""
        db_path, engine = temp_db
        
        # Initialize database
        init_db()
        
        # Check if tables were created
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        expected_tables = [
            'games', 'game_mechanics', 'game_categories',
            'game_designers', 'game_artists', 'game_publishers'
        ]
        
        for table in expected_tables:
            assert table in table_names
    
    def test_save_and_load_games(self, temp_db, sample_games):
        """Test saving and loading games"""
        db_path, engine = temp_db
        
        # Save games
        save_games(sample_games)
        
        # Load games
        loaded_games = load_games()
        
        # Verify all games were loaded
        assert len(loaded_games) == 3
        
        # Check first game details
        agricola = next(g for g in loaded_games if g.id == 1)
        assert agricola.name == "Agricola"
        assert agricola.year == 2007
        assert set(agricola.mechanics) == {"Worker Placement", "Farming"}
        assert set(agricola.designers) == {"Uwe Rosenberg"}
    
    def test_save_games_replaces_existing(self, temp_db, sample_games):
        """Test that saving games replaces existing data"""
        db_path, engine = temp_db
        
        # Save games first time
        save_games(sample_games[:2])  # Save first 2 games
        assert len(load_games()) == 2
        
        # Save different games
        new_games = [Game(id=999, name="New Game", mechanics=[], categories=[], designers=[], artists=[], publishers=[])]
        save_games(new_games)
        
        # Should only have the new game
        loaded_games = load_games()
        assert len(loaded_games) == 1
        assert loaded_games[0].name == "New Game"


class TestGameFiltering:
    """Test game filtering functionality"""
    
    def test_filter_by_mechanics(self, temp_db, sample_games):
        """Test filtering games by mechanics"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by worker placement
        worker_placement_games = get_games_filtered(mechanics=["Worker Placement"])
        assert len(worker_placement_games) == 1
        assert worker_placement_games[0].name == "Agricola"
        
        # Filter by multiple mechanics
        dice_games = get_games_filtered(mechanics=["Dice Rolling"])
        assert len(dice_games) == 1
        assert dice_games[0].name == "Catan"
    
    def test_filter_by_categories(self, temp_db, sample_games):
        """Test filtering games by categories"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by strategy category
        strategy_games = get_games_filtered(categories=["Strategy"])
        assert len(strategy_games) == 3  # All games are strategy
        
        # Filter by family category
        family_games = get_games_filtered(categories=["Family"])
        assert len(family_games) == 1
        assert family_games[0].name == "Catan"
    
    def test_filter_by_designers(self, temp_db, sample_games):
        """Test filtering games by designers"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by Uwe Rosenberg
        uwe_games = get_games_filtered(designers=["Uwe Rosenberg"])
        assert len(uwe_games) == 1
        assert uwe_games[0].name == "Agricola"
    
    def test_filter_by_year_range(self, temp_db, sample_games):
        """Test filtering games by year range"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by year range
        modern_games = get_games_filtered(year_min=2000)
        assert len(modern_games) == 2  # Agricola and Pandemic
        
        old_games = get_games_filtered(year_max=2000)
        assert len(old_games) == 1  # Catan
    
    def test_filter_by_player_count(self, temp_db, sample_games):
        """Test filtering games by player count"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by exact player count
        two_player_games = get_games_filtered(players=2)
        assert len(two_player_games) == 2  # Both Pandemic and Agricola support 2 players
        
        # Filter by player range
        family_games = get_games_filtered(players_min=3, players_max=5)
        assert len(family_games) == 3  # Agricola (1-5), Catan (3-4), and Pandemic (2-4)
    
    def test_filter_by_playing_time(self, temp_db, sample_games):
        """Test filtering games by playing time"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by max playing time
        short_games = get_games_filtered(time_max=60)
        assert len(short_games) == 1  # Pandemic
        
        long_games = get_games_filtered(time_max=120)
        assert len(long_games) == 2  # Pandemic and Catan
    
    def test_filter_by_weight(self, temp_db, sample_games):
        """Test filtering games by weight"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by weight range
        light_games = get_games_filtered(weight_max=2.5)
        assert len(light_games) == 2  # Catan and Pandemic
        
        heavy_games = get_games_filtered(weight_min=3.0)
        assert len(heavy_games) == 1  # Agricola
    
    def test_filter_by_rating(self, temp_db, sample_games):
        """Test filtering games by rating"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Filter by minimum rating
        high_rated_games = get_games_filtered(rating_min=7.5)
        assert len(high_rated_games) == 2  # Agricola and Pandemic
    
    def test_search_by_name(self, temp_db, sample_games):
        """Test searching games by name"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Search by partial name
        catan_results = get_games_filtered(search="Catan")
        assert len(catan_results) == 1
        assert catan_results[0].name == "Catan"
        
        # Search by partial name (case insensitive)
        agri_results = get_games_filtered(search="agri")
        assert len(agri_results) == 1
        assert agri_results[0].name == "Agricola"
    
    def test_combined_filters(self, temp_db, sample_games):
        """Test combining multiple filters"""
        db_path, engine = temp_db
        save_games(sample_games)
        
        # Combine multiple filters
        results = get_games_filtered(
            categories=["Strategy"],
            year_min=2000,
            weight_max=3.0
        )
        assert len(results) == 1  # Only Pandemic (Agricola is 3.64 weight, > 3.0)
        
        # More restrictive combination
        results = get_games_filtered(
            categories=["Strategy"],
            year_min=2000,
            weight_max=2.5
        )
        assert len(results) == 1  # Only Pandemic


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_games_list(self, temp_db):
        """Test saving empty list of games"""
        db_path, engine = temp_db
        
        save_games([])
        loaded_games = load_games()
        assert len(loaded_games) == 0
    
    def test_game_with_no_relationships(self, temp_db):
        """Test game with empty relationship lists"""
        db_path, engine = temp_db
        
        minimal_game = Game(
            id=999,
            name="Minimal Game",
            mechanics=[],
            categories=[],
            designers=[],
            artists=[],
            publishers=[]
        )
        
        save_games([minimal_game])
        loaded_games = load_games()
        
        assert len(loaded_games) == 1
        assert loaded_games[0].name == "Minimal Game"
        assert loaded_games[0].mechanics == []
        assert loaded_games[0].categories == []
    
    def test_null_values(self, temp_db):
        """Test handling of null values"""
        db_path, engine = temp_db
        
        null_game = Game(
            id=888,
            name="Null Test Game",
            year=None,
            weight=None,
            avg_rating=None,
            mechanics=[],
            categories=[],
            designers=[],
            artists=[],
            publishers=[]
        )
        
        save_games([null_game])
        loaded_games = load_games()
        
        assert len(loaded_games) == 1
        assert loaded_games[0].year is None
        assert loaded_games[0].weight is None
        assert loaded_games[0].avg_rating is None
