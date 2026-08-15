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
from app.models.private_league import MiniLeague, MiniLeagueMember
from app.models.settings import SystemSetting
from app.models.synclog import SyncLog

# sqladmin's own UI chrome (buttons, "Logout", pagination, login form) is
# hardcoded in its templates and not translatable without overriding them —
# out of proportion for an internal admin tool. Model/column labels below
# are the part users actually read, so those are in Russian.


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id, User.username, User.email, User.is_admin, User.is_active, User.created_at,
        User.reset_code, User.reset_code_expires,
    ]
    column_labels = {
        User.username: "Имя пользователя", User.email: "Email",
        User.is_admin: "Админ", User.is_active: "Активен", User.created_at: "Создан",
        User.reset_code: "Код сброса пароля", User.reset_code_expires: "Код действует до",
    }
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.created_at]
    can_delete = True
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"


class SeasonAdmin(ModelView, model=Season):
    column_list = [Season.id, Season.name, Season.year, Season.is_active]
    column_labels = {Season.name: "Название", Season.year: "Год", Season.is_active: "Активен"}
    column_sortable_list = [Season.id]
    name = "Сезон"
    name_plural = "Сезоны"
    icon = "fa-solid fa-calendar"


class RoundAdmin(ModelView, model=Round):
    column_list = [Round.id, Round.season_id, Round.number, Round.status, Round.deadline]
    column_labels = {
        Round.season_id: "Сезон", Round.number: "Номер",
        Round.status: "Статус", Round.deadline: "Дедлайн",
    }
    column_sortable_list = [Round.number]
    name = "Тур"
    name_plural = "Туры"
    icon = "fa-solid fa-list-ol"


class TeamAdmin(ModelView, model=Team):
    """Real football clubs — named "Клуб" (not "Команда") to avoid confusion
    with FantasyTeam, which is the actual user-facing "команда"."""
    column_list = [Team.id, Team.name, Team.short_name]
    column_labels = {Team.name: "Название", Team.short_name: "Короткое имя"}
    column_searchable_list = [Team.name]
    name = "Клуб"
    name_plural = "Клубы"
    icon = "fa-solid fa-shield"


class PlayerAdmin(ModelView, model=Player):
    column_list = [Player.id, Player.name, Player.position, Player.price, Player.team_id, Player.is_active]
    column_labels = {
        Player.name: "Имя", Player.position: "Позиция", Player.price: "Цена",
        Player.team_id: "Клуб", Player.is_active: "Активен",
    }
    column_searchable_list = [Player.name]
    column_sortable_list = [Player.price, Player.position]
    column_filters = [Player.position, Player.is_active]
    name = "Игрок"
    name_plural = "Игроки"
    icon = "fa-solid fa-person-running"


class MatchAdmin(ModelView, model=Match):
    column_list = [Match.id, Match.round_id, Match.home_team_id, Match.away_team_id,
                   Match.home_score, Match.away_score, Match.status, Match.stats_synced]
    column_labels = {
        Match.round_id: "Тур", Match.home_team_id: "Хозяева", Match.away_team_id: "Гости",
        Match.home_score: "Счёт хозяев", Match.away_score: "Счёт гостей",
        Match.status: "Статус", Match.stats_synced: "Статистика синхр.",
    }
    column_sortable_list = [Match.started_at]
    name = "Матч"
    name_plural = "Матчи"
    icon = "fa-solid fa-futbol"


class PlayerMatchStatAdmin(ModelView, model=PlayerMatchStat):
    column_list = [
        PlayerMatchStat.id, PlayerMatchStat.match_id, PlayerMatchStat.player_id,
        PlayerMatchStat.minutes_played, PlayerMatchStat.goals, PlayerMatchStat.assists,
        PlayerMatchStat.yellow_cards, PlayerMatchStat.red_cards, PlayerMatchStat.saves,
        PlayerMatchStat.clean_sheet, PlayerMatchStat.fantasy_points,
    ]
    column_labels = {
        PlayerMatchStat.match_id: "Матч", PlayerMatchStat.player_id: "Игрок",
        PlayerMatchStat.minutes_played: "Минуты", PlayerMatchStat.goals: "Голы",
        PlayerMatchStat.assists: "Ассисты", PlayerMatchStat.yellow_cards: "ЖК",
        PlayerMatchStat.red_cards: "КК", PlayerMatchStat.saves: "Сейвы",
        PlayerMatchStat.clean_sheet: "Сухой матч", PlayerMatchStat.fantasy_points: "Очки",
    }
    name = "Статистика игрока"
    name_plural = "Статистика игроков"
    icon = "fa-solid fa-chart-bar"


class FantasyTeamAdmin(ModelView, model=FantasyTeam):
    column_list = [FantasyTeam.id, FantasyTeam.name, FantasyTeam.user_id,
                   FantasyTeam.season_id, FantasyTeam.budget, FantasyTeam.total_points]
    column_labels = {
        FantasyTeam.name: "Название", FantasyTeam.user_id: "Пользователь",
        FantasyTeam.season_id: "Сезон", FantasyTeam.budget: "Бюджет",
        FantasyTeam.total_points: "Очки",
    }
    column_sortable_list = [FantasyTeam.total_points]
    name = "Фэнтези-команда"
    name_plural = "Фэнтези-команды"
    icon = "fa-solid fa-trophy"


class FantasyPickAdmin(ModelView, model=FantasyPick):
    column_list = [FantasyPick.id, FantasyPick.fantasy_team_id, FantasyPick.player_id,
                   FantasyPick.round_id, FantasyPick.slot, FantasyPick.is_captain, FantasyPick.is_vice_captain]
    column_labels = {
        FantasyPick.fantasy_team_id: "Команда", FantasyPick.player_id: "Игрок",
        FantasyPick.round_id: "Тур", FantasyPick.slot: "Слот",
        FantasyPick.is_captain: "Капитан", FantasyPick.is_vice_captain: "Вице-капитан",
    }
    column_filters = [FantasyPick.round_id]
    name = "Пик"
    name_plural = "Пики"
    icon = "fa-solid fa-clipboard-list"


class FantasyRoundScoreAdmin(ModelView, model=FantasyRoundScore):
    column_list = [FantasyRoundScore.id, FantasyRoundScore.fantasy_team_id,
                   FantasyRoundScore.round_id, FantasyRoundScore.points]
    column_labels = {
        FantasyRoundScore.fantasy_team_id: "Команда",
        FantasyRoundScore.round_id: "Тур", FantasyRoundScore.points: "Очки",
    }
    column_filters = [FantasyRoundScore.round_id]
    column_sortable_list = [FantasyRoundScore.points]
    name = "Очки за тур"
    name_plural = "Очки за туры"
    icon = "fa-solid fa-chart-line"


class MiniLeagueAdmin(ModelView, model=MiniLeague):
    column_list = [MiniLeague.id, MiniLeague.name, MiniLeague.code,
                   MiniLeague.season_id, MiniLeague.owner_user_id, MiniLeague.created_at]
    column_labels = {
        MiniLeague.name: "Название", MiniLeague.code: "Код приглашения",
        MiniLeague.season_id: "Сезон", MiniLeague.owner_user_id: "Создатель",
        MiniLeague.created_at: "Создана",
    }
    column_searchable_list = [MiniLeague.name, MiniLeague.code]
    name = "Мини-лига"
    name_plural = "Мини-лиги"
    icon = "fa-solid fa-user-group"


class MiniLeagueMemberAdmin(ModelView, model=MiniLeagueMember):
    column_list = [MiniLeagueMember.id, MiniLeagueMember.league_id,
                   MiniLeagueMember.user_id, MiniLeagueMember.joined_at]
    column_labels = {
        MiniLeagueMember.league_id: "Лига", MiniLeagueMember.user_id: "Пользователь",
        MiniLeagueMember.joined_at: "Вступил",
    }
    column_filters = [MiniLeagueMember.league_id]
    name = "Участник мини-лиги"
    name_plural = "Участники мини-лиг"
    icon = "fa-solid fa-user-plus"


class MatchEventAdmin(ModelView, model=MatchEvent):
    column_list = [MatchEvent.id, MatchEvent.match_id, MatchEvent.player_id,
                   MatchEvent.event_type, MatchEvent.minute]
    column_labels = {
        MatchEvent.match_id: "Матч", MatchEvent.player_id: "Игрок",
        MatchEvent.event_type: "Тип события", MatchEvent.minute: "Минута",
    }
    column_filters = [MatchEvent.event_type]
    name = "Событие матча"
    name_plural = "События матчей"
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
    column_labels = {
        SyncLog.created_at: "Время", SyncLog.task_name: "Задача",
        SyncLog.target: "Цель", SyncLog.status: "Статус", SyncLog.message: "Сообщение",
    }
    column_sortable_list = [SyncLog.created_at]
    column_default_sort = [(SyncLog.created_at, True)]
    column_filters = [SyncLog.status, SyncLog.task_name]
    column_searchable_list = [SyncLog.task_name, SyncLog.target, SyncLog.message]
    can_create = False
    can_edit = False
    name = "Лог синка"
    name_plural = "Логи синка"
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
    column_labels = {SystemSetting.sofascore_provider: "Источник данных"}
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
    name = "Настройка"
    name_plural = "Настройки"
    icon = "fa-solid fa-database"
