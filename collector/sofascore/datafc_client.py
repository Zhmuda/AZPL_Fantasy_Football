"""SofaScore access via the `datafc` library — alternative to client.py.

Seasons/rounds/round-events use datafc's public API (datafc.sofascore.*).

Incidents/lineups go through datafc's HTTP transport (retries, shared rate
limit, optional disk cache) but hit the exact same endpoints as client.py and
return the exact same raw JSON shape, so parsers.py's parse_incidents /
parse_lineups work unchanged for either provider. That transport lives in
datafc.utils._client — a private module not covered by datafc's public
`__all__`, so the pinned version in requirements.txt matters: bump it
deliberately, don't let it float.
"""
import os

import pandas as pd
from datafc.sofascore import seasons_data, season_rounds_data, match_data
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS

REQUEST_DELAY = float(os.getenv("SOFASCORE_REQUEST_DELAY", "2.0"))


def _rate_limit() -> float:
    return 1.0 / REQUEST_DELAY if REQUEST_DELAY > 0 else 2.0


def get_seasons(tournament_id: int) -> list[dict]:
    df = seasons_data(tournament_id, rate_limit=_rate_limit())
    return [
        {"id": row.season_id, "name": row.season_name, "year": row.season_year}
        for row in df.itertuples()
    ]


def get_rounds(tournament_id: int, season_id: int) -> list[dict]:
    df = season_rounds_data(tournament_id, season_id, rate_limit=_rate_limit())
    return [{"round": row.round_number} for row in df.itertuples()]


def get_round_events(tournament_id: int, season_id: int, round_number: int) -> pd.DataFrame:
    """Returns the flat datafc match_data DataFrame — shape differs from the raw
    SofaScore JSON the legacy client returns. Adapted by parsers_datafc.py."""
    return match_data(tournament_id, season_id, week_number=round_number, rate_limit=_rate_limit())


def get_event_incidents(event_id: int) -> list[dict]:
    with SofascoreClient(rate_limit=_rate_limit()) as client:
        data = client.get(f"{API_URLS['sofascore']}/api/v1/event/{event_id}/incidents")
    return data.get("incidents", [])


def get_event_lineups(event_id: int) -> dict:
    with SofascoreClient(rate_limit=_rate_limit()) as client:
        return client.get(f"{API_URLS['sofascore']}/api/v1/event/{event_id}/lineups")


def get_team_players(team_id: int) -> list[dict]:
    with SofascoreClient(rate_limit=_rate_limit()) as client:
        data = client.get(f"{API_URLS['sofascore']}/api/v1/team/{team_id}/players")
    return data.get("players", [])
