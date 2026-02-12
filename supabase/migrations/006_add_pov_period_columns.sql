-- Add columns for derived fields calculated from both current listings and past 6 months
-- This allows users to toggle between viewing stats based on current vs historical POV values
-- All existing derived fields are kept for backward compatibility (they use current listings)

-- Add columns for current listings derived fields
ALTER TABLE lego_sets_with_pov
ADD COLUMN IF NOT EXISTS profit_pct_current NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS pov_vs_sale_profit_current NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS pov_vs_msrp_profit_current NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS pov_per_piece_current NUMERIC(10, 4),
ADD COLUMN IF NOT EXISTS value_ratio_current NUMERIC(10, 4),
ADD COLUMN IF NOT EXISTS profit_margin_pct_current NUMERIC(5, 2);

-- Add columns for past 6 months derived fields
ALTER TABLE lego_sets_with_pov
ADD COLUMN IF NOT EXISTS profit_pct_past_6m NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS pov_vs_sale_profit_past_6m NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS pov_vs_msrp_profit_past_6m NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS pov_per_piece_past_6m NUMERIC(10, 4),
ADD COLUMN IF NOT EXISTS value_ratio_past_6m NUMERIC(10, 4),
ADD COLUMN IF NOT EXISTS profit_margin_pct_past_6m NUMERIC(5, 2);

-- Create indexes for current listings derived fields (most commonly used)
CREATE INDEX IF NOT EXISTS idx_sets_pov_profit_pct_current ON lego_sets_with_pov(profit_pct_current);
CREATE INDEX IF NOT EXISTS idx_sets_pov_vs_sale_profit_current ON lego_sets_with_pov(pov_vs_sale_profit_current);
CREATE INDEX IF NOT EXISTS idx_sets_pov_per_piece_current ON lego_sets_with_pov(pov_per_piece_current);

-- Create indexes for past 6 months derived fields
CREATE INDEX IF NOT EXISTS idx_sets_pov_profit_pct_past_6m ON lego_sets_with_pov(profit_pct_past_6m);
CREATE INDEX IF NOT EXISTS idx_sets_pov_vs_sale_profit_past_6m ON lego_sets_with_pov(pov_vs_sale_profit_past_6m);
CREATE INDEX IF NOT EXISTS idx_sets_pov_per_piece_past_6m ON lego_sets_with_pov(pov_per_piece_past_6m);

-- Populate current listings derived fields from existing data
-- profit_pct_current: ((pov_current_listings - sale_price) / sale_price) * 100
UPDATE lego_sets_with_pov
SET profit_pct_current = ROUND(((pov_current_listings - sale_price) / sale_price) * 100, 2)
WHERE pov_current_listings IS NOT NULL
  AND sale_price IS NOT NULL
  AND sale_price > 0;

-- pov_vs_sale_profit_current: pov_current_listings - sale_price
UPDATE lego_sets_with_pov
SET pov_vs_sale_profit_current = ROUND(pov_current_listings - sale_price, 2)
WHERE pov_current_listings IS NOT NULL
  AND sale_price IS NOT NULL;

-- pov_vs_msrp_profit_current: pov_current_listings - msrp
UPDATE lego_sets_with_pov
SET pov_vs_msrp_profit_current = ROUND(pov_current_listings - msrp, 2)
WHERE pov_current_listings IS NOT NULL
  AND msrp IS NOT NULL;

-- pov_per_piece_current: pov_current_listings / piece_count
UPDATE lego_sets_with_pov
SET pov_per_piece_current = ROUND(pov_current_listings / piece_count::NUMERIC, 4)
WHERE pov_current_listings IS NOT NULL
  AND piece_count IS NOT NULL
  AND piece_count > 0;

-- value_ratio_current: pov_current_listings / sale_price (or msrp if sale_price is null)
UPDATE lego_sets_with_pov
SET value_ratio_current = ROUND(
    pov_current_listings / NULLIF(
        COALESCE(sale_price, msrp),
        0
    ),
    4
)
WHERE pov_current_listings IS NOT NULL
  AND COALESCE(sale_price, msrp) IS NOT NULL
  AND COALESCE(sale_price, msrp) > 0;

-- profit_margin_pct_current: ((pov_current_listings - sale_price) / sale_price) * 100
UPDATE lego_sets_with_pov
SET profit_margin_pct_current = ROUND(((pov_current_listings - sale_price) / sale_price) * 100, 2)
WHERE pov_current_listings IS NOT NULL
  AND sale_price IS NOT NULL
  AND sale_price > 0;

-- Populate past 6 months derived fields from existing data
-- profit_pct_past_6m: ((pov_past_6_months - sale_price) / sale_price) * 100
UPDATE lego_sets_with_pov
SET profit_pct_past_6m = ROUND(((pov_past_6_months - sale_price) / sale_price) * 100, 2)
WHERE pov_past_6_months IS NOT NULL
  AND sale_price IS NOT NULL
  AND sale_price > 0;

-- pov_vs_sale_profit_past_6m: pov_past_6_months - sale_price
UPDATE lego_sets_with_pov
SET pov_vs_sale_profit_past_6m = ROUND(pov_past_6_months - sale_price, 2)
WHERE pov_past_6_months IS NOT NULL
  AND sale_price IS NOT NULL;

-- pov_vs_msrp_profit_past_6m: pov_past_6_months - msrp
UPDATE lego_sets_with_pov
SET pov_vs_msrp_profit_past_6m = ROUND(pov_past_6_months - msrp, 2)
WHERE pov_past_6_months IS NOT NULL
  AND msrp IS NOT NULL;

-- pov_per_piece_past_6m: pov_past_6_months / piece_count
UPDATE lego_sets_with_pov
SET pov_per_piece_past_6m = ROUND(pov_past_6_months / piece_count::NUMERIC, 4)
WHERE pov_past_6_months IS NOT NULL
  AND piece_count IS NOT NULL
  AND piece_count > 0;

-- value_ratio_past_6m: pov_past_6_months / sale_price (or msrp if sale_price is null)
UPDATE lego_sets_with_pov
SET value_ratio_past_6m = ROUND(
    pov_past_6_months / NULLIF(
        COALESCE(sale_price, msrp),
        0
    ),
    4
)
WHERE pov_past_6_months IS NOT NULL
  AND COALESCE(sale_price, msrp) IS NOT NULL
  AND COALESCE(sale_price, msrp) > 0;

-- profit_margin_pct_past_6m: ((pov_past_6_months - sale_price) / sale_price) * 100
UPDATE lego_sets_with_pov
SET profit_margin_pct_past_6m = ROUND(((pov_past_6_months - sale_price) / sale_price) * 100, 2)
WHERE pov_past_6_months IS NOT NULL
  AND sale_price IS NOT NULL
  AND sale_price > 0;

-- Set NULL values where calculations are not possible (for current listings)
UPDATE lego_sets_with_pov
SET profit_pct_current = NULL
WHERE pov_current_listings IS NULL
   OR sale_price IS NULL
   OR sale_price <= 0;

UPDATE lego_sets_with_pov
SET pov_vs_sale_profit_current = NULL
WHERE pov_current_listings IS NULL
   OR sale_price IS NULL;

UPDATE lego_sets_with_pov
SET pov_vs_msrp_profit_current = NULL
WHERE pov_current_listings IS NULL
   OR msrp IS NULL;

UPDATE lego_sets_with_pov
SET pov_per_piece_current = NULL
WHERE pov_current_listings IS NULL
   OR piece_count IS NULL
   OR piece_count <= 0;

UPDATE lego_sets_with_pov
SET value_ratio_current = NULL
WHERE pov_current_listings IS NULL
   OR COALESCE(sale_price, msrp) IS NULL
   OR COALESCE(sale_price, msrp) <= 0;

UPDATE lego_sets_with_pov
SET profit_margin_pct_current = NULL
WHERE pov_current_listings IS NULL
   OR sale_price IS NULL
   OR sale_price <= 0;

-- Set NULL values where calculations are not possible (for past 6 months)
UPDATE lego_sets_with_pov
SET profit_pct_past_6m = NULL
WHERE pov_past_6_months IS NULL
   OR sale_price IS NULL
   OR sale_price <= 0;

UPDATE lego_sets_with_pov
SET pov_vs_sale_profit_past_6m = NULL
WHERE pov_past_6_months IS NULL
   OR sale_price IS NULL;

UPDATE lego_sets_with_pov
SET pov_vs_msrp_profit_past_6m = NULL
WHERE pov_past_6_months IS NULL
   OR msrp IS NULL;

UPDATE lego_sets_with_pov
SET pov_per_piece_past_6m = NULL
WHERE pov_past_6_months IS NULL
   OR piece_count IS NULL
   OR piece_count <= 0;

UPDATE lego_sets_with_pov
SET value_ratio_past_6m = NULL
WHERE pov_past_6_months IS NULL
   OR COALESCE(sale_price, msrp) IS NULL
   OR COALESCE(sale_price, msrp) <= 0;

UPDATE lego_sets_with_pov
SET profit_margin_pct_past_6m = NULL
WHERE pov_past_6_months IS NULL
   OR sale_price IS NULL
   OR sale_price <= 0;

-- Add comments to document the columns
COMMENT ON COLUMN lego_sets_with_pov.profit_pct_current IS 
'Percentage of sale price that the part-out-value profit represents, calculated from current listings. Formula: ((pov_current_listings - sale_price) / sale_price) * 100';

COMMENT ON COLUMN lego_sets_with_pov.profit_pct_past_6m IS 
'Percentage of sale price that the part-out-value profit represents, calculated from past 6 months data. Formula: ((pov_past_6_months - sale_price) / sale_price) * 100';

COMMENT ON COLUMN lego_sets_with_pov.pov_vs_sale_profit_current IS 
'Profit from part-out-value minus sale price, calculated from current listings. Formula: pov_current_listings - sale_price';

COMMENT ON COLUMN lego_sets_with_pov.pov_vs_sale_profit_past_6m IS 
'Profit from part-out-value minus sale price, calculated from past 6 months data. Formula: pov_past_6_months - sale_price';

COMMENT ON COLUMN lego_sets_with_pov.pov_vs_msrp_profit_current IS 
'Profit from part-out-value minus MSRP, calculated from current listings. Formula: pov_current_listings - msrp';

COMMENT ON COLUMN lego_sets_with_pov.pov_vs_msrp_profit_past_6m IS 
'Profit from part-out-value minus MSRP, calculated from past 6 months data. Formula: pov_past_6_months - msrp';

COMMENT ON COLUMN lego_sets_with_pov.pov_per_piece_current IS 
'Part-out-value per piece, calculated from current listings. Formula: pov_current_listings / piece_count';

COMMENT ON COLUMN lego_sets_with_pov.pov_per_piece_past_6m IS 
'Part-out-value per piece, calculated from past 6 months data. Formula: pov_past_6_months / piece_count';

COMMENT ON COLUMN lego_sets_with_pov.value_ratio_current IS 
'Ratio of part-out-value to sale price (or MSRP if sale_price is null), calculated from current listings. Formula: pov_current_listings / COALESCE(sale_price, msrp)';

COMMENT ON COLUMN lego_sets_with_pov.value_ratio_past_6m IS 
'Ratio of part-out-value to sale price (or MSRP if sale_price is null), calculated from past 6 months data. Formula: pov_past_6_months / COALESCE(sale_price, msrp)';

COMMENT ON COLUMN lego_sets_with_pov.profit_margin_pct_current IS 
'Profit margin percentage, calculated from current listings. Formula: ((pov_current_listings - sale_price) / sale_price) * 100';

COMMENT ON COLUMN lego_sets_with_pov.profit_margin_pct_past_6m IS 
'Profit margin percentage, calculated from past 6 months data. Formula: ((pov_past_6_months - sale_price) / sale_price) * 100';

