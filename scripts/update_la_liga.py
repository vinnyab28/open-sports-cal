#!/usr/bin/env python3
"""La Liga 2026-27: full regeneration from fixturedownload.com."""
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("football/la-liga/2026-27")
FEED_URL = "https://fixturedownload.com/feed/json/la-liga-2026"
UID_PREFIX = "la-liga-2026"
LEAGUE_NAME = "La Liga 2026-27"
CATEGORIES = "Football,La Liga,La Liga 2026-27"
LABEL = "La Liga"
TZ = "Europe/Madrid"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def fetch_fixtures():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    print(f"{LABEL}: fetching from fixturedownload.com...")
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "all-teams.ics").write_text(
        make_calendar(events, f"{LEAGUE_NAME} - All Matches", LEAGUE_NAME),
        encoding="utf-8",
    )
    print(f"  Wrote all-teams.ics ({len(events)} events)")

    teams = {ts: pairs[0][1] for ts, pairs in team_events.items()}
    for ts, team_name in sorted(teams.items()):
        team_path = OUT_DIR / f"{ts}.ics"
        cal_name = f"{LEAGUE_NAME} - {team_name}"
        if team_path.exists():
            m = re.search(r"X-WR-CALNAME:(.+)", team_path.read_text(encoding="utf-8"))
            if m:
                cal_name = m.group(1).strip()
        team_path.write_text(
            make_calendar([ve for ve, _ in team_events[ts]], cal_name, LEAGUE_NAME),
            encoding="utf-8",
        )
    print(f"  Wrote {len(teams)} team files")
    print(f"{LABEL}: done.")


if __name__ == "__main__":
    main()
