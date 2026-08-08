"""Calculate fantasy points after match stats are synced."""
import logging
from celery_app import app
from db import get_session
from models import (
    PlayerMatchStat, Player, Match, Round,
    FantasyTeam, FantasyPick, FantasyRoundScore,
)
from sync_log import log_error

logger = logging.getLogger(__name__)

SCORING = {
    "minutes_1_59": 1,
    "minutes_60_plus": 2,
    "goal": {"G": 6, "D": 6, "M": 5, "F": 4},
    "assist": 3,
    "clean_sheet": {"G": 4, "D": 4, "M": 1, "F": 0},
    "saves_per_3": 1,
    "penalty_save": 5,
    "penalty_miss": -2,
    "yellow_card": -1,
    "red_card": -3,
    "own_goal": -2,
}


def _calc(stat: PlayerMatchStat, position: str) -> int:
    pts = 0
    if stat.minutes_played >= 60:
        pts += SCORING["minutes_60_plus"]
    elif stat.minutes_played > 0:
        pts += SCORING["minutes_1_59"]
    pts += stat.goals * SCORING["goal"][position]
    pts += stat.assists * SCORING["assist"]
    pts += (stat.saves // 3) * SCORING["saves_per_3"]
    pts += stat.penalty_save * SCORING["penalty_save"]
    pts += stat.penalty_miss * SCORING["penalty_miss"]
    pts += stat.yellow_cards * SCORING["yellow_card"]
    pts += stat.red_cards * SCORING["red_card"]
    pts += stat.own_goals * SCORING["own_goal"]
    if stat.clean_sheet and stat.minutes_played >= 60:
        pts += SCORING["clean_sheet"][position]
    return pts


def _get_round_stat(player_id: int, round_id: int, session) -> "PlayerMatchStat | None":
    return (
        session.query(PlayerMatchStat)
        .join(Match, PlayerMatchStat.match_id == Match.id)
        .filter(PlayerMatchStat.player_id == player_id, Match.round_id == round_id)
        .first()
    )


@app.task(name="tasks.calc_points.calc_match_points")
def calc_match_points(match_id: int):
    session = get_session()
    try:
        match = session.get(Match, match_id)
        if not match or not match.stats_synced:
            return

        stats = session.query(PlayerMatchStat).filter_by(match_id=match_id).all()
        for stat in stats:
            player = session.get(Player, stat.player_id)
            if not player:
                continue
            stat.fantasy_points = _calc(stat, player.position)

        session.commit()
        logger.info("Calculated points for %d players in match %d", len(stats), match_id)

        if match.round_id:
            _update_round_scores(match.round_id, session)
    except Exception as e:
        logger.exception("calc_match_points failed for match %d", match_id)
        log_error(session, "calc_points.calc_match_points", str(e), target=f"match:{match_id}")
        raise
    finally:
        session.close()


def _update_round_scores(round_id: int, session):
    # A postponed match never reaches status="finished", so it never gets
    # stats_synced — don't let it block round scoring forever. Its players
    # simply score 0 until/unless the match is replayed and re-triggers this.
    unsynced = (
        session.query(Match)
        .filter(Match.round_id == round_id, Match.stats_synced == False, Match.status != "postponed")
        .count()
    )
    if unsynced > 0:
        logger.info("Round %d: %d matches still pending", round_id, unsynced)
        return

    picks = session.query(FantasyPick).filter_by(round_id=round_id).all()

    team_picks: dict[int, list[FantasyPick]] = {}
    for pick in picks:
        team_picks.setdefault(pick.fantasy_team_id, []).append(pick)

    for team_id, team_pick_list in team_picks.items():
        starter_picks = [p for p in team_pick_list if p.slot <= 11]

        # Determine captain multiplier:
        # Captain × 2 if they played > 0 min.
        # If captain played 0 min, VC gets × 2 as replacement captain.
        captain_pick = next((p for p in starter_picks if p.is_captain), None)
        captain_played = False
        if captain_pick:
            cap_stat = _get_round_stat(captain_pick.player_id, round_id, session)
            captain_played = cap_stat is not None and cap_stat.minutes_played > 0

        total = 0
        for pick in starter_picks:
            stat = _get_round_stat(pick.player_id, round_id, session)
            if not stat:
                continue
            pts = stat.fantasy_points
            if pick.is_captain and captain_played:
                pts *= 2
            elif pick.is_vice_captain and not captain_played:
                pts *= 2  # VC acts as captain
            total += pts

        score = session.query(FantasyRoundScore).filter_by(
            fantasy_team_id=team_id, round_id=round_id
        ).first()
        if score:
            score.points = total
        else:
            session.add(FantasyRoundScore(fantasy_team_id=team_id, round_id=round_id, points=total))

        session.flush()

        team = session.get(FantasyTeam, team_id)
        if team:
            all_scores = session.query(FantasyRoundScore).filter_by(fantasy_team_id=team_id).all()
            team.total_points = sum(s.points for s in all_scores)

    session.commit()
    logger.info("Updated round scores for round %d", round_id)
