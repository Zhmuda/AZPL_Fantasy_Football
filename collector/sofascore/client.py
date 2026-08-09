"""SofaScore unofficial API client using curl_cffi for TLS fingerprint bypass."""
import time
import os
from curl_cffi import requests

BASE_URL = "https://api.sofascore.com/api/v1"
REQUEST_DELAY = float(os.getenv("SOFASCORE_REQUEST_DELAY", "2.0"))

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "x-requested-with": "XMLHttpRequest",
}


def _get(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    response = requests.get(url, headers=_HEADERS, impersonate="chrome120", timeout=15)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY)
    return response.json()


def get_seasons(tournament_id: int) -> list[dict]:
    data = _get(f"/unique-tournament/{tournament_id}/seasons")
    return data.get("seasons", [])


def get_rounds(tournament_id: int, season_id: int) -> list[dict]:
    data = _get(f"/unique-tournament/{tournament_id}/season/{season_id}/rounds")
    return data.get("rounds", [])


def get_round_events(tournament_id: int, season_id: int, round_number: int) -> list[dict]:
    data = _get(f"/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_number}")
    return data.get("events", [])


def get_event_incidents(event_id: int) -> list[dict]:
    data = _get(f"/event/{event_id}/incidents")
    return data.get("incidents", [])


def get_event_lineups(event_id: int) -> dict:
    return _get(f"/event/{event_id}/lineups")


def get_team_players(team_id: int) -> list[dict]:
    data = _get(f"/team/{team_id}/players")
    return data.get("players", [])


def get_standings(tournament_id: int, season_id: int) -> list[dict]:
    """Final/current league table — [{"team_id": int, "rank": int}, ...]."""
    data = _get(f"/unique-tournament/{tournament_id}/season/{season_id}/standings/total")
    rows = (data.get("standings") or [{}])[0].get("rows", [])
    return [{"team_id": r["team"]["id"], "rank": r["position"]} for r in rows]
