-- Create table for themes data
CREATE TABLE IF NOT EXISTS themes (
    id BIGSERIAL PRIMARY KEY,
    theme_name TEXT NOT NULL,
    theme_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(theme_name)
);

-- Create index on theme_name for faster lookups
CREATE INDEX IF NOT EXISTS idx_themes_name ON themes(theme_name);

-- Create table for LEGO sets overview
CREATE TABLE IF NOT EXISTS lego_sets_overview (
    id BIGSERIAL PRIMARY KEY,
    set_name TEXT NOT NULL,
    msrp NUMERIC(10, 2),
    sale_price NUMERIC(10, 2),
    piece_count INTEGER,
    url TEXT,
    item_number TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(item_number)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_lego_sets_item_number ON lego_sets_overview(item_number);
CREATE INDEX IF NOT EXISTS idx_lego_sets_msrp ON lego_sets_overview(msrp);
CREATE INDEX IF NOT EXISTS idx_lego_sets_piece_count ON lego_sets_overview(piece_count);

-- Create table for POV (Part-Out-Value) data
CREATE TABLE IF NOT EXISTS pov_data (
    id BIGSERIAL PRIMARY KEY,
    item_number TEXT NOT NULL,
    pov_past_6_months TEXT,
    pov_past_6_months_volume TEXT,
    pov_current_listings TEXT,
    pov_current_listings_volume TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(item_number)
);

-- Create index on item_number for faster lookups
CREATE INDEX IF NOT EXISTS idx_pov_item_number ON pov_data(item_number);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_themes_updated_at BEFORE UPDATE ON themes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lego_sets_overview_updated_at BEFORE UPDATE ON lego_sets_overview
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pov_data_updated_at BEFORE UPDATE ON pov_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

