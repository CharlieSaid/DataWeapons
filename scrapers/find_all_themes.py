import asyncio
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd

# Constants
MAX_RETRY_ATTEMPTS = 3
PAGE_LOAD_TIMEOUT = 60000
WAIT_TIME_SHORT = 1000
WAIT_TIME_MEDIUM = 2000
MAX_PAGES_DEFAULT = 200

BASE_URL = "https://www.lego.com/en-us/themes"

from scrape_lego_overview import handle_age_gate, navigate_to_page, build_page_url

# Import supabase_client
try:
    from supabase_client import get_supabase_client, upsert_themes
except ImportError:
    # Fallback if supabase_client is not available
    def get_supabase_client():
        return None
    def upsert_themes(*args, **kwargs):
        return False

# async def handle_age_gate(page) -> None:
#     """Handle age gate"""

#     if page is None:
#         print("Page is None, exiting...")
#         return
    
#     # Confirm age gate is present
#     if 'age-gate' not in page.url:
#         print("No age gate found, exiting...")
#         return
    
#     for attempt in range(MAX_RETRY_ATTEMPTS):
#         try:

#             continue_button = await page.wait_for_selector('button[data-test="age-gate-grown-up-cta"]', timeout=PAGE_LOAD_TIMEOUT)

#             if not continue_button:
#                 print("No continue button found, exiting...")
#                 return

#             print(f"Clicking age gate button {attempt + 1}/{MAX_RETRY_ATTEMPTS}")
#             await continue_button.click(timeout=PAGE_LOAD_TIMEOUT, force=True)

#             # Assumed success (No exception raised)
#             print(f"Age gate button clicked {attempt + 1}/{MAX_RETRY_ATTEMPTS}!  Continuing...")
#             await page.wait_for_timeout(WAIT_TIME_MEDIUM)
#             break

#         # If exception raised, retry up to MAX_RETRY_ATTEMPTS times
#         except Exception as e:
#             await page.wait_for_timeout(WAIT_TIME_MEDIUM)
#             print(f"Retry {attempt + 1}/{MAX_RETRY_ATTEMPTS}: {e}")

#     # If all retries fail, raise an error
#     else:
#         print(f"Failed to handle age gate after {MAX_RETRY_ATTEMPTS} attempts")
        
#         # write the html to a file for further inspection
#         os.makedirs("html_files", exist_ok=True)
#         with open(f"html_files/age_gate.html", "w", encoding='utf-8') as f:
#             f.write(await page.content())
#         print(f"HTML saved to html_files/age_gate.html for inspection")

#         raise Exception(f"Failed to handle age gate after {MAX_RETRY_ATTEMPTS} attempts")


async def handle_cookie_consent(page) -> None:
    """Handle cookie consent"""

    if page is None:
        print("Page is None, exiting...")
        return

    # Confirm cookie consent is present
    if 'consent-modal' not in page.url:
        print("No cookie consent found, exiting...")
        return

    # Try to click the cookie consent button up to MAX_RETRY_ATTEMPTS times
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            continue_button = await page.wait_for_selector('button[data-test="cookie-accept-all"]', timeout=PAGE_LOAD_TIMEOUT)

            if not continue_button:
                print("No continue button found, exiting...")
                return

            print(f"Clicking cookie consent button {attempt + 1}/{MAX_RETRY_ATTEMPTS}")
            await continue_button.click(timeout=PAGE_LOAD_TIMEOUT, force=True)
            print(f"Cookie consent button clicked {attempt + 1}/{MAX_RETRY_ATTEMPTS}!  Continuing...")
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)
            break
        
        # If exception raised, retry up to MAX_RETRY_ATTEMPTS times
        except Exception as e:
            await page.wait_for_timeout(WAIT_TIME_SHORT)
            print(f"Retry {attempt + 1}/{MAX_RETRY_ATTEMPTS}")

    else:
        print(f"Failed to handle cookie consent after {MAX_RETRY_ATTEMPTS} attempts")
        # write the html to a file for further inspection
        with open(f"html_files/cookie_consent.html", "w", encoding='utf-8') as f:
            f.write(await page.content())
        print(f"HTML saved to html_files/cookie_consent.html for inspection")
        
        raise Exception(f"Failed to handle cookie consent after {MAX_RETRY_ATTEMPTS} attempts")



# def build_page_url(base_url: str, page_number: int) -> str:
#     """Build URL for a specific page number"""

#     # This checks if the URL already has a parameter or if it needs the page number to be the first parameter.
#     if '?' in base_url:
#         return f"{base_url}&page={page_number}"
#     else:
#         return f"{base_url}?page={page_number}"


# async def navigate_to_page(page, url: str, timeout: int = PAGE_LOAD_TIMEOUT) -> None:
#     """Navigate to a page with error handling"""
#     await page.goto(url, timeout=timeout)
#     await page.wait_for_timeout(WAIT_TIME_MEDIUM)


async def find_all_themes() -> List[Dict[str, Any]]:
    
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        

        return_data = []

        await navigate_to_page(page, BASE_URL)

        content = await page.content()


        # Debug: Check what's actually on the page
        real_url = page.url
        print(f"Current URL: {real_url}")

        # Handle age gate or cookie consent
        if 'age-gate' in real_url:
            print('Age gate encountered!')
            await handle_age_gate(page)
            # After handling age gate, we need to navigate to the actual page

            await navigate_to_page(page, BASE_URL)

            # Get fresh content after navigation
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            real_url = page.url
            print(f"After age gate handling, URL: {real_url}")
            
        if 'consent-modal' in real_url:
            print('Cookie consent encountered!')
            await handle_cookie_consent(page)
            # After handling cookie consent, we need to navigate to the actual page

            await navigate_to_page(page, BASE_URL)
            
            # Get fresh content after navigation
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            real_url = page.url
            print(f"After cookie consent handling, URL: {real_url}")


        soup = BeautifulSoup(content, "html.parser")

        # Find all the themes

        theme_elements = soup.find_all('a', attrs={"class": "Linksstyles__Anchor-sc-83wpk9-0 dfbGrg CategoryLeafstyles__DetailsLink-sc-2bwko3-14 hTmaUD", "href": True, "data-test": "themes-link"})
        for theme_element in theme_elements:
            theme_name = theme_element.get('href').split('/')[-1]
            print(f"Found theme: {theme_name}")
            return_data.append({
                "theme_name": theme_name,
                "theme_url": theme_element.get('href')
            })
        print(f"Found {len(theme_elements)}")
                    
        await browser.close()
        print('Browser closed!')

        return return_data

if __name__ == "__main__":
    import sys
    
    try:
        print("Starting find_all_themes scraper...")
        return_data = asyncio.run(find_all_themes())
        
        if not return_data:
            print("⚠️  Warning: No themes found. This might indicate a scraping issue.")
            sys.exit(1)  # Exit with error if no data found
        
        df = pd.DataFrame(return_data)
        print(f"Found {len(df)} themes")
        
        # Save to CSV as backup
        csv_path = "themes_list.csv"
        print(f"Saving {len(df)} themes to {csv_path}.")
        print(f"Current working directory: {os.getcwd()}")
        df.to_csv(csv_path, index=False)
        if os.path.exists(csv_path):
            print(f"✅ {csv_path} saved successfully at {os.path.abspath(csv_path)}")
        else:
            print(f"❌ {csv_path} was not saved - investigate!")
            print(f"   Expected path: {os.path.abspath(csv_path)}")
            sys.exit(1)
        
        # Save to Supabase
        supabase = get_supabase_client()
        if supabase:
            success = upsert_themes(supabase, return_data)
            if success:
                print("✅ Themes successfully saved to Supabase")
            else:
                print("❌ Failed to save themes to Supabase")
                sys.exit(1)  # Exit with error if Supabase save fails
        else:
            print("⚠️  Supabase client not available, skipping database write")
            print("   Make sure SUPABASE_URL and SUPABASE_KEY environment variables are set")
            # Don't exit with error if Supabase is unavailable - CSV backup is still saved
        
        print("✅ Scraper completed successfully")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error running scraper: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)