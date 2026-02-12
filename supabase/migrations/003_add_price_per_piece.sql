-- Add price_per_piece column to lego_sets_overview table
ALTER TABLE lego_sets_overview 
ADD COLUMN IF NOT EXISTS price_per_piece NUMERIC(10, 4);

-- Create index on price_per_piece for faster sorting and filtering
CREATE INDEX IF NOT EXISTS idx_lego_sets_price_per_piece ON lego_sets_overview(price_per_piece);

