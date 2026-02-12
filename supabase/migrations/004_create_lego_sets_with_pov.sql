-- Create table for joined LEGO sets with POV data
-- This table pre-computes the join and calculated fields for better website performance
CREATE TABLE IF NOT EXISTS lego_sets_with_pov (
    id BIGSERIAL PRIMARY KEY,
    
    -- Fields from lego_sets_overview
    set_name TEXT NOT NULL,
    msrp NUMERIC(10, 2),
    sale_price NUMERIC(10, 2),
    piece_count INTEGER,
    url TEXT,
    item_number TEXT NOT NULL,
    price_per_piece NUMERIC(10, 4),
    
    -- Fields from pov_data
    pov_past_6_months NUMERIC(10, 2),
    pov_past_6_months_volume INTEGER,
    pov_current_listings NUMERIC(10, 2),
    pov_current_listings_volume INTEGER,
    
    -- Calculated fields
    pov_vs_msrp_profit NUMERIC(10, 2),  -- pov_current_listings - msrp
    pov_vs_sale_profit NUMERIC(10, 2),   -- pov_current_listings - sale_price
    pov_per_piece NUMERIC(10, 4),        -- pov_current_listings / piece_count
    value_ratio NUMERIC(10, 4),           -- pov_current_listings / sale_price (or msrp if sale_price is null)
    profit_margin_pct NUMERIC(5, 2),     -- ((pov_current_listings - sale_price) / sale_price) * 100
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(item_number)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sets_pov_item_number ON lego_sets_with_pov(item_number);
CREATE INDEX IF NOT EXISTS idx_sets_pov_pov_current_listings ON lego_sets_with_pov(pov_current_listings);
CREATE INDEX IF NOT EXISTS idx_sets_pov_profit_margin ON lego_sets_with_pov(profit_margin_pct);
CREATE INDEX IF NOT EXISTS idx_sets_pov_value_ratio ON lego_sets_with_pov(value_ratio);
CREATE INDEX IF NOT EXISTS idx_sets_pov_piece_count ON lego_sets_with_pov(piece_count);

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_lego_sets_with_pov_updated_at BEFORE UPDATE ON lego_sets_with_pov
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

