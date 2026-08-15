from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.fantasy import FantasyTeam


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Password reset — no email delivery, so the code just sits here for the
    # site owner to read in the admin panel and relay to the user manually.
    reset_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    reset_code_expires: Mapped[datetime | None] = mapped_column(nullable=True)

    fantasy_teams: Mapped[list["FantasyTeam"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.username}>"
