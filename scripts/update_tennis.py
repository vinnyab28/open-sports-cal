#!/usr/bin/env python3
"""
Tennis Grand Slams 2026: full regeneration from ESPN.
UIDs are hardcoded (4 fixed tournaments), dates fetched from ESPN.
Events are all-day (no specific time).
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import make_calendar, DTSTAMP

OUT_DIR = Path("tennis/grand-slams/2026")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

SLAMS = [
    {
        "uid": "tennis-2026-australian-open",
        "name": "Australian Open 2026",
        "slug": "australian-open",
        "location": "Melbourne Park, Melbourne, Australia",
        "surface": "Hard",
        "search": "Australian Open",
    },
    {
        "uid": "tennis-2026-french-open",
        "name": "French Open 2026",
        "slug": "french-open",
        "location": "Roland-Garros, Paris, France",
        "surface": "Clay",
        "search": "Roland Garros",
    },
    {
        "uid": "tennis-2026-wimbledon",
        "name": "Wimbledon 2026",
        "slug": "wimbledon",
        "location": "All England Club, London, UK",
        "surface": "Grass",
        "search": "Wimbledon",
    },
    {
        "uid": "tennis-2026-us-open",
        "name": "US Open 2026",
        "slug": "us-open",
        "location": "USTA Billie Jean King National Tennis Center, New York, USA",
        "surface": "Hard",
        "search": "US Open",
    },
]

# Known 2026 Grand Slam date ranges (fallback if ESPN fails)
FALLBACK_DATES = {
    "australian-open": ("20260112", "20260203"),
    "french-open":     ("20260524", "20260609"),
    "wimbledon":       ("20260629", "20260714"),
    "us-open":         ("20260824", "20260914"),
}


def fetch_espn_tennis():
    url = ("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
           "?dates=20260101-20261231&limit=100")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("events", [])
    except Exception as e:
        print(f"  Warning: ESPN fetch failed: {e}")
        return []


def find_slam_dates(events, search_term):
    for event in events:
        name = event.get("name", "") or event.get("shortName", "")
        if search_term.lower() in name.lower():
            start_str = event.get("date", "")
            end_str = (event.get("endDate") or event.get("competitions", [{}])[0].get("endDate", ""))
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    start_date = start_dt.strftime("%Y%m%d")
                    if end_str:
                        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                        # DTEND is exclusive (day after last day)
                        end_date = (end_dt + timedelta(days=1)).strftime("%Y%m%d")
                    else:
                        end_date = None
                    return start_date, end_date
                except ValueError:
                    pass
    return None, None


def make_allday_vevent(uid, summary, dtstart, dtend, location, description):
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}@open-sports-cal",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"DTEND;VALUE=DATE:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        "CATEGORIES:Tennis,Grand Slam",
        "STATUS:CONFIRMED",
        f"DTSTAMP:{DTSTAMP}",
        "END:VEVENT",
    ]
    return "\r\n".join(lines)


def main():
    print("Tennis: fetching Grand Slam dates from ESPN...")
    espn_events = fetch_espn_tennis()
    print(f"  ESPN returned {len(espn_events)} events")

    all_vevents = []

    for slam in SLAMS:
        start_date, end_date = find_slam_dates(espn_events, slam["search"])

        if start_date and end_date:
            print(f"  {slam['name']}: {start_date} – {end_date} (from ESPN)")
        else:
            start_date, end_date = FALLBACK_DATES[slam["slug"]]
            print(f"  {slam['name']}: {start_date} – {end_date} (fallback)")

        description = (f"Tennis Grand Slam 2026\\n{slam['name']}\\n"
                       f"{slam['location']}\\nSurface: {slam['surface']}")
        vevent = make_allday_vevent(slam["uid"], slam["name"], start_date, end_date,
                                   slam["location"], description)
        all_vevents.append(vevent)

        (OUT_DIR / f"{slam['slug']}.ics").write_text(
            make_calendar([vevent], slam["name"], "Tennis Grand Slams 2026"),
            encoding="utf-8",
        )

    (OUT_DIR / "all-grand-slams.ics").write_text(
        make_calendar(all_vevents, "Tennis Grand Slams 2026", "Tennis Grand Slams 2026"),
        encoding="utf-8",
    )
    print(f"  Wrote all-grand-slams.ics + 4 individual files")
    print("Tennis: done.")


if __name__ == "__main__":
    main()
