#!/usr/bin/env python3
"""
NBA 2026-27: full regeneration.
Regular season (80 games per team) comes from fixturedownload.com;
playoff games are refreshed from ESPN once the league releases the
playoff schedule. Games with unconfirmed teams (e.g. in-season
tournament placeholders) are skipped until participants are known.
Regular season UIDs are date+team based (stable across reruns).
"""
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("basketball/nba/2026-27")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

SEASON = "NBA 2026-27"
UID_PREFIX = "nba-2026-27"
CATEGORIES = "Basketball,NBA,NBA 2026-27"
PLAYOFF_CATEGORIES = "Basketball,NBA,NBA Playoffs 2026-27"
GAME_HOURS = 3
FEED_URL = "https://fixturedownload.com/feed/json/nba-2026"

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
    "LA Clippers": "America/Los_Angeles",
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


def fetch_fixtures():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_espn_playoffs():
    # ESPN's scoreboard endpoint no longer accepts date ranges — fetch
    # day-by-day. The playoff window doesn't open until April 2027, so
    # skip entirely before then to keep daily runs light.
    from time import sleep
    today = datetime.now(timezone.utc).date()
    season_end = datetime(2027, 4, 13).date()  # regular season ends April 12, 2027
    end = datetime(2027, 6, 30).date()
    if today <= season_end:
        print("  Regular season still running — skipping ESPN playoff fetch")
        return []
    start = max(today - timedelta(days=2), datetime(2027, 4, 13).date())
    events = {}
    d = start
    while d <= end:
        url = ("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
               f"?dates={d.strftime('%Y%m%d')}&limit=100")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                for e in json.loads(r.read()).get("events", []):
                    events[e["id"]] = e
        except Exception as e:
            print(f"  Warning: ESPN fetch failed for {d}: {e}")
        d += timedelta(days=1)
        sleep(0.1)
    return list(events.values())


def build_playoff_events(espn_events):
    games = []
    for event in espn_events:
        # Only post-season events (type 3) — the scoreboard window can
        # also contain regular season finales around mid-April.
        if event.get("season", {}).get("type") not in (3, "3"):
            continue
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
            "date_str": dt.astimezone(ZoneInfo(tz)).date().strftime("%Y-%m-%d"),
            "home": home_name, "away": away_name,
            "location": location, "tz": tz, "round_name": round_name,
        })

    games.sort(key=lambda g: g["date"])
    series_counts = defaultdict(int)
    result = []
    for g in games:
        series_key = frozenset([g["away"], g["home"]])
        series_counts[series_key] += 1
        game_num = series_counts[series_key]
        away_s, home_s = slug(g["away"]), slug(g["home"])
        uid = f"{UID_PREFIX}-playoffs-{g['date_str']}-{away_s}-vs-{home_s}-g{game_num}@open-sports-cal"
        summary = f"{g['away']} @ {g['home']} (Game {game_num})"
        description = (
            f"NBA Playoffs 2026-27 — {g['round_name']}\\n"
            f"{g['away']} @ {g['home']} — Game {game_num}\\n"
            f"{g['location']}"
        )
        g["away_slug"] = away_s
        g["home_slug"] = home_s
        g["vevent"] = make_vevent(uid, summary,
                                 fmt_utc(g["date"]), fmt_utc(g["date"] + timedelta(hours=GAME_HOURS)),
                                 g["location"], description, PLAYOFF_CATEGORIES, g["tz"])
        result.append(g)
    return result


def main():
    print("NBA: fetching regular season from fixturedownload.com...")
    fixtures = fetch_fixtures()
    print(f"  Got {len(fixtures)} fixtures")

    events = []
    team_events = defaultdict(list)
    skipped = 0

    for g in fixtures:
        date_utc = g.get("DateUtc", "")
        home, away = g.get("HomeTeam", ""), g.get("AwayTeam", "")
        if not date_utc or not home or not away:
            continue
        if "announced" in home.lower() or "announced" in away.lower() or "tbd" in home.lower() or "tbd" in away.lower():
            skipped += 1
            continue
        try:
            dt = datetime.strptime(date_utc, "%Y-%m-%d %H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        location = g.get("Location", "TBD")
        tz = TEAM_TZ.get(home, "America/New_York")
        local_date = dt.astimezone(ZoneInfo(tz)).date().strftime("%Y-%m-%d")
        away_s, home_s = slug(away), slug(home)
        uid = f"{UID_PREFIX}-{local_date}-{away_s}-vs-{home_s}@open-sports-cal"
        summary = f"{away} @ {home}"
        description = f"{SEASON}\\n{away} @ {home}\\n{location}"

        vevent = make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=GAME_HOURS)),
                             location, description, CATEGORIES, tz)
        events.append(vevent)
        team_events[home_s].append((vevent, home))
        team_events[away_s].append((vevent, away))
    print(f"  Built {len(events)} regular season events (skipped {skipped} unconfirmed-team games)")

    print("NBA: checking ESPN for playoff schedule...")
    playoff_games = build_playoff_events(fetch_espn_playoffs())
    print(f"  Built {len(playoff_games)} playoff game events")
    for g in playoff_games:
        events.append(g["vevent"])
        team_events[g["home_slug"]].append((g["vevent"], g["home"]))
        team_events[g["away_slug"]].append((g["vevent"], g["away"]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_events = sorted(events, key=lambda v: re.search(r"^DTSTART[^:]*:(.+)$", v, re.M).group(1))
    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(all_events, "NBA 2026-27 - All Matches", SEASON),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(all_events)} events)")

    teams = {ts: pairs[0][1] for ts, pairs in team_events.items()}
    for ts, team_name in sorted(teams.items()):
        team_path = OUT_DIR / f"{ts}.ics"
        cal_name = f"{SEASON} - {team_name}"
        if team_path.exists():
            m = re.search(r"X-WR-CALNAME:(.+)", team_path.read_text(encoding="utf-8"))
            if m:
                cal_name = m.group(1).strip()
        team_path.write_text(
            make_calendar([ve for ve, _ in team_events[ts]], cal_name, SEASON),
            encoding="utf-8",
        )
    print(f"  Wrote {len(teams)} team files")
    print("NBA: done.")


if __name__ == "__main__":
    main()
