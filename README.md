# ⚽ WC2026 Syndicate

Live World Cup 2026 sweepstake tracker for your office syndicate.

**Features**
- 🏆 **Leaderboard** — everyone ranked by points (how far their team has gone)
- ⚽ **Teams** — all 48 teams with results and status
- ⚔️ **Clashes** — knockout matches where two syndicate teams face each other
- Auto-updates every 15 minutes via GitHub Actions
- Click any team for a full stats modal: progress strip, W/D/L, goals, next fixture

---

## Setup

### 1. Fork / copy this repo

Create a new GitHub repo and push these files, or just fork this one.

### 2. Get a football-data.org API key

Sign up free at https://www.football-data.org — the free tier is enough.

### 3. Add your API key as a GitHub secret

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

- Name: `FOOTBALL_API_KEY`
- Value: your key from football-data.org

### 4. Enable GitHub Pages

Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/ (root)`
- Save

Your site will be live at `https://YOUR_USERNAME.github.io/YOUR_REPO/`

### 5. Trigger the first data fetch

Go to **Actions → Update Match Data → Run workflow**

This populates `data.json` immediately. After that it runs every 15 minutes automatically.

### 6. Share the URL with colleagues

That's it. Everyone opens the GitHub Pages URL — no login, no HA needed.

---

## Home Assistant version

The same `index.html` works as a local HA dashboard card.

1. Copy `index.html` to `config/www/syndicate-2026.html`
2. Change `USE_JSON = false` near the top
3. Set `HA_TOKEN` to a long-lived access token (HA → Profile → Security)
4. Add a `webpage` card to your Lovelace dashboard: `url: /local/syndicate-2026.html`

The HA version reads from `sensor.fixtures` (from the World Cup 2026 HACS integration) and refreshes every 60 seconds.

---

## Notes

- Spellings in the syndicate list are based on OCR — check against the original sheet if any names look wrong
- The **Clashes** tab is empty until two syndicate teams meet in the knockout rounds — it will populate automatically as the tournament progresses
- Points system: Qualified=1, Won R32=2, Won R16=3, Won QF=4, Won SF=5, Runner-Up=6, Champion=7
