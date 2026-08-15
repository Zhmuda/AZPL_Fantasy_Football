"""Parse raw SofaScore API responses into clean dicts for DB insertion."""
from datetime import datetime, timezone

_FINISHED_DESCRIPTIONS = {"ended", "ended after extra time", "ended after penalties"}
_POSTPONED_DESCRIPTIONS = {
    "postponed", "cancelled", "canceled", "abandoned", "delayed", "walkover", "interrupted",
}


def classify_status(description: str, status_type: str = "") -> str:
    """Maps a SofaScore status (description text, optionally status.type) to our
    four match-status buckets: scheduled / ongoing / finished / postponed.

    Postponed/cancelled/abandoned matches get their own "postponed" bucket
    instead of collapsing into "scheduled" — otherwise a round containing one
    never reaches all-matches-finished, which permanently blocks round
    advancement in sync_matches and round-score calculation in calc_points.
    Shared by both providers since parsers_datafc.py's match_data rows and the
    legacy client's raw status object both carry a description string.
    """
    if status_type == "inprogress":
        return "ongoing"

    desc = (description or "").strip().lower()
    if desc in _FINISHED_DESCRIPTIONS or status_type == "finished":
        return "finished"
    if desc in _POSTPONED_DESCRIPTIONS:
        return "postponed"
    return "scheduled"


def parse_team(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw["name"],
        "short_name": raw.get("shortName", raw["name"])[:20],
        "logo_url": f"https://api.sofascore.com/api/v1/team/{raw['id']}/image",
    }


def parse_player(raw: dict, team_id: int | None = None) -> dict:
    pos_map = {"G": "G", "D": "D", "M": "M", "F": "F"}
    pos_raw = raw.get("position", "M")
    return {
        "id": raw["id"],
        "team_id": team_id,
        "name": raw["name"],
        "position": pos_map.get(pos_raw, "M"),
        "photo_url": f"https://api.sofascore.com/api/v1/player/{raw['id']}/image",
    }


def parse_match(raw: dict, season_id: int, round_id: int | None) -> dict:
    started_at = None
    if ts := raw.get("startTimestamp"):
        started_at = datetime.fromtimestamp(ts, tz=timezone.utc)

    status = raw.get("status", {})
    status_str = classify_status(status.get("description", ""), status.get("type", ""))

    return {
        "id": raw["id"],
        "season_id": season_id,
        "round_id": round_id,
        "home_team_id": raw["homeTeam"]["id"],
        "away_team_id": raw["awayTeam"]["id"],
        "home_score": raw.get("homeScore", {}).get("current"),
        "away_score": raw.get("awayScore", {}).get("current"),
        "status": status_str,
        "started_at": started_at,
    }


def parse_incidents(incidents: list[dict]) -> dict:
    """Returns {player_id: {event_type: count, ...}, ...} and list of raw events."""
    events = []
    for inc in incidents:
        inc_type = inc.get("incidentType")

        if inc_type == "goal":
            player = inc.get("player") or {}
            assist = inc.get("assist1") or {}
            is_own = inc.get("incidentClass") == "ownGoal"
            is_penalty_miss = inc.get("incidentClass") == "missedPenalty"

            if player.get("id"):
                events.append({
                    "player_id": player["id"],
                    "event_type": "own_goal" if is_own else ("penalty_miss" if is_penalty_miss else "goal"),
                    "minute": inc.get("time"),
                })
            if assist.get("id"):
                events.append({
                    "player_id": assist["id"],
                    "event_type": "assist",
                    "minute": inc.get("time"),
                })

        elif inc_type == "card":
            player = inc.get("player") or {}
            card_class = inc.get("incidentClass", "yellow")
            if player.get("id"):
                events.append({
                    "player_id": player["id"],
                    "event_type": "yellow_card" if card_class == "yellow" else "red_card",
                    "minute": inc.get("time"),
                })

        elif inc_type == "substitution":
            player_in = inc.get("playerIn") or {}
            player_out = inc.get("playerOut") or {}
            if player_in.get("id"):
                events.append({"player_id": player_in["id"], "event_type": "sub_in", "minute": inc.get("time")})
            if player_out.get("id"):
                events.append({"player_id": player_out["id"], "event_type": "sub_out", "minute": inc.get("time")})

    return events


def compute_minutes_played(lineups: dict, events: list[dict]) -> dict[int, int]:
    """SofaScore's per-player `statistics.minutesPlayed` is missing entirely
    for lower-tier competitions like AZPL (the lineup entries only carry
    player/team/position, no stats block) — derive minutes from the
    substitution and red-card incidents instead, which are always present."""
    MATCH_LENGTH = 90

    starters: set[int] = set()
    bench: set[int] = set()
    for side in ("home", "away"):
        for entry in lineups.get(side, {}).get("players", []):
            player_id = (entry.get("player") or {}).get("id")
            if not player_id:
                continue
            (bench if entry.get("substitute") else starters).add(player_id)

    sub_in: dict[int, int] = {}
    sub_out: dict[int, int] = {}
    red_card: dict[int, int] = {}
    for ev in events:
        minute = ev.get("minute") or 0
        if ev["event_type"] == "sub_in":
            sub_in[ev["player_id"]] = minute
        elif ev["event_type"] == "sub_out":
            sub_out[ev["player_id"]] = minute
        elif ev["event_type"] == "red_card":
            red_card[ev["player_id"]] = minute

    minutes: dict[int, int] = {}
    for player_id in starters:
        end = min(sub_out.get(player_id, MATCH_LENGTH), red_card.get(player_id, MATCH_LENGTH))
        minutes[player_id] = max(0, end)
    for player_id in bench:
        if player_id not in sub_in:
            continue  # never came on
        end = min(sub_out.get(player_id, MATCH_LENGTH), red_card.get(player_id, MATCH_LENGTH))
        minutes[player_id] = max(0, end - sub_in[player_id])

    return minutes


def parse_lineups(lineups: dict, match_id: int, home_team_id: int, away_team_id: int) -> tuple[list[dict], list[dict]]:
    """Returns (players_data, player_stats_data)."""
    players = []
    stats = []

    for side in ("home", "away"):
        side_data = lineups.get(side, {})
        team_id = home_team_id if side == "home" else away_team_id

        for entry in side_data.get("players", []):
            player_raw = entry.get("player", {})
            player_id = player_raw.get("id")
            if not player_id:
                continue

            players.append(parse_player(player_raw, team_id))

            raw_stats = entry.get("statistics", {})
            stats.append({
                "match_id": match_id,
                "player_id": player_id,
                "minutes_played": raw_stats.get("minutesPlayed", 0),
                "saves": raw_stats.get("saves", 0),
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "own_goals": 0,
                "penalty_miss": 0,
                "penalty_save": 0,
                "clean_sheet": False,
                "fantasy_points": 0,
            })

    return players, stats
