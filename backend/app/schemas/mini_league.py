from pydantic import BaseModel, Field


class MiniLeagueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    season_id: int


class MiniLeagueJoin(BaseModel):
    code: str = Field(min_length=1, max_length=10)


class MiniLeagueOut(BaseModel):
    id: int
    name: str
    code: str
    season_id: int
    member_count: int
    is_owner: bool


class MiniLeagueStandingEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    team_name: str | None
    total_points: int
    is_me: bool


class MiniLeagueStandingsOut(BaseModel):
    league: MiniLeagueOut
    standings: list[MiniLeagueStandingEntry]
