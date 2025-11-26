"""
Shared Supabase client utility for scrapers.
"""
import os
from supabase import create_client, Client
from typing import Optional

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://uxdqrswbcgkkftvompwd.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')  # Service role key for write operations

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

def upsert_themes(supabase: Client, themes_data: list) -> bool:
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

def upsert_lego_sets(supabase: Client, sets_data: list) -> bool:
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
            # Convert msrp and sale_price to float, handling string values like "$79.99"
            if 'msrp' in cleaned_item and cleaned_item['msrp']:
                if isinstance(cleaned_item['msrp'], str):
                    cleaned_item['msrp'] = float(cleaned_item['msrp'].replace('$', '').replace(',', ''))
                else:
                    cleaned_item['msrp'] = float(cleaned_item['msrp'])
            else:
                cleaned_item['msrp'] = None
                
            if 'sale_price' in cleaned_item and cleaned_item['sale_price']:
                if isinstance(cleaned_item['sale_price'], str):
                    cleaned_item['sale_price'] = float(cleaned_item['sale_price'].replace('$', '').replace(',', ''))
                else:
                    cleaned_item['sale_price'] = float(cleaned_item['sale_price'])
            else:
                cleaned_item['sale_price'] = None
            
            # Convert piece_count to int
            if 'piece_count' in cleaned_item and cleaned_item['piece_count']:
                if isinstance(cleaned_item['piece_count'], str):
                    # Handle cases like "Piece count not found"
                    if cleaned_item['piece_count'].isdigit():
                        cleaned_item['piece_count'] = int(cleaned_item['piece_count'])
                    else:
                        cleaned_item['piece_count'] = None
                else:
                    cleaned_item['piece_count'] = int(cleaned_item['piece_count'])
            else:
                cleaned_item['piece_count'] = None
            
            cleaned_data.append(cleaned_item)
        
        response = supabase.table('lego_sets_overview').upsert(
            cleaned_data,
            on_conflict='item_number'
        ).execute()
        print(f"Successfully upserted {len(cleaned_data)} LEGO sets to Supabase")
        return True
    except Exception as e:
        print(f"Error upserting LEGO sets: {e}")
        return False

def upsert_pov_data(supabase: Client, pov_data: list) -> bool:
    """
    Upsert POV (Part-Out-Value) data to Supabase.
    
    Args:
        supabase: Supabase client instance
        pov_data: List of dicts with POV information
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        response = supabase.table('pov_data').upsert(
            pov_data,
            on_conflict='item_number'
        ).execute()
        print(f"Successfully upserted {len(pov_data)} POV records to Supabase")
        return True
    except Exception as e:
        print(f"Error upserting POV data: {e}")
        return False

