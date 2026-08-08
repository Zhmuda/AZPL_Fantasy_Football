from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.stats import PlayerMatchStat, MatchEvent
    from app.models.fantasy import FantasyTeam, FantasyPick


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)  # SofaScore ID
    name: Mapped[str] = mapped_column(String(100))
    year: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(default=False)

    rounds: Mapped[list["Round"]] = relationship(back_populates="season", order_by="Round.number")
    matches: Mapped[list["Match"]] = relationship(back_populates="season")
    fantasy_teams: Mapped[list["FantasyTeam"]] = relationship(back_populates="season")

    def __repr__(self) -> str:
        return f"<Season {self.name}>"


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    number: Mapped[int]
    # scheduled | ongoing | finished
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    deadline: Mapped[datetime | None] = mapped_column(nullable=True)

    season: Mapped["Season"] = relationship(back_populates="rounds")
    matches: Mapped[list["Match"]] = relationship(back_populates="round")
    picks: Mapped[list["FantasyPick"]] = relationship(back_populates="round")

    def __repr__(self) -> str:
        return f"<Round {self.number}>"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)  # SofaScore ID
    name: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    players: Mapped[list["Player"]] = relationship(back_populates="team")
    home_matches: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.away_team_id", back_populates="away_team"
    )

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)  # SofaScore ID
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    # G=Goalkeeper, D=Defender, M=Midfielder, F=Forward
    position: Mapped[str] = mapped_column(String(1))
    price: Mapped[float] = mapped_column(default=5.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    team: Mapped["Team | None"] = relationship(back_populates="players")
    match_stats: Mapped[list["PlayerMatchStat"]] = relationship(back_populates="player")
    events: Mapped[list["MatchEvent"]] = relationship(back_populates="player")

    def __repr__(self) -> str:
        return f"<Player {self.name} ({self.position})>"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)  # SofaScore ID
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    round_id: Mapped[int | None] = mapped_column(ForeignKey("rounds.id"), nullable=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_score: Mapped[int | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None] = mapped_column(nullable=True)
    # scheduled | ongoing | finished
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    stats_synced: Mapped[bool] = mapped_column(default=False)

    season: Mapped["Season"] = relationship(back_populates="matches")
    round: Mapped["Round | None"] = relationship(back_populates="matches")
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id], back_populates="away_matches")
    player_stats: Mapped[list["PlayerMatchStat"]] = relationship(back_populates="match")
    events: Mapped[list["MatchEvent"]] = relationship(back_populates="match")

    def __repr__(self) -> str:
        return f"<Match {self.id}: {self.home_team_id} vs {self.away_team_id}>"
