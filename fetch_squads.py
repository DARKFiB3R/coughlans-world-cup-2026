#!/usr/bin/env python3
"""
One-time squad fetcher — run this ONCE to populate squads.json.
Reads team IDs from data.json (produced by fetch_data.py) then hits
the ESPN roster API for each team. Squads don't change during the
tournament, so you don't need to re-run this every 15 minutes.

Usage:
    python fetch_squads.py

Writes: squads.json
"""

import json, sys, time, urllib.request, urllib.error

DATA_FILE   = "data.json"
OUTPUT_FILE = "squads.json"

# ESPN roster endpoint patterns to try (in order)
ROSTER_URLS = [
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{id}/roster",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{id}/roster",
]

POSITION_MAP = {
    "GK": "GK", "G": "GK",
    "D": "DEF", "CB": "DEF", "LB": "DEF", "RB": "DEF",
    "CD": "DEF", "CD-L": "DEF", "CD-R": "DEF",
    "LWB": "DEF", "RWB": "DEF",
    "M": "MID", "CM": "MID", "LM": "MID", "RM": "MID",
    "DM": "MID", "AM": "MID", "CM-R": "MID", "CM-L": "MID",
    "CAM": "MID", "CDM": "MID",
    "F": "FWD", "FW": "FWD", "LW": "FWD", "RW": "FWD",
    "CF": "FWD", "ST": "FWD", "SS": "FWD",
    "SUB": "?",
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def normalise_pos(raw):
    if not raw: return "?"
    base = raw.split("-")[0].upper() if "-" in raw else raw.upper()
    return POSITION_MAP.get(base, POSITION_MAP.get(raw.upper(), "?"))

def fetch_roster(team_id):
    for url_tmpl in ROSTER_URLS:
        url = url_tmpl.format(id=team_id)
        try:
            data = fetch(url)
            athletes = data.get("athletes", [])
            if athletes:
                return athletes
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        except Exception:
            continue
    return []

def parse_player(a):
    return {
        "id":       a.get("id", ""),
        "name":     a.get("displayName", a.get("fullName", "")),
        "shirt":    a.get("jersey", ""),
        "position": normalise_pos(a.get("position", {}).get("abbreviation", "")),
        "age":      a.get("age", ""),
        "club":     "",  # ESPN doesn't always provide club in roster endpoint
    }

def main():
    # Load team IDs from data.json
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {DATA_FILE} not found. Run fetch_data.py first.", file=sys.stderr)
        sys.exit(1)

    teams = data.get("teams", {})
    if not teams:
        print("ERROR: No team data found in data.json.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching rosters for {len(teams)} teams…")
    squads = {}
    failed = []

    for team_name, team_meta in sorted(teams.items()):
        team_id = team_meta.get("id")
        if not team_id:
            print(f"  {team_name}: no ESPN ID — skipping")
            continue

        try:
            athletes = fetch_roster(team_id)
            if not athletes:
                print(f"  {team_name} [{team_id}]: no athletes returned")
                failed.append(team_name)
                continue

            players = [parse_player(a) for a in athletes]
            squads[team_name] = sorted(players, key=lambda p: (
                {"GK":0,"DEF":1,"MID":2,"FWD":3}.get(p["position"], 4),
                int(p["shirt"]) if str(p["shirt"]).isdigit() else 99
            ))
            print(f"  ✓ {team_name}: {len(players)} players")
            time.sleep(0.3)  # be polite to ESPN's servers

        except Exception as e:
            print(f"  ✗ {team_name}: {e}", file=sys.stderr)
            failed.append(team_name)

    if failed:
        print(f"\nFailed to fetch {len(failed)} teams: {', '.join(failed)}")

    output = {
        "squads":  squads,
        "updated": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))
    print(f"\nWritten → {OUTPUT_FILE}  ({len(squads)} squads)")

if __name__ == "__main__":
    main()
