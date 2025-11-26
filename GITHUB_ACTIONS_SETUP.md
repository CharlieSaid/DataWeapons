# GitHub Actions Setup Guide

This guide walks you through setting up GitHub Actions to run your scrapers daily.

## Prerequisites

1. Your code must be in a GitHub repository
2. You need access to your Supabase service role key
3. GitHub Actions must be enabled for your repository (enabled by default)

## Step-by-Step Setup

### Step 1: Add GitHub Secrets

1. Go to your GitHub repository
2. Click on **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** and add two secrets:

   **Secret 1:**
   - Name: `SUPABASE_URL`
   - Value: `https://uxdqrswbcgkkftvompwd.supabase.co`

   **Secret 2:**
   - Name: `SUPABASE_KEY`
   - Value: Your Supabase service role key
     - Find it in: Supabase Dashboard → Settings → API → Service Role Key
     - ⚠️ **Important**: Use the **service role key**, not the anon key

### Step 2: Verify Workflow File

The workflow file is already created at `.github/workflows/run-scrapers.yml`. It's configured to:
- Run daily at 2 AM UTC
- Install all dependencies including Playwright
- Run all scrapers in sequence
- Save logs as artifacts if something fails

### Step 3: Push to GitHub

If you haven't already, commit and push the workflow file:

```bash
git add .github/workflows/run-scrapers.yml
git commit -m "Add GitHub Actions workflow for daily scrapers"
git push
```

### Step 4: Test the Workflow

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. You should see "Run Scrapers Daily" in the workflow list
4. Click on it, then click **Run workflow** → **Run workflow** (green button)
5. Watch it execute in real-time

### Step 5: Verify It's Scheduled

1. In the **Actions** tab, you'll see scheduled runs appear automatically
2. The workflow will run daily at 2 AM UTC
3. You can check the schedule by looking at the workflow file - it shows `cron: '0 2 * * *'`

## Understanding the Schedule

The cron expression `0 2 * * *` means:
- `0` - minute 0
- `2` - hour 2 (2 AM)
- `*` - every day of month
- `*` - every month
- `*` - every day of week

**To change the schedule:**
- Edit `.github/workflows/run-scrapers.yml`
- Modify the cron expression
- Use [crontab.guru](https://crontab.guru) to help create cron expressions
- Examples:
  - `0 0 * * *` - Midnight UTC daily
  - `0 14 * * *` - 2 PM UTC daily (10 AM EST)
  - `0 2 * * 1` - 2 AM UTC every Monday

## Monitoring Runs

### View Run History
1. Go to **Actions** tab
2. Click on **Run Scrapers Daily**
3. See all past runs with their status (✅ success, ❌ failure, ⏸️ in progress)

### View Logs
1. Click on any run
2. Expand the steps to see detailed logs
3. If a run fails, download the logs artifact to see CSV files and error details

### Check Supabase
After a successful run, verify data in Supabase:
```sql
-- Check recent themes
SELECT COUNT(*) FROM themes;

-- Check recent sets
SELECT COUNT(*) FROM lego_sets_overview 
WHERE created_at > NOW() - INTERVAL '1 day';

-- Check recent POV data
SELECT COUNT(*) FROM pov_data 
WHERE created_at > NOW() - INTERVAL '1 day';
```

## Troubleshooting

### Workflow Not Running
- **Check**: Is the workflow file in `.github/workflows/` directory?
- **Check**: Did you push the file to GitHub?
- **Check**: Go to Actions tab - is the workflow listed?

### "SUPABASE_KEY not set" Error
- **Fix**: Make sure you added the secret in Settings → Secrets and variables → Actions
- **Fix**: Secret name must be exactly `SUPABASE_KEY` (case-sensitive)
- **Fix**: Make sure you're using the **service role key**, not anon key

### Playwright Installation Fails
- This is rare, but if it happens:
  - The workflow includes `playwright install-deps chromium` which should handle system dependencies
  - Check the logs in the Actions tab for specific error messages

### Scrapers Timeout
- Default timeout is 60 minutes
- If your scrapers take longer, edit the workflow file and increase `timeout-minutes`
- Consider optimizing scrapers or running them in parallel if needed

### Manual Trigger Not Working
- Make sure `workflow_dispatch` is in the `on:` section
- You need write access to the repository to trigger manually

## Cost

GitHub Actions is **free** for:
- Public repositories: Unlimited minutes
- Private repositories: 2,000 minutes/month free

Each scraper run typically takes 5-15 minutes, so you have plenty of free minutes.

## Best Practices

1. **Monitor regularly**: Check the Actions tab weekly to ensure runs are succeeding
2. **Keep secrets secure**: Never commit your Supabase key to the repository
3. **Test changes**: Use "Run workflow" to test before relying on the schedule
4. **Review logs**: Periodically check logs to catch issues early
5. **Update dependencies**: Keep `requirements.txt` up to date

## Next Steps

Once set up:
1. ✅ Workflow runs automatically daily
2. ✅ Data is saved to Supabase tables
3. ✅ CSV backups are created as artifacts
4. ✅ You can manually trigger runs anytime

You're all set! The scrapers will now run automatically every day.

