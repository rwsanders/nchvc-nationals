# NCHVC Nationals Viewer

An easier-to-read view of the National Christian Homeschool Volleyball Championships (NCHVC) Nationals brackets. It reads the organizers' public Google Sheets and turns them into one searchable page with pools, brackets, team schedules and a by-court view.

**Unofficial.** Always confirm game times on the [official bracket index](https://docs.google.com/spreadsheets/d/1Uq8uFxIn-y3YwMAzIwCft1l4zgfFA0E7rKGuIBQvo5U/edit).

## How it works

| File | Purpose |
|---|---|
| `nchvc_scrape.py` | Downloads the index sheet and every linked division workbook as `.xlsx`, then parses pools, set scores, standings and bracket matches into `data.json` |
| `page_template.html` | The viewer (plain HTML/CSS/JS, no build step) |
| `build_page.py` | Builds the page: `--site` writes `site/` for hosting, or embeds the data in one HTML file |
| `simulate_demo.py` | Fills in made-up scores to produce `demo.html`, a preview of the page mid-tournament |
| `.github/workflows/refresh.yml` | Scheduled job: scrape → build → deploy to Azure Static Web Apps |

The hosted page loads `data.json` and checks for new data every minute, so open pages update on their own.

## Run locally

```bash
pip install -r requirements.txt
python nchvc_scrape.py          # writes data.json (about 15 s)
python simulate_demo.py         # optional: demo_data.json
python build_page.py --site     # writes site/
python -m http.server -d site 8000
```

## Hosting

The site is static, hosted on the **Azure Static Web Apps Free** plan. The workflow deploys when the repo secret `AZURE_STATIC_WEB_APPS_API_TOKEN` is set (copy it from the Static Web App's **Manage deployment token** in the Azure portal). Without the secret, the workflow still scrapes and builds, which works as a health check.

Schedule: every 5 minutes during tournament week (Oct 14–18), once a day otherwise. Run it any time from **Actions → Refresh brackets → Run workflow**.

## Notes on the sheets

- Each division workbook has a hidden `Ref` tab with every team, pool, seed and advancement slot.
- Bracket matches are fixed-shape blocks: day, time, court and round name stacked in one column, with the seed label one column to the left of each team slot.
- The score is written under the winning team, winner's points first.
- Large Girls divisions share one "POOLS" workbook (for example G18u D1 & D2), which feeds separate bracket workbooks per division.
