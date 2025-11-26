-- Create table to log scraper runs
CREATE TABLE IF NOT EXISTS scraper_runs (
    id BIGSERIAL PRIMARY KEY,
    run_type TEXT NOT NULL DEFAULT 'manual', -- 'manual', 'scheduled', 'triggered'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'triggered', 'running', 'completed', 'failed'
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    themes_count INTEGER,
    sets_count INTEGER,
    pov_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on status and triggered_at for querying recent runs
CREATE INDEX IF NOT EXISTS idx_scraper_runs_status ON scraper_runs(status);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_triggered_at ON scraper_runs(triggered_at DESC);

