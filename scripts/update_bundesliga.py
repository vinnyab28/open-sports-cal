#!/usr/bin/env python3
"""Bundesliga 2025-26: full regeneration from fixturedownload.com."""
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("football/bundesliga/2025-26")
FEED_URL = "https://fixturedownload.com/feed/json/bundesliga-2025"
UID_PREFIX = "bundesliga-2025"
LEAGUE_NAME = "Bundesliga 2025-26"
CATEGORIES = "Football,Bundesliga,Bundesliga 2025-26"
TZ = "Europe/Berlin"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def fetch_fixtures():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    print("Bundesliga: fetching from fixturedownload.com...")
    fixtures = fetch_fixtures()
    print(f"  Got {len(fixtures)} fixtures")

    events = []
    team_events = defaultdict(list)

    for i, g in enumerate(fixtures):
        date_utc = g.get("DateUtc", "")
        if not date_utc:
            continue
        try:
            dt = datetime.strptime(date_utc, "%Y-%m-%d %H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        home, away = g.get("HomeTeam", ""), g.get("AwayTeam", "")
        if not home or not away:
            continue

        location = g.get("Location", "TBD")
        uid = f"{UID_PREFIX}-{i}@open-sports-cal"
        summary = f"{away} @ {home}"
        description = f"{LEAGUE_NAME}\\n{away} @ {home}\\n{location}"

        vevent = make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=2)),
                             location, description, CATEGORIES, TZ)
        events.append(vevent)
        team_events[slug(home)].append((vevent, home))
        team_events[slug(away)].append((vevent, away))

    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(events, f"{LEAGUE_NAME} - All Matches", LEAGUE_NAME),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(events)} events)")

    team_files = [f for f in OUT_DIR.glob("*.ics") if f.name != "all-teams.ics"]
    for team_file in sorted(team_files):
        ts = team_file.stem
        team_vevents = [ve for ve, _ in team_events.get(ts, [])]
        team_name = team_events[ts][0][1] if team_events.get(ts) else ts
        team_file.write_text(
            make_calendar(team_vevents, f"{LEAGUE_NAME} - {team_name}", LEAGUE_NAME),
            encoding="utf-8",
        )

    print("Bundesliga: done.")


if __name__ == "__main__":
    main()
