from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_
from .database import engine
from .db_models import Base, GameDB, GameMechanic, GameCategory, GameDesigner, GameArtist, GamePublisher
from .models import Game


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)


def get_total_game_count(db: Session) -> int:
    return db.query(GameDB).count()


def _to_game(game_db: GameDB) -> Game:
    return Game(
        id=game_db.id,
        name=game_db.name,
        year=game_db.year,
        image=game_db.image,
        thumbnail=game_db.thumbnail,
        min_players=game_db.min_players,
        max_players=game_db.max_players,
        playing_time=game_db.playing_time,
        weight=game_db.weight,
        avg_rating=game_db.avg_rating,
        bayes_rating=game_db.bayes_rating,
        my_rating=game_db.my_rating,
        mechanics=[m.mechanic for m in game_db.mechanics],
        categories=[c.category for c in game_db.categories],
        designers=[d.designer for d in game_db.designers],
        artists=[a.artist for a in game_db.artists],
        publishers=[p.publisher for p in game_db.publishers],
    )


def save_games(games: List[Game], db: Session) -> None:
    """Replace all games in the database with the provided list."""
    # Delete child rows first (bulk delete bypasses ORM cascade).
    db.query(GameMechanic).delete()
    db.query(GameCategory).delete()
    db.query(GameDesigner).delete()
    db.query(GameArtist).delete()
    db.query(GamePublisher).delete()
    db.query(GameDB).delete()

    for game in games:
        db.add(GameDB(
            id=game.id, name=game.name, year=game.year,
            image=game.image, thumbnail=game.thumbnail,
            min_players=game.min_players, max_players=game.max_players,
            playing_time=game.playing_time, weight=game.weight,
            avg_rating=game.avg_rating, bayes_rating=game.bayes_rating,
            my_rating=game.my_rating,
        ))
        for m in game.mechanics:
            db.add(GameMechanic(game_id=game.id, mechanic=m))
        for c in game.categories:
            db.add(GameCategory(game_id=game.id, category=c))
        for d in game.designers:
            db.add(GameDesigner(game_id=game.id, designer=d))
        for a in game.artists:
            db.add(GameArtist(game_id=game.id, artist=a))
        for p in game.publishers:
            db.add(GamePublisher(game_id=game.id, publisher=p))

    db.commit()


def load_games(db: Session) -> List[Game]:
    """Load all games from the database (single query + selectinload)."""
    games_db = (
        db.query(GameDB)
        .options(
            selectinload(GameDB.mechanics),
            selectinload(GameDB.categories),
            selectinload(GameDB.designers),
            selectinload(GameDB.artists),
            selectinload(GameDB.publishers),
        )
        .all()
    )
    return [_to_game(g) for g in games_db]


def get_games_filtered(
    db: Session,
    mechanics: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    designers: Optional[List[str]] = None,
    artists: Optional[List[str]] = None,
    publishers: Optional[List[str]] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    players: Optional[int] = None,
    players_min: Optional[int] = None,
    players_max: Optional[int] = None,
    time_max: Optional[int] = None,
    weight_min: Optional[float] = None,
    weight_max: Optional[float] = None,
    rating_min: Optional[float] = None,
    search: Optional[str] = None,
) -> List[Game]:
    """Return games matching all supplied filters."""
    query = db.query(GameDB)

    if mechanics:
        query = query.join(GameMechanic).filter(GameMechanic.mechanic.in_(mechanics))
    if categories:
        query = query.join(GameCategory).filter(GameCategory.category.in_(categories))
    if designers:
        query = query.join(GameDesigner).filter(GameDesigner.designer.in_(designers))
    if artists:
        query = query.join(GameArtist).filter(GameArtist.artist.in_(artists))
    if publishers:
        query = query.join(GamePublisher).filter(GamePublisher.publisher.in_(publishers))

    if year_min is not None:
        query = query.filter(GameDB.year >= year_min)
    if year_max is not None:
        query = query.filter(GameDB.year <= year_max)

    if players is not None:
        query = query.filter(
            and_(
                or_(GameDB.min_players.is_(None), GameDB.min_players <= players),
                or_(GameDB.max_players.is_(None), GameDB.max_players >= players),
            )
        )
    if players_min is not None:
        query = query.filter(or_(GameDB.max_players.is_(None), GameDB.max_players >= players_min))
    if players_max is not None:
        query = query.filter(or_(GameDB.min_players.is_(None), GameDB.min_players <= players_max))

    # For time/weight/rating: NULLs are excluded when a bound is active.
    # A game with unknown weight should not appear in a weight-filtered result.
    if time_max is not None:
        query = query.filter(GameDB.playing_time <= time_max)
    if weight_min is not None:
        query = query.filter(GameDB.weight >= weight_min)
    if weight_max is not None:
        query = query.filter(GameDB.weight <= weight_max)
    if rating_min is not None:
        query = query.filter(GameDB.avg_rating >= rating_min)

    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(GameDB.name.ilike(f"%{escaped}%", escape="\\"))

    games_db = (
        query.distinct()
        .options(
            selectinload(GameDB.mechanics),
            selectinload(GameDB.categories),
            selectinload(GameDB.designers),
            selectinload(GameDB.artists),
            selectinload(GameDB.publishers),
        )
        .all()
    )
    return [_to_game(g) for g in games_db]
