from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class GameDB(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)
    image = Column(Text, nullable=True)
    thumbnail = Column(Text, nullable=True)
    min_players = Column(Integer, nullable=True)
    max_players = Column(Integer, nullable=True)
    playing_time = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    avg_rating = Column(Float, nullable=True)
    bayes_rating = Column(Float, nullable=True)
    my_rating = Column(Float, nullable=True)
    
    # Relationships for many-to-many fields
    mechanics = relationship("GameMechanic", back_populates="game")
    categories = relationship("GameCategory", back_populates="game")
    designers = relationship("GameDesigner", back_populates="game")
    artists = relationship("GameArtist", back_populates="game")
    publishers = relationship("GamePublisher", back_populates="game")

class GameMechanic(Base):
    __tablename__ = "game_mechanics"
    
    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    mechanic = Column(String, primary_key=True)
    game = relationship("GameDB", back_populates="mechanics")

class GameCategory(Base):
    __tablename__ = "game_categories"
    
    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    category = Column(String, primary_key=True)
    game = relationship("GameDB", back_populates="categories")

class GameDesigner(Base):
    __tablename__ = "game_designers"
    
    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    designer = Column(String, primary_key=True)
    game = relationship("GameDB", back_populates="designers")

class GameArtist(Base):
    __tablename__ = "game_artists"
    
    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    artist = Column(String, primary_key=True)
    game = relationship("GameDB", back_populates="artists")

class GamePublisher(Base):
    __tablename__ = "game_publishers"
    
    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    publisher = Column(String, primary_key=True)
    game = relationship("GameDB", back_populates="publishers")
