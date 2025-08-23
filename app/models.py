from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Game(BaseModel):
    id: int
    name: str
    year: Optional[int] = None
    image: Optional[str] = None
    thumbnail: Optional[str] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    playing_time: Optional[int] = None
    weight: Optional[float] = None
    avg_rating: Optional[float] = None
    bayes_rating: Optional[float] = None
    my_rating: Optional[float] = None
    mechanics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    designers: List[str] = Field(default_factory=list)
    artists: List[str] = Field(default_factory=list)
    publishers: List[str] = Field(default_factory=list)

class Facets(BaseModel):
    mechanics: Dict[str, int]
    categories: Dict[str, int]
    designers: Dict[str, int]
    artists: Dict[str, int]
    publishers: Dict[str, int]
    years: Dict[str, int]
    player_counts: Dict[str, int]
    time_buckets: Dict[str, int]
    weight_buckets: Dict[str, int]

class RefreshResponse(BaseModel):
    username: str
    total_in_collection: int
    total_hydrated: int
    cached: bool
