from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.league import Match, Player


class MatchEvent(Base):
    """Raw match incidents: goals, assists, cards, substitutions."""
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    # goal | own_goal | assist | yellow_card | red_card | sub_in | sub_out
    # penalty_miss | penalty_save
    event_type: Mapped[str]
    minute: Mapped[int | None] = mapped_column(nullable=True)

    match: Mapped["Match"] = relationship(back_populates="events")
    player: Mapped["Player"] = relationship(back_populates="events")


class PlayerMatchStat(Base):
    """Aggregated per-match stats used to calculate fantasy points."""
    __tablename__ = "player_match_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))

    minutes_played: Mapped[int] = mapped_column(default=0)
    goals: Mapped[int] = mapped_column(default=0)
    assists: Mapped[int] = mapped_column(default=0)
    yellow_cards: Mapped[int] = mapped_column(default=0)
    red_cards: Mapped[int] = mapped_column(default=0)
    saves: Mapped[int] = mapped_column(default=0)
    own_goals: Mapped[int] = mapped_column(default=0)
    penalty_miss: Mapped[int] = mapped_column(default=0)
    penalty_save: Mapped[int] = mapped_column(default=0)
    clean_sheet: Mapped[bool] = mapped_column(default=False)
    fantasy_points: Mapped[int] = mapped_column(default=0)

    match: Mapped["Match"] = relationship(back_populates="player_stats")
    player: Mapped["Player"] = relationship(back_populates="match_stats")

    __table_args__ = (UniqueConstraint("match_id", "player_id", name="uq_player_match"),)
