# AGENTS.md

Guidance for AI agents working in this repository. For full format specifications and code patterns, refer to `CLAUDE.md`.

---

## What This Repo Is

A public collection of iCalendar (`.ics`) files for sports schedules. No application code, no build pipeline. The only executable file is `validate.py`. All work produces `.ics` files and/or `README.md` files.

---

## Verify Your Work

After any change to `.ics` files or folder structure:

```bash
python3 validate.py
```

This is the only test command. All changes must pass with zero errors before being considered complete. CI runs this on every pull request.

---

## Common Tasks and How to Approach Them

### Adding a new season for an existing league

1. Identify the correct data source from the table in `CLAUDE.md` → Data Sources
2. Write a Python generation script named `_gen_<league>.py`
3. Run it to produce `all-teams.ics` + per-team `.ics` files in `<sport>/<league>/<season>/`
4. Run `python3 validate.py <sport>/<league>/<season>` — fix any errors
5. Write `<sport>/<league>/<season>/README.md` following the pattern of an existing league README
6. Update the Available Calendars and Data Sources tables in the root `README.md`
7. Update the folder structure list and data sources table in `CLAUDE.md`
8. Delete the generation script — it must not be committed

### Fixing a wrong date, time, or venue

1. Read the affected `.ics` file
2. Find the VEVENT by its `SUMMARY` or `UID`
3. Edit `DTSTART`, `DTEND`, or `LOCATION` directly
4. Run `python3 validate.py` to confirm the file is still valid

### Adding a new sport or league (not previously in the repo)

1. Choose the sport folder name (lowercase, hyphenated) — check `CLAUDE.md` for existing conventions
2. Discuss the data source and generation approach before writing files
3. Follow the same steps as "adding a new season" above
4. Add the new sport folder to `CLAUDE.md` folder structure list

### Updating a README

Edit the file directly. All READMEs follow the same structure — see any existing league README as a reference. Always keep the raw GitHub URL template using `<username>` as a placeholder.

---

## Decision Rules

**Hardcode vs. live API:**
- If an official free API exists (MLB Stats API, fixturedownload.com), always use it — don't hardcode schedules that can be fetched
- If no API exists (F1, MotoGP, Tennis, IPL), extract from official PDFs or announcements and hardcode in the script

**Which data source to use:**
- Prefer official governing body sources (BCCI, MLB, NBA, UEFA)
- fixturedownload.com is the approved fallback for soccer leagues and NBA
- Never use unofficial scrapers or unreliable third-party sources without flagging it

**When the schedule isn't available yet:**
- Don't create placeholder or estimated `.ics` files
- Note the expected release date in the relevant README and in `CLAUDE.md`
- NFL 2026 is a known pending case — do not generate estimated fixtures

**Timezone:**
- Use `TZID=Asia/Kolkata` only for IPL; use UTC (`Z` suffix) for everything else
- Never mix timezone formats within the same file

**File naming:**
- Team files: lowercase, hyphens only, no special characters (see slug rules in `CLAUDE.md`)
- Aggregate files: `all-teams.ics`, `all-races.ics`, or `all-grand-slams.ics`
- Generation scripts: `_gen_<league>.py` (gitignored, never committed)

---

## What Not to Do

- **Do not commit generation scripts** — they are temporary, run-and-delete
- **Do not create `.ics` files with estimated or unconfirmed data** — only use officially published schedules
- **Do not add playoff or postseason games** until those schedules are officially released
- **Do not modify `validate.py`** to make failing files pass — fix the files instead
- **Do not hardcode `DTSTAMP`** — always generate it at script run time using `datetime.now(timezone.utc)`
- **Do not change UID values** of existing events — this breaks calendar subscriptions for existing users
- **Do not skip the README** — every season folder with `.ics` files must have one

---

## Files to Know

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Full format spec, code patterns, field-by-field rules — read this before generating anything |
| `validate.py` | The only test — run after every change |
| `CONTRIBUTING.md` | PR process and contributor expectations |
| `.github/workflows/validate.yml` | CI config — runs `validate.py` on every PR |
| `.gitignore` | Includes `_gen_*.py` — generation scripts are gitignored by design |
