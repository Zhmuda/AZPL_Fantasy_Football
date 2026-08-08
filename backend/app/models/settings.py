from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SystemSetting(Base):
    """Singleton row (id=1) holding app-wide toggles editable from the admin panel."""
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    # datafc | legacy
    sofascore_provider: Mapped[str] = mapped_column(String(20), default="datafc")

    def __repr__(self) -> str:
        return f"<SystemSetting sofascore_provider={self.sofascore_provider}>"
