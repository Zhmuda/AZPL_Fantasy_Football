"""
Calculate and set player prices based on season statistics.

Formula (per position group, normalized 0–1):
  composite = pts_normalized * 0.50
            + contribution_normalized * 0.30   (goals*weight + assists*0.4)
            + availability * 0.20              (matches_played / 30)

Price ranges:
  GK  £4.5 – £6.0   (narrow: keepers are similarly priced)
  DEF £4.5 – £7.5
  MID £5.0 – £10.0
  FWD £5.5 – £12.0

Players with < MIN_MATCHES get the minimum price for their position.
All prices are rounded to the nearest £0.5m.
"""
import logging
from sqlalchemy import func
from celery_app import app
from db import get_session
from models import Player, PlayerMatchStat, Match, Season
from sync_log import log_error

logger = logging.getLogger(__name__)

PRICE_RANGES = {
    "G": (4.5, 6.0),
    "D": (4.5, 7.5),
    "M": (5.0, 10.0),
    "F": (5.5, 12.0),
}

# How much a goal contributes to "attack score" per position
GOAL_WEIGHT = {"G": 0.0, "D": 0.5, "M": 0.7, "F": 1.0}

MIN_MATCHES = 5  # below this → min price (unreliable/bench player)


def _round_half(v: float) -> float:
    return round(v * 2) / 2


@app.task(name="tasks.set_prices.set_player_prices")
def set_player_prices(season_id: int | None = None):
    session = get_session()
    try:
        if season_id is None:
            season = (
                session.query(Season).filter_by(is_active=True).first()
                or session.query(Season).order_by(Season.id.desc()).first()
            )
            if not season:
                logger.error("No season found")
                return
            season_id = season.id

        logger.info("Computing prices from season %d stats", season_id)

        # Aggregate season totals per player
        rows = (
            session.query(
                Player.id.label("player_id"),
                Player.position.label("pos"),
                func.coalesce(func.sum(PlayerMatchStat.fantasy_points), 0).label("total_pts"),
                func.coalesce(func.sum(PlayerMatchStat.goals), 0).label("total_goals"),
                func.coalesce(func.sum(PlayerMatchStat.assists), 0).label("total_assists"),
                func.count(PlayerMatchStat.id).label("matches"),
            )
            .join(PlayerMatchStat, Player.id == PlayerMatchStat.player_id)
            .join(Match, PlayerMatchStat.match_id == Match.id)
            .filter(Match.season_id == season_id, Player.is_active == True)
            .group_by(Player.id, Player.position)
            .all()
        )

        # Group by position
        by_pos: dict[str, list] = {}
        priced_player_ids: set[int] = set()
        for r in rows:
            by_pos.setdefault(r.pos, []).append(r)
            priced_player_ids.add(r.player_id)

        updated = 0
        for pos, group in by_pos.items():
            if pos not in PRICE_RANGES:
                continue

            gw = GOAL_WEIGHT[pos]
            min_p, max_p = PRICE_RANGES[pos]

            max_pts    = max(r.total_pts for r in group) or 1
            max_contrib = max(r.total_goals * gw + r.total_assists * 0.4 for r in group) or 1

            for r in group:
                player = session.get(Player, r.player_id)
                if not player:
                    continue

                if r.matches < MIN_MATCHES:
                    player.price = min_p
                else:
                    pts_norm  = r.total_pts / max_pts
                    contrib   = (r.total_goals * gw + r.total_assists * 0.4) / max_contrib
                    avail     = min(r.matches / 30.0, 1.0)
                    composite = pts_norm * 0.50 + contrib * 0.30 + avail * 0.20
                    raw       = min_p + composite * (max_p - min_p)
                    player.price = _round_half(max(min_p, min(max_p, raw)))

                updated += 1

        # The aggregation above only sees players with at least one PlayerMatchStat
        # row (inner join). Players with zero matches this season — e.g. squads
        # just synced ahead of round 1 — never appear in `rows`, so floor-price
        # them here instead of leaving them at the Player model's raw default.
        zero_stat_players = (
            session.query(Player)
            .filter(Player.is_active == True, ~Player.id.in_(priced_player_ids))
            .all()
        )
        for player in zero_stat_players:
            if player.position not in PRICE_RANGES:
                continue
            player.price = PRICE_RANGES[player.position][0]
            updated += 1

        session.commit()
        logger.info("Updated prices for %d players", updated)

    except Exception as e:
        logger.exception("set_player_prices failed")
        log_error(session, "set_prices.set_player_prices", str(e))
        raise
    finally:
        session.close()
