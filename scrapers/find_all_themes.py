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
        # Launch browser with stealth settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',  # Remove automation flags
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # Create context with realistic browser properties
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},  # Realistic viewport
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # Updated, realistic UA
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC coordinates
            color_scheme='light',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        page = await context.new_page()
        
        # Remove webdriver traces and add stealth JavaScript
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins to look more realistic
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        

        return_data = []

        # Navigate with better wait strategy
        print(f"Navigating to {BASE_URL}...")
        await page.goto(BASE_URL, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(WAIT_TIME_MEDIUM)  # Extra wait for JS to render
        
        # Wait for page to be fully loaded
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            await page.wait_for_load_state('networkidle', timeout=15000)
        except Exception as e:
            print(f"Warning: Load state wait timed out: {e}")

        # Debug: Check what's actually on the page
        real_url = page.url
        print(f"Current URL: {real_url}")

        # Handle age gate or cookie consent
        if 'age-gate' in real_url:
            print('Age gate encountered!')
            await handle_age_gate(page)
            # After handling age gate, we need to navigate to the actual page
            print(f"Navigating to {BASE_URL} after age gate...")
            await page.goto(BASE_URL, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)
            await page.wait_for_load_state('networkidle', timeout=15000)
            real_url = page.url
            print(f"After age gate handling, URL: {real_url}")
        else:
            print("No age gate found")
            
        if 'consent-modal' in real_url:
            print('Cookie consent encountered!')
            await handle_cookie_consent(page)
            # After handling cookie consent, we need to navigate to the actual page
            print(f"Navigating to {BASE_URL} after cookie consent...")
            await page.goto(BASE_URL, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)
            await page.wait_for_load_state('networkidle', timeout=15000)
            real_url = page.url
            print(f"After cookie consent handling, URL: {real_url}")
        else:
            print("No cookie consent found")

        # Wait for page to be fully loaded and theme elements to appear
        # Try multiple selectors in case the page structure changed
        try:
            # Wait for any theme link to appear (more reliable than waiting for specific class)
            await page.wait_for_selector('a[href*="/themes/"][data-test="themes-link"]', timeout=PAGE_LOAD_TIMEOUT)
            print("Theme elements detected on page")
        except Exception as e:
            print(f"Warning: Could not find theme elements with data-test selector: {e}")
            # Try alternative: wait for any link containing /themes/
            try:
                await page.wait_for_selector('a[href*="/themes/"]', timeout=10000)
                print("Found theme links with alternative selector")
            except Exception as e2:
                print(f"Warning: Could not find theme links with alternative selector: {e2}")

        # Wait a bit more for JavaScript to fully render
        await page.wait_for_timeout(WAIT_TIME_MEDIUM * 2)  # Extra wait for JS-heavy pages
        
        # Scroll page to trigger lazy loading if any
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(WAIT_TIME_SHORT)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(WAIT_TIME_SHORT)

        # Get fresh content after all navigation and waiting
        content = await page.content()
        if content:
            print(f"Content found! Content length: {len(content)}")
            # Check if we got a minimal/error page
            if len(content) < 10000:
                print(f"⚠️  Warning: Content length is suspiciously short ({len(content)} chars)")
                print(f"   This might indicate bot detection or an error page")
                # Check for common error indicators
                if 'blocked' in content.lower() or 'access denied' in content.lower() or 'captcha' in content.lower():
                    print("   ⚠️  Page appears to be blocked or showing CAPTCHA")
        else:
            print("No content found")
            await context.close()
            await browser.close()
            return return_data

        soup = BeautifulSoup(content, "html.parser")

        # Find all the themes - try multiple selectors for robustness
        # First try the data-test attribute (most reliable)
        theme_elements = soup.find_all('a', attrs={"data-test": "themes-link", "href": True})
        
        # If that doesn't work, try the class-based selector
        if len(theme_elements) == 0:
            print("No themes found with data-test selector, trying class-based selector...")
            theme_elements = soup.find_all('a', attrs={"class": "sc-99390ee5-0 iqhEUq sc-c51a6d83-4 eZQczn", "href": True})
        
        # If still nothing, try a more generic selector (any link to /themes/)
        if len(theme_elements) == 0:
            print("No themes found with class selector, trying generic /themes/ link selector...")
            all_links = soup.find_all('a', href=True)
            theme_elements = [link for link in all_links if '/themes/' in link.get('href', '') and link.get('href', '').count('/') >= 4]
        
        print(f"Found {len(theme_elements)} theme elements")

        # Extract theme names, filtering out invalid ones
        for theme_element in theme_elements:
            href = theme_element.get('href', '')
            if not href:
                print(f"Skipping because no href")
                continue
            
            # Extract theme name from URL (e.g., /en-us/themes/star-wars -> star-wars)
            theme_name = href.rstrip('/').split('/')[-1]
            
            # Skip if theme_name is empty or looks invalid
            if not theme_name or theme_name in ['themes', 'en-us', '']:
                print(f"Skipping invalid theme name: {theme_name} because it looks invalid")
                continue
            
            # Skip if it's not a valid theme URL (should be a single word/slug)
            if '?' in theme_name or '#' in theme_name or '=' in theme_name:
                print(f"Skipping invalid theme name: {theme_name} because it contains invalid characters")
                continue
            
            print(f"Found theme: {theme_name}")
            return_data.append({
                "theme_name": theme_name,
                "theme_url": href if href.startswith('http') else f"https://www.lego.com{href}"
            })
        
        print(f"Found {len(return_data)} valid themes")
        
        # If no themes found, save HTML for debugging (especially useful in CI)
        if len(return_data) == 0:
            print("⚠️  No themes found! Saving HTML for debugging...")
            os.makedirs("html_files", exist_ok=True)
            html_path = "html_files/themes_page_no_results.html"
            with open(html_path, "w", encoding='utf-8') as f:
                f.write(content)
            print(f"HTML saved to {html_path} for inspection")
            print(f"Page URL was: {real_url}")
            print(f"Content length: {len(content)} characters")
            # Also save a screenshot for debugging
            try:
                screenshot_path = "html_files/themes_page_screenshot.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                print(f"Could not save screenshot: {e}")
                    
        await context.close()
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
        print(f"Supabase client: {supabase}")
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