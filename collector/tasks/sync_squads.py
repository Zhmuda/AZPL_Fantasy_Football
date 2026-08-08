"""Sync full team squads from SofaScore.

Unlike sync_stats (which only learns about a player once they appear in a
match lineup, close to kickoff), this pulls each team's full current roster —
so fantasy squads can be built before a single match has been played.
"""
import logging
from celery_app import app
from db import get_session
from models import Team, Player
from sofascore import provider
from sync_log import log_error

logger = logging.getLogger(__name__)


@app.task(name="tasks.sync_squads.sync_team_squad")
def sync_team_squad(team_id: int):
    """Sync a single team's roster (manual retry from the admin panel)."""
    session = get_session()
    try:
        team = session.get(Team, team_id)
        if not team:
            logger.error("Team %d not found", team_id)
            return
        active_provider = provider.resolve_provider(session)
        _sync_team_safe(team, session, active_provider)
    finally:
        session.close()


def _sync_team_safe(team: Team, session, active_provider: str) -> list[int] | None:
    """Returns the list of player ids synced, or None if the fetch failed (logged)."""
    try:
        players = provider.get_team_squad(team.id, active_provider)
    except Exception as e:
        logger.exception("Failed to sync squad for team %d", team.id)
        log_error(session, "sync_squads", str(e), target=f"team:{team.id}")
        return None

    for p in players:
        existing = session.get(Player, p["id"])
        if not existing:
            session.add(Player(**p))
        else:
            existing.name = p["name"]
            existing.position = p["position"]
            existing.team_id = p["team_id"]
            existing.photo_url = p["photo_url"]
            existing.is_active = True
    session.commit()
    logger.info("Synced squad for %s: %d players", team.name, len(players))
    return [p["id"] for p in players]


@app.task(name="tasks.sync_squads.sync_all_squads")
def sync_all_squads():
    """Sync rosters for every team already known in the DB (run sync_matches first)."""
    session = get_session()
    try:
        active_provider = provider.resolve_provider(session)
        teams = session.query(Team).all()
        if not teams:
            logger.warning("No teams in DB yet — run sync_matches first")
            return

        seen_player_ids: set[int] = set()
        squad_sizes: dict[int, int] = {}
        failed_team_ids: set[int] = set()
        total = 0
        for team in teams:
            player_ids = _sync_team_safe(team, session, active_provider)
            if player_ids is None:
                failed_team_ids.add(team.id)
                continue
            squad_sizes[team.id] = len(player_ids)
            total += len(player_ids)
            seen_player_ids.update(player_ids)

        # Players who used to belong to one of our teams but no longer show up
        # in any current squad (transferred out of the league, retired, etc.)
        # — deactivate so they drop out of squad-selection. Keep the row itself
        # for historical picks/stats. Skip this pass if any team came back
        # empty or failed outright — that's almost certainly a fetch hiccup,
        # not a real 0-man squad, and would otherwise wipe out that team's
        # players entirely.
        if failed_team_ids or any(size == 0 for size in squad_sizes.values()):
            logger.warning(
                "%d team(s) failed or came back empty — skipping deactivation pass",
                len(failed_team_ids) + sum(1 for s in squad_sizes.values() if s == 0),
            )
        else:
            known_team_ids = [t.id for t in teams]
            deactivated = (
                session.query(Player)
                .filter(
                    Player.team_id.in_(known_team_ids),
                    Player.is_active == True,
                    ~Player.id.in_(seen_player_ids),
                )
                .update({"is_active": False}, synchronize_session=False)
            )
            session.commit()
            if deactivated:
                logger.info("Deactivated %d players no longer in any squad", deactivated)

        logger.info("Synced %d player rows across %d teams via %s", total, len(teams), active_provider)
    finally:
        session.close()
