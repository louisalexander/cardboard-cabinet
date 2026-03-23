"""Unit tests for database models"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db_models import Base, GameDB, GameMechanic, GameCategory, GameDesigner, GameArtist, GamePublisher


@pytest.fixture
def test_engine():
    """Create a test database engine"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


class TestGameDB:
    """Test GameDB model"""
    
    def test_create_game(self, test_session):
        """Test creating a basic game"""
        game = GameDB(
            id=1,
            name="Test Game",
            year=2024,
            min_players=2,
            max_players=4,
            weight=2.5,
            avg_rating=7.5
        )
        test_session.add(game)
        test_session.commit()
        
        # Verify the game was saved
        saved_game = test_session.query(GameDB).filter_by(id=1).first()
        assert saved_game is not None
        assert saved_game.name == "Test Game"
        assert saved_game.year == 2024
        assert saved_game.weight == 2.5
    
    def test_game_optional_fields(self, test_session):
        """Test creating a game with minimal required fields"""
        game = GameDB(
            id=2,
            name="Minimal Game"
        )
        test_session.add(game)
        test_session.commit()
        
        saved_game = test_session.query(GameDB).filter_by(id=2).first()
        assert saved_game.name == "Minimal Game"
        assert saved_game.year is None
        assert saved_game.weight is None


class TestGameMechanic:
    """Test GameMechanic model"""
    
    def test_create_mechanic(self, test_session):
        """Test creating a game mechanic relationship"""
        # Create a game first
        game = GameDB(id=3, name="Mechanic Test Game")
        test_session.add(game)
        test_session.commit()
        
        # Create a mechanic
        mechanic = GameMechanic(game_id=3, mechanic="Deck Building")
        test_session.add(mechanic)
        test_session.commit()
        
        saved_mechanic = test_session.query(GameMechanic).filter_by(game_id=3).first()
        assert saved_mechanic.mechanic == "Deck Building"
        assert saved_mechanic.game_id == 3


class TestGameCategory:
    """Test GameCategory model"""
    
    def test_create_category(self, test_session):
        """Test creating a game category relationship"""
        # Create a game first
        game = GameDB(id=4, name="Category Test Game")
        test_session.add(game)
        test_session.commit()
        
        # Create a category
        category = GameCategory(game_id=4, category="Strategy")
        test_session.add(category)
        test_session.commit()
        
        saved_category = test_session.query(GameCategory).filter_by(game_id=4).first()
        assert saved_category.category == "Strategy"
        assert saved_category.game_id == 4


class TestGameDesigner:
    """Test GameDesigner model"""
    
    def test_create_designer(self, test_session):
        """Test creating a game designer relationship"""
        # Create a game first
        game = GameDB(id=5, name="Designer Test Game")
        test_session.add(game)
        test_session.commit()
        
        # Create a designer
        designer = GameDesigner(game_id=5, designer="Uwe Rosenberg")
        test_session.add(designer)
        test_session.commit()
        
        saved_designer = test_session.query(GameDesigner).filter_by(game_id=5).first()
        assert saved_designer.designer == "Uwe Rosenberg"
        assert saved_designer.game_id == 5


class TestGameArtist:
    """Test GameArtist model"""
    
    def test_create_artist(self, test_session):
        """Test creating a game artist relationship"""
        # Create a game first
        game = GameDB(id=6, name="Artist Test Game")
        test_session.add(game)
        test_session.commit()
        
        # Create an artist
        artist = GameArtist(game_id=6, artist="Klemens Franz")
        test_session.add(artist)
        test_session.commit()
        
        saved_artist = test_session.query(GameArtist).filter_by(game_id=6).first()
        assert saved_artist.artist == "Klemens Franz"
        assert saved_artist.game_id == 6


class TestGamePublisher:
    """Test GamePublisher model"""
    
    def test_create_publisher(self, test_session):
        """Test creating a game publisher relationship"""
        # Create a game first
        game = GameDB(id=7, name="Publisher Test Game")
        test_session.add(game)
        test_session.commit()
        
        # Create a publisher
        publisher = GamePublisher(game_id=7, publisher="Lookout Games")
        test_session.add(publisher)
        test_session.commit()
        
        saved_publisher = test_session.query(GamePublisher).filter_by(game_id=7).first()
        assert saved_publisher.publisher == "Lookout Games"
        assert saved_publisher.game_id == 7


class TestRelationships:
    """Test model relationships"""
    
    def test_game_with_all_relationships(self, test_session):
        """Test creating a game with all relationship types"""
        # Create a game
        game = GameDB(id=8, name="Full Relationship Game")
        test_session.add(game)
        test_session.commit()
        
        # Add relationships
        test_session.add(GameMechanic(game_id=8, mechanic="Worker Placement"))
        test_session.add(GameCategory(game_id=8, category="Euro"))
        test_session.add(GameDesigner(game_id=8, designer="Test Designer"))
        test_session.add(GameArtist(game_id=8, artist="Test Artist"))
        test_session.add(GamePublisher(game_id=8, publisher="Test Publisher"))
        test_session.commit()
        
        # Query the game with relationships
        saved_game = test_session.query(GameDB).filter_by(id=8).first()
        
        # Check relationships
        assert len(saved_game.mechanics) == 1
        assert saved_game.mechanics[0].mechanic == "Worker Placement"
        
        assert len(saved_game.categories) == 1
        assert saved_game.categories[0].category == "Euro"
        
        assert len(saved_game.designers) == 1
        assert saved_game.designers[0].designer == "Test Designer"
        
        assert len(saved_game.artists) == 1
        assert saved_game.artists[0].artist == "Test Artist"
        
        assert len(saved_game.publishers) == 1
        assert saved_game.publishers[0].publisher == "Test Publisher"


