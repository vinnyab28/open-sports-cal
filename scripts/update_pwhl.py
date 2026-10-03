#!/usr/bin/env python3
"""
PWHL 2026-27: full regeneration from HockeyTech API.
The 2026-27 regular season is released in blocks: season_id=10
(November opening block) and season_id=11 (December onwards).
Playoffs arrive in season_id=12 once the league publishes them.
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

OUT_DIR = Path("hockey/pwhl/2026-27")
BASE_URL = ("https://lscluster.hockeytech.com/feed/"
            "?feed=modulekit&view=schedule&key=446521baf8c38984&client_code=pwhl&fmt=json")

TEAM_TZ = {
    "Boston Fleet": "America/New_York",
    "PWHL Detroit": "America/New_York",
    "PWHL Hamilton": "America/Toronto",
    "PWHL Las Vegas": "America/Los_Angeles",
    "PWHL San Jose": "America/Los_Angeles",
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

    reg_games = []
    for sid in (10, 11):
        games = parse_games(fetch_season(sid), f"regular season block {sid}")
        print(f"  Regular season block {sid}: {len(games)} games")
        reg_games.extend(games)

    playoff_games = parse_games(fetch_season(12), "playoffs")
    print(f"  Playoffs: {len(playoff_games)} games")

    all_games = reg_games + playoff_games
    seen_uids = set()
    events = []
    team_events = {}

    for g in all_games:
        dt = g["dt"]
        away_s, home_s = slug(g["away"]), slug(g["home"])
        uid = f"pwhl-2026-27-{g['game_date']}-{away_s}-vs-{home_s}@open-sports-cal"

        if uid in seen_uids:
            continue
        seen_uids.add(uid)

        summary = f"{g['away']} @ {g['home']}"
        description = f"PWHL 2026-27\\n{g['away']} @ {g['home']}\\n{g['venue']}"
        tz = TEAM_TZ.get(g["home"], "America/New_York")

        vevent = make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=3)),
                             g["venue"], description, "Hockey,PWHL,PWHL 2026-27", tz)
        events.append(vevent)
        for ts, name in ((away_s, g["away"]), (home_s, g["home"])):
            team_events.setdefault(ts, []).append((vevent, name))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(events, "PWHL 2026-27 - All Teams", "PWHL 2026-27"),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(events)} events)")

    teams = {ts: pairs[0][1] for ts, pairs in team_events.items()}
    for ts, team_name in sorted(teams.items()):
        team_file = OUT_DIR / f"{ts}.ics"
        cal_name = f"PWHL 2026-27 - {team_name}"
        if team_file.exists():
            existing = team_file.read_text(encoding="utf-8")
            cal_name_m = re.search(r"X-WR-CALNAME:(.+)", existing)
            if cal_name_m:
                cal_name = cal_name_m.group(1).strip()
        team_file.write_text(
            make_calendar([ve for ve, _ in team_events[ts]], cal_name, "PWHL 2026-27"),
            encoding="utf-8",
        )
    print(f"  Wrote {len(teams)} team files")
    print("PWHL: done.")


if __name__ == "__main__":
    main()
