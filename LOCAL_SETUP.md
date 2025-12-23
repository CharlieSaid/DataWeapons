# Local Development Setup

## Setting Up Supabase Connection Locally

To run scrapers locally and save data to Supabase, you need to set your Supabase credentials.

### Option 1: Using .env file (Recommended)

1. **Install python-dotenv** (already added to requirements.txt):
   ```bash
   pip install python-dotenv
   ```

2. **Create a `.env` file** in the project root (`/Users/charlie/Desktop/DataWeapons/.env`):
   ```bash
   SUPABASE_URL=https://uxdqrswbcgkkftvompwd.supabase.co
   SUPABASE_KEY=your_service_role_key_here
   ```

3. **Get your Supabase service role key**:
   - Go to [Supabase Dashboard](https://supabase.com/dashboard)
   - Select your project
   - Go to Settings → API
   - Copy the **Service Role Key** (NOT the anon key!)
   - Paste it into your `.env` file

4. **The `.env` file is already in `.gitignore`**, so it won't be committed to git.

### Option 2: Using Environment Variables Directly

If you prefer not to use a `.env` file, you can set environment variables in your shell:

**On macOS/Linux:**
```bash
export SUPABASE_URL="https://uxdqrswbcgkkftvompwd.supabase.co"
export SUPABASE_KEY="your_service_role_key_here"
```

**To make it persistent**, add these lines to your `~/.zshrc` (or `~/.bashrc`):
```bash
export SUPABASE_URL="https://uxdqrswbcgkkftvompwd.supabase.co"
export SUPABASE_KEY="your_service_role_key_here"
```

Then reload your shell:
```bash
source ~/.zshrc
```

### Verify It Works

Run a scraper locally:
```bash
cd scrapers
python3 find_all_themes.py
```

You should see:
- ✅ "themes_list.csv saved successfully"
- ✅ "Themes successfully saved to Supabase" (instead of the warning)

If you still see the warning, check:
1. Is the `.env` file in the project root (not in the `scrapers/` folder)?
2. Did you install `python-dotenv`? (`pip install python-dotenv`)
3. Is `SUPABASE_KEY` set correctly? (Make sure it's the service role key, not anon key)

