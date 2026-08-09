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

Below MIN_MATCHES, the merit formula above hasn't seen enough of the current
season to mean much, so it's blended with a price based on the player's
club's final rank in the *previous* season — weighted by matches played,
0 matches = pure last-season rank, MIN_MATCHES = pure merit formula. Without
this, everyone's price would collapse to the position floor the moment they
log their first match of the new season, then stay there for a month. See
_last_season_team_ranks / _rank_based_price.
All prices are rounded to the nearest £0.5m.
"""
import logging
import os
from sqlalchemy import func
from celery_app import app
from db import get_session
from models import Player, PlayerMatchStat, Match, Season
from sofascore import provider
from sync_log import log_error

logger = logging.getLogger(__name__)

TOURNAMENT_ID = int(os.getenv("SOFASCORE_TOURNAMENT_ID", "709"))

PRICE_RANGES = {
    "G": (4.5, 6.0),
    "D": (4.5, 7.5),
    "M": (5.0, 10.0),
    "F": (5.5, 12.0),
}

# How much a goal contributes to "attack score" per position
GOAL_WEIGHT = {"G": 0.0, "D": 0.5, "M": 0.7, "F": 1.0}

MIN_MATCHES = 5  # below this → min price (unreliable/bench player)

# How much of a position's price range the last-season-rank bonus can use —
# kept modest since it's a speculative pre-season signal, not this season's
# actual form. 0.0 = champion's players cost the same as last place's;
# 1.0 = champion's players would cost the position max outright.
PRESEASON_RANK_WEIGHT = 0.35


def _round_half(v: float) -> float:
    return round(v * 2) / 2


def _last_season_team_ranks(session, active_season_id: int) -> dict[int, int]:
    """team_id -> final league rank in the season immediately before
    active_season_id. Empty dict if there's no prior season on record or the
    standings fetch fails — callers fall back to flat floor pricing then."""
    prev_season = (
        session.query(Season)
        .filter(Season.id != active_season_id)
        .order_by(Season.id.desc())
        .first()
    )
    if not prev_season:
        return {}

    active_provider = provider.resolve_provider(session)
    try:
        standings = provider.get_standings(TOURNAMENT_ID, prev_season.id, active_provider)
    except Exception:
        logger.exception("Failed to fetch previous season standings for pre-season pricing")
        return {}
    return {row["team_id"]: row["rank"] for row in standings}


def _rank_based_price(position: str, team_id: int | None, team_ranks: dict[int, int], n_teams: int) -> float:
    """Unrounded — callers blend this with other signals before rounding."""
    min_p, max_p = PRICE_RANGES[position]
    rank = team_ranks.get(team_id) if team_id else None
    if not rank or n_teams <= 1:
        return min_p
    rank_factor = (n_teams - rank) / (n_teams - 1)  # 1.0 for champion, 0.0 for last place
    return min_p + rank_factor * (max_p - min_p) * PRESEASON_RANK_WEIGHT


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

        zero_stat_players = (
            session.query(Player)
            .filter(Player.is_active == True, ~Player.id.in_(priced_player_ids))
            .all()
        )

        # Last-season club rank backs the price for anyone without a big enough
        # current-season sample yet — fetch once, only if it's actually needed,
        # since it's a network call and most of the season won't need it at all.
        needs_ranks = bool(zero_stat_players) or any(r.matches < MIN_MATCHES for r in rows)
        team_ranks = _last_season_team_ranks(session, season_id) if needs_ranks else {}
        n_teams = len(team_ranks)

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

                pts_norm  = r.total_pts / max_pts
                contrib   = (r.total_goals * gw + r.total_assists * 0.4) / max_contrib
                avail     = min(r.matches / 30.0, 1.0)
                composite = pts_norm * 0.50 + contrib * 0.30 + avail * 0.20
                merit_raw = min_p + composite * (max_p - min_p)

                if r.matches < MIN_MATCHES:
                    # Blend last season's club-rank price with this season's
                    # early signal, weighted by how many matches it's based on —
                    # avoids everyone's price collapsing to the floor the moment
                    # they log their first match of the new season.
                    rank_raw = _rank_based_price(pos, player.team_id, team_ranks, n_teams)
                    weight   = r.matches / MIN_MATCHES
                    raw      = rank_raw * (1 - weight) + merit_raw * weight
                else:
                    raw = merit_raw

                player.price = _round_half(max(min_p, min(max_p, raw)))
                updated += 1

        # The aggregation above only sees players with at least one PlayerMatchStat
        # row (inner join). Players with zero matches this season — e.g. squads
        # just synced ahead of round 1 — never appear in `rows`, so price them
        # here instead of leaving them at the Player model's raw default.
        for player in zero_stat_players:
            if player.position not in PRICE_RANGES:
                continue
            raw = _rank_based_price(player.position, player.team_id, team_ranks, n_teams)
            player.price = _round_half(raw)
            updated += 1

        session.commit()
        logger.info("Updated prices for %d players", updated)

    except Exception as e:
        logger.exception("set_player_prices failed")
        log_error(session, "set_prices.set_player_prices", str(e))
        raise
    finally:
        session.close()
