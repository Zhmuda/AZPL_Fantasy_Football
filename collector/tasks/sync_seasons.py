"""Sync seasons and rounds from SofaScore."""
import os
import logging
from celery_app import app
from db import get_session
from models import Season, Round
from sofascore import provider
from sync_log import log_error

logger = logging.getLogger(__name__)
TOURNAMENT_ID = int(os.getenv("SOFASCORE_TOURNAMENT_ID", "709"))


@app.task(name="tasks.sync_seasons.sync_seasons")
def sync_seasons():
    logger.info("Syncing seasons for tournament %d", TOURNAMENT_ID)
    session = get_session()
    try:
        active_provider = provider.resolve_provider(session)
        seasons = provider.get_seasons(TOURNAMENT_ID, active_provider)
        for s in seasons:
            existing = session.get(Season, s["id"])
            if not existing:
                session.add(Season(id=s["id"], name=s["name"], year=s.get("year", "")))
        session.commit()
        logger.info("Synced %d seasons", len(seasons))

        # Sync rounds for the active season
        active = session.query(Season).filter_by(is_active=True).first()
        if not active and seasons:
            active = session.get(Season, seasons[0]["id"])
            if active:
                active.is_active = True
                session.commit()

        if active:
            sync_rounds_for_season(active.id, session, active_provider)
    except Exception as e:
        logger.exception("sync_seasons failed")
        log_error(session, "sync_seasons.sync_seasons", str(e))
        raise
    finally:
        session.close()


def sync_rounds_for_season(season_id: int, session, active_provider: str):
    rounds = provider.get_rounds(TOURNAMENT_ID, season_id, active_provider)
    for r in rounds:
        existing = session.query(Round).filter_by(season_id=season_id, number=r["round"]).first()
        if not existing:
            session.add(Round(season_id=season_id, number=r["round"]))
    session.commit()
    logger.info("Synced %d rounds for season %d", len(rounds), season_id)
