# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**open-sports-cal** is a public repository of iCalendar (`.ics`) files for sports events. Users subscribe to or download these files to get sports schedules in Google Calendar, Apple Calendar, and Microsoft Outlook. There is no build system, server, or application — this is a pure data repository.

---

## Folder Structure

```
<sport>/<league>/<season>/
  README.md
  all-teams.ics        ← every event in the league/season combined
  <team-slug>.ics      ← one file per team/participant (home + away games)
```

**Sport folder names in use:**
- `cricket/ipl/`
- `football/premier-league/`, `football/la-liga/`, `football/bundesliga/`, `football/serie-a/`, `football/ligue-1/`
- `basketball/nba/`
- `baseball/mlb/`
- `hockey/nhl/`
- `hockey/pwhl/`
- `tennis/grand-slams/`
- `motorsport/formula-1/`, `motorsport/motogp/`
- NFL is pending — schedule expected May 13, 2026; will go in `american-football/nfl/`

**Season naming convention:**
- Single-year seasons: `2026` (IPL, MLB, F1, MotoGP, Tennis)
- Split-year seasons: `2025-26` (NBA, EPL, La Liga, Bundesliga, Serie A, Ligue 1)

---

## Validation

Always run before committing:

```bash
python3 validate.py                                   # validate all files
python3 validate.py football/premier-league/2025-26   # validate one folder
```

CI runs the same script on every PR via `.github/workflows/validate.yml`. All 181 current files pass.

---

## Adding a New League or Season — Step-by-Step

1. **Create the folder**
   ```bash
   mkdir -p <sport>/<league>/<season>
   ```

2. **Write a generation script** (see template below), run it, then **delete it** — scripts are never committed. Use the naming pattern `_gen_<league>.py` (gitignored).

3. **Validate**
   ```bash
   python3 validate.py <sport>/<league>/<season>
   ```

4. **Add a `README.md`** in the new season folder (see README Conventions section).

5. **Update the root `README.md`** — add a row to the Available Calendars table and the Data Sources table.

6. **Update `CLAUDE.md`** — add the new league to the folder structure list and data sources table.

---

## Generation Script Template

Scripts are written in Python, run once, then deleted. No third-party libraries — only the standard library. The pattern used across all existing leagues:

```python
#!/usr/bin/env python3
import json, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT_DIR = Path("<sport>/<league>/<season>")
DTSTAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def slug(name):
    return (name.lower()
            .replace(" ", "-").replace(".", "").replace("'", "")
            .replace("/", "-").replace("&", "and")
            .replace("ü","u").replace("ö","o").replace("ä","a")
            .replace("í","i").replace("é","e").replace("á","a"))

def fmt_utc(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")

def make_vevent(uid, summary, dtstart, dtend, location, description, categories, timezone=""):
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        f"CATEGORIES:{categories}",
        "STATUS:CONFIRMED",
        f"DTSTAMP:{DTSTAMP}",
    ]
    if timezone:
        lines.append(f"X-TIMEZONE:{timezone}")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)

def make_calendar(events, cal_name, prodid_label):
    header = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//open-sports-cal//{prodid_label}//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        "X-WR-TIMEZONE:UTC",
        "X-WR-CALDESC:https://vinnyab28.github.io/open-sports-cal/",
    ])
    return f"{header}\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR\r\n"

# --- fetch data, build events, write files ---
# all-teams
all_events = [...]
(OUT_DIR / "all-teams.ics").write_text(
    make_calendar(all_events, "<League> - All Teams", "<League Season>"), encoding="utf-8")

# per-team
for team in teams:
    team_events = [e for e in all_events if team in e]
    (OUT_DIR / f"{slug(team)}.ics").write_text(
        make_calendar(team_events, f"<League> - {team}", "<League Season>"), encoding="utf-8")
```

---

## iCalendar File Format

### Calendar wrapper

Every `.ics` file must start and end exactly like this:

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//open-sports-cal//<League Season>//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:<Calendar display name>
X-WR-TIMEZONE:UTC
X-WR-CALDESC:https://vinnyab28.github.io/open-sports-cal/
<VTIMEZONE block — only for IST leagues>
<VEVENT blocks>
END:VCALENDAR
```

### VTIMEZONE block (IST only — IPL)

Include this block immediately after the calendar header, before the first VEVENT:

```
BEGIN:VTIMEZONE
TZID:Asia/Kolkata
BEGIN:STANDARD
TZOFFSETFROM:+0530
TZOFFSETTO:+0530
TZNAME:IST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE
```

### VEVENT — team sport (UTC)

```
BEGIN:VEVENT
UID:mlb-2026-2026-03-25-new-york-yankees-vs-san-francisco-giants@open-sports-cal
DTSTART:20260325T201000Z
DTEND:20260325T231000Z
SUMMARY:New York Yankees @ San Francisco Giants
DESCRIPTION:MLB 2026\nNew York Yankees @ San Francisco Giants\nOracle Park
LOCATION:Oracle Park
CATEGORIES:Baseball,MLB,MLB 2026
STATUS:CONFIRMED
DTSTAMP:20260329T230000Z
X-TIMEZONE:America/Los_Angeles
END:VEVENT
```

### VEVENT — cricket / IST timezone

```
BEGIN:VEVENT
UID:ipl2026-match01@open-sports-cal
DTSTART;TZID=Asia/Kolkata:20260328T193000
DTEND;TZID=Asia/Kolkata:20260328T233000
SUMMARY:Royal Challengers Bengaluru vs Sunrisers Hyderabad
DESCRIPTION:IPL 2026 — Match 1\nRoyal Challengers Bengaluru vs Sunrisers Hyderabad\n7:30 PM IST\nM. Chinnaswamy Stadium, Bengaluru
LOCATION:M. Chinnaswamy Stadium, Bengaluru
CATEGORIES:Cricket,IPL,IPL 2026
STATUS:CONFIRMED
DTSTAMP:20260329T230449Z
END:VEVENT
```

### VEVENT — motorsport

```
BEGIN:VEVENT
UID:f1-2026-r01-race@open-sports-cal
DTSTART:20260308T040000Z
DTEND:20260308T060000Z
SUMMARY:Australian Grand Prix
DESCRIPTION:F1 2026 — Round 1 of 22\nAustralian Grand Prix\nAlbert Park Grand Prix Circuit\nMelbourne, Australia
LOCATION:Albert Park Grand Prix Circuit, Melbourne, Australia
CATEGORIES:Motorsport,Formula 1,F1 2026
STATUS:CONFIRMED
DTSTAMP:20260329T231717Z
X-TIMEZONE:Australia/Melbourne
END:VEVENT
```

### VEVENT — tennis (all-day, multi-day)

```
BEGIN:VEVENT
UID:tennis-2026-wimbledon@open-sports-cal
DTSTART;VALUE=DATE:20260629
DTEND;VALUE=DATE:20260713
SUMMARY:Wimbledon 2026
DESCRIPTION:Tennis Grand Slam 2026\nWimbledon 2026\nAll England Club, London, UK\nSurface: Grass
LOCATION:All England Club, London, UK
STATUS:CONFIRMED
DTSTAMP:20260329T231717Z
END:VEVENT
```

Note: `DTEND` for all-day events is the day **after** the last day (exclusive), matching RFC 5545.

---

## Field-by-Field Rules

### UID
Format: `<identifier>@open-sports-cal`

Identifier patterns by sport:
- IPL: `ipl<year>-match<NN>` → `ipl2026-match01@open-sports-cal`
- MLB/NBA/NHL: `<league>-<season>-<date>-<away-slug>-vs-<home-slug>` → `nhl-2025-26-2025-10-08-bruins-vs-capitals@open-sports-cal`
- F1: `f1-<year>-r<NN>-race` or `f1-<year>-r<NN>-sprint` → `f1-2026-r01-race@open-sports-cal`
- MotoGP: `motogp-<year>-r<NN>` → `motogp-2026-r01@open-sports-cal`
- Soccer: `<league-code>-<index>` → `epl-2025-0@open-sports-cal`
- Tennis: `tennis-<year>-<slam-slug>` → `tennis-2026-wimbledon@open-sports-cal`

UIDs must be unique within each `.ics` file.

### SUMMARY
| Sport | Format | Example |
|-------|--------|---------|
| Cricket | `Home vs Away` | `Mumbai Indians vs Kolkata Knight Riders` |
| Football/Soccer | `Away @ Home` | `Arsenal @ Liverpool` |
| Basketball | `Away @ Home` | `Boston Celtics @ New York Knicks` |
| Baseball | `Away @ Home` | `New York Yankees @ San Francisco Giants` |
| Hockey | `Away @ Home` | `Toronto Maple Leafs @ Boston Bruins` |
| F1 race | `<Grand Prix Name>` | `Australian Grand Prix` |
| F1 sprint | `<Grand Prix Name> — Sprint` | `Chinese Grand Prix — Sprint` |
| F1 race (sprint weekend) | `<Grand Prix Name> (Sprint Weekend)` | `Chinese Grand Prix (Sprint Weekend)` |
| MotoGP | `<Grand Prix Name>` | `Thai Grand Prix` |
| Tennis | `<Tournament Name> <Year>` | `Wimbledon 2026` |

### DESCRIPTION
Use `\n` (literal backslash-n) to separate lines within the DESCRIPTION value. Include:
- League and season
- Match/event details (teams or name)
- Time in local timezone (for IST events)
- Venue

### LOCATION
Full venue name and city. Examples:
- `Wankhede Stadium, Mumbai`
- `M. Chinnaswamy Stadium, Bengaluru`
- `Albert Park Grand Prix Circuit, Melbourne, Australia`

### CATEGORIES
Comma-separated, no spaces after commas:
- Cricket: `Cricket,IPL,IPL 2026`
- Football: `Football,Premier League,Premier League 2025-26`
- Basketball: `Basketball,NBA,NBA 2025-26`
- Baseball: `Baseball,MLB,MLB 2026`
- Hockey: `Hockey,NHL,NHL 2025-26`
- F1: `Motorsport,Formula 1,F1 2026`
- MotoGP: `Motorsport,MotoGP,MotoGP 2026`
- Tennis: `Tennis,Grand Slam,<Tournament Name>`

### DTSTART / DTEND
- **UTC (all sports except IPL):** `DTSTART:20260308T040000Z`
- **IST (IPL only):** `DTSTART;TZID=Asia/Kolkata:20260328T193000`
- **All-day (Tennis):** `DTSTART;VALUE=DATE:20260629`
- Line endings within the file must be `\r\n` (CRLF) per RFC 5545

### X-TIMEZONE
A custom property that records the **venue's IANA timezone**. Used by the website to display the event's local time alongside the user's local time.

- Required for all UTC-based events (team sports, motorsport, soccer)
- **Not** needed for IPL (timezone already in `DTSTART;TZID=Asia/Kolkata`)
- **Not** needed for Tennis (all-day events have no clock time)
- Value must be a valid IANA timezone string, e.g. `America/New_York`, `Europe/London`, `Australia/Melbourne`
- Set it per-event in `make_vevent` using the `timezone` parameter; for fixed-location leagues (soccer, F1, MotoGP) derive it from a lookup dict; for multi-city leagues (NBA, MLB) look up the home team's city

Examples:
```
X-TIMEZONE:America/Los_Angeles    # Oracle Park, San Francisco
X-TIMEZONE:Europe/London          # Premier League home games in England
X-TIMEZONE:Australia/Melbourne    # Albert Park, F1
```

### Event Durations
| Sport | Duration | Rationale |
|-------|----------|-----------|
| Cricket T20 (IPL) | 4 hours | Match + breaks |
| Football / Soccer | 2 hours | 90 min + buffer |
| Basketball (NBA) | 3 hours | Game + overtime buffer |
| Baseball (MLB) | 3 hours | Average game length |
| Hockey (NHL) | 3 hours | Game + overtime buffer |
| F1 race | 2 hours | Typical race duration |
| F1 sprint | 1 hour | Sprint race length |
| MotoGP race | 90 minutes | Typical race duration |
| Tennis Grand Slams | Full tournament window | All-day multi-day event |

### DTSTAMP
Always the UTC timestamp of when the file was generated:
```python
DTSTAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
```

---

## Team File Naming (Slug Rules)

Python slug function used across all generation scripts:

```python
def slug(name):
    return (name.lower()
            .replace(" ", "-").replace(".", "").replace("'", "")
            .replace("/", "-").replace("&", "and")
            .replace("ü","u").replace("ö","o").replace("ä","a")
            .replace("í","i").replace("é","e").replace("á","a"))
```

Examples:
- `Mumbai Indians` → `mumbai-indians.ics`
- `FC Bayern München` → `fc-bayern-munchen.ics`
- `Borussia Mönchengladbach` → `borussia-monchengladbach.ics`
- `Atlético de Madrid` → `atletico-de-madrid.ics`
- `1. FC Köln` → `1-fc-koln.ics`

`all-teams.ics`, `all-races.ics`, `all-grand-slams.ics` are exempt from the slug rule.

---

## Data Sources

| League | Source | Fetch method |
|--------|--------|-------------|
| IPL | BCCI official PDF (`documents.iplt20.com`) | Download PDF → `pdftotext` → hardcode parsed data |
| MLB | `statsapi.mlb.com` | Live API, fetch month-by-month |
| NBA | `fixturedownload.com/feed/json/nba-2025` | Live JSON feed |
| NHL | `api-web.nhle.com/v1/schedule/{date}` | Live API, fetch week-by-week |
| PWHL | `lscluster.hockeytech.com/feed/?feed=modulekit&view=schedule&season_id=8&key=446521baf8c38984&client_code=pwhl` | Live API, season_id=8 for 2025-26 |
| Premier League | `fixturedownload.com/feed/json/epl-2025` | Live JSON feed |
| La Liga | `fixturedownload.com/feed/json/la-liga-2025` | Live JSON feed |
| Bundesliga | `fixturedownload.com/feed/json/bundesliga-2025` | Live JSON feed |
| Serie A | `fixturedownload.com/feed/json/serie-a-2025` | Live JSON feed |
| Ligue 1 | `fixturedownload.com/feed/json/ligue-1-2025` | Live JSON feed |
| Formula 1 | `formula1.com` / `f1calendar.com` | Hardcoded (no public API) |
| MotoGP | `motogp.com/en/calendar/2026` | Hardcoded (no public API) |
| Tennis | ATP / WTA official announcements | Hardcoded |
| NFL (pending) | `api.nfl.com` | Live API once schedule is released (May 13, 2026) |

### fixturedownload.com JSON feed

```python
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"  # User-Agent required

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

games = fetch_json("https://fixturedownload.com/feed/json/epl-2025")
# Each game: {"DateUtc": "2025-08-15 19:00:00Z", "HomeTeam": "Liverpool",
#              "AwayTeam": "Bournemouth", "Location": "Anfield", ...}
```

League codes for 2025-26 season: `epl-2025`, `la-liga-2025`, `bundesliga-2025`, `serie-a-2025`, `ligue-1-2025`, `nba-2025`

When adding a new season (e.g. 2026-27), increment the year suffix: `epl-2026`, etc.

### MLB Stats API

Fetch month-by-month to avoid response size limits. Season runs late March–late September.

```python
import urllib.request, json

def fetch_mlb_month(season, start, end):
    fields = "dates,date,games,gamePk,gameDate,teams,away,home,team,name,venue"
    url = (f"https://statsapi.mlb.com/api/v1/schedule"
           f"?sportId=1&season={season}&gameType=R"
           f"&startDate={start}&endDate={end}&fields={fields}")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    games = []
    for date_obj in data.get("dates", []):
        for game in date_obj.get("games", []):
            games.append({
                "date":  date_obj["date"],
                "dt":    game["gameDate"],   # ISO UTC e.g. "2026-03-25T20:10:00Z"
                "away":  game["teams"]["away"]["team"]["name"],
                "home":  game["teams"]["home"]["team"]["name"],
                "venue": game.get("venue", {}).get("name", "TBD"),
            })
    return games
```

### IPL schedule extraction

```bash
# Download official BCCI PDF
curl -L "<pdf-url>" -o /tmp/ipl_schedule.pdf
pdftotext /tmp/ipl_schedule.pdf -   # outputs parseable text table
```

The PDF text output is clean enough to read directly. Hardcode the parsed match data in the generation script.

---

## README Conventions

Every `<sport>/<league>/<season>/README.md` must include:

1. **Header** — league full name, team/match count, season date range
2. **Timezone note** — UTC or IST, and that the calendar app auto-converts
3. **All-teams subscribe block** — raw GitHub URL template + download link
4. **Team table** — full team names with individual `.ics` download links
5. **Subscribe instructions** — Google Calendar, Apple Calendar (macOS + iOS), Microsoft Outlook
6. **Key dates** (if applicable) — season start/end, playoffs, finals
7. **Data source** — link to the official source

Raw URL pattern (use `<username>` as placeholder until the repo is pushed to GitHub):
```
https://raw.githubusercontent.com/<username>/open-sports-cal/main/<sport>/<league>/<season>/<file>.ics
```

The root `README.md` maintains:
- **Available Calendars** table — one row per league
- **Data Sources** table — one row per league with source link

---

## What to Update When Adding a League

| File | What to change |
|------|----------------|
| `<sport>/<league>/<season>/README.md` | Create new file |
| `README.md` | Add row to Available Calendars + Data Sources tables |
| `CLAUDE.md` | Add to folder structure list + data sources table |
| `validate.py` | No change needed — automatically picks up new `.ics` files |
