from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.league import Season, Round, Player


class FantasyTeam(Base):
    __tablename__ = "fantasy_teams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    name: Mapped[str]
    budget: Mapped[float] = mapped_column(default=100.0)  # 100M total
    total_points: Mapped[int] = mapped_column(default=0)

    user: Mapped["User"] = relationship(back_populates="fantasy_teams")
    season: Mapped["Season"] = relationship(back_populates="fantasy_teams")
    picks: Mapped[list["FantasyPick"]] = relationship(back_populates="fantasy_team", cascade="all, delete-orphan")
    round_scores: Mapped[list["FantasyRoundScore"]] = relationship(back_populates="fantasy_team")

    __table_args__ = (UniqueConstraint("user_id", "season_id", name="uq_user_season_team"),)

    def __repr__(self) -> str:
        return f"<FantasyTeam {self.name}>"


class FantasyPick(Base):
    """A player picked by a user for a specific round.
    Slots 1-11 = starting XI, 12-15 = bench.
    """
    __tablename__ = "fantasy_picks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasy_teams.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    slot: Mapped[int]  # 1-11 starting, 12-15 bench
    is_captain: Mapped[bool] = mapped_column(default=False)
    is_vice_captain: Mapped[bool] = mapped_column(default=False)

    fantasy_team: Mapped["FantasyTeam"] = relationship(back_populates="picks")
    player: Mapped["Player"] = relationship()
    round: Mapped["Round"] = relationship(back_populates="picks")

    __table_args__ = (
        UniqueConstraint("fantasy_team_id", "player_id", "round_id", name="uq_pick_team_player_round"),
    )


class FantasyRoundScore(Base):
    __tablename__ = "fantasy_round_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasy_teams.id"))
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    points: Mapped[int] = mapped_column(default=0)

    fantasy_team: Mapped["FantasyTeam"] = relationship(back_populates="round_scores")
    round: Mapped["Round"] = relationship()

    __table_args__ = (UniqueConstraint("fantasy_team_id", "round_id", name="uq_score_team_round"),)
