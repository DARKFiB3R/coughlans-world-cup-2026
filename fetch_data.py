#!/usr/bin/env python3
"""
Fetches FIFA World Cup 2026 match data + top scorers from football-data.org
and writes data.json in the format expected by index.html.

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
COMPETITION = "WC"
BASE        = f"https://api.football-data.org/v4/competitions/{COMPETITION}"
OUTPUT      = "data.json"

STAGE_MAP = {
    "ROUND_OF_32": "LAST_32",
    "ROUND_OF_16": "LAST_16",
    "GROUP_STAGE":    "GROUP_STAGE",
    "QUARTER_FINALS": "QUARTER_FINALS",
    "SEMI_FINALS":    "SEMI_FINALS",
    "THIRD_PLACE":    "THIRD_PLACE",
    "FINAL":          "FINAL",
}

def fetch(url):
    if not API_KEY:
        print("ERROR: FOOTBALL_API_KEY not set.", file=sys.stderr)
        sys.exit(1)
    req = urllib.request.Request(url, headers={"X-Auth-Token": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} — {e.reason} ({url})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # Matches
    print("Fetching matches…")
    raw = fetch(f"{BASE}/matches?limit=200")
    matches = []
    for m in raw.get("matches", []):
        score = m.get("score", {})
        ft    = score.get("fullTime", {})
        matches.append({
            "utcDate":   m.get("utcDate"),
            "status":    m.get("status"),
            "stage":     STAGE_MAP.get(m.get("stage", ""), m.get("stage", "")),
            "group":     m.get("group"),
            "home":      m.get("homeTeam", {}).get("name", "TBD"),
            "away":      m.get("awayTeam", {}).get("name", "TBD"),
            "homeScore": ft.get("home"),
            "awayScore": ft.get("away"),
            "winner":    score.get("winner"),
            "minute":    m.get("minute"),
        })
    print(f"  {len(matches)} matches ({sum(1 for m in matches if m['status']=='FINISHED')} finished)")

    # Scorers
    print("Fetching scorers…")
    raw_sc = fetch(f"{BASE}/scorers?limit=100")
    scorers = []
    for s in raw_sc.get("scorers", []):
        scorers.append({
            "player":    s.get("player", {}).get("name", ""),
            "team":      s.get("team", {}).get("name", ""),
            "goals":     s.get("goals", 0),
            "assists":   s.get("assists", 0),
            "penalties": s.get("penalties", 0),
        })
    print(f"  {len(scorers)} scorers")

    output = {
        "matches": matches,
        "scorers": scorers,
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))
    print(f"Written to {OUTPUT}")

if __name__ == "__main__":
    main()
