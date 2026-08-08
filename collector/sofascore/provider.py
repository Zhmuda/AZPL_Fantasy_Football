"""Single entry point the Celery tasks use to fetch SofaScore data.

Dispatches to either the legacy hand-rolled client or datafc, based on the
SystemSetting singleton row in the DB (edited from the admin panel), so
switching providers takes effect on the next task run — no redeploy needed.
Both branches return the same normalized shapes; tasks never see which
provider actually ran.
"""
import logging

from models import SystemSetting
from sofascore import client, parsers, datafc_client, parsers_datafc

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "datafc"


def resolve_provider(session) -> str:
    setting = session.get(SystemSetting, 1)
    if not setting:
        setting = SystemSetting(id=1, sofascore_provider=DEFAULT_PROVIDER)
        session.add(setting)
        session.commit()
        return DEFAULT_PROVIDER
    return setting.sofascore_provider


def get_seasons(tournament_id: int, provider: str) -> list[dict]:
    if provider == "legacy":
        return client.get_seasons(tournament_id)
    return datafc_client.get_seasons(tournament_id)


def get_rounds(tournament_id: int, season_id: int, provider: str) -> list[dict]:
    if provider == "legacy":
        return client.get_rounds(tournament_id, season_id)
    return datafc_client.get_rounds(tournament_id, season_id)


def get_round_matches(
    tournament_id: int,
    season_id: int,
    round_number: int,
    round_id: int | None,
    provider: str,
) -> tuple[list[dict], list[dict]]:
    """Returns (teams, matches) already in the normalized dict shape parsers.py
    produces, ready for upsert — callers don't need to branch on provider."""
    if provider == "legacy":
        events = client.get_round_events(tournament_id, season_id, round_number)
        teams, matches = [], []
        for event in events:
            teams.append(parsers.parse_team(event["homeTeam"]))
            teams.append(parsers.parse_team(event["awayTeam"]))
            matches.append(parsers.parse_match(event, season_id, round_id))
        return teams, matches

    df = datafc_client.get_round_events(tournament_id, season_id, round_number)
    teams, matches = [], []
    for row in df.to_dict("records"):
        teams.append(parsers_datafc.parse_team_datafc(row["home_team_id"], row["home_team"]))
        teams.append(parsers_datafc.parse_team_datafc(row["away_team_id"], row["away_team"]))
        matches.append(parsers_datafc.parse_match_datafc(row, season_id, round_id))
    return teams, matches


def get_event_incidents(event_id: int, provider: str) -> list[dict]:
    if provider == "legacy":
        return client.get_event_incidents(event_id)
    return datafc_client.get_event_incidents(event_id)


def get_event_lineups(event_id: int, provider: str) -> dict:
    if provider == "legacy":
        return client.get_event_lineups(event_id)
    return datafc_client.get_event_lineups(event_id)


def get_team_squad(team_id: int, provider: str) -> list[dict]:
    """Returns parsed Player dicts ready for upsert — same normalized shape for
    both providers, since both return the same raw /team/{id}/players JSON."""
    if provider == "legacy":
        raw_players = client.get_team_players(team_id)
    else:
        raw_players = datafc_client.get_team_players(team_id)
    return [
        parsers.parse_player(entry["player"], team_id)
        for entry in raw_players
        if entry.get("player", {}).get("id")
    ]
