-- Create table for tracking page views
-- This table stores visitor analytics data for the website

CREATE TABLE IF NOT EXISTS page_views (
    id BIGSERIAL PRIMARY KEY,
    
    -- Page information
    page_name TEXT NOT NULL,  -- e.g., 'index.html', 'part-out-value.html', 'advanced.html'
    page_path TEXT,           -- Full path if available
    
    -- Visitor information (privacy-friendly, no PII)
    user_agent TEXT,          -- Browser user agent
    referrer TEXT,            -- Where they came from
    
    -- Timestamps
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Optional: IP address (hashed for privacy if needed)
    -- We'll store just the first 3 octets for privacy: 192.168.1.xxx
    ip_address TEXT,
    
    -- Session tracking (optional, using localStorage)
    session_id TEXT
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_page_views_page_name ON page_views(page_name);
CREATE INDEX IF NOT EXISTS idx_page_views_viewed_at ON page_views(viewed_at);
CREATE INDEX IF NOT EXISTS idx_page_views_session_id ON page_views(session_id);

-- Create a view for daily page view statistics
CREATE OR REPLACE VIEW page_views_daily AS
SELECT 
    page_name,
    DATE(viewed_at) as view_date,
    COUNT(*) as view_count,
    COUNT(DISTINCT session_id) as unique_sessions
FROM page_views
GROUP BY page_name, DATE(viewed_at)
ORDER BY view_date DESC, view_count DESC;

-- Create a view for total page views by page
CREATE OR REPLACE VIEW page_views_summary AS
SELECT 
    page_name,
    COUNT(*) as total_views,
    COUNT(DISTINCT session_id) as unique_sessions,
    MIN(viewed_at) as first_viewed,
    MAX(viewed_at) as last_viewed
FROM page_views
GROUP BY page_name
ORDER BY total_views DESC;

-- Add comment to document the table
COMMENT ON TABLE page_views IS 
'Stores page view analytics data for website visitor tracking. Privacy-friendly - no personally identifiable information stored.';

COMMENT ON COLUMN page_views.session_id IS 
'Session identifier stored in browser localStorage for tracking unique sessions.';

