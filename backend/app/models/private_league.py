from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.league import Season


class MiniLeague(Base):
    """A private league friends join via an invite code — scoped to a single
    season, separate from the global leaderboard."""
    __tablename__ = "mini_leagues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    season: Mapped["Season"] = relationship()
    owner: Mapped["User"] = relationship(foreign_keys=[owner_user_id])
    members: Mapped[list["MiniLeagueMember"]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MiniLeague {self.name} ({self.code})>"


class MiniLeagueMember(Base):
    __tablename__ = "mini_league_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("mini_leagues.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())

    league: Mapped["MiniLeague"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()

    __table_args__ = (UniqueConstraint("league_id", "user_id", name="uq_league_member"),)
