#!/usr/bin/env python3
"""
Main script to run all scrapers in sequence.
This script should be executed daily via cron or a scheduled task.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the scrapers directory to the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from find_all_themes import find_all_themes
from scrape_lego_overview import scrape_lego
from check_pov import check_pov_custom
import pandas as pd

def main():
    """Run all scrapers in sequence."""
    print("=" * 60)
    print(f"Starting scraper run at {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Step 1: Find all themes
        print("\n[1/3] Running find_all_themes...")
        print("-" * 60)
        themes_data = asyncio.run(find_all_themes())
        
        # Extract theme names for scrape_lego()
        theme_names = None
        if themes_data:
            print(f"✅ Found {len(themes_data)} themes")
            # Save themes to CSV file for backup
            themes_df = pd.DataFrame(themes_data)
            csv_path = "themes_list.csv"
            themes_df.to_csv(csv_path, index=False)
            print(f"✅ Saved {len(themes_df)} themes to {csv_path}")
            # Extract theme names to pass directly to scrape_lego()
            theme_names = [theme['theme_name'] for theme in themes_data]
        else:
            print("⚠️  No themes found. Checking for existing themes_list.csv...")
            # Fallback: try to use existing CSV if available
            if os.path.exists("themes_list.csv"):
                print("✅ Found existing themes_list.csv, will use it")
                themes_df = pd.read_csv("themes_list.csv")
                theme_names = themes_df["theme_name"].tolist()
                print(f"✅ Loaded {len(theme_names)} themes from existing CSV")
            else:
                print("❌ No themes found and no existing themes_list.csv available")
                print("   Cannot proceed with scraping LEGO sets without themes")
                return 1
        
        # Step 2: Scrape LEGO overview (pass themes directly)
        print("\n[2/3] Running scrape_lego_overview...")
        print("-" * 60)
        sets_data = asyncio.run(scrape_lego(themes=theme_names))
        
        if not sets_data:
            print("⚠️  No sets found.")
        else:
            print(f"✅ Found {len(sets_data)} sets")
            # Save sets to CSV file for next scraper
            sets_df = pd.DataFrame(sets_data)
            # Convert the msrp and sale_price to float for CSV
            sets_df['msrp'] = sets_df['msrp'].apply(lambda x: float(str(x).replace('$', '').replace(',', '')) if pd.notna(x) and str(x) != 'None' else None)
            sets_df['sale_price'] = sets_df['sale_price'].apply(lambda x: float(str(x).replace('$', '').replace(',', '')) if pd.notna(x) and str(x) != 'None' else None)
            csv_path = "lego_store_overview.csv"
            sets_df.to_csv(csv_path, index=False)
            print(f"✅ Saved {len(sets_df)} sets to {csv_path}")
        
        # Step 3: Check POV (requires lego_store_overview.csv)
        print("\n[3/3] Running check_pov...")
        print("-" * 60)
        
        # Check if lego_store_overview.csv exists
        if not os.path.exists("lego_store_overview.csv"):
            print("⚠️  lego_store_overview.csv not found. Skipping POV check.")
            print("   Run scrape_lego_overview.py first to generate this file.")
        else:
            sets_df = pd.read_csv("lego_store_overview.csv")
            
            # Remove duplicate rows
            sets_df = sets_df.drop_duplicates(keep='first')
            
            # Drop rows where the item_number is None
            sets_df = sets_df[sets_df['item_number'].notna()]
            
            # Filter sets
            if 'piece_count' in sets_df.columns:
                sets_df = sets_df[sets_df['piece_count'] != 'Piece count not found']
                # Convert piece_count to int
                sets_df['piece_count'] = pd.to_numeric(sets_df['piece_count'], errors='coerce')
                sets_df = sets_df[sets_df['piece_count'] >= 10]
            
            item_numbers = sets_df["item_number"].tolist()
            print(f"Checking POV for {len(item_numbers)} sets...")
            
            pov_data = asyncio.run(check_pov_custom(item_numbers))
            
            if pov_data:
                print(f"✅ Retrieved POV data for {len(pov_data)} sets")
            else:
                print("⚠️  No POV data retrieved")
        
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

