# Contributing to open-sports-cal

Thank you for helping keep these calendars accurate and growing! Here's how to contribute.

---

## Ways to Contribute

- **Fix a wrong date, time, or venue** in an existing calendar
- **Add a new season** for an existing league
- **Add a new league or sport**
- **Improve a README**

---

## Fixing Data Errors

If a match date, time, or venue is incorrect:

1. Fork the repository and create a branch: `fix/<league>-<description>`
2. Edit the relevant `.ics` file(s) directly
3. Submit a pull request with a link to the official source confirming the correct data

Always include a source (official league website, official PDF, etc.) in your PR description.

---

## Adding a New Season

1. Create the season folder following the existing structure:
   ```
   <sport>/<league>/<season>/
   ```
2. Generate the `.ics` files (see [File Format](#ics-file-format) below)
3. Add a `README.md` in the new folder — copy an existing one and update the details
4. Update the **Available Calendars** table in the root `README.md`
5. Update the **Data Sources** table in the root `README.md` if applicable

---

## Adding a New League or Sport

1. Discuss first — open an issue describing the league, data source, and how you plan to generate the files
2. Follow the folder convention: `<sport>/<league>/<season>/`
3. Every season folder must have:
   - `all-teams.ics` — the full league schedule
   - Individual `.ics` files per team/participant
   - `README.md` with subscribe instructions and team list

---

## .ics File Format

All calendar files must follow these conventions:

**Timezones**
- Use `DTSTART;TZID=Asia/Kolkata:` (with a `VTIMEZONE` block) only for IST-based leagues (e.g. IPL)
- Use UTC (`DTSTART:20260328T140000Z`) for all other leagues

**Event duration by sport**

| Sport | Duration |
|-------|----------|
| Cricket T20 | 4 hours |
| Football / Soccer | 2 hours |
| Basketball (NBA) | 3 hours |
| Baseball (MLB) | 3 hours |
| F1 race | 2 hours |
| F1 sprint | 1 hour |
| MotoGP race | 90 minutes |
| Tennis Grand Slams | All-day (VALUE=DATE) |

**Required VEVENT fields**
```
BEGIN:VEVENT
UID:<sport>-<season>-<identifier>@open-sports-cal
DTSTART:...
DTEND:...
SUMMARY:...
DESCRIPTION:...
LOCATION:...
CATEGORIES:...
STATUS:CONFIRMED
DTSTAMP:...
END:VEVENT
```

**UID format**: `<sport>-<season>-<identifier>@open-sports-cal`
- e.g. `ipl2026-match01@open-sports-cal`, `f1-2026-r03-race@open-sports-cal`

**SUMMARY format**
- Team sports: `Away Team @ Home Team`
- Cricket: `Home vs Away`
- Motorsport/Tennis: event name only

**Team file naming**: lowercase, spaces replaced with hyphens, punctuation removed
- e.g. `Manchester City` → `manchester-city.ics`, `FC Bayern München` → `fc-bayern-munchen.ics`

---

## Generation Scripts

Scripts used to generate `.ics` files are **not committed** to the repository — they are run locally and deleted. If you write a script to generate files, document the data source and API used in the PR description so others can reproduce it.

The naming convention `_gen_*.py` is gitignored by default.

---

## Validation

Before submitting a PR, run the local validator:

```bash
python3 validate.py
```

This checks all `.ics` files for:
- Valid `BEGIN:VCALENDAR` / `END:VCALENDAR` structure
- Required `VERSION`, `PRODID` (must contain `open-sports-cal`)
- All VEVENT fields present: `UID`, `DTSTART`, `DTEND`, `SUMMARY`, `LOCATION`, `STATUS`, `DTSTAMP`
- UID format ending in `@open-sports-cal`
- No duplicate UIDs within a file
- Lowercase hyphenated filenames
- `README.md` present in every season folder

You can also validate a specific folder only:

```bash
python3 validate.py football/premier-league/2025-26
```

CI runs the same validator automatically on every pull request.

---

## Pull Request Guidelines

- One PR per league/fix — keep changes focused
- Include the data source URL in the PR description
- Run `python3 validate.py` and confirm it passes before submitting
- Test by importing the changed `.ics` file into at least one calendar app (Google Calendar, Apple Calendar, or Outlook)
- Update the relevant `README.md` if team names or file names change

---

## Data Sources

Prefer official sources in this order:
1. Official league/governing body website or API (e.g. MLB Stats API, BCCI PDF)
2. Established aggregators (e.g. fixturedownload.com)
3. Community-maintained sources (document clearly and note reliability)

---

## Reporting Issues

Use [GitHub Issues](../../issues) to report:
- Incorrect match data (date, time, venue, teams)
- Missing leagues or seasons you'd like to see added
- Broken calendar subscriptions
