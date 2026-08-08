from sqladmin import ModelView, action
from sqladmin.fields import SelectField
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.celery_client import send_task
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.league import Season, Round, Team, Player, Match
from app.models.stats import PlayerMatchStat, MatchEvent
from app.models.fantasy import FantasyTeam, FantasyPick, FantasyRoundScore
from app.models.settings import SystemSetting
from app.models.synclog import SyncLog


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.is_admin, User.is_active, User.created_at]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.created_at]
    can_delete = True
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"


class SeasonAdmin(ModelView, model=Season):
    column_list = [Season.id, Season.name, Season.year, Season.is_active]
    column_sortable_list = [Season.id]
    name = "Season"
    name_plural = "Seasons"
    icon = "fa-solid fa-calendar"


class RoundAdmin(ModelView, model=Round):
    column_list = [Round.id, Round.season_id, Round.number, Round.status, Round.deadline]
    column_sortable_list = [Round.number]
    name = "Round"
    name_plural = "Rounds"
    icon = "fa-solid fa-list-ol"


class TeamAdmin(ModelView, model=Team):
    column_list = [Team.id, Team.name, Team.short_name]
    column_searchable_list = [Team.name]
    name = "Team"
    name_plural = "Teams"
    icon = "fa-solid fa-shield"


class PlayerAdmin(ModelView, model=Player):
    column_list = [Player.id, Player.name, Player.position, Player.price, Player.team_id, Player.is_active]
    column_searchable_list = [Player.name]
    column_sortable_list = [Player.price, Player.position]
    column_filters = [Player.position, Player.is_active]
    name = "Player"
    name_plural = "Players"
    icon = "fa-solid fa-person-running"


class MatchAdmin(ModelView, model=Match):
    column_list = [Match.id, Match.round_id, Match.home_team_id, Match.away_team_id,
                   Match.home_score, Match.away_score, Match.status, Match.stats_synced]
    column_sortable_list = [Match.started_at]
    name = "Match"
    name_plural = "Matches"
    icon = "fa-solid fa-futbol"


class PlayerMatchStatAdmin(ModelView, model=PlayerMatchStat):
    column_list = [
        PlayerMatchStat.id, PlayerMatchStat.match_id, PlayerMatchStat.player_id,
        PlayerMatchStat.minutes_played, PlayerMatchStat.goals, PlayerMatchStat.assists,
        PlayerMatchStat.yellow_cards, PlayerMatchStat.red_cards, PlayerMatchStat.saves,
        PlayerMatchStat.clean_sheet, PlayerMatchStat.fantasy_points,
    ]
    name = "Player Match Stat"
    name_plural = "Player Match Stats"
    icon = "fa-solid fa-chart-bar"


class FantasyTeamAdmin(ModelView, model=FantasyTeam):
    column_list = [FantasyTeam.id, FantasyTeam.name, FantasyTeam.user_id,
                   FantasyTeam.season_id, FantasyTeam.budget, FantasyTeam.total_points]
    column_sortable_list = [FantasyTeam.total_points]
    name = "Fantasy Team"
    name_plural = "Fantasy Teams"
    icon = "fa-solid fa-trophy"


class FantasyPickAdmin(ModelView, model=FantasyPick):
    column_list = [FantasyPick.id, FantasyPick.fantasy_team_id, FantasyPick.player_id,
                   FantasyPick.round_id, FantasyPick.slot, FantasyPick.is_captain, FantasyPick.is_vice_captain]
    column_filters = [FantasyPick.round_id]
    name = "Fantasy Pick"
    name_plural = "Fantasy Picks"
    icon = "fa-solid fa-clipboard-list"


class FantasyRoundScoreAdmin(ModelView, model=FantasyRoundScore):
    column_list = [FantasyRoundScore.id, FantasyRoundScore.fantasy_team_id,
                   FantasyRoundScore.round_id, FantasyRoundScore.points]
    column_filters = [FantasyRoundScore.round_id]
    column_sortable_list = [FantasyRoundScore.points]
    name = "Round Score"
    name_plural = "Round Scores"
    icon = "fa-solid fa-chart-line"


class MatchEventAdmin(ModelView, model=MatchEvent):
    column_list = [MatchEvent.id, MatchEvent.match_id, MatchEvent.player_id,
                   MatchEvent.event_type, MatchEvent.minute]
    column_filters = [MatchEvent.event_type]
    name = "Match Event"
    name_plural = "Match Events"
    icon = "fa-solid fa-bolt"


def _resolve_retry_task(log: SyncLog) -> tuple[str, list] | None:
    """Maps a failed SyncLog row back to the Celery task + args that would
    redo just that piece of work."""
    target = log.target or ""
    if target.startswith("match:"):
        match_id = int(target.split(":", 1)[1])
        if log.task_name.startswith("calc_points"):
            return "tasks.calc_points.calc_match_points", [match_id]
        return "tasks.sync_stats.sync_match_stats", [match_id]
    if target.startswith("round:"):
        return "tasks.sync_matches.sync_round", [int(target.split(":", 1)[1])]
    if target.startswith("team:"):
        return "tasks.sync_squads.sync_team_squad", [int(target.split(":", 1)[1])]
    if log.task_name == "sync_seasons.sync_seasons":
        return "tasks.sync_seasons.sync_seasons", []
    if log.task_name == "set_prices.set_player_prices":
        return "tasks.set_prices.set_player_prices", []
    return None


class SyncLogAdmin(ModelView, model=SyncLog):
    column_list = [
        SyncLog.id, SyncLog.created_at, SyncLog.task_name,
        SyncLog.target, SyncLog.status, SyncLog.message,
    ]
    column_sortable_list = [SyncLog.created_at]
    column_default_sort = [(SyncLog.created_at, True)]
    column_filters = [SyncLog.status, SyncLog.task_name]
    column_searchable_list = [SyncLog.task_name, SyncLog.target, SyncLog.message]
    can_create = False
    can_edit = False
    name = "Sync Log"
    name_plural = "Sync Logs"
    icon = "fa-solid fa-triangle-exclamation"

    @action(
        name="retry",
        label="Повторить",
        confirmation_message="Повторить выбранные задачи заново?",
    )
    async def retry(self, request: Request) -> RedirectResponse:
        pks = request.query_params.get("pks", "")
        ids = [int(x) for x in pks.split(",") if x]

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SyncLog).where(SyncLog.id.in_(ids)))
            logs = result.scalars().all()

        for log in logs:
            resolved = _resolve_retry_task(log)
            if resolved:
                task_name, args = resolved
                send_task(task_name, args)

        referer = request.headers.get("referer") or "/admin/sync-log/list"
        return RedirectResponse(url=referer, status_code=302)


class SystemSettingAdmin(ModelView, model=SystemSetting):
    """Singleton settings row — only editing is allowed, no create/delete."""
    column_list = [SystemSetting.id, SystemSetting.sofascore_provider]
    form_columns = [SystemSetting.sofascore_provider]
    form_overrides = {"sofascore_provider": SelectField}
    form_args = {
        "sofascore_provider": {
            "choices": [
                ("datafc", "datafc (по умолчанию)"),
                ("legacy", "legacy (собственный скрапер)"),
            ],
        },
    }
    can_create = False
    can_delete = False
    name = "Data Source"
    name_plural = "Data Source"
    icon = "fa-solid fa-database"
