# Quick Start Guide

## Setup (One-time)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set environment variables:**
   ```bash
   export SUPABASE_URL="https://uxdqrswbcgkkftvompwd.supabase.co"
   export SUPABASE_KEY="your_service_role_key_here"
   ```
   
   Or create a `.env` file (make sure to add it to `.gitignore`).

3. **Create Supabase tables:**
   - Go to Supabase Dashboard → SQL Editor
   - Run `supabase/migrations/001_create_scraper_tables.sql`
   - Run `supabase/migrations/002_create_scraper_runs_table.sql`

## Run Scrapers

**Run all scrapers:**
```bash
cd scrapers
python run_all_scrapers.py
```

**Run individual scrapers:**
```bash
cd scrapers
python find_all_themes.py
python scrape_lego_overview.py
python check_pov.py
```

## Schedule Daily Runs

### GitHub Actions (Recommended - Easiest)
1. **Add GitHub secrets:**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add `SUPABASE_URL` = `https://uxdqrswbcgkkftvompwd.supabase.co`
   - Add `SUPABASE_KEY` = your Supabase service role key
2. **Push to GitHub** (workflow file is already created)
3. **Done!** Runs daily at 2 AM UTC automatically
4. **Manual trigger:** Go to Actions tab → "Run Scrapers Daily" → Run workflow

**See `GITHUB_ACTIONS_SETUP.md` for detailed instructions.**

### Alternative: Local Cron
```bash
crontab -e
# Add: 0 2 * * * cd /path/to/DataWeapons/scrapers && python3 run_all_scrapers.py
```

## Data Output

- **CSV files**: Saved locally as backup (`themes_list.csv`, `lego_store_overview.csv`, `pov.csv`)
- **Supabase tables**: 
  - `themes` - Theme data
  - `lego_sets_overview` - LEGO sets data
  - `pov_data` - Part-out-value data

## Troubleshooting

- **"SUPABASE_KEY not set"**: Set the environment variable
- **Import errors**: Make sure you're in the `scrapers` directory
- **Playwright errors**: Run `playwright install chromium`

For more details, see `SCRAPER_SETUP.md`.

