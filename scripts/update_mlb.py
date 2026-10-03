#!/usr/bin/env python3
"""
MLB 2027: full regeneration from statsapi.mlb.com.
UIDs are date+team based (stable across reruns).
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("baseball/mlb/2027")

TEAM_TZ = {
    "Arizona Diamondbacks": "America/Phoenix",
    "Atlanta Braves": "America/New_York",
    "Baltimore Orioles": "America/New_York",
    "Boston Red Sox": "America/New_York",
    "Chicago Cubs": "America/Chicago",
    "Chicago White Sox": "America/Chicago",
    "Cincinnati Reds": "America/New_York",
    "Cleveland Guardians": "America/New_York",
    "Colorado Rockies": "America/Denver",
    "Detroit Tigers": "America/New_York",
    "Houston Astros": "America/Chicago",
    "Kansas City Royals": "America/Chicago",
    "Los Angeles Angels": "America/Los_Angeles",
    "Los Angeles Dodgers": "America/Los_Angeles",
    "Miami Marlins": "America/New_York",
    "Milwaukee Brewers": "America/Chicago",
    "Minnesota Twins": "America/Chicago",
    "New York Mets": "America/New_York",
    "New York Yankees": "America/New_York",
    "Athletics": "America/Los_Angeles",
    "Philadelphia Phillies": "America/New_York",
    "Pittsburgh Pirates": "America/New_York",
    "San Diego Padres": "America/Los_Angeles",
    "San Francisco Giants": "America/Los_Angeles",
    "Seattle Mariners": "America/Los_Angeles",
    "St. Louis Cardinals": "America/Chicago",
    "Tampa Bay Rays": "America/New_York",
    "Texas Rangers": "America/Chicago",
    "Toronto Blue Jays": "America/Toronto",
    "Washington Nationals": "America/New_York",
}


def fetch_month(start, end):
    fields = "dates,date,games,gamePk,gameDate,status,startTimeTBD,teams,away,home,team,name,venue"
    url = (f"https://statsapi.mlb.com/api/v1/schedule"
           f"?sportId=1&season=2027&gameType=R"
           f"&startDate={start}&endDate={end}&fields={fields}")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    games = []
    for date_obj in data.get("dates", []):
        for g in date_obj.get("games", []):
            games.append({
                "date": date_obj["date"],
                "dt_str": g["gameDate"],
                "tbd": g.get("status", {}).get("startTimeTBD", False),
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"],
                "venue": g.get("venue", {}).get("name", "TBD"),
            })
    return games


def main():
    print("MLB: fetching 2027 schedule from statsapi.mlb.com...")
    months = [
        ("2027-03-20", "2027-03-31"),
        ("2027-04-01", "2027-04-30"),
        ("2027-05-01", "2027-05-31"),
        ("2027-06-01", "2027-06-30"),
        ("2027-07-01", "2027-07-31"),
        ("2027-08-01", "2027-08-31"),
        ("2027-09-01", "2027-09-30"),
        ("2027-10-01", "2027-10-05"),
    ]

    all_games = []
    for start, end in months:
        games = fetch_month(start, end)
        all_games.extend(games)
        print(f"  {start[:7]}: {len(games)} games")

    print(f"  Total: {len(all_games)} games")

    seen_uids = set()
    events = []
    team_events = {}

    for g in all_games:
        try:
            dt = datetime.fromisoformat(g["dt_str"].replace("Z", "+00:00"))
        except ValueError:
            continue
        away_s, home_s = slug(g["away"]), slug(g["home"])
        date_str = g["date"]
        base_uid = f"mlb-2027-{date_str}-{away_s}-vs-{home_s}"

        # Doubleheaders share date+teams — number the games so both are kept
        game_no = 1
        uid = f"{base_uid}@open-sports-cal"
        while uid in seen_uids:
            game_no += 1
            uid = f"{base_uid}-g{game_no}@open-sports-cal"
        seen_uids.add(uid)

        summary = f"{g['away']} @ {g['home']}"
        if game_no > 1:
            summary = f"{g['away']} @ {g['home']} (Game {game_no})"
        description = f"MLB 2027\\n{g['away']} @ {g['home']}\\n{g['venue']}"
        tz = TEAM_TZ.get(g["home"], "America/New_York")

        if g.get("tbd"):
            # Start time not announced yet — emit as an all-day event on
            # the scheduled date; the daily auto-update converts it to a
            # timed event once MLB publishes real start times.
            date_compact = date_str.replace("-", "")
            end_compact = (datetime.fromisoformat(date_str).date() + timedelta(days=1)).strftime("%Y%m%d")
            vevent = make_vevent(uid, summary, date_compact, end_compact,
                                 g["venue"], description + "\\nStart time TBD",
                                 "Baseball,MLB,MLB 2027", all_day=True)
        else:
            vevent = make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=3)),
                                 g["venue"], description, "Baseball,MLB,MLB 2027", tz)
        events.append(vevent)

        for ts in (away_s, home_s):
            team_events.setdefault(ts, []).append(vevent)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(events, "MLB 2027 - All Teams", "MLB 2027"),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(events)} events)")

    import re
    slug_to_name = {}
    for g in all_games:
        slug_to_name.setdefault(slug(g["home"]), g["home"])
        slug_to_name.setdefault(slug(g["away"]), g["away"])
    for ts, team_name in sorted(slug_to_name.items()):
        team_file = OUT_DIR / f"{ts}.ics"
        cal_name = f"MLB 2027 - {team_name}"
        if team_file.exists():
            existing = team_file.read_text(encoding="utf-8")
            cal_name_m = re.search(r"X-WR-CALNAME:(.+)", existing)
            if cal_name_m:
                cal_name = cal_name_m.group(1).strip()
        team_file.write_text(
            make_calendar(team_events.get(ts, []), cal_name, "MLB 2027"),
            encoding="utf-8",
        )

    print("MLB: done.")


if __name__ == "__main__":
    main()
