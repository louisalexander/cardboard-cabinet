"""Unit tests for database storage operations"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db_models import Base
from app.db_storage import save_games, load_games, get_games_filtered, init_db
from app.models import Game


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    engine = create_engine(f"sqlite:///{temp_file.name}", echo=False)
    Base.metadata.create_all(bind=engine)

    yield temp_file.name, engine

    engine.dispose()
    os.unlink(temp_file.name)


@pytest.fixture
def db_session(temp_db):
    """Provide a Session scoped to the temporary database."""
    _, engine = temp_db
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_games():
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
            publishers=["Lookout Games"],
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
            publishers=["Catan Studio"],
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
            publishers=["Z-Man Games"],
        ),
    ]


class TestDatabaseOperations:

    def test_init_db(self, temp_db):
        _, engine = temp_db
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        for table in ["games", "game_mechanics", "game_categories",
                      "game_designers", "game_artists", "game_publishers"]:
            assert table in table_names

    def test_save_and_load_games(self, db_session, sample_games):
        save_games(sample_games, db_session)
        loaded = load_games(db_session)
        assert len(loaded) == 3
        agricola = next(g for g in loaded if g.id == 1)
        assert agricola.name == "Agricola"
        assert agricola.year == 2007
        assert set(agricola.mechanics) == {"Worker Placement", "Farming"}
        assert set(agricola.designers) == {"Uwe Rosenberg"}

    def test_save_games_replaces_existing(self, db_session, sample_games):
        save_games(sample_games[:2], db_session)
        assert len(load_games(db_session)) == 2

        new_games = [Game(id=999, name="New Game", mechanics=[], categories=[],
                          designers=[], artists=[], publishers=[])]
        save_games(new_games, db_session)
        loaded = load_games(db_session)
        assert len(loaded) == 1
        assert loaded[0].name == "New Game"


class TestGameFiltering:

    def test_filter_by_mechanics(self, db_session, sample_games):
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, mechanics=["Worker Placement"])
        assert len(results) == 1
        assert results[0].name == "Agricola"

        results = get_games_filtered(db_session, mechanics=["Dice Rolling"])
        assert len(results) == 1
        assert results[0].name == "Catan"

    def test_filter_by_categories(self, db_session, sample_games):
        save_games(sample_games, db_session)
        assert len(get_games_filtered(db_session, categories=["Strategy"])) == 3
        results = get_games_filtered(db_session, categories=["Family"])
        assert len(results) == 1
        assert results[0].name == "Catan"

    def test_filter_by_designers(self, db_session, sample_games):
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, designers=["Uwe Rosenberg"])
        assert len(results) == 1
        assert results[0].name == "Agricola"

    def test_filter_by_year_range(self, db_session, sample_games):
        save_games(sample_games, db_session)
        assert len(get_games_filtered(db_session, year_min=2000)) == 2
        assert len(get_games_filtered(db_session, year_max=2000)) == 1

    def test_filter_by_player_count(self, db_session, sample_games):
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, players=2)
        assert len(results) == 2  # Agricola (1-5) and Pandemic (2-4)

        results = get_games_filtered(db_session, players_min=3, players_max=5)
        assert len(results) == 3

    def test_filter_by_playing_time(self, db_session, sample_games):
        save_games(sample_games, db_session)
        assert len(get_games_filtered(db_session, time_max=60)) == 1   # Pandemic
        assert len(get_games_filtered(db_session, time_max=120)) == 2  # Pandemic + Catan

    def test_filter_by_weight(self, db_session, sample_games):
        save_games(sample_games, db_session)
        assert len(get_games_filtered(db_session, weight_max=2.5)) == 2  # Catan + Pandemic
        assert len(get_games_filtered(db_session, weight_min=3.0)) == 1  # Agricola

    def test_filter_by_rating(self, db_session, sample_games):
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, rating_min=7.5)
        assert len(results) == 2  # Agricola (8.0) and Pandemic (7.6)

    def test_search_by_name(self, db_session, sample_games):
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, search="Catan")
        assert len(results) == 1
        assert results[0].name == "Catan"

        results = get_games_filtered(db_session, search="agri")
        assert len(results) == 1
        assert results[0].name == "Agricola"

    def test_combined_filters(self, db_session, sample_games):
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, categories=["Strategy"], year_min=2000, weight_max=3.0)
        assert len(results) == 1  # Only Pandemic (Agricola weight 3.64 > 3.0)

    def test_search_wildcard_characters_safe(self, db_session, sample_games):
        """% and _ in search should not be treated as SQL wildcards."""
        save_games(sample_games, db_session)
        results = get_games_filtered(db_session, search="%")
        assert len(results) == 0  # Should match nothing, not everything


class TestEdgeCases:

    def test_empty_games_list(self, db_session):
        save_games([], db_session)
        assert len(load_games(db_session)) == 0

    def test_game_with_no_relationships(self, db_session):
        game = Game(id=999, name="Minimal Game", mechanics=[], categories=[],
                    designers=[], artists=[], publishers=[])
        save_games([game], db_session)
        loaded = load_games(db_session)
        assert len(loaded) == 1
        assert loaded[0].mechanics == []

    def test_null_values(self, db_session):
        game = Game(id=888, name="Null Test Game", year=None, weight=None,
                    avg_rating=None, mechanics=[], categories=[], designers=[],
                    artists=[], publishers=[])
        save_games([game], db_session)
        loaded = load_games(db_session)
        assert loaded[0].year is None
        assert loaded[0].weight is None
        assert loaded[0].avg_rating is None
