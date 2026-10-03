#!/usr/bin/env python3
"""
NFL 2026: full regeneration from ESPN's public team-schedule API.
Regular season only — playoffs are added once officially released
(season type 3), same as the NBA script does.

Games whose kickoff time has not been announced yet (flex games in
weeks 16-18) are emitted as all-day events with a "Kickoff time TBD"
note. The daily auto-update converts them to timed events as soon as
ESPN publishes real kickoff times. If a flex game moves to a different
day when announced, its date-based UID changes and the placeholder
event is replaced.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("american-football/nfl/2026")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

SEASON = "NFL 2026"
LEAGUE_KEY = "nfl-2026"
CATEGORIES = "American Football,NFL,NFL 2026"
GAME_HOURS = 3

# ESPN per-team schedule endpoint; every game appears in both teams'
# schedules, so events are deduped by id.
TEAM_ABBRS = [
    "ari", "atl", "bal", "buf", "car", "chi", "cin", "cle", "dal", "den",
    "det", "gb", "hou", "ind", "jax", "kc", "lv", "lac", "lar", "mia",
    "min", "ne", "no", "nyg", "nyj", "phi", "pit", "sf", "sea", "tb",
    "ten", "wsh",
]

# Venue → IANA timezone. International games resolve through this map
# the same way home stadiums do (e.g. Melbourne Cricket Ground).
VENUE_TZ = {
    "Acrisure Stadium": "America/New_York",
    "Allegiant Stadium": "America/Los_Angeles",
    "Arrowhead Stadium": "America/Chicago",
    "AT&T Stadium": "America/Chicago",
    "Bank of America Stadium": "America/New_York",
    "Caesars Superdome": "America/Chicago",
    "Empower Field at Mile High": "America/Denver",
    "Estadio Banorte": "America/Mexico_City",
    "EverBank Stadium": "America/New_York",
    "FC Bayern Munich Stadium": "Europe/Berlin",
    "Ford Field": "America/New_York",
    "Gillette Stadium": "America/New_York",
    "Hard Rock Stadium": "America/New_York",
    "Highmark Stadium": "America/New_York",
    "Huntington Bank Field": "America/New_York",
    "Lambeau Field": "America/Chicago",
    "Levi's Stadium": "America/Los_Angeles",
    "Lincoln Financial Field": "America/New_York",
    "Lucas Oil Stadium": "America/New_York",
    "Lumen Field": "America/Los_Angeles",
    "M&T Bank Stadium": "America/New_York",
    "Maracanã Stadium": "America/Sao_Paulo",
    "Melbourne Cricket Ground": "Australia/Melbourne",
    "Mercedes-Benz Stadium": "America/New_York",
    "MetLife Stadium": "America/New_York",
    "Nissan Stadium": "America/Chicago",
    "Northwest Stadium": "America/New_York",
    "Paycor Stadium": "America/New_York",
    "Raymond James Stadium": "America/New_York",
    "Reliant Stadium": "America/Chicago",
    "Santiago Bernabéu": "Europe/Madrid",
    "SoFi Stadium": "America/Los_Angeles",
    "Soldier Field": "America/Chicago",
    "Stade de France": "Europe/Paris",
    "State Farm Stadium": "America/Phoenix",
    "Tottenham Hotspur Stadium": "Europe/London",
    "U.S. Bank Stadium": "America/Chicago",
    "Wembley Stadium": "Europe/London",
}

DEFAULT_TZ = "America/New_York"


def fetch_team_schedule(abbr):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{abbr}/schedule?season=2026"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("events", [])
    except Exception as e:
        print(f"  Warning: failed to fetch {abbr} schedule: {e}")
        return []


def fetch_all_games():
    events = {}
    for abbr in TEAM_ABBRS:
        for e in fetch_team_schedule(abbr):
            events[e["id"]] = e
    games = []
    for e in events.values():
        comp = e.get("competitions", [{}])[0]
        if e.get("seasonType", {}).get("type") != 2:  # regular season only
            continue
        home = away = None
        for c in comp.get("competitors", []):
            if c.get("homeAway") == "home":
                home = c.get("team", {}).get("displayName", "")
            elif c.get("homeAway") == "away":
                away = c.get("team", {}).get("displayName", "")
        if not home or not away:
            continue
        venue = comp.get("venue", {}).get("fullName", "TBD")
        games.append({
            "date": e.get("date", ""),
            "week": e.get("week", {}).get("number", 0),
            "home": home,
            "away": away,
            "venue": venue,
        })
    games.sort(key=lambda g: g["date"])
    return games


def parse_utc(date_str):
    s = date_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:  # e.g. "2026-09-10T00:20+00:00" missing seconds
        return datetime.fromisoformat(s + ":00")


def build_events(games):
    vevents = []
    unknown_venues = set()
    for g in games:
        away_s, home_s = slug(g["away"]), slug(g["home"])
        tz = VENUE_TZ.get(g["venue"])
        if tz is None:
            unknown_venues.add(g["venue"])
            tz = DEFAULT_TZ
        try:
            dt = parse_utc(g["date"])
        except ValueError:
            continue

        if g["date"].endswith("T05:00Z"):
            # Kickoff not announced yet (ESPN placeholder time for flex
            # games) — emit as an all-day event on the scheduled date.
            # The placeholder is midnight ET, so the UTC date is the
            # scheduled day; venue-local conversion would shift it.
            local_date = dt.date()
            uid = f"{LEAGUE_KEY}-{local_date}-{away_s}-vs-{home_s}@open-sports-cal"
            dtstart = local_date.strftime("%Y%m%d")
            dtend = (local_date + timedelta(days=1)).strftime("%Y%m%d")
            summary = f"{g['away']} @ {g['home']}"
            description = (
                f"{SEASON} — Week {g['week']}\\n"
                f"{g['away']} @ {g['home']}\\n"
                f"{g['venue']}\\n"
                f"Kickoff time TBD"
            )
            vevent = make_vevent(uid, summary, dtstart, dtend, g["venue"],
                                 description, CATEGORIES,
                                 all_day=True)
        else:
            local_date = dt.astimezone(ZoneInfo(tz)).date()
            uid = f"{LEAGUE_KEY}-{local_date}-{away_s}-vs-{home_s}@open-sports-cal"
            summary = f"{g['away']} @ {g['home']}"
            description = (
                f"{SEASON} — Week {g['week']}\\n"
                f"{g['away']} @ {g['home']}\\n"
                f"{g['venue']}"
            )
            vevent = make_vevent(uid, summary, fmt_utc(dt),
                                 fmt_utc(dt + timedelta(hours=GAME_HOURS)),
                                 g["venue"], description, CATEGORIES, tz)
        vevents.append({"vevent": vevent, "away_slug": away_s, "home_slug": home_s})

    if unknown_venues:
        print(f"  Warning: unknown venues (using {DEFAULT_TZ}): {sorted(unknown_venues)}")
    return vevents


def main():
    print("NFL: fetching schedule from ESPN...")
    games = fetch_all_games()
    print(f"  Fetched {len(games)} regular season games")

    events = build_events(games)
    print(f"  Built {len(events)} events")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_vevents = [e["vevent"] for e in events]
    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(all_vevents, "NFL 2026 - All Teams", SEASON),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(all_vevents)} events)")

    team_names = {}
    for g in games:
        team_names[g["home"]] = True
        team_names[g["away"]] = True

    for team in sorted(team_names):
        ts = slug(team)
        team_events = [e["vevent"] for e in events
                        if e["away_slug"] == ts or e["home_slug"] == ts]
        team_path = OUT_DIR / f"{ts}.ics"
        cal_name = f"NFL 2026 - {team}"
        if team_path.exists():
            existing = team_path.read_text(encoding="utf-8")
            m = re.search(r"X-WR-CALNAME:(.+)", existing)
            if m:
                cal_name = m.group(1).strip()
        team_path.write_text(make_calendar(team_events, cal_name, SEASON),
                             encoding="utf-8")
    print(f"  Wrote {len(team_names)} team files")
    print("NFL: done.")


if __name__ == "__main__":
    main()
