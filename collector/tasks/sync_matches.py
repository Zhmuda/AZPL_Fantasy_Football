"""Sync matches (events) for all rounds from SofaScore."""
import os
import logging
from celery_app import app
from db import get_session
from models import Season, Round, Team, Match
from sofascore import provider
from sync_log import log_error

logger = logging.getLogger(__name__)
TOURNAMENT_ID = int(os.getenv("SOFASCORE_TOURNAMENT_ID", "709"))


@app.task(name="tasks.sync_matches.sync_current_round")
def sync_current_round():
    """Sync matches for the current active round, plus any earlier round still
    holding a postponed match — a postponed match can get rescheduled and
    played weeks later, and nothing else ever re-checks a round once it's
    behind the current one."""
    session = get_session()
    try:
        active_season = session.query(Season).filter_by(is_active=True).first()
        if not active_season:
            logger.warning("No active season found")
            return

        rounds = session.query(Round).filter_by(season_id=active_season.id).order_by(Round.number).all()

        target_round = next((r for r in rounds if r.status != "finished"), None)
        targets = [target_round] if target_round else []

        postponed_round_ids = {
            m.round_id for m in session.query(Match)
            .filter_by(season_id=active_season.id, status="postponed")
            .all()
            if m.round_id
        }
        targets += [r for r in rounds if r.id in postponed_round_ids and r is not target_round]

        if not targets:
            logger.info("All rounds finished")
            return

        active_provider = provider.resolve_provider(session)
        for r in targets:
            _sync_round_safe(r, active_season.id, session, active_provider)
    finally:
        session.close()


@app.task(name="tasks.sync_matches.sync_round")
def sync_round(round_id: int):
    """Sync a specific round (manual retry from the admin panel)."""
    session = get_session()
    try:
        round_obj = session.get(Round, round_id)
        if not round_obj:
            logger.error("Round %d not found", round_id)
            return
        active_provider = provider.resolve_provider(session)
        _sync_round_safe(round_obj, round_obj.season_id, session, active_provider)
    finally:
        session.close()


@app.task(name="tasks.sync_matches.sync_all_rounds")
def sync_all_rounds():
    """Full sync of all rounds — use once at project start."""
    session = get_session()
    try:
        active_season = session.query(Season).filter_by(is_active=True).first()
        if not active_season:
            logger.warning("No active season found")
            return

        active_provider = provider.resolve_provider(session)
        rounds = session.query(Round).filter_by(season_id=active_season.id).all()
        for r in rounds:
            _sync_round_safe(r, active_season.id, session, active_provider)
    finally:
        session.close()


def _sync_round_safe(round_obj: Round, season_id: int, session, active_provider: str):
    """One round's failure shouldn't abort the rest of the batch."""
    try:
        _sync_round(round_obj, season_id, session, active_provider)
    except Exception as e:
        logger.exception("Failed to sync round %d", round_obj.number)
        log_error(session, "sync_matches", str(e), target=f"round:{round_obj.id}")


def _sync_round(round_obj: Round, season_id: int, session, active_provider: str):
    logger.info("Syncing round %d (season %d) via %s", round_obj.number, season_id, active_provider)
    teams, matches = provider.get_round_matches(
        TOURNAMENT_ID, season_id, round_obj.number, round_obj.id, active_provider
    )

    # Upsert teams first so matches' FKs resolve
    for team_data in teams:
        if not session.get(Team, team_data["id"]):
            session.add(Team(**team_data))
    session.flush()

    for match_data in matches:
        existing = session.get(Match, match_data["id"])
        if existing:
            for k, v in match_data.items():
                setattr(existing, k, v)
        else:
            session.add(Match(**match_data))

        # Update round status based on match statuses. A postponed match counts
        # toward "done" here so one reschedule doesn't block every later round
        # forever — sync_current_round separately keeps re-checking rounds that
        # still hold a postponed match, so a late replay still gets picked up.
        if match_data["status"] == "ongoing":
            round_obj.status = "ongoing"
        elif match_data["status"] == "scheduled" and round_obj.status == "finished":
            pass  # don't downgrade
        elif all(m["status"] in ("finished", "postponed") for m in matches):
            round_obj.status = "finished"

    # Squad-lock deadline = kickoff of the round's earliest known match —
    # recomputed every sync so a reschedule shifts it automatically.
    kickoffs = [m["started_at"] for m in matches if m.get("started_at")]
    if kickoffs:
        round_obj.deadline = min(kickoffs)

    session.commit()
    logger.info("Synced %d matches for round %d", len(matches), round_obj.number)
