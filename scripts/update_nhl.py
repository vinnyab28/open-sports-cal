#!/usr/bin/env python3
"""
NHL 2025-26: full regeneration from api-web.nhle.com.
Regular season UIDs are date+team based (stable across reruns).
Playoff UIDs include game number per series.
"""
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, write_calendar, DTSTAMP

OUT_DIR = Path("hockey/nhl/2025-26")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

TEAM_TZ = {
    "Anaheim Ducks": "America/Los_Angeles",
    "Boston Bruins": "America/New_York",
    "Buffalo Sabres": "America/New_York",
    "Calgary Flames": "America/Edmonton",
    "Carolina Hurricanes": "America/New_York",
    "Chicago Blackhawks": "America/Chicago",
    "Colorado Avalanche": "America/Denver",
    "Columbus Blue Jackets": "America/New_York",
    "Dallas Stars": "America/Chicago",
    "Detroit Red Wings": "America/New_York",
    "Edmonton Oilers": "America/Edmonton",
    "Florida Panthers": "America/New_York",
    "Los Angeles Kings": "America/Los_Angeles",
    "Minnesota Wild": "America/Chicago",
    "Montreal Canadiens": "America/Toronto",
    "Nashville Predators": "America/Chicago",
    "New Jersey Devils": "America/New_York",
    "New York Islanders": "America/New_York",
    "New York Rangers": "America/New_York",
    "Ottawa Senators": "America/Toronto",
    "Philadelphia Flyers": "America/New_York",
    "Pittsburgh Penguins": "America/New_York",
    "San Jose Sharks": "America/Los_Angeles",
    "Seattle Kraken": "America/Los_Angeles",
    "St. Louis Blues": "America/Chicago",
    "Tampa Bay Lightning": "America/New_York",
    "Toronto Maple Leafs": "America/Toronto",
    "Utah Hockey Club": "America/Denver",
    "Vancouver Canucks": "America/Vancouver",
    "Vegas Golden Knights": "America/Los_Angeles",
    "Washington Capitals": "America/New_York",
    "Winnipeg Jets": "America/Winnipeg",
}


def fetch_week(date_str):
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("gameWeek", [])
    except Exception as e:
        print(f"  Warning: failed to fetch {date_str}: {e}")
        return []


def fetch_all_games():
    games = {}  # uid -> game dict (dedup)
    start = datetime(2025, 10, 1)
    end = datetime(2026, 6, 30)
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        week = fetch_week(date_str)
        for day in week:
            local_date = day.get("date", "")
            for g in day.get("games", []):
                game_type = g.get("gameType", 0)
                if game_type not in (2, 3):
                    continue
                home = g.get("homeTeam", {})
                away = g.get("awayTeam", {})
                home_name = f"{home.get('placeName', {}).get('default', '')} {home.get('commonName', {}).get('default', '')}".strip()
                away_name = f"{away.get('placeName', {}).get('default', '')} {away.get('commonName', {}).get('default', '')}".strip()
                if not home_name or not away_name:
                    continue
                start_utc = g.get("startTimeUTC", "")
                venue = g.get("venue", {}).get("default", "TBD")
                games[g["id"]] = {
                    "id": g["id"],
                    "game_type": game_type,
                    "local_date": local_date,
                    "home": home_name,
                    "away": away_name,
                    "venue": venue,
                    "start_utc": start_utc,
                }
        current += timedelta(days=7)
    return list(games.values())


def build_events(games):
    reg_season = [g for g in games if g["game_type"] == 2]
    playoffs = [g for g in games if g["game_type"] == 3]

    reg_season.sort(key=lambda g: g["start_utc"])
    playoffs.sort(key=lambda g: g["start_utc"])

    vevents = []

    for g in reg_season:
        try:
            dt = datetime.fromisoformat(g["start_utc"].replace("Z", "+00:00"))
        except ValueError:
            continue
        away_s, home_s = slug(g["away"]), slug(g["home"])
        uid = f"nhl-2025-26-{g['local_date']}-{away_s}-vs-{home_s}@open-sports-cal"
        summary = f"{g['away']} @ {g['home']}"
        description = f"NHL 2025-26\\n{g['away']} @ {g['home']}\\n{g['venue']}"
        tz = TEAM_TZ.get(g["home"], "America/New_York")
        vevents.append({
            "vevent": make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=3)),
                                  g["venue"], description, "Hockey,NHL,NHL 2025-26", tz),
            "away_slug": away_s,
            "home_slug": home_s,
        })

    series_counts = defaultdict(int)
    for g in playoffs:
        try:
            dt = datetime.fromisoformat(g["start_utc"].replace("Z", "+00:00"))
        except ValueError:
            continue
        series_key = frozenset([g["away"], g["home"]])
        series_counts[series_key] += 1
        game_num = series_counts[series_key]
        away_s, home_s = slug(g["away"]), slug(g["home"])
        uid = f"nhl-2025-26-playoffs-{g['local_date']}-{away_s}-vs-{home_s}-g{game_num}@open-sports-cal"
        summary = f"{g['away']} @ {g['home']} (Game {game_num})"
        description = (f"NHL Playoffs 2025-26\\n"
                       f"{g['away']} @ {g['home']} — Game {game_num}\\n"
                       f"{g['venue']}")
        tz = TEAM_TZ.get(g["home"], "America/New_York")
        vevents.append({
            "vevent": make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=3)),
                                  g["venue"], description,
                                  "Hockey,NHL,NHL Playoffs 2025-26", tz),
            "away_slug": away_s,
            "home_slug": home_s,
        })

    return vevents


def main():
    print("NHL: fetching schedule from nhle.com...")
    games = fetch_all_games()
    print(f"  Fetched {len(games)} games ({sum(1 for g in games if g['game_type']==2)} reg, "
          f"{sum(1 for g in games if g['game_type']==3)} playoff)")

    events = build_events(games)
    print(f"  Built {len(events)} events")

    all_vevents = [e["vevent"] for e in events]
    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(all_vevents, "NHL 2025-26 - All Teams", "NHL 2025-26"),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(all_vevents)} events)")

    team_files = [f for f in OUT_DIR.glob("*.ics") if f.name != "all-teams.ics"]
    for team_file in sorted(team_files):
        ts = team_file.stem
        team_events = [e["vevent"] for e in events
                       if e["away_slug"] == ts or e["home_slug"] == ts]
        import re
        existing = team_file.read_text(encoding="utf-8")
        cal_name_m = re.search(r"X-WR-CALNAME:(.+)", existing)
        cal_name = cal_name_m.group(1).strip() if cal_name_m else f"NHL 2025-26 - {ts}"
        team_file.write_text(make_calendar(team_events, cal_name, "NHL 2025-26"),
                             encoding="utf-8")

    print("NHL: done.")


if __name__ == "__main__":
    main()
