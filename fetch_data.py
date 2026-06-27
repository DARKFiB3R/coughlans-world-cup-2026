#!/usr/bin/env python3
"""
Fetches World Cup 2026 data from:
  PRIMARY:   ESPN public scoreboard API (no key — matches, events, stats, team data)
  SECONDARY: football-data.org (tournament top scorers summary)

Writes data.json for the syndicate dashboard.
"""

import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

# football-data.org API key (only needed for scorers)
API_KEY  = os.environ.get("FOOTBALL_API_KEY", "")
OUTPUT   = "data.json"

ESPN_URL  = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?limit=200&dates=20260611-20260719"
FD_URL    = "https://api.football-data.org/v4/competitions/WC/scorers?limit=100"

# ESPN season slug → our stage codes
SLUG_TO_STAGE = {
    "group-stage":    "GROUP_STAGE",
    "round-of-32":    "LAST_32",
    "round-of-16":    "LAST_16",
    "quarterfinals":  "QUARTER_FINALS",
    "semifinals":     "SEMI_FINALS",
    "3rd-place":      "THIRD_PLACE",
    "third-place":    "THIRD_PLACE",
    "final":          "FINAL",
}

# ESPN team displayName → syndicate name (where they differ)
ESPN_NAMES = {
    "Bosnia-Herzegovina":        "Bosnia",
    "United States":             "USA",
    "Curaçao":                   "Curacao",
    "Korea Republic":            "South Korea",
    "DR Congo":                  "DR Congo",
    "Congo, DR":                 "DR Congo",
    "Ivory Coast":               "Ivory Coast",
    "Cape Verde Islands":        "Cape Verde",
    "Türkiye":                   "Turkey",
}

def ename(n):
    return ESPN_NAMES.get(n, n)

def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} — {url}", file=sys.stderr)
        raise

def fetch_espn():
    print(f"Fetching ESPN scoreboard…")
    data = fetch(ESPN_URL)
    events = data.get("events", [])
    print(f"  {len(events)} events returned")

    matches = []
    teams   = {}   # syndicateName → team metadata

    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_raw = home_c.get("team", {}).get("displayName", "")
        away_raw = away_c.get("team", {}).get("displayName", "")
        home_name = ename(home_raw)
        away_name = ename(away_raw)

        # ── Team metadata ──────────────────────────────────────────────────
        for c, sname in [(home_c, home_name), (away_c, away_name)]:
            t = c.get("team", {})
            if sname and sname not in teams:
                raw_color = t.get("color", "1a3050")
                raw_alt   = t.get("alternateColor", "e8edf5")
                teams[sname] = {
                    "id":       t.get("id", ""),
                    "abbr":     t.get("abbreviation", "").lower(),
                    "color":    "#" + raw_color,
                    "altColor": "#" + raw_alt,
                    "logo":     t.get("logo", ""),
                    "form":     c.get("form", ""),
                }
            elif sname in teams and c.get("form"):
                # Update form on later matches (more recent)
                teams[sname]["form"] = c.get("form")

        # ── Status ─────────────────────────────────────────────────────────
        st = comp.get("status", {}).get("type", {})
        state  = st.get("state", "pre")   # pre / in / post
        status = "FINISHED" if state == "post" else ("IN_PLAY" if state == "in" else "SCHEDULED")

        home_score = home_c.get("score")
        away_score = away_c.get("score")
        if state == "pre":
            home_score = away_score = None
        else:
            try: home_score = int(home_score)
            except: home_score = 0
            try: away_score = int(away_score)
            except: away_score = 0

        # ── Winner ─────────────────────────────────────────────────────────
        winner = None
        if state == "post":
            if home_c.get("winner"):       winner = "HOME_TEAM"
            elif away_c.get("winner"):     winner = "AWAY_TEAM"
            elif home_score == away_score: winner = "DRAW"

        # ── Stage / Group ──────────────────────────────────────────────────
        slug  = ev.get("season", {}).get("slug", "group-stage")
        stage = SLUG_TO_STAGE.get(slug, "GROUP_STAGE")
        group = None
        alt   = comp.get("altGameNote", "")
        if "Group" in alt and stage == "GROUP_STAGE":
            letter = alt.split("Group ")[-1].strip()
            if len(letter) == 1:
                group = f"GROUP_{letter}"

        # ── Match events (goals + cards) ───────────────────────────────────
        # Build id→name lookup for this match
        id_to_name = {c.get("team", {}).get("id"): ename(c.get("team", {}).get("displayName", ""))
                      for c in competitors}

        match_events = []
        for d in comp.get("details", []):
            is_goal   = d.get("scoringPlay", False)
            is_yellow = d.get("yellowCard", False)
            is_red    = d.get("redCard", False)
            if not (is_goal or is_yellow or is_red):
                continue
            athletes = d.get("athletesInvolved", [])
            player   = athletes[0].get("displayName", "") if athletes else ""
            team_id  = d.get("team", {}).get("id", "")
            team_nm  = id_to_name.get(team_id, "")
            ev_type_text = d.get("type", {}).get("text", "")
            match_events.append({
                "type":    "goal" if is_goal else ("redcard" if is_red else "yellowcard"),
                "team":    team_nm,
                "player":  player,
                "minute":  d.get("clock", {}).get("displayValue", ""),
                "header":  "Header" in ev_type_text,
                "penalty": d.get("penaltyKick", False),
                "ownGoal": d.get("ownGoal", False),
            })

        # ── Match stats ────────────────────────────────────────────────────
        stats = {}
        for c, sname in [(home_c, home_name), (away_c, away_name)]:
            raw = {s["abbreviation"]: s.get("displayValue", "0") for s in c.get("statistics", [])}
            if raw:
                stats[sname] = {
                    "possession":     float(raw.get("PP", 0) or 0),
                    "shots":          int(float(raw.get("SHOT", 0) or 0)),
                    "shotsOnTarget":  int(float(raw.get("SOG",  0) or 0)),
                    "corners":        int(float(raw.get("CW",   0) or 0)),
                    "fouls":          int(float(raw.get("FC",   0) or 0)),
                }

        # ── Headline ───────────────────────────────────────────────────────
        headline = ""
        for hl in comp.get("headlines", []):
            if hl.get("type") in ("Recap", "GameSummary"):
                headline = hl.get("shortLinkText") or hl.get("description", "")
                break

        matches.append({
            "utcDate":   ev.get("date"),
            "status":    status,
            "stage":     stage,
            "group":     group,
            "home":      home_name,
            "away":      away_name,
            "homeScore": home_score,
            "awayScore": away_score,
            "winner":    winner,
            "venue":     comp.get("venue", {}).get("fullName", ""),
            "attendance": comp.get("attendance"),
            "events":    match_events,
            "stats":     stats,
            "headline":  headline,
            "espnId":    ev.get("id", ""),
        })

    finished = sum(1 for m in matches if m["status"] == "FINISHED")
    live     = sum(1 for m in matches if m["status"] == "IN_PLAY")
    print(f"  {len(matches)} matches ({finished} finished, {live} live)")
    print(f"  {len(teams)} teams with metadata")
    return matches, teams


def fetch_scorers():
    if not API_KEY:
        print("  No FOOTBALL_API_KEY set — skipping top scorers.")
        return []
    try:
        data = fetch(FD_URL, {"X-Auth-Token": API_KEY})
        scorers = []
        for s in data.get("scorers", []):
            scorers.append({
                "player":   s.get("player", {}).get("name", ""),
                "team":     s.get("team", {}).get("name", ""),
                "goals":    s.get("goals", 0),
                "assists":  s.get("assists", 0),
                "penalties":s.get("penalties", 0),
            })
        print(f"  {len(scorers)} scorers from football-data.org")
        return scorers
    except Exception as e:
        print(f"  Scorers fetch failed: {e} — continuing without.", file=sys.stderr)
        return []


def main():
    matches, teams = fetch_espn()
    print("Fetching top scorers…")
    scorers = fetch_scorers()

    output = {
        "matches": matches,
        "scorers": scorers,
        "teams":   teams,
        "updated": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))
    print(f"Written → {OUTPUT}")


if __name__ == "__main__":
    main()
