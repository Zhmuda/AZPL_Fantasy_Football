"""Sync player stats for finished matches that haven't been processed yet."""
import logging
from celery_app import app
from db import get_session
from models import Match, Player, MatchEvent, PlayerMatchStat
from sofascore import provider
from sofascore.parsers import parse_incidents, parse_lineups
from sync_log import log_error

logger = logging.getLogger(__name__)


@app.task(name="tasks.sync_stats.sync_finished_matches")
def sync_finished_matches():
    """Find finished matches without stats and sync them."""
    session = get_session()
    try:
        pending = (
            session.query(Match)
            .filter_by(status="finished", stats_synced=False)
            .all()
        )
        logger.info("Found %d matches to sync stats for", len(pending))
        active_provider = provider.resolve_provider(session)
        for match in pending:
            _sync_match_stats(match, session, active_provider)
    finally:
        session.close()


@app.task(name="tasks.sync_stats.sync_match_stats")
def sync_match_stats(match_id: int):
    """Sync stats for a specific match (can be triggered manually)."""
    session = get_session()
    try:
        match = session.get(Match, match_id)
        if not match:
            logger.error("Match %d not found", match_id)
            return
        active_provider = provider.resolve_provider(session)
        _sync_match_stats(match, session, active_provider)
    finally:
        session.close()


def _sync_match_stats(match: Match, session, active_provider: str):
    logger.info("Syncing stats for match %d via %s", match.id, active_provider)
    try:
        _do_sync_match_stats(match, session, active_provider)
    except Exception as e:
        logger.exception("Failed to sync stats for match %d", match.id)
        log_error(session, "sync_stats.sync_match_stats", str(e), target=f"match:{match.id}")


def _do_sync_match_stats(match: Match, session, active_provider: str):
    lineups_raw = provider.get_event_lineups(match.id, active_provider)
    incidents_raw = provider.get_event_incidents(match.id, active_provider)

    # Upsert players from lineups
    players_data, stats_data = parse_lineups(lineups_raw, match.id, match.home_team_id, match.away_team_id)
    for p in players_data:
        existing = session.get(Player, p["id"])
        if not existing:
            session.add(Player(**p))
        else:
            existing.name = p["name"]
            existing.photo_url = p["photo_url"]
            existing.team_id = p["team_id"]
    session.flush()

    # Build player stat records from lineup data
    stat_map: dict[int, PlayerMatchStat] = {}
    for s in stats_data:
        existing_stat = (
            session.query(PlayerMatchStat)
            .filter_by(match_id=s["match_id"], player_id=s["player_id"])
            .first()
        )
        if not existing_stat:
            record = PlayerMatchStat(**s)
            session.add(record)
            session.flush()
            stat_map[s["player_id"]] = record
        else:
            existing_stat.minutes_played = s["minutes_played"]
            existing_stat.saves = s["saves"]
            stat_map[s["player_id"]] = existing_stat

    # Parse incidents and apply to stats
    events = parse_incidents(incidents_raw)

    # Clear old events for this match first
    session.query(MatchEvent).filter_by(match_id=match.id).delete()
    session.flush()

    for ev in events:
        player_id = ev["player_id"]
        # Only count events for players in lineup
        if player_id not in stat_map:
            continue

        session.add(MatchEvent(match_id=match.id, **ev))

        stat = stat_map[player_id]
        if ev["event_type"] == "goal":
            stat.goals += 1
        elif ev["event_type"] == "assist":
            stat.assists += 1
        elif ev["event_type"] == "yellow_card":
            stat.yellow_cards += 1
        elif ev["event_type"] == "red_card":
            stat.red_cards += 1
        elif ev["event_type"] == "own_goal":
            stat.own_goals += 1
        elif ev["event_type"] == "penalty_miss":
            stat.penalty_miss += 1
        elif ev["event_type"] == "penalty_save":
            stat.penalty_save += 1

    # Determine clean sheets
    home_conceded = match.away_score or 0
    away_conceded = match.home_score or 0

    for player_id, stat in stat_map.items():
        player = session.get(Player, player_id)
        if not player:
            continue

        conceded = home_conceded if _is_home_player(player_id, lineups_raw) else away_conceded
        stat.clean_sheet = (conceded == 0)

    match.stats_synced = True
    session.commit()
    logger.info("Stats synced for match %d (%d players)", match.id, len(stat_map))

    # Trigger points calculation
    from tasks.calc_points import calc_match_points
    calc_match_points.delay(match.id)


def _is_home_player(player_id: int, lineups: dict) -> bool:
    for entry in lineups.get("home", {}).get("players", []):
        if entry.get("player", {}).get("id") == player_id:
            return True
    return False
