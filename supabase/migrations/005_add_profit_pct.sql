-- Add profit_pct column to lego_sets_with_pov table
-- This column represents the percentage of the sale price that the part-out-value profit represents
-- Formula: ((pov_current_listings - sale_price) / sale_price) * 100
-- Example: If set costs $50 and POV is $150, profit is $100, which is 200% of cost

-- Add the column
ALTER TABLE lego_sets_with_pov
ADD COLUMN IF NOT EXISTS profit_pct NUMERIC(10, 2);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_sets_pov_profit_pct ON lego_sets_with_pov(profit_pct);

-- Populate the column with calculated values from existing data
-- Only calculate where both pov_current_listings and sale_price are available and sale_price > 0
UPDATE lego_sets_with_pov
SET profit_pct = ROUND(((pov_current_listings - sale_price) / sale_price) * 100, 2)
WHERE pov_current_listings IS NOT NULL
  AND sale_price IS NOT NULL
  AND sale_price > 0;

-- Set profit_pct to NULL where calculation is not possible
UPDATE lego_sets_with_pov
SET profit_pct = NULL
WHERE pov_current_listings IS NULL
   OR sale_price IS NULL
   OR sale_price <= 0;

-- Add comment to document the column
COMMENT ON COLUMN lego_sets_with_pov.profit_pct IS 
'Percentage of sale price that the part-out-value profit represents. Calculated as ((pov_current_listings - sale_price) / sale_price) * 100. Example: Set costs $50, POV is $150, profit is $100 (200% of cost).';

