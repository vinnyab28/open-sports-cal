# open-sports-cal

Free, open-source sports calendars in iCalendar (`.ics`) format — subscribe or download for Google Calendar, Apple Calendar, and Microsoft Outlook.

Times vary by sport and league — see each league's README for timezone details. Most calendars use **UTC**; IPL uses **IST (UTC+5:30)**. Your calendar app will convert to local time automatically.

---

## Available Calendars

### Cricket

| League | Season | Calendar |
|--------|--------|----------|
| IPL | [2026](cricket/ipl/2026/) | All teams + 10 individual team calendars |

### Football / Soccer

| League | Season | Calendar |
|--------|--------|----------|
| Premier League | [2025-26](football/premier-league/2025-26/) | All teams + 20 individual team calendars |
| La Liga | [2025-26](football/la-liga/2025-26/) | All teams + 20 individual team calendars |
| Bundesliga | [2025-26](football/bundesliga/2025-26/) | All teams + 18 individual team calendars |
| Serie A | [2025-26](football/serie-a/2025-26/) | All teams + 20 individual team calendars |
| Ligue 1 | [2025-26](football/ligue-1/2025-26/) | All teams + 18 individual team calendars |

### Basketball

| League | Season | Calendar |
|--------|--------|----------|
| NBA | [2025-26](basketball/nba/2025-26/) | All teams + 30 individual team calendars |

### Baseball

| League | Season | Calendar |
|--------|--------|----------|
| MLB | [2026](baseball/mlb/2026/) | All teams + 30 individual team calendars |

### Tennis

| Tournament | Year | Calendar |
|-----------|------|----------|
| Grand Slams (AO, RG, Wimbledon, USO) | [2026](tennis/grand-slams/2026/) | All 4 slams combined + individual files |

### Motorsport

| League | Season | Calendar |
|--------|--------|----------|
| Formula 1 | [2026](motorsport/formula-1/2026/) | All 22 races + 6 sprints |
| MotoGP | [2026](motorsport/motogp/2026/) | All 22 races |

> **NFL 2026**: The regular season schedule is expected to be released on May 13, 2026. It will be added once available.

---

## How to Use

### Subscribe (stays updated automatically)

#### Google Calendar
1. Open [Google Calendar](https://calendar.google.com)
2. Click **+** next to "Other calendars" → **From URL**
3. Paste the raw `.ics` URL and click **Add calendar**

#### Apple Calendar (macOS / iOS)
- **macOS**: File → New Calendar Subscription → paste the URL
- **iOS**: Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar → paste the URL

#### Microsoft Outlook
1. Open Outlook → **Calendar** view
2. Click **Add calendar** → **Subscribe from web**
3. Paste the URL and click **Import**

### Download & Import (one-time snapshot)

1. Click the `.ics` file link below
2. Click **Raw** to get the file
3. Open the downloaded file — your calendar app will offer to import it

---

## Raw URL Format

All raw URLs follow this pattern:

```
https://raw.githubusercontent.com/<username>/open-sports-cal/main/<path-to-file>.ics
```

---

## Contributing

- Found a wrong date or venue? Open an issue or submit a PR.
- Want to add a new sport/league? Follow the existing folder structure:
  `<sport>/<league>/<season>/`

---

## Disclaimer

Schedules are sourced from official publications and public APIs, and are provided in good faith. Match timings and venues are subject to change — always verify with the official source before travelling to a match.

## Data Sources

| Sport / League | Source |
|---------------|--------|
| IPL | [BCCI / IPLT20 Official Schedule](https://www.iplt20.com/matches/fixtures) |
| Premier League, La Liga, Bundesliga, Serie A, Ligue 1, NBA | [fixturedownload.com](https://fixturedownload.com) |
| MLB | [MLB Stats API](https://statsapi.mlb.com) |
| Formula 1 | [formula1.com](https://www.formula1.com/en/racing/2026) / [f1calendar.com](https://f1calendar.com) |
| MotoGP | [motogp.com](https://www.motogp.com/en/calendar/2026) |
| Tennis Grand Slams | [ATP Tour](https://www.atptour.com) / [WTA](https://www.wtatennis.com) |
