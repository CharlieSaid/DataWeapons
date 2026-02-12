"""
Shared Supabase client utility for scrapers.
"""
import os
from supabase import create_client, Client
from typing import Optional, Any, Dict, List

# Try to load from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    
    # Determine project root: go up from scrapers/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))  # scrapers/ directory
    project_root = os.path.dirname(script_dir)  # project root
    env_path = os.path.join(project_root, '.env')
    
    # Try to load from project root first
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"✅ Loaded .env file from {env_path}")
    else:
        # Fallback: try current working directory
        cwd_env = os.path.join(os.getcwd(), '.env')
        if os.path.exists(cwd_env):
            load_dotenv(cwd_env, override=True)
            print(f"✅ Loaded .env file from {cwd_env}")
        else:
            print(f"⚠️  .env file not found at {env_path} or {cwd_env}")
            print(f"   Script dir: {script_dir}")
            print(f"   Project root: {project_root}")
            print(f"   Current dir: {os.getcwd()}")
except ImportError:
    # python-dotenv not installed
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Or set SUPABASE_KEY environment variable directly.")

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://uxdqrswbcgkkftvompwd.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')  # Service role key for write operations


def clean_price_string(price_str: Any) -> Optional[float]:
    """Convert price string to float, handling currency symbols and commas."""
    if not price_str:
        return None
    
    # Handle NaN values (can occur when reading from CSV)
    if isinstance(price_str, float):
        import math
        if math.isnan(price_str):
            return None
        return float(price_str)
    
    if isinstance(price_str, int):
        return float(price_str)
    
    if isinstance(price_str, str):
        # Handle NaN string representation
        if price_str.lower() in ('nan', 'none', 'null', ''):
            return None
        # Remove currency symbols, prefixes, and commas
        cleaned = price_str.replace('US ', '').replace('$', '').replace(',', '').strip()
        try:
            num_value = float(cleaned)
            # Check for NaN
            import math
            if math.isnan(num_value):
                return None
            return num_value
        except (ValueError, AttributeError):
            return None
    
    return None


def clean_piece_count(piece_count: Any) -> Optional[int]:
    """Convert piece count to int, handling string values."""
    if not piece_count:
        return None
    
    if isinstance(piece_count, (int, float)):
        return int(piece_count)
    
    if isinstance(piece_count, str):
        # Handle cases like "Piece count not found"
        if piece_count.isdigit():
            return int(piece_count)
        # Default to 1 if piece count is not found (as per original logic)
        return 1
    
    return None


def clean_volume_string(volume_str: Any) -> Optional[int]:
    """Extract first number from volume string (e.g., '123|456' -> 123)."""
    if not volume_str:
        return None
    
    # Handle NaN values (can occur when reading from CSV)
    if isinstance(volume_str, float):
        import math
        if math.isnan(volume_str):
            return None
        return int(volume_str)
    
    if isinstance(volume_str, int):
        return volume_str
    
    if isinstance(volume_str, str):
        # Handle NaN string representation
        if volume_str.lower() in ('nan', 'none', 'null', ''):
            return None
        # Extract first number before '|'
        first_part = volume_str.split('|')[0].strip()
        try:
            num_value = float(first_part)
            # Check for NaN
            import math
            if math.isnan(num_value):
                return None
            return int(num_value)
        except (ValueError, AttributeError):
            return None
    
    return None

def get_supabase_client() -> Optional[Client]:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: Supabase client instance, or None if key is not set
    """
    if not SUPABASE_KEY:
        print("Warning: SUPABASE_KEY environment variable not set. Cannot connect to Supabase.")
        print("Please set SUPABASE_KEY to your Supabase service role key.")
        return None
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def upsert_themes(supabase: Client, themes_data: List[Dict[str, Any]]) -> bool:
    """
    Upsert themes data to Supabase.
    
    Args:
        supabase: Supabase client instance
        themes_data: List of dicts with theme_name and theme_url
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        response = supabase.table('themes').upsert(
            themes_data,
            on_conflict='theme_name'
        ).execute()
        print(f"Successfully upserted {len(themes_data)} themes to Supabase")
        return True
    except Exception as e:
        print(f"Error upserting themes: {e}")
        return False

def upsert_lego_sets(supabase: Client, sets_data: List[Dict[str, Any]]) -> bool:
    """
    Upsert LEGO sets data to Supabase.
    
    Args:
        supabase: Supabase client instance
        sets_data: List of dicts with set information
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Clean and convert data types
        cleaned_data = []
        for item in sets_data:
            cleaned_item = item.copy()
            
            # Clean prices
            cleaned_item['msrp'] = clean_price_string(cleaned_item.get('msrp'))
            cleaned_item['sale_price'] = clean_price_string(cleaned_item.get('sale_price'))
            
            # Clean piece count
            cleaned_item['piece_count'] = clean_piece_count(cleaned_item.get('piece_count'))
            
            # Calculate price_per_piece: use sale_price if available, otherwise msrp
            price_to_use = cleaned_item.get('sale_price') if cleaned_item.get('sale_price') is not None else cleaned_item.get('msrp')
            piece_count = cleaned_item.get('piece_count')
            
            if price_to_use is not None and piece_count is not None and piece_count > 0:
                cleaned_item['price_per_piece'] = round(price_to_use / piece_count, 4)
            else:
                cleaned_item['price_per_piece'] = None
            
            cleaned_data.append(cleaned_item)
        
        # Deduplicate by item_number - keep the last occurrence of each item_number
        seen_item_numbers = {}
        items_without_number = []
        for item in cleaned_data:
            item_number = item.get('item_number')
            if item_number:
                seen_item_numbers[item_number] = item
            else:
                items_without_number.append(item)
        
        deduplicated_data = list(seen_item_numbers.values())
        
        if items_without_number:
            print(f"⚠️  Skipping {len(items_without_number)} items without item_number")
        
        if len(deduplicated_data) < len(cleaned_data):
            print(f"⚠️  Removed {len(cleaned_data) - len(deduplicated_data)} duplicate item_number entries")
        
        response = supabase.table('lego_sets_overview').upsert(
            deduplicated_data,
            on_conflict='item_number'
        ).execute()
        print(f"Successfully upserted {len(deduplicated_data)} LEGO sets to Supabase")
        return True
    except Exception as e:
        print(f"Error upserting LEGO sets: {e}")
        return False

def upsert_pov_data(supabase: Client, pov_data: List[Dict[str, Any]], wipe_table: bool = True) -> bool:
    """
    Upsert POV (Part-Out-Value) data to Supabase.
    
    Args:
        supabase: Supabase client instance
        pov_data: List of dicts with POV information
        wipe_table: If True, delete all existing data from pov_data table before uploading
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Wipe the table first if requested (ensures all data is current)
        if wipe_table:
            print("🗑️  Wiping existing pov_data table to ensure all data is current...")
            try:
                # Delete all rows from pov_data table
                # Fetch all item_numbers first, then delete them
                # This ensures we delete all rows reliably
                existing_response = supabase.table('pov_data').select('item_number').execute()
                
                if existing_response.data and len(existing_response.data) > 0:
                    item_numbers_to_delete = [row['item_number'] for row in existing_response.data if row.get('item_number')]
                    
                    if item_numbers_to_delete:
                        # Delete in batches to avoid query size limits
                        batch_size = 1000
                        for i in range(0, len(item_numbers_to_delete), batch_size):
                            batch = item_numbers_to_delete[i:i + batch_size]
                            delete_response = supabase.table('pov_data').delete().in_('item_number', batch).execute()
                        print(f"✅ Cleared {len(item_numbers_to_delete)} existing records from pov_data table")
                    else:
                        print("ℹ️  pov_data table was already empty")
                else:
                    print("ℹ️  pov_data table was already empty")
            except Exception as e:
                print(f"⚠️  Warning: Could not clear pov_data table: {e}")
                print("   Continuing with upsert (may result in stale data)")
        
        # Clean and convert data types, filtering out items with NA/None values
        cleaned_data = []
        skipped_na_count = 0
        
        for item in pov_data:
            cleaned_item = item.copy()
            
            # Clean prices
            pov_past_6_months = clean_price_string(cleaned_item.get('pov_past_6_months'))
            pov_current_listings = clean_price_string(cleaned_item.get('pov_current_listings'))
            
            # Clean volumes
            past_volume = clean_volume_string(cleaned_item.get('pov_past_6_months_volume'))
            current_volume = clean_volume_string(cleaned_item.get('pov_current_listings_volume'))
            
            # Filter out items with NA/None values in critical POV fields
            # We require at least pov_current_listings to have a value
            if pov_current_listings is None:
                skipped_na_count += 1
                item_num = cleaned_item.get('item_number', 'unknown')
                print(f"⚠️  Skipping {item_num} - pov_current_listings is NA/None")
                continue
            
            # Set cleaned values
            cleaned_item['pov_past_6_months'] = pov_past_6_months
            cleaned_item['pov_current_listings'] = pov_current_listings
            cleaned_item['pov_past_6_months_volume'] = past_volume
            cleaned_item['pov_current_listings_volume'] = current_volume
            
            cleaned_data.append(cleaned_item)
        
        if skipped_na_count > 0:
            print(f"⚠️  Skipped {skipped_na_count} items with NA/None values in POV fields")

        # Deduplicate by item_number - keep the last occurrence of each item_number
        # This prevents the "ON CONFLICT DO UPDATE command cannot affect row a second time" error
        seen_item_numbers = {}
        items_without_number = []
        for item in cleaned_data:
            item_number = item.get('item_number')
            if item_number:
                seen_item_numbers[item_number] = item
            else:
                items_without_number.append(item)
        
        deduplicated_data = list(seen_item_numbers.values())
        
        if items_without_number:
            print(f"⚠️  Skipping {len(items_without_number)} POV items without item_number")
        
        if len(deduplicated_data) < len(cleaned_data):
            print(f"⚠️  Removed {len(cleaned_data) - len(deduplicated_data)} duplicate item_number entries from POV data")

        if not deduplicated_data:
            print("⚠️  No valid POV data to upload (all items had NA values or were filtered out)")
            return True  # Return True since we successfully processed (just had no data)
        
        # Insert all data (since we wiped the table, we can use insert instead of upsert)
        if wipe_table:
            response = supabase.table('pov_data').insert(deduplicated_data).execute()
            print(f"✅ Successfully inserted {len(deduplicated_data)} POV records to Supabase (table was wiped)")
        else:
            response = supabase.table('pov_data').upsert(
                deduplicated_data,
                on_conflict='item_number'
            ).execute()
            print(f"✅ Successfully upserted {len(deduplicated_data)} POV records to Supabase")
        return True
    except Exception as e:
        print(f"Error upserting POV data: {e}")
        return False

def rebuild_lego_sets_with_pov(supabase: Client) -> bool:
    """
    Join lego_sets_overview with pov_data and calculate derived fields.
    Stores the result in lego_sets_with_pov table.
    
    This function should be called after both sets and POV data have been updated.
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("Starting to rebuild lego_sets_with_pov table...")
        
        # Fetch all sets data
        sets_response = supabase.table('lego_sets_overview').select('*').execute()
        if not sets_response.data:
            print("⚠️  No sets data found in lego_sets_overview")
            return False
        
        sets_data = sets_response.data
        print(f"Found {len(sets_data)} sets in lego_sets_overview")
        
        # Fetch all POV data
        pov_response = supabase.table('pov_data').select('*').execute()
        if not pov_response.data:
            print("⚠️  No POV data found in pov_data")
            # Still create records for sets without POV data
            pov_data = []
        else:
            pov_data = pov_response.data
            print(f"Found {len(pov_data)} POV records")
        
        # Create a lookup dictionary for POV data by item_number
        pov_lookup = {item['item_number']: item for item in pov_data}
        
        # Join and calculate fields
        joined_data = []
        for set_item in sets_data:
            item_number = set_item.get('item_number')
            if not item_number:
                continue
            
            pov_item = pov_lookup.get(item_number)
            
            
            # Helper function to safely convert to int
            def to_int(value: Any) -> Optional[int]:
                if value is None:
                    return None
                if isinstance(value, (int, float)):
                    import math
                    if math.isnan(value):
                        return None
                    return int(value)
                if isinstance(value, str):
                    if value.lower() in ('nan', 'none', 'null', ''):
                        return None
                    try:
                        num_value = float(value)
                        import math
                        if math.isnan(num_value):
                            return None
                        return int(num_value)
                    except (ValueError, AttributeError):
                        return None
                return None
            
            # Start with set data, converting types
            joined_item = {
                'item_number': item_number,
                'set_name': set_item.get('set_name'),
                'msrp': clean_price_string(set_item.get('msrp')),
                'sale_price': clean_price_string(set_item.get('sale_price')),
                'piece_count': to_int(set_item.get('piece_count')),
                'url': set_item.get('url'),
                'price_per_piece': clean_price_string(set_item.get('price_per_piece')),
            }
            
            # Add POV data if available, converting types
            if pov_item:
                joined_item['pov_past_6_months'] = clean_price_string(pov_item.get('pov_past_6_months'))
                joined_item['pov_past_6_months_volume'] = to_int(pov_item.get('pov_past_6_months_volume'))
                joined_item['pov_current_listings'] = clean_price_string(pov_item.get('pov_current_listings'))
                joined_item['pov_current_listings_volume'] = to_int(pov_item.get('pov_current_listings_volume'))
            else:
                joined_item['pov_past_6_months'] = None
                joined_item['pov_past_6_months_volume'] = None
                joined_item['pov_current_listings'] = None
                joined_item['pov_current_listings_volume'] = None
            
            # Calculate derived fields for BOTH current listings and past 6 months
            pov_current = joined_item.get('pov_current_listings')
            pov_past_6m = joined_item.get('pov_past_6_months')
            msrp = joined_item.get('msrp')
            sale_price = joined_item.get('sale_price')
            piece_count = joined_item.get('piece_count')
            
            # Helper function to calculate derived fields for a given POV value
            def calculate_derived_fields(pov_value, suffix):
                """Calculate all derived fields for a given POV value."""
                fields = {}
                
                # pov_vs_msrp_profit
                if pov_value is not None and msrp is not None:
                    fields[f'pov_vs_msrp_profit{suffix}'] = round(pov_value - msrp, 2)
                else:
                    fields[f'pov_vs_msrp_profit{suffix}'] = None
                
                # pov_vs_sale_profit
                if pov_value is not None and sale_price is not None:
                    fields[f'pov_vs_sale_profit{suffix}'] = round(pov_value - sale_price, 2)
                else:
                    fields[f'pov_vs_sale_profit{suffix}'] = None
                
                # pov_per_piece
                if pov_value is not None and piece_count is not None and piece_count > 0:
                    fields[f'pov_per_piece{suffix}'] = round(pov_value / piece_count, 4)
                else:
                    fields[f'pov_per_piece{suffix}'] = None
                
                # value_ratio (use sale_price if available, otherwise msrp)
                price_to_compare = sale_price if sale_price is not None else msrp
                if pov_value is not None and price_to_compare is not None and price_to_compare > 0:
                    fields[f'value_ratio{suffix}'] = round(pov_value / price_to_compare, 4)
                else:
                    fields[f'value_ratio{suffix}'] = None
                
                # profit_margin_pct
                if pov_value is not None and sale_price is not None and sale_price > 0:
                    fields[f'profit_margin_pct{suffix}'] = round(((pov_value - sale_price) / sale_price) * 100, 2)
                else:
                    fields[f'profit_margin_pct{suffix}'] = None
                
                # profit_pct: Percentage of sale price that the profit represents
                # Formula: ((POV - Sale Price) / Sale Price) * 100
                if pov_value is not None and sale_price is not None and sale_price > 0:
                    profit_pct = ((pov_value - sale_price) / sale_price) * 100
                    fields[f'profit_pct{suffix}'] = round(profit_pct, 2)
                else:
                    fields[f'profit_pct{suffix}'] = None
                
                return fields
            
            # Calculate for current listings
            current_fields = calculate_derived_fields(pov_current, '_current')
            joined_item.update(current_fields)
            
            # Calculate for past 6 months
            past_6m_fields = calculate_derived_fields(pov_past_6m, '_past_6m')
            joined_item.update(past_6m_fields)
            
            # For backward compatibility, also set the original fields to use current listings
            # (these will be used by default, but frontend can switch to _past_6m versions)
            joined_item['pov_vs_msrp_profit'] = joined_item.get('pov_vs_msrp_profit_current')
            joined_item['pov_vs_sale_profit'] = joined_item.get('pov_vs_sale_profit_current')
            joined_item['pov_per_piece'] = joined_item.get('pov_per_piece_current')
            joined_item['value_ratio'] = joined_item.get('value_ratio_current')
            joined_item['profit_margin_pct'] = joined_item.get('profit_margin_pct_current')
            joined_item['profit_pct'] = joined_item.get('profit_pct_current')
            
            joined_data.append(joined_item)
        
        # Upsert to lego_sets_with_pov table
        if joined_data:
            response = supabase.table('lego_sets_with_pov').upsert(
                joined_data,
                on_conflict='item_number'
            ).execute()
            print(f"✅ Successfully upserted {len(joined_data)} records to lego_sets_with_pov")
            
            # Count how many have POV data
            with_pov = sum(1 for item in joined_data if item.get('pov_current_listings') is not None)
            print(f"   - {with_pov} records have POV data")
            print(f"   - {len(joined_data) - with_pov} records without POV data")
            return True
        else:
            print("⚠️  No data to upsert")
            return False
            
    except Exception as e:
        print(f"Error rebuilding lego_sets_with_pov: {e}")
        import traceback
        traceback.print_exc()
        return False

