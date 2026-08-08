"""SQLAlchemy models for the collector service (sync, mirrors backend models)."""
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Season(Base):
    __tablename__ = "seasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    year: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(default=False)


class Round(Base):
    __tablename__ = "rounds"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    number: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    deadline: Mapped[datetime | None] = mapped_column(nullable=True)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[str] = mapped_column(String(1))
    price: Mapped[float] = mapped_column(default=5.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    round_id: Mapped[int | None] = mapped_column(ForeignKey("rounds.id"), nullable=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_score: Mapped[int | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    stats_synced: Mapped[bool] = mapped_column(default=False)


class MatchEvent(Base):
    __tablename__ = "match_events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    event_type: Mapped[str]
    minute: Mapped[int | None] = mapped_column(nullable=True)


class PlayerMatchStat(Base):
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

    __table_args__ = (UniqueConstraint("match_id", "player_id", name="uq_player_match"),)


# Users table — only needed as FK target
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)


class FantasyTeam(Base):
    __tablename__ = "fantasy_teams"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    name: Mapped[str]
    budget: Mapped[float] = mapped_column(default=100.0)
    total_points: Mapped[int] = mapped_column(default=0)
    __table_args__ = (UniqueConstraint("user_id", "season_id", name="uq_user_season_team"),)


class FantasyPick(Base):
    __tablename__ = "fantasy_picks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasy_teams.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    slot: Mapped[int]
    is_captain: Mapped[bool] = mapped_column(default=False)
    is_vice_captain: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint("fantasy_team_id", "player_id", "round_id", name="uq_pick_team_player_round"),)


class FantasyRoundScore(Base):
    __tablename__ = "fantasy_round_scores"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasy_teams.id"))
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    points: Mapped[int] = mapped_column(default=0)
    __table_args__ = (UniqueConstraint("fantasy_team_id", "round_id", name="uq_score_team_round"),)


class SyncLog(Base):
    """One row per sync failure (or explicit success note), browsable/retryable
    from the admin panel — without this, failures only ever existed in
    container stdout."""
    __tablename__ = "sync_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(100))
    # e.g. "match:16568133", "round:5", "team:5215" — None for whole-task failures
    target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="error")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SystemSetting(Base):
    """Singleton row (id=1) holding app-wide toggles editable from the admin panel."""
    __tablename__ = "system_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    # datafc | legacy
    sofascore_provider: Mapped[str] = mapped_column(String(20), default="datafc")
