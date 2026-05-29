#!/usr/bin/env python3
"""
PWHL 2025-26: full regeneration from HockeyTech API.
Fetches both regular season (season_id=8) and playoffs (season_id=9).
UIDs are date+team based (stable across reruns).
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("hockey/pwhl/2025-26")
BASE_URL = ("https://lscluster.hockeytech.com/feed/"
            "?feed=modulekit&view=schedule&key=446521baf8c38984&client_code=pwhl&fmt=json")

TEAM_TZ = {
    "Boston Fleet": "America/New_York",
    "Minnesota Frost": "America/Chicago",
    "Montréal Victoire": "America/Toronto",
    "New York Sirens": "America/New_York",
    "Ottawa Charge": "America/Toronto",
    "Seattle Torrent": "America/Los_Angeles",
    "Toronto Sceptres": "America/Toronto",
    "Vancouver Goldeneyes": "America/Vancouver",
}


def fetch_season(season_id):
    url = f"{BASE_URL}&season_id={season_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def parse_games(data, label):
    games = []
    try:
        raw_games = data["SiteKit"]["Schedule"]
        for g in raw_games:
            dt_str = g.get("date_time_played", "")
            game_date = g.get("date_played", "")
            home = g.get("home_team_name", "")
            away = g.get("visiting_team_name", "")
            if not home or not away or not dt_str:
                continue
            venue = g.get("venue_name", "TBD")
            venue_loc = g.get("venue_location", "")
            if venue_loc:
                venue = f"{venue}, {venue_loc}"
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            games.append({"game_date": game_date, "dt": dt, "home": home, "away": away, "venue": venue})
    except (KeyError, TypeError) as e:
        print(f"  Warning: parse error in {label}: {e}")
    return games


def main():
    print("PWHL: fetching schedule from HockeyTech...")

    reg_data = fetch_season(8)
    reg_games = parse_games(reg_data, "regular season")
    print(f"  Regular season: {len(reg_games)} games")

    playoff_data = fetch_season(9)
    playoff_games = parse_games(playoff_data, "playoffs")
    print(f"  Playoffs: {len(playoff_games)} games")

    all_games = reg_games + playoff_games
    seen_uids = set()
    events = []
    team_events = {}

    for g in all_games:
        dt = g["dt"]
        away_s, home_s = slug(g["away"]), slug(g["home"])
        uid = f"pwhl-2025-26-{g['game_date']}-{away_s}-vs-{home_s}@open-sports-cal"

        if uid in seen_uids:
            continue
        seen_uids.add(uid)

        summary = f"{g['away']} @ {g['home']}"
        description = f"PWHL 2025-26\\n{g['away']} @ {g['home']}\\n{g['venue']}"
        tz = TEAM_TZ.get(g["home"], "America/New_York")

        vevent = make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=3)),
                             g["venue"], description, "Hockey,PWHL,PWHL 2025-26", tz)
        events.append(vevent)
        for ts in (away_s, home_s):
            team_events.setdefault(ts, []).append(vevent)

    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(events, "PWHL 2025-26 - All Teams", "PWHL 2025-26"),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(events)} events)")

    team_files = [f for f in OUT_DIR.glob("*.ics") if f.name != "all-teams.ics"]
    for team_file in sorted(team_files):
        ts = team_file.stem
        existing = team_file.read_text(encoding="utf-8")
        cal_name_m = re.search(r"X-WR-CALNAME:(.+)", existing)
        cal_name = cal_name_m.group(1).strip() if cal_name_m else f"PWHL 2025-26 - {ts}"
        team_file.write_text(
            make_calendar(team_events.get(ts, []), cal_name, "PWHL 2025-26"),
            encoding="utf-8",
        )

    print("PWHL: done.")


if __name__ == "__main__":
    main()
