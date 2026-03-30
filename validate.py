#!/usr/bin/env python3
"""
Validate all .ics files in open-sports-cal.

Usage:
    python3 validate.py                        # run all checks
    python3 validate.py path/to/dir            # validate a specific folder
    python3 validate.py --check structure      # only check VCALENDAR structure + PRODID
    python3 validate.py --check fields         # only check required VEVENT fields
    python3 validate.py --check uids           # only check UID format and uniqueness
    python3 validate.py --check naming         # only check filename slugs
    python3 validate.py --check readmes        # only check README.md presence
    python3 validate.py --check readme-sync   # check root + season READMEs mention all files/folders

    Combine a folder with a check:
    python3 validate.py football/premier-league/2025-26 --check fields
"""

import re
import sys
from pathlib import Path

# ── Rules ─────────────────────────────────────────────────────────────────────

REQUIRED_VEVENT_FIELDS = {
    "UID", "DTSTART", "DTEND", "SUMMARY", "LOCATION", "STATUS", "DTSTAMP"
}

UID_SUFFIX = "@open-sports-cal"

# Valid team/event file: lowercase, hyphens, digits only
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.ics$")

# all-teams.ics, all-races.ics, all-grand-slams.ics etc. are exempt from slug check
ALL_FILE_RE = re.compile(r"^all-.+\.ics$")

VALID_CHECKS = {"structure", "fields", "uids", "naming", "readmes", "readme-sync"}


# ── Helpers ───────────────────────────────────────────────────────────────────

class Results:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, msg):
        self.errors.append(f"  ERROR  {path}: {msg}")

    def warn(self, path, msg):
        self.warnings.append(f"  WARN   {path}: {msg}")

    def ok(self):
        return len(self.errors) == 0


def parse_vevents(content: str) -> list[dict]:
    """Return a list of dicts, one per VEVENT, mapping property name → raw line."""
    vevents, current, inside = [], {}, False
    for line in content.splitlines():
        if line == "BEGIN:VEVENT":
            inside, current = True, {}
        elif line == "END:VEVENT":
            if inside:
                vevents.append(current)
            inside = False
        elif inside and ":" in line:
            key = line.split(";")[0].split(":")[0]  # strip params like ;TZID=...
            current.setdefault(key, line)
    return vevents


def read_ics(path: Path, r: Results):
    """Read .ics file content, recording an error on failure. Returns content or None."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        r.error(path.relative_to(ROOT), f"could not read file: {e}")
        return None


# ── Individual checks ──────────────────────────────────────────────────────────

def check_naming(path: Path, r: Results):
    """Filename must be lowercase with hyphens/digits only (slug format)."""
    name = path.name
    if ALL_FILE_RE.match(name):
        return
    if not SLUG_RE.match(name):
        r.error(path.relative_to(ROOT), f"filename must be lowercase with hyphens only (got '{name}')")


def check_structure(path: Path, r: Results):
    """VCALENDAR wrapper, VERSION:2.0, and PRODID containing 'open-sports-cal'."""
    content = read_ics(path, r)
    if content is None:
        return

    rel = path.relative_to(ROOT)

    if not content.startswith("BEGIN:VCALENDAR"):
        r.error(rel, "does not start with BEGIN:VCALENDAR")
        return
    if "END:VCALENDAR" not in content:
        r.error(rel, "missing END:VCALENDAR")
        return
    if "VERSION:2.0" not in content:
        r.error(rel, "missing VERSION:2.0")
    if "PRODID:" not in content:
        r.error(rel, "missing PRODID")
    else:
        m = re.search(r"PRODID:(.+)", content)
        if m and "open-sports-cal" not in m.group(1):
            r.error(rel, f"PRODID must contain 'open-sports-cal' (got '{m.group(1).strip()}')")

    vevents = parse_vevents(content)
    if not vevents:
        r.error(rel, "contains no VEVENT blocks")


def check_fields(path: Path, r: Results):
    """Every VEVENT must have all required fields; STATUS should be CONFIRMED."""
    content = read_ics(path, r)
    if content is None:
        return

    rel = path.relative_to(ROOT)
    vevents = parse_vevents(content)
    if not vevents:
        r.error(rel, "contains no VEVENT blocks")
        return

    for i, ev in enumerate(vevents, 1):
        label = f"event #{i}"
        for field in REQUIRED_VEVENT_FIELDS:
            if field not in ev:
                r.error(rel, f"{label} missing required field '{field}'")
        if "STATUS" in ev:
            status_val = ev["STATUS"].split(":", 1)[-1].strip()
            if status_val != "CONFIRMED":
                r.warn(rel, f"{label} STATUS is '{status_val}', expected 'CONFIRMED'")
        if "DTSTART" in ev and "DTEND" not in ev:
            r.error(rel, f"{label} has DTSTART but no DTEND")


def check_uids(path: Path, r: Results):
    """Every VEVENT UID must end with @open-sports-cal and be unique within the file."""
    content = read_ics(path, r)
    if content is None:
        return

    rel = path.relative_to(ROOT)
    vevents = parse_vevents(content)
    if not vevents:
        r.error(rel, "contains no VEVENT blocks")
        return

    uids = []
    for i, ev in enumerate(vevents, 1):
        label = f"event #{i}"
        if "UID" in ev:
            uid_val = ev["UID"].split(":", 1)[1] if ":" in ev["UID"] else ""
            if not uid_val.endswith(UID_SUFFIX):
                r.error(rel, f"{label} UID must end with '{UID_SUFFIX}' (got '{uid_val}')")
            uids.append(uid_val)

    seen = set()
    for uid in uids:
        if uid in seen:
            r.error(rel, f"duplicate UID '{uid}'")
        seen.add(uid)


def check_readmes(folder: Path, r: Results):
    """Every season folder containing .ics files must have a README.md."""
    ics_files = list(folder.glob("*.ics"))
    if ics_files and not (folder / "README.md").exists():
        r.error(folder.relative_to(ROOT), "folder has .ics files but no README.md")


def check_readme_sync(season_folders: set, r: Results):
    """
    1. Root README.md must mention every season folder path.
    2. Each season README.md must mention every .ics filename in that folder.
    """
    root_readme = ROOT / "README.md"
    if not root_readme.exists():
        r.error("README.md", "root README.md is missing")
        return
    root_content = root_readme.read_text(encoding="utf-8")

    for folder in sorted(season_folders):
        folder_rel = str(folder.relative_to(ROOT))  # e.g. "cricket/ipl/2026"

        # 1. Root README must reference this season folder
        if folder_rel not in root_content:
            r.error(folder_rel, "season path not mentioned in root README.md — add it to the Available Calendars table")

        # 2. Season README must mention every .ics file in the folder
        season_readme = folder / "README.md"
        if not season_readme.exists():
            continue  # already caught by check_readmes
        season_content = season_readme.read_text(encoding="utf-8")
        for ics_file in sorted(folder.glob("*.ics")):
            if ics_file.name not in season_content:
                r.error(
                    str(folder.relative_to(ROOT) / ics_file.name),
                    f"'{ics_file.name}' not mentioned in season README.md",
                )


# ── Check dispatch ─────────────────────────────────────────────────────────────

FILE_CHECKS = {
    "structure": check_structure,
    "fields":    check_fields,
    "uids":      check_uids,
    "naming":    check_naming,
}


def run_checks(all_ics: list[Path], selected: str | None, r: Results):
    season_folders = {path.parent for path in all_ics}

    if selected is None:
        # Run everything
        for path in sorted(all_ics):
            check_naming(path, r)
            check_structure(path, r)
            check_fields(path, r)
            check_uids(path, r)
        for folder in sorted(season_folders):
            check_readmes(folder, r)
        check_readme_sync(season_folders, r)
    elif selected == "readmes":
        for folder in sorted(season_folders):
            check_readmes(folder, r)
    elif selected == "readme-sync":
        check_readme_sync(season_folders, r)
    else:
        fn = FILE_CHECKS[selected]
        for path in sorted(all_ics):
            fn(path, r)


# ── Main ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent


def main():
    args = sys.argv[1:]

    # Parse --check <name>
    selected_check = None
    if "--check" in args:
        idx = args.index("--check")
        if idx + 1 >= len(args):
            print("Error: --check requires an argument. Valid checks: " + ", ".join(sorted(VALID_CHECKS)))
            sys.exit(1)
        selected_check = args[idx + 1]
        if selected_check not in VALID_CHECKS:
            print(f"Error: unknown check '{selected_check}'. Valid checks: {', '.join(sorted(VALID_CHECKS))}")
            sys.exit(1)
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    # Remaining arg is optional folder path
    target = Path(args[0]) if args else ROOT
    all_ics = [p for p in target.rglob("*.ics") if ".claude" not in p.parts]

    if not all_ics:
        print("No .ics files found.")
        sys.exit(1)

    r = Results()
    run_checks(all_ics, selected_check, r)

    # Report
    total = len(all_ics)
    check_label = f" [{selected_check}]" if selected_check else ""
    print(f"open-sports-cal validator{check_label} — {total} files\n")

    for msg in r.warnings:
        print(msg)
    for msg in r.errors:
        print(msg)

    if r.errors:
        print(f"\n✗  {len(r.errors)} error(s) found.")
        sys.exit(1)
    else:
        extra = f"  {len(r.warnings)} warning(s)." if r.warnings else ""
        print(f"✓  All checks passed.{extra}")


if __name__ == "__main__":
    main()
