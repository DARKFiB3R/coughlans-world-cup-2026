#!/usr/bin/env python3
"""
Fetches FIFA World Cup 2026 match data from football-data.org
and writes it as data.json in the format expected by index.html.

Run manually:  FOOTBALL_API_KEY=your_key python fetch_data.py
GitHub Action: key is read from environment (set as a repository secret)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_KEY     = os.environ.get("FOOTBALL_API_KEY", "")
COMPETITION = "WC"   # football-data.org competition code for FIFA World Cup
SEASON      = "2026"
URL         = f"https://api.football-data.org/v4/competitions/{COMPETITION}/matches?season={SEASON}&limit=200"
OUTPUT      = "data.json"

# Stage name normalisation — football-data.org uses ROUND_OF_32 / ROUND_OF_16,
# the HA integration (and our HTML) expects LAST_32 / LAST_16.
STAGE_MAP = {
    "ROUND_OF_32": "LAST_32",
    "ROUND_OF_16": "LAST_16",
    "GROUP_STAGE": "GROUP_STAGE",
    "QUARTER_FINALS": "QUARTER_FINALS",
    "SEMI_FINALS": "SEMI_FINALS",
    "THIRD_PLACE": "THIRD_PLACE",
    "FINAL": "FINAL",
}

def fetch_matches():
    if not API_KEY:
        print("ERROR: FOOTBALL_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    req = urllib.request.Request(URL, headers={"X-Auth-Token": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} from football-data.org — {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    matches = []
    for m in data.get("matches", []):
        score   = m.get("score", {})
        ft      = score.get("fullTime", {})
        ht      = score.get("halfTime", {})
        stage   = STAGE_MAP.get(m.get("stage", ""), m.get("stage", ""))
        group   = m.get("group")  # e.g. "GROUP_A" or None for knockout

        matches.append({
            "matchNumber": m.get("id"),
            "utcDate":     m.get("utcDate"),
            "status":      m.get("status"),       # SCHEDULED, TIMED, IN_PLAY, PAUSED, FINISHED
            "stage":       stage,
            "group":       group,
            "venue":       m.get("venue", ""),
            "home":        m.get("homeTeam", {}).get("name", "TBD"),
            "away":        m.get("awayTeam", {}).get("name", "TBD"),
            "homeScore":   ft.get("home"),         # None until kicked off
            "awayScore":   ft.get("away"),
            "winner":      score.get("winner"),    # HOME_TEAM / AWAY_TEAM / DRAW / None
            "minute":      m.get("minute"),
        })

    return matches

def main():
    print(f"Fetching {URL} …")
    matches = fetch_matches()
    finished = sum(1 for m in matches if m["status"] == "FINISHED")
    live     = sum(1 for m in matches if m["status"] in ("IN_PLAY", "PAUSED"))
    print(f"Got {len(matches)} matches ({finished} finished, {live} live)")

    output = {
        "matches": matches,
        "updated": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    print(f"Written to {OUTPUT}")

if __name__ == "__main__":
    main()
