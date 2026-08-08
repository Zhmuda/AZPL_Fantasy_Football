from datetime import datetime
from pydantic import BaseModel


class SeasonOut(BaseModel):
    id: int
    name: str
    year: str
    is_active: bool
    model_config = {"from_attributes": True}


class RoundOut(BaseModel):
    id: int
    number: int
    status: str
    deadline: datetime | None
    model_config = {"from_attributes": True}


class TeamOut(BaseModel):
    id: int
    name: str
    short_name: str
    logo_url: str | None
    model_config = {"from_attributes": True}


class PlayerOut(BaseModel):
    id: int
    name: str
    position: str
    price: float
    is_active: bool
    photo_url: str | None
    team: TeamOut | None
    season_goals: int = 0
    season_assists: int = 0
    season_points: int = 0
    season_matches: int = 0
    model_config = {"from_attributes": True}


class MatchOut(BaseModel):
    id: int
    round_id: int | None
    home_team: TeamOut
    away_team: TeamOut
    home_score: int | None
    away_score: int | None
    status: str
    started_at: datetime | None
    model_config = {"from_attributes": True}
