# Scraper Setup Guide

This guide explains how to set up and schedule the scrapers to run daily and save data to Supabase.

## Prerequisites

1. **Supabase Account**: You need a Supabase project with the tables created
2. **Supabase Service Role Key**: Required for write operations
3. **Python Environment**: Python 3.8+ with required packages
4. **Playwright**: Browser automation tool (installed via pip)

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set Up Supabase Tables

Run the SQL migrations in your Supabase SQL editor:

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Run the migration files in order:
   - `supabase/migrations/001_create_scraper_tables.sql`
   - `supabase/migrations/002_create_scraper_runs_table.sql`

### 3. Configure Environment Variables

Create a `.env` file in the project root (or set environment variables):

```bash
SUPABASE_URL=https://uxdqrswbcgkkftvompwd.supabase.co
SUPABASE_KEY=your_service_role_key_here
```

**Important**: Use the **service role key** (not the anon key) for write operations. You can find it in:
- Supabase Dashboard → Settings → API → Service Role Key

### 4. Test the Scrapers

Test each scraper individually:

```bash
cd scrapers
python find_all_themes.py
python scrape_lego_overview.py
python check_pov.py
```

Or run all scrapers at once:

```bash
cd scrapers
python run_all_scrapers.py
```

## Scheduling Options

Since the scrapers use Playwright (which requires a browser), they cannot run directly in Supabase Edge Functions. Here are your options:

### Option 1: GitHub Actions (Recommended - Easiest & Free)

**See detailed setup guide: `GITHUB_ACTIONS_SETUP.md`**

The workflow file is already created at `.github/workflows/run-scrapers.yml`. Just:
1. Add GitHub secrets (`SUPABASE_URL` and `SUPABASE_KEY`)
2. Push to GitHub
3. Done! Runs daily at 2 AM UTC

**Pros:**
- ✅ Free for public repos, 2000 free minutes/month for private
- ✅ No server to manage
- ✅ Easy to monitor via GitHub UI
- ✅ Can manually trigger runs
- ✅ Automatic logs and artifacts

### Option 2: Local Cron Job (For Development/Testing)

If you have a server or computer that runs 24/7:

**On macOS/Linux:**
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 2 AM
0 2 * * * cd /Users/charlie/Desktop/DataWeapons/scrapers && /usr/bin/python3 run_all_scrapers.py >> /Users/charlie/Desktop/DataWeapons/scraper.log 2>&1
```

**On Windows:**
Use Task Scheduler to create a daily task that runs:
```
python C:\path\to\DataWeapons\scrapers\run_all_scrapers.py
```

### Option 3: Cloud Function (AWS Lambda, Google Cloud Functions, etc.)

You'll need to:
1. Package the scrapers with Playwright
2. Use a service that supports headless browsers
3. Set up a CloudWatch Event / Cloud Scheduler to trigger daily

**Note**: Playwright in serverless functions can be challenging due to browser binary size and cold starts.

### Option 4: Dedicated Server / VPS

Run the scrapers on a VPS (DigitalOcean, Linode, etc.) with a cron job:

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set up cron
crontab -e
# Add: 0 2 * * * cd /path/to/DataWeapons/scrapers && python3 run_all_scrapers.py
```

## Supabase Edge Function (Optional)

The `supabase/functions/run-scrapers/index.ts` function can be used to:
- Log scraper run requests
- Trigger external services (webhooks)
- Coordinate with other systems

To deploy:
```bash
supabase functions deploy run-scrapers
```

To schedule it with pg_cron (if enabled in Supabase):
```sql
SELECT cron.schedule(
  'run-scrapers-daily',
  '0 2 * * *',  -- Daily at 2 AM
  $$
  SELECT net.http_post(
    url := 'https://uxdqrswbcgkkftvompwd.supabase.co/functions/v1/run-scrapers',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY", "Content-Type": "application/json"}'::jsonb
  ) AS request_id;
  $$
);
```

## Monitoring

Check scraper runs in Supabase:
```sql
SELECT * FROM scraper_runs 
ORDER BY triggered_at DESC 
LIMIT 10;
```

## Troubleshooting

1. **"SUPABASE_KEY not set"**: Make sure you've set the environment variable
2. **Playwright errors**: Run `playwright install chromium`
3. **Import errors**: Make sure you're running from the `scrapers` directory or have the path set correctly
4. **Database errors**: Verify tables exist and you're using the service role key

## Data Flow

1. `find_all_themes.py` → `themes` table
2. `scrape_lego_overview.py` → `lego_sets_overview` table
3. `check_pov.py` → `pov_data` table

All scrapers also save CSV backups locally for redundancy.

