#!/usr/bin/env python3
"""
FIFA World Cup 2026: full regeneration from ESPN.
Generates all-matches.ics, group-stage.ics, 12 group files, 48 team files.
Falls back silently if ESPN has no data yet (tournament starts June 11).
"""
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import slug, fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("football/world-cup/2026")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

TEAM_GROUP = {
    "Mexico": "A", "South Africa": "A", "South Korea": "A", "Czechia": "A",
    "Canada": "B", "Bosnia & Herzegovina": "B", "Qatar": "B", "Switzerland": "B",
    "Brazil": "C", "Morocco": "C", "Haiti": "C", "Scotland": "C",
    "USA": "D", "Paraguay": "D", "Australia": "D", "Turkey": "D",
    "Germany": "E", "Curacao": "E", "Ivory Coast": "E", "Ecuador": "E",
    "Netherlands": "F", "Japan": "F", "Sweden": "F", "Tunisia": "F",
    "Iran": "G", "New Zealand": "G", "Belgium": "G", "Egypt": "G",
    "Spain": "H", "Cape Verde": "H", "Saudi Arabia": "H", "Uruguay": "H",
    "France": "I", "Senegal": "I", "Iraq": "I", "Norway": "I",
    "Argentina": "J", "Algeria": "J", "Austria": "J", "Jordan": "J",
    "Portugal": "K", "DR Congo": "K", "Uzbekistan": "K", "Colombia": "K",
    "England": "L", "Croatia": "L", "Ghana": "L", "Panama": "L",
}

# ESPN display names that differ from TEAM_GROUP keys / existing file slugs
ESPN_NAME_MAP = {
    "United States": "USA",
    "Türkiye": "Turkey",
    "Bosnia-Herzegovina": "Bosnia & Herzegovina",
    "Congo DR": "DR Congo",
}

ROUND_NAMES = {
    "GROUP": "Group Stage",
    "R16": "Round of 16",
    "QF": "Quarter-finals",
    "SF": "Semi-finals",
    "FINAL": "Final",
    "3RD": "Third-place play-off",
}

# Host-city timezone by partial venue name
VENUE_TZ_LOOKUP = [
    ("Azteca",        "America/Mexico_City"),
    ("Akron",         "America/Mexico_City"),
    ("BBVA",          "America/Monterrey"),
    ("SoFi",          "America/Los_Angeles"),
    ("Levi",          "America/Los_Angeles"),
    ("Lumen",         "America/Los_Angeles"),
    ("AT&T",          "America/Chicago"),
    ("Mercedes-Benz", "America/New_York"),
    ("Arrowhead",     "America/Chicago"),
    ("MetLife",       "America/New_York"),
    ("Gillette",      "America/New_York"),
    ("Lincoln",       "America/New_York"),
    ("Hard Rock",     "America/New_York"),
    ("BMO",           "America/Toronto"),
    ("BC Place",      "America/Vancouver"),
    ("NRG",           "America/Chicago"),
]


def venue_tz(venue_name):
    for keyword, tz in VENUE_TZ_LOOKUP:
        if keyword.lower() in venue_name.lower():
            return tz
    return "America/New_York"


def fetch_matches():
    url = ("https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
           "?dates=20260611-20260719&limit=200")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("events", [])
    except Exception as e:
        print(f"  Warning: ESPN fetch failed: {e}")
        return []


def main():
    print("World Cup: fetching from ESPN...")
    events = fetch_matches()
    print(f"  ESPN returned {len(events)} events")

    if len(events) < 10:
        print("  Not enough data yet — skipping update (tournament may not have started)")
        return

    matches = []
    for event in events:
        comp = event.get("competitions", [{}])[0]
        status = event.get("status", {}).get("type", {}).get("name", "")
        if status in ("STATUS_CANCELLED", "STATUS_POSTPONED"):
            continue

        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        home_name = ESPN_NAME_MAP.get(home["team"]["displayName"], home["team"]["displayName"])
        away_name = ESPN_NAME_MAP.get(away["team"]["displayName"], away["team"]["displayName"])

        venue = comp.get("venue", {})
        location = venue.get("fullName", "TBD")
        city = venue.get("address", {}).get("city", "")
        if city:
            location = f"{location}, {city}"
        tz = venue_tz(venue.get("fullName", ""))

        round_code = comp.get("type", {}).get("abbreviation", "GROUP")
        round_name = ROUND_NAMES.get(round_code, round_code)

        dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))

        group = None
        if round_code == "GROUP":
            group = TEAM_GROUP.get(home_name) or TEAM_GROUP.get(away_name)

        matches.append({
            "dt": dt,
            "home": home_name, "away": away_name,
            "location": location, "tz": tz,
            "round_code": round_code, "round_name": round_name,
            "group": group,
        })

    matches.sort(key=lambda m: m["dt"])

    all_vevents = []
    group_vevents = defaultdict(list)
    team_vevents = defaultdict(list)

    for i, m in enumerate(matches, 1):
        uid = f"fwc2026-m{i:03d}@open-sports-cal"
        summary = f"{m['home']} vs {m['away']}"

        if m["group"]:
            desc_line = f"FIFA World Cup 2026 — Group {m['group']}"
        else:
            desc_line = f"FIFA World Cup 2026 — {m['round_name']}"

        description = f"{desc_line}\\n{summary}\\n{m['location']}"
        vevent = make_vevent(uid, summary, fmt_utc(m["dt"]), fmt_utc(m["dt"] + timedelta(hours=2)),
                             m["location"], description,
                             "Football,FIFA World Cup,FIFA World Cup 2026", m["tz"])

        all_vevents.append(vevent)

        if m["group"]:
            group_vevents[m["group"]].append(vevent)
            team_vevents[slug(m["home"])].append(vevent)
            team_vevents[slug(m["away"])].append(vevent)
        else:
            team_vevents[slug(m["home"])].append(vevent)
            team_vevents[slug(m["away"])].append(vevent)

    # all-matches.ics
    (OUT_DIR / "all-matches.ics").write_text(
        make_calendar(all_vevents, "FIFA World Cup 2026 - All Matches", "FIFA World Cup 2026"),
        encoding="utf-8",
    )

    # group-stage.ics
    group_stage = [ve for m, ve in zip(matches, all_vevents) if m["group"]]
    (OUT_DIR / "group-stage.ics").write_text(
        make_calendar(group_stage, "FIFA World Cup 2026 - Group Stage", "FIFA World Cup 2026"),
        encoding="utf-8",
    )

    # group-a.ics … group-l.ics
    for letter, vevents in group_vevents.items():
        fname = f"group-{letter.lower()}.ics"
        cal_name = f"FIFA World Cup 2026 - Group {letter}"
        (OUT_DIR / fname).write_text(
            make_calendar(vevents, cal_name, "FIFA World Cup 2026"),
            encoding="utf-8",
        )

    # per-team files
    team_files = [f for f in OUT_DIR.glob("*.ics")
                  if f.name not in ("all-matches.ics", "group-stage.ics")
                  and not f.name.startswith("group-")]
    for team_file in sorted(team_files):
        ts = team_file.stem
        import re
        existing = team_file.read_text(encoding="utf-8")
        cal_name_m = re.search(r"X-WR-CALNAME:(.+)", existing)
        cal_name = cal_name_m.group(1).strip() if cal_name_m else f"FIFA World Cup 2026 - {ts}"
        team_file.write_text(
            make_calendar(team_vevents.get(ts, []), cal_name, "FIFA World Cup 2026"),
            encoding="utf-8",
        )

    print(f"  Wrote all-matches.ics ({len(all_vevents)} events) + group files + team files")
    print("World Cup: done.")


if __name__ == "__main__":
    main()
