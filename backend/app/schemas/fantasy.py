from pydantic import BaseModel, field_validator


class FantasyTeamCreate(BaseModel):
    name: str
    season_id: int


class FantasyTeamOut(BaseModel):
    id: int
    name: str
    budget: float
    total_points: int
    rank: int | None = None
    last_round_points: int | None = None
    model_config = {"from_attributes": True}


class PickCreate(BaseModel):
    player_id: int
    round_id: int
    slot: int
    is_captain: bool = False
    is_vice_captain: bool = False

    @field_validator("slot")
    @classmethod
    def slot_range(cls, v: int) -> int:
        if not (1 <= v <= 15):
            raise ValueError("slot must be 1-15")
        return v


class TeamBriefOut(BaseModel):
    id: int
    name: str
    short_name: str
    model_config = {"from_attributes": True}


class PlayerInPickOut(BaseModel):
    id: int
    name: str
    position: str
    price: float
    is_active: bool
    photo_url: str | None
    team: TeamBriefOut | None
    model_config = {"from_attributes": True}


class PickWithPlayerOut(BaseModel):
    id: int
    player_id: int
    round_id: int
    slot: int
    is_captain: bool
    is_vice_captain: bool
    player: PlayerInPickOut
    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    team_name: str
    username: str
    total_points: int
    model_config = {"from_attributes": True}
