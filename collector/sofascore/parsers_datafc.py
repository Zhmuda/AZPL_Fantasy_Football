"""Adapt datafc's flat match_data rows to the same normalized dicts that
parsers.parse_team / parsers.parse_match produce from raw SofaScore JSON.

datafc's match_data DataFrame has no nested homeTeam/awayTeam objects and no
status.type — only a human-readable status description — so it can't be fed
into parsers.py directly. These functions bridge that gap; incidents/lineups
need no equivalent since datafc_client returns raw JSON for those.
"""
from datetime import datetime, timezone

from sofascore.parsers import classify_status


def parse_team_datafc(team_id: int, name: str) -> dict:
    return {
        "id": team_id,
        "name": name,
        # datafc's match_data doesn't carry shortName — falls back to the full
        # name, same as parsers.parse_team's own fallback. Fix up via TeamAdmin.
        "short_name": name[:20],
        "logo_url": f"https://api.sofascore.com/api/v1/team/{team_id}/image",
    }


def _is_nan(value) -> bool:
    return isinstance(value, float) and value != value


def _int_or_none(value) -> int | None:
    """pandas upcasts int columns with any missing value to float64, so unplayed
    matches come back as NaN rather than None — guard against both."""
    if value is None or _is_nan(value):
        return None
    return int(value)


def parse_match_datafc(row: dict, season_id: int, round_id: int | None) -> dict:
    ts = row.get("start_timestamp")
    started_at = None
    if ts is not None and not _is_nan(ts):
        started_at = datetime.fromtimestamp(ts, tz=timezone.utc)

    return {
        "id": row["game_id"],
        "season_id": season_id,
        "round_id": round_id,
        "home_team_id": row["home_team_id"],
        "away_team_id": row["away_team_id"],
        "home_score": _int_or_none(row.get("home_score_current")),
        "away_score": _int_or_none(row.get("away_score_current")),
        "status": classify_status(row.get("status", "")),
        "started_at": started_at,
    }
