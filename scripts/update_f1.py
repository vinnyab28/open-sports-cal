#!/usr/bin/env python3
"""F1 2026: full regeneration from Jolpica (Ergast successor) API."""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fmt_utc, make_vevent, make_calendar, DTSTAMP

OUT_DIR = Path("motorsport/formula-1/2026")

# IANA timezone by race venue locality (from Jolpica Circuit.Location.locality)
LOCALITY_TZ = {
    "Melbourne": "Australia/Melbourne",
    "Shanghai": "Asia/Shanghai",
    "Sakhir": "Asia/Bahrain",
    "Jeddah": "Asia/Riyadh",
    "Miami": "America/New_York",
    "Monte-Carlo": "Europe/Monaco",
    "Barcelona": "Europe/Madrid",
    "Montreal": "America/Toronto",
    "Spielberg": "Europe/Vienna",
    "Silverstone": "Europe/London",
    "Budapest": "Europe/Budapest",
    "Spa": "Europe/Brussels",
    "Zandvoort": "Europe/Amsterdam",
    "Monza": "Europe/Rome",
    "Baku": "Asia/Baku",
    "Singapore": "Asia/Singapore",
    "Austin": "America/Chicago",
    "Mexico City": "America/Mexico_City",
    "São Paulo": "America/Sao_Paulo",
    "Las Vegas": "America/Los_Angeles",
    "Lusail": "Asia/Qatar",
    "Abu Dhabi": "Asia/Dubai",
}


def fetch_season():
    url = "https://api.jolpi.ca/ergast/f1/2026.json"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    return data["MRData"]["RaceTable"]["Races"]


def parse_dt(date, time):
    if not time:
        return None
    try:
        return datetime.fromisoformat(f"{date}T{time}".replace("Z", "+00:00"))
    except ValueError:
        return None


def main():
    print("F1: fetching 2026 calendar from Jolpica...")
    races = fetch_season()
    total = len(races)
    print(f"  Got {total} races")

    events = []

    for race in races:
        rnd = int(race["round"])
        rnd_str = f"r{rnd:02d}"
        name = race["raceName"]
        circuit = race["Circuit"]
        circuit_name = circuit["circuitName"]
        locality = circuit["Location"]["locality"]
        country = circuit["Location"]["country"]
        location = f"{circuit_name}, {locality}, {country}"
        tz = LOCALITY_TZ.get(locality, "UTC")

        is_sprint = "Sprint" in race

        # Sprint event (sprint weekends only)
        if is_sprint:
            sprint = race["Sprint"]
            dt = parse_dt(sprint["date"], sprint.get("time", ""))
            if dt:
                uid = f"f1-2026-{rnd_str}-sprint@open-sports-cal"
                summary = f"{name} — Sprint"
                description = (f"F1 2026 — Round {rnd} of {total}\\n"
                               f"{name} — Sprint\\n{circuit_name}\\n{locality}, {country}")
                events.append(make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=1)),
                                         location, description, "Motorsport,Formula 1,F1 2026", tz))

        # Race
        dt = parse_dt(race["date"], race.get("time", ""))
        if dt:
            uid = f"f1-2026-{rnd_str}-race@open-sports-cal"
            summary = f"{name} (Sprint Weekend)" if is_sprint else name
            description = (f"F1 2026 — Round {rnd} of {total}\\n"
                           f"{name}\\n{circuit_name}\\n{locality}, {country}")
            events.append(make_vevent(uid, summary, fmt_utc(dt), fmt_utc(dt + timedelta(hours=2)),
                                     location, description, "Motorsport,Formula 1,F1 2026", tz))

    (OUT_DIR / "all-races.ics").write_text(
        make_calendar(events, "Formula 1 2026", "F1 2026"),
        encoding="utf-8",
    )
    print(f"  Wrote all-races.ics ({len(events)} events)")
    print("F1: done.")


if __name__ == "__main__":
    main()
