#!/usr/bin/env python3
"""
Main script to run all scrapers in sequence.
This script should be executed daily via cron or a scheduled task.
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

# Add the scrapers directory to the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from find_all_themes import find_all_themes
from scrape_lego_overview import scrape_lego
from check_pov import check_pov_custom
import pandas as pd

# Import supabase_client for uploads
try:
    from supabase_client import (
        get_supabase_client,
        upsert_themes,
        upsert_lego_sets,
        upsert_pov_data,
        rebuild_lego_sets_with_pov
    )
except ImportError:
    print("Error importing supabase_client!")
    # Fallback if supabase_client is not available
    def get_supabase_client():
        return None
    def upsert_themes(*args, **kwargs):
        return False
    def upsert_lego_sets(*args, **kwargs):
        return False
    def upsert_pov_data(*args, **kwargs):
        return False
    def rebuild_lego_sets_with_pov(*args, **kwargs):
        return False

# Constants
THEMES_CSV = "themes_list.csv"
SETS_CSV = "lego_store_overview.csv"
POV_CSV = "pov_data.csv"
MIN_PIECE_COUNT = 10

def clean_price_string(price_str: Any) -> Optional[float]:
    """Convert price string to float, handling currency symbols and commas."""
    if pd.isna(price_str) or str(price_str) == 'None':
        return None
    try:
        cleaned = str(price_str).replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def save_to_csv(data: List[Dict[str, Any]], filepath: str, description: str) -> bool:
    """Save data to CSV file."""
    try:
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        print(f"✅ Saved {len(df)} {description} to {filepath}")
        return True
    except Exception as e:
        print(f"❌ Failed to save {description} to {filepath}: {e}")
        return False


def upload_to_supabase(
    supabase: Optional[Any],
    data: List[Dict[str, Any]],
    upload_func: Callable,
    description: str
) -> bool:
    """Upload data to Supabase using the provided upload function."""
    if not supabase:
        print(f"⚠️  Supabase client not available, skipping {description} database write")
        return False
    
    if not data:
        print(f"⚠️  No {description} to upload")
        return False
    
    success = upload_func(supabase, data)
    if success:
        print(f"✅ {description} successfully saved to Supabase")
    else:
        print(f"❌ Failed to save {description} to Supabase")
    return success


def load_themes_from_csv(filepath: str) -> Optional[List[str]]:
    """Load theme names from CSV file."""
    if not os.path.exists(filepath):
        return None
    
    try:
        themes_df = pd.read_csv(filepath)
        theme_names = themes_df["theme_name"].tolist()
        print(f"✅ Loaded {len(theme_names)} themes from existing CSV")
        return theme_names
    except Exception as e:
        print(f"❌ Error loading themes from CSV: {e}")
        return None


def clean_sets_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and filter sets dataframe."""
    # Remove duplicates
    df = df.drop_duplicates(keep='first')
    
    # Drop rows where item_number is None
    df = df[df['item_number'].notna()]
    
    # Filter by piece_count if column exists
    if 'piece_count' in df.columns:
        df = df[df['piece_count'] != 'Piece count not found']
        df['piece_count'] = pd.to_numeric(df['piece_count'], errors='coerce')
        df = df[df['piece_count'] >= MIN_PIECE_COUNT]
    
    return df


def step1_find_themes() -> Optional[List[str]]:
    """Step 1: Find all themes and return theme names."""
    print("\n[1/4] Running find_all_themes...")
    print("-" * 60)
    
    themes_data = asyncio.run(find_all_themes())
    
    if themes_data:
        print(f"✅ Found {len(themes_data)} themes")
        save_to_csv(themes_data, THEMES_CSV, "themes")
        
        supabase = get_supabase_client()
        upload_to_supabase(supabase, themes_data, upsert_themes, "Themes")
        
        theme_names = [theme['theme_name'] for theme in themes_data]
        return theme_names
    else:
        print("⚠️  No themes found. Checking for existing themes_list.csv...")
        theme_names = load_themes_from_csv(THEMES_CSV)
        
        if not theme_names:
            print("❌ No themes found and no existing themes_list.csv available")
            print("   Cannot proceed with scraping LEGO sets without themes")
            return None
        
        return theme_names


def step2_scrape_sets(theme_names: List[str]) -> Optional[List[Dict[str, Any]]]:
    """Step 2: Scrape LEGO sets for given themes."""
    print("\n[2/4] Running scrape_lego_overview...")
    print("-" * 60)
    print(f"Scraping {len(theme_names)} themes")
    
    sets_data = asyncio.run(scrape_lego(themes=theme_names))
    
    if not sets_data:
        print("⚠️  No sets found.")
        return None
    
    print(f"✅ Found {len(sets_data)} sets")
    
    # Prepare DataFrame for CSV
    sets_df = pd.DataFrame(sets_data)
    sets_df['msrp'] = sets_df['msrp'].apply(clean_price_string)
    sets_df['sale_price'] = sets_df['sale_price'].apply(clean_price_string)
    
    save_to_csv(sets_df.to_dict('records'), SETS_CSV, "sets")
    
    supabase = get_supabase_client()
    upload_to_supabase(supabase, sets_data, upsert_lego_sets, "LEGO sets")
    
    return sets_data


def step3_check_pov() -> bool:
    """
    Step 3: Check POV for sets.
    
    This function now ALWAYS uploads ALL POV data from the CSV file,
    not just newly processed items. This ensures Supabase has the complete dataset.
    """
    print("\n[3/4] Running check_pov...")
    print("-" * 60)
    
    if not os.path.exists(SETS_CSV):
        print(f"⚠️  {SETS_CSV} not found. Skipping POV check.")
        print("   Run scrape_lego_overview.py first to generate this file.")
        return False
    
    sets_df = pd.read_csv(SETS_CSV)
    sets_df = clean_sets_dataframe(sets_df)
    
    item_numbers = sets_df["item_number"].tolist()
    print(f"Checking POV for {len(item_numbers)} sets...")
    
    # Process POV data
    pov_data = asyncio.run(check_pov_custom(item_numbers))
    
    # Load ALL POV data from CSV (including previously processed items)
    # This ensures we upload everything, not just newly processed items
    if os.path.exists(POV_CSV):
        try:
            existing_pov_df = pd.read_csv(POV_CSV)
            print(f"📂 Found existing POV CSV with {len(existing_pov_df)} records")
            
            # If we have new data, merge it with existing
            if pov_data:
                new_pov_df = pd.DataFrame(pov_data)
                # Merge: keep existing, update/add new items
                # Use item_number as key, new data takes precedence
                combined_df = pd.concat([existing_pov_df, new_pov_df]).drop_duplicates(
                    subset=['item_number'], 
                    keep='last'  # Keep the most recent data
                )
                print(f"📊 Merged: {len(existing_pov_df)} existing + {len(new_pov_df)} new = {len(combined_df)} total")
            else:
                combined_df = existing_pov_df
                print(f"📊 Using existing POV data: {len(combined_df)} records")
            
            # Save merged data
            save_to_csv(combined_df.to_dict('records'), POV_CSV, "POV records")
            
            # Upload ALL data from CSV
            pov_data_for_db = combined_df.to_dict('records')
            print(f"📤 Uploading ALL {len(pov_data_for_db)} POV records to Supabase...")
            
        except Exception as e:
            print(f"⚠️  Error reading existing POV CSV: {e}")
            # Fallback to just new data
            if not pov_data:
                print("⚠️  POV data is empty")
                return False
            pov_df = pd.DataFrame(pov_data)
            save_to_csv(pov_df.to_dict('records'), POV_CSV, "POV records")
            pov_data_for_db = pov_df.to_dict('records')
    else:
        # No existing CSV, just use new data
        if not pov_data:
            print("⚠️  POV data is empty and no existing CSV found")
            return False
        
        pov_df = pd.DataFrame(pov_data)
        save_to_csv(pov_df.to_dict('records'), POV_CSV, "POV records")
        pov_data_for_db = pov_df.to_dict('records')
        print(f"✅ Retrieved POV data for {len(pov_data)} sets")
    
    supabase = get_supabase_client()
    # Upload with wipe_table=True to ensure all data is current
    if supabase:
        if not pov_data_for_db:
            print("⚠️  No POV data to upload")
            return True
        
        # Call upsert_pov_data directly with wipe_table=True to wipe table before upload
        success = upsert_pov_data(supabase, pov_data_for_db, wipe_table=True)
        if success:
            print("✅ POV data successfully saved to Supabase")
        else:
            print("❌ Failed to save POV data to Supabase")
        return success
    else:
        print("⚠️  Supabase client not available, skipping database write")
        return False
    
    return True


def step4_rebuild_table() -> bool:
    """Step 4: Rebuild joined table with calculated fields."""
    print("\n[4/4] Rebuilding lego_sets_with_pov table...")
    print("-" * 60)
    
    supabase = get_supabase_client()
    if not supabase:
        print("⚠️  Supabase client not available, skipping joined table rebuild")
        return False
    
    success = rebuild_lego_sets_with_pov(supabase)
    if success:
        print("✅ Joined table successfully rebuilt")
    else:
        print("❌ Failed to rebuild joined table")
    return success


def main():
    """Run all scrapers in sequence."""
    print("=" * 60)
    print(f"Starting scraper run at {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Step 1: Find all themes
        theme_names = step1_find_themes()
        if not theme_names:
            return 1
        
        # Step 2: Scrape LEGO sets
        sets_data = step2_scrape_sets(theme_names)
        if not sets_data:
            print("⚠️  No sets data available, but continuing...")
        
        # Step 3: Check POV
        step3_check_pov()
        
        # Step 4: Rebuild joined table
        step4_rebuild_table()
        
        print("\n" + "=" * 60)
        print(f"✅ All scrapers completed at {datetime.now().isoformat()}")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Error running scrapers: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

