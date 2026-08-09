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


class PlayerMatchHistoryOut(BaseModel):
    match_id: int
    round_number: int | None
    opponent: str
    is_home: bool
    home_score: int | None
    away_score: int | None
    started_at: datetime | None
    minutes_played: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    own_goals: int
    saves: int
    penalty_save: int
    penalty_miss: int
    clean_sheet: bool
    fantasy_points: int
