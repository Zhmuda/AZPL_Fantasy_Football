"""
Test script: SofaScore API for Azerbaijan Premier League
Checks: seasons, rounds, match incidents (goals/cards/subs), player stats
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from curl_cffi import requests
import json
import time

BASE = "https://api.sofascore.com/api/v1"
TOURNAMENT_ID = 709  # Misli Premier League (Azerbaijan)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=10, impersonate="chrome120")
    print(f"  [{r.status_code}] {url}")
    if r.status_code == 200:
        return r.json()
    return None


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── 1. Seasons ────────────────────────────────────────────────
section("1. Seasons for AZPL (tournament 709)")
data = get(f"{BASE}/unique-tournament/{TOURNAMENT_ID}/seasons")
if data:
    seasons = data.get("seasons", [])
    print(f"  Found {len(seasons)} seasons:")
    for s in seasons[:5]:
        print(f"    id={s['id']}  name={s['name']}  year={s.get('year','')}")
    current_season = seasons[0] if seasons else None
else:
    print("  FAILED — cannot continue without season")
    exit(1)

SEASON_ID = current_season["id"]
print(f"\n  >> Using season: id={SEASON_ID} name={current_season['name']}")
time.sleep(1)

# ── 2. Rounds ─────────────────────────────────────────────────
section("2. Rounds in current season")
data = get(f"{BASE}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/rounds")
if data:
    rounds = data.get("rounds", [])
    print(f"  Found {len(rounds)} rounds: {[r.get('round') for r in rounds[:10]]}...")
    last_round = max(r.get("round", 0) for r in rounds) if rounds else 1
    print(f"  >> Using last round: {last_round}")
else:
    last_round = 5
    print(f"  FAILED — falling back to round {last_round}")
time.sleep(1)

# ── 3. Events (matches) in a round ────────────────────────────
section(f"3. Matches in round {last_round}")
data = get(f"{BASE}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{last_round}")
if data:
    events = data.get("events", [])
    print(f"  Found {len(events)} matches:")
    for e in events:
        home = e["homeTeam"]["name"]
        away = e["awayTeam"]["name"]
        status = e["status"]["description"]
        score_home = e.get("homeScore", {}).get("current", "?")
        score_away = e.get("awayScore", {}).get("current", "?")
        print(f"    [{e['id']}] {home} {score_home}:{score_away} {away}  — {status}")
    finished = [e for e in events if e["status"]["type"] == "finished"]
    test_event = finished[0] if finished else (events[0] if events else None)
else:
    test_event = None
    print("  FAILED")
time.sleep(1)

if not test_event:
    print("\n  No match found to test details — trying to find any finished match...")
    for rnd in range(last_round, 0, -1):
        d = get(f"{BASE}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{rnd}")
        time.sleep(0.5)
        if d:
            finished = [e for e in d.get("events", []) if e["status"]["type"] == "finished"]
            if finished:
                test_event = finished[0]
                break

if not test_event:
    print("\n  Cannot find a finished match. Stopping.")
    exit(1)

EVENT_ID = test_event["id"]
home = test_event["homeTeam"]["name"]
away = test_event["awayTeam"]["name"]
print(f"\n  >> Testing with match: [{EVENT_ID}] {home} vs {away}")
time.sleep(1)

# ── 4. Match incidents (goals, cards, subs) ───────────────────
section(f"4. Incidents for match {EVENT_ID}")
data = get(f"{BASE}/event/{EVENT_ID}/incidents")
if data:
    incidents = data.get("incidents", [])
    print(f"  Total incidents: {len(incidents)}")
    by_type = {}
    for inc in incidents:
        t = inc.get("incidentType", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    print(f"  By type: {by_type}")

    print("\n  Sample incidents:")
    for inc in incidents[:8]:
        t = inc.get("incidentType")
        if t == "goal":
            player = inc.get("player", {}).get("name", "?")
            assist = inc.get("assist1", {}).get("name", "") if inc.get("assist1") else ""
            minute = inc.get("time", "?")
            print(f"    GOAL  {minute}'  {player}  (assist: {assist})")
        elif t == "card":
            player = inc.get("player", {}).get("name", "?")
            card_type = inc.get("incidentClass", "?")
            minute = inc.get("time", "?")
            print(f"    CARD  {minute}'  {player}  [{card_type}]")
        elif t == "substitution":
            player_in = inc.get("playerIn", {}).get("name", "?")
            player_out = inc.get("playerOut", {}).get("name", "?")
            minute = inc.get("time", "?")
            print(f"    SUB   {minute}'  IN:{player_in}  OUT:{player_out}")
        else:
            print(f"    {t}: {json.dumps(inc)[:80]}")
else:
    print("  FAILED")
time.sleep(1)

# ── 5. Match statistics (possession, shots, etc.) ─────────────
section(f"5. Match statistics for {EVENT_ID}")
data = get(f"{BASE}/event/{EVENT_ID}/statistics")
if data:
    stats = data.get("statistics", [])
    if stats:
        period = stats[0]
        print(f"  Period: {period.get('period')}")
        groups = period.get("groups", [])
        for group in groups[:2]:
            print(f"  Group: {group.get('groupName')}")
            for item in group.get("statisticsItems", []):
                print(f"    {item['name']}: {item.get('home')} / {item.get('away')}")
else:
    print("  FAILED")
time.sleep(1)

# ── 6. Lineups ────────────────────────────────────────────────
section(f"6. Lineups for match {EVENT_ID}")
data = get(f"{BASE}/event/{EVENT_ID}/lineups")
if data:
    home_players = data.get("home", {}).get("players", [])
    away_players = data.get("away", {}).get("players", [])
    print(f"  Home lineup: {len(home_players)} players")
    print(f"  Away lineup: {len(away_players)} players")
    if home_players:
        print("  Home players (first 5):")
        for p in home_players[:5]:
            player = p.get("player", {})
            pos = p.get("position", "?")
            rating = p.get("statistics", {}).get("rating", "—")
            print(f"    #{p.get('jerseyNumber','?')} {player.get('name','?')}  pos={pos}  rating={rating}")
else:
    print("  FAILED")
time.sleep(1)

# ── 7. Player statistics in match ─────────────────────────────
section(f"7. Player stats in match (first home player)")
if data and home_players:
    p = home_players[0]
    player_id = p.get("player", {}).get("id")
    player_name = p.get("player", {}).get("name")
    print(f"  Player: {player_name} (id={player_id})")
    stats = p.get("statistics", {})
    if stats:
        print(f"  Statistics: {json.dumps(stats, indent=4)}")
    else:
        print("  No stats in lineup data")

    # Try separate rating breakdown endpoint
    time.sleep(1)
    d = get(f"{BASE}/event/{EVENT_ID}/player/{player_id}/rating-breakdown")
    if d:
        print(f"  Rating breakdown: {json.dumps(d, indent=2)[:500]}")
else:
    print("  Skipped (no lineup data)")

# ── Summary ───────────────────────────────────────────────────
section("SUMMARY")
print("""
What we checked:
  [1] Seasons          — list of AZPL seasons
  [2] Rounds           — rounds in current season
  [3] Match list       — matches per round with scores
  [4] Incidents        — goals (scorer + assist), cards, substitutions
  [5] Match stats      — possession, shots, etc.
  [6] Lineups          — starting XI + bench with jersey numbers
  [7] Player stats     — per-match rating and detailed stats

For Fantasy Football scoring we need:
  goals, assists, cards, minutes_played, clean_sheet, saves (GK)
  -> All available via incidents + lineups endpoints
""")
