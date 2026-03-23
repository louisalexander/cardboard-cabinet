from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .database import get_db, engine
from .db_models import Base, GameDB, GameMechanic, GameCategory, GameDesigner, GameArtist, GamePublisher
from .models import Game

def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine)

def save_games(games: List[Game]) -> None:
    """Save games to the database, replacing existing data"""
    db = next(get_db())
    try:
        # Clear existing data
        db.query(GameMechanic).delete()
        db.query(GameCategory).delete()
        db.query(GameDesigner).delete()
        db.query(GameArtist).delete()
        db.query(GamePublisher).delete()
        db.query(GameDB).delete()
        
        # Add new games
        for game in games:
            game_db = GameDB(
                id=game.id,
                name=game.name,
                year=game.year,
                image=game.image,
                thumbnail=game.thumbnail,
                min_players=game.min_players,
                max_players=game.max_players,
                playing_time=game.playing_time,
                weight=game.weight,
                avg_rating=game.avg_rating,
                bayes_rating=game.bayes_rating,
                my_rating=game.my_rating
            )
            db.add(game_db)
            
            # Add related data
            for mechanic in game.mechanics:
                db.add(GameMechanic(game_id=game.id, mechanic=mechanic))
            
            for category in game.categories:
                db.add(GameCategory(game_id=game.id, category=category))
            
            for designer in game.designers:
                db.add(GameDesigner(game_id=game.id, designer=designer))
            
            for artist in game.artists:
                db.add(GameArtist(game_id=game.id, artist=artist))
            
            for publisher in game.publishers:
                db.add(GamePublisher(game_id=game.id, publisher=publisher))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def load_games() -> List[Game]:
    """Load all games from the database"""
    db = next(get_db())
    try:
        games_db = db.query(GameDB).all()
        games = []
        
        for game_db in games_db:
            # Get related data
            mechanics = [m.mechanic for m in game_db.mechanics]
            categories = [c.category for c in game_db.categories]
            designers = [d.designer for d in game_db.designers]
            artists = [a.artist for a in game_db.artists]
            publishers = [p.publisher for p in game_db.publishers]
            
            game = Game(
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
                mechanics=mechanics,
                categories=categories,
                designers=designers,
                artists=artists,
                publishers=publishers
            )
            games.append(game)
        
        return games
    finally:
        db.close()

def get_games_filtered(
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
    search: Optional[str] = None
) -> List[Game]:
    """Get games from database with filters applied"""
    db = next(get_db())
    try:
        query = db.query(GameDB)
        
        # Apply filters
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
                    or_(GameDB.max_players.is_(None), GameDB.max_players >= players)
                )
            )
        
        if players_min is not None:
            query = query.filter(or_(GameDB.max_players.is_(None), GameDB.max_players >= players_min))
        
        if players_max is not None:
            query = query.filter(or_(GameDB.min_players.is_(None), GameDB.min_players <= players_max))
        
        if time_max is not None:
            query = query.filter(or_(GameDB.playing_time.is_(None), GameDB.playing_time <= time_max))
        
        if weight_min is not None:
            query = query.filter(or_(GameDB.weight.is_(None), GameDB.weight >= weight_min))
        
        if weight_max is not None:
            query = query.filter(or_(GameDB.weight.is_(None), GameDB.weight <= weight_max))
        
        if rating_min is not None:
            query = query.filter(or_(GameDB.avg_rating.is_(None), GameDB.avg_rating >= rating_min))
        
        if search:
            query = query.filter(GameDB.name.ilike(f"%{search}%"))
        
        # Add distinct() to avoid duplicates when using joins
        query = query.distinct()
        
        # Execute query and convert to Game objects
        games_db = query.all()
        games = []
        
        for game_db in games_db:
            # Get related data
            mechanics = [m.mechanic for m in game_db.mechanics]
            categories = [c.category for c in game_db.categories]
            designers = [d.designer for d in game_db.designers]
            artists = [a.artist for a in game_db.artists]
            publishers = [p.publisher for p in game_db.publishers]
            
            game = Game(
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
                mechanics=mechanics,
                categories=categories,
                designers=designers,
                artists=artists,
                publishers=publishers
            )
            games.append(game)
        
        return games
    finally:
        db.close()
