# This script will check the Part-out-Value of a set.

import asyncio
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd

# Import supabase_client
try:
    from supabase_client import get_supabase_client, upsert_pov_data
except ImportError:
    # Fallback if supabase_client is not available
    def get_supabase_client():
        return None
    def upsert_pov_data(*args, **kwargs):
        return False

bricklink_url = "https://www.bricklink.com/catalogPOV.asp?itemType=S&itemNo=77057&itemSeq=1&itemQty=1&breakType=M&itemCondition=N&incInstr=Y"
WAIT_TIME_MEDIUM = 2000
PAGE_LOAD_TIMEOUT = 60000


async def check_pov_custom(item_numbers: List[str]):
    

    item_info = []

    # Loop over each set (item) that was passed in.
    for item_number in item_numbers:
        bricklink_url = f"https://www.bricklink.com/catalogPOV.asp?itemType=S&itemNo={item_number}&itemSeq=1&itemQty=1&breakType=M&itemCondition=N"
        print(f"Checking POV for {item_number} at {bricklink_url}")
    
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            })
            
            await page.goto(bricklink_url)
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)

            # Polite wait
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)


            soup = BeautifulSoup(await page.content(), "html.parser")

            all_text = soup.find_all('font')


            item_info.append(parese_results_to_table(all_text, item_number))
    return item_info

def parese_results_to_table(results: List[str], item_number: str) -> Dict[str, Any]:

    """This function parses a single set's PoV results into a dict."""
    
    pov_past_6_months = None
    pov_past_6_months_volume = None
    pov_current_listings = None
    pov_current_listings_volume = None

    if results is None:
        print('No results given!')
        return None

    print('Parsing results...')

    for line in results:
        print(line)
        line_text = line.get_text()
        if '$' in line_text:
            if pov_past_6_months is None:
                pov_past_6_months = line_text
            else:
                pov_current_listings = line_text
        
        if 'Including' in line:
            if pov_past_6_months_volume is None:
                pov_past_6_months_volume = line_text.split(sep = ' ')[1]
            else:
                pov_current_listings_volume = line_text.split(sep = ' ')[1]
    print('--------------------------------')
    print(f"POV for {item_number}: {pov_past_6_months} - {pov_current_listings}")
    print('--------------------------------')
    return {
                "item_number": item_number,
                "pov_past_6_months": pov_past_6_months,
                "pov_past_6_months_volume": pov_past_6_months_volume,
                "pov_current_listings": pov_current_listings,
                "pov_current_listings_volume": pov_current_listings_volume
            }

# Main function
if __name__ == "__main__":
    
    # open lego_store_overview.csv
    sets_df = pd.read_csv("lego_store_overview.csv")
    print("inital set count: ", len(sets_df))

    # Remove duplicate rows
    sets_df = sets_df.drop_duplicates(keep='first')
    # Drop rows where the item_number is None
    sets_df = sets_df[sets_df['item_number'].notna()]
    sets_df = sets_df[sets_df['piece_count'] != 'Piece count not found']
    # Convert piece_count to int
    sets_df['piece_count'] = sets_df['piece_count'].astype(int)
    # Drop rows where piece count is < 100
    sets_df = sets_df[sets_df['piece_count'] >= 10]

    print("cleaned set count: ", len(sets_df))

    item_numbers = sets_df["item_number"].tolist()
    
    results_table = asyncio.run(check_pov_custom(item_numbers[1:5]))
    pov_df = pd.DataFrame(results_table)

    # Join the pov_df with the sets_df on the item_number column
    df_complete = sets_df.merge(pov_df, on='item_number', how='left')

    # Save the dataframe to a csv file as backup
    df_complete.to_csv('pov.csv', index=False)
    print('CSV saved successfully!')
    
    # Save POV data to Supabase (only the POV columns, not the full merged data)
    pov_data_for_db = pov_df.to_dict('records')
    supabase = get_supabase_client()
    if supabase:
        success = upsert_pov_data(supabase, pov_data_for_db)
        if success:
            print("✅ POV data successfully saved to Supabase")
        else:
            print("❌ Failed to save POV data to Supabase")
    else:
        print("⚠️  Supabase client not available, skipping database write")