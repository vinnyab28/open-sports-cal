#!/usr/bin/env python3
"""
NBA 2025-26: keeps regular season events unchanged, refreshes playoffs from ESPN.
Regular season uses sequential UIDs (nba-2025-N) that can't be safely regenerated.
"""
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, extract_vevents, get_uid, DTSTAMP

OUT_DIR = Path("basketball/nba/2025-26")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

TEAM_TZ = {
    "Atlanta Hawks": "America/New_York",
    "Boston Celtics": "America/New_York",
    "Brooklyn Nets": "America/New_York",
    "Charlotte Hornets": "America/New_York",
    "Chicago Bulls": "America/Chicago",
    "Cleveland Cavaliers": "America/New_York",
    "Dallas Mavericks": "America/Chicago",
    "Denver Nuggets": "America/Denver",
    "Detroit Pistons": "America/New_York",
    "Golden State Warriors": "America/Los_Angeles",
    "Houston Rockets": "America/Chicago",
    "Indiana Pacers": "America/Indiana/Indianapolis",
    "Los Angeles Clippers": "America/Los_Angeles",
    "Los Angeles Lakers": "America/Los_Angeles",
    "Memphis Grizzlies": "America/Chicago",
    "Miami Heat": "America/New_York",
    "Milwaukee Bucks": "America/Chicago",
    "Minnesota Timberwolves": "America/Chicago",
    "New Orleans Pelicans": "America/Chicago",
    "New York Knicks": "America/New_York",
    "Oklahoma City Thunder": "America/Chicago",
    "Orlando Magic": "America/New_York",
    "Philadelphia 76ers": "America/New_York",
    "Phoenix Suns": "America/Phoenix",
    "Portland Trail Blazers": "America/Los_Angeles",
    "Sacramento Kings": "America/Los_Angeles",
    "San Antonio Spurs": "America/Chicago",
    "Toronto Raptors": "America/Toronto",
    "Utah Jazz": "America/Denver",
    "Washington Wizards": "America/New_York",
}

ROUND_NAMES = {
    "RD16": "First Round",
    "QTR":  "Conference Semifinals",
    "SEMI": "Conference Finals",
    "FINAL": "NBA Finals",
}


def fetch_espn_playoffs():
    url = ("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
           "?dates=20260418-20260630&limit=300")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("events", [])


def is_playoff_event(vevent):
    return "nba-2025-playoffs-" in get_uid(vevent)


def build_playoff_events(espn_events):
    games = []
    for event in espn_events:
        comp = event.get("competitions", [{}])[0]
        status = event.get("status", {}).get("type", {}).get("name", "")
        if status in ("STATUS_CANCELLED", "STATUS_POSTPONED"):
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]
        if not home_name or not away_name or "TBD" in home_name or "TBD" in away_name:
            continue
        venue = comp.get("venue", {})
        location = venue.get("fullName", "TBD")
        tz = TEAM_TZ.get(home_name, "America/New_York")
        round_code = comp.get("type", {}).get("abbreviation", "")
        round_name = ROUND_NAMES.get(round_code, "NBA Playoffs")
        dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        games.append({
            "date": dt,
            "date_str": dt.strftime("%Y-%m-%d"),
            "home": home_name, "away": away_name,
            "location": location, "tz": tz, "round_name": round_name,
            "dtstart": fmt_utc(dt), "dtend": fmt_utc(dt + timedelta(hours=3)),
        })

    games.sort(key=lambda g: g["date"])
    series_counts = defaultdict(int)
    result = []
    for g in games:
        series_key = frozenset([g["away"], g["home"]])
        series_counts[series_key] += 1
        game_num = series_counts[series_key]
        away_s, home_s = slug(g["away"]), slug(g["home"])
        uid = f"nba-2025-playoffs-{g['date_str']}-{away_s}-vs-{home_s}-g{game_num}@open-sports-cal"
        summary = f"{g['away']} @ {g['home']} (Game {game_num})"
        description = (
            f"NBA Playoffs 2025-26 — {g['round_name']}\\n"
            f"{g['away']} @ {g['home']} — Game {game_num}\\n"
            f"{g['location']}"
        )
        g["uid"] = uid
        g["away_slug"] = away_s
        g["home_slug"] = home_s
        g["vevent"] = make_vevent(uid, summary, g["dtstart"], g["dtend"],
                                  g["location"], description,
                                  "Basketball,NBA,NBA Playoffs 2025-26", g["tz"])
        result.append(g)
    return result


def main():
    print("NBA: fetching playoff data from ESPN...")
    espn_events = fetch_espn_playoffs()
    print(f"  ESPN returned {len(espn_events)} events")

    playoff_games = build_playoff_events(espn_events)
    print(f"  Built {len(playoff_games)} playoff game events")

    all_teams_path = OUT_DIR / "all-teams.ics"
    existing = all_teams_path.read_text(encoding="utf-8")
    reg_season = [ve for ve in extract_vevents(existing) if not is_playoff_event(ve)]
    print(f"  Keeping {len(reg_season)} regular season events")

    all_vevents = reg_season + [g["vevent"] for g in playoff_games]
    all_teams_path.write_text(
        make_calendar(all_vevents, "NBA 2025-26 - All Matches", "NBA 2025-26"),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(all_vevents)} events)")

    team_files = [f for f in OUT_DIR.glob("*.ics") if f.name != "all-teams.ics"]
    updated = []
    for team_file in sorted(team_files):
        team_slug = team_file.stem
        existing_tf = team_file.read_text(encoding="utf-8")
        cal_name_m = re.search(r"X-WR-CALNAME:(.+)", existing_tf)
        cal_name = cal_name_m.group(1).strip() if cal_name_m else f"NBA 2025-26 - {team_slug}"
        reg = [ve for ve in extract_vevents(existing_tf) if not is_playoff_event(ve)]
        playoffs = [g["vevent"] for g in playoff_games
                    if g["away_slug"] == team_slug or g["home_slug"] == team_slug]
        if playoffs:
            updated.append(team_slug)
        team_file.write_text(make_calendar(reg + playoffs, cal_name, "NBA 2025-26"),
                             encoding="utf-8")

    print(f"  Updated {len(updated)} team files with new playoff data")
    print("NBA: done.")


if __name__ == "__main__":
    main()
