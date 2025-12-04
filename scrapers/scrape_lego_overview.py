import asyncio
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re

# Import supabase_client
try:
    from supabase_client import get_supabase_client, upsert_lego_sets
except ImportError:
    # Fallback if supabase_client is not available
    def get_supabase_client():
        return None
    def upsert_lego_sets(*args, **kwargs):
        return False

# Constants
MAX_RETRY_ATTEMPTS = 3
PAGE_LOAD_TIMEOUT = 60000
WAIT_TIME_SHORT = 1000
WAIT_TIME_MEDIUM = 2000
MAX_PAGES_DEFAULT = 200


async def handle_age_gate(page) -> None:
    """Handle age gate"""

    if page is None:
        print("Page is None, exiting...")
        return
    
    # Confirm age gate is present
    if 'age-gate' not in page.url:
        print("No age gate found, exiting...")
        return
    
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:

            continue_button = await page.wait_for_selector('button[data-test="age-gate-grown-up-cta"]', timeout=PAGE_LOAD_TIMEOUT)

            if not continue_button:
                print("No continue button found, exiting...")
                return

            print(f"Clicking age gate button {attempt + 1}/{MAX_RETRY_ATTEMPTS}")
            await continue_button.click(timeout=PAGE_LOAD_TIMEOUT, force=True)

            # Assumed success (No exception raised)
            print(f"Age gate button clicked {attempt + 1}/{MAX_RETRY_ATTEMPTS}!  Continuing...")
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)
            break

        # If exception raised, retry up to MAX_RETRY_ATTEMPTS times
        except Exception as e:
            await page.wait_for_timeout(WAIT_TIME_MEDIUM)
            print(f"Retry {attempt + 1}/{MAX_RETRY_ATTEMPTS}: {e}")

    # If all retries fail, raise an error
    else:
        print(f"Failed to handle age gate after {MAX_RETRY_ATTEMPTS} attempts")
        
        # write the html to a file for further inspection
        os.makedirs("html_files", exist_ok=True)
        with open(f"html_files/age_gate.html", "w", encoding='utf-8') as f:
            f.write(await page.content())
        print(f"HTML saved to html_files/age_gate.html for inspection")

        raise Exception(f"Failed to handle age gate after {MAX_RETRY_ATTEMPTS} attempts")


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
            continue_button = await page.wait_for_selector('button[data-test="cookie-necessary-button"]', timeout=PAGE_LOAD_TIMEOUT)

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



def build_page_url(base_url: str, page_number: int) -> str:
    """Build URL for a specific page number"""

    # This checks if the URL already has a parameter or if it needs the page number to be the first parameter.
    if '?' in base_url:
        return f"{base_url}&page={page_number}"
    else:
        return f"{base_url}?page={page_number}"


async def navigate_to_page(page, url: str, timeout: int = PAGE_LOAD_TIMEOUT) -> None:
    """Navigate to a page with error handling"""
    await page.goto(url, timeout=timeout)
    await page.wait_for_timeout(WAIT_TIME_MEDIUM)


async def scrape_lego(themes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if themes is None:
        themes = pd.read_csv("themes_list.csv")["theme_name"].tolist()
        print(f'No themes provided, using {len(themes)} themes from themes_list.csv')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        
        error_count = 0
        total_sets = 0

        return_data = []

        
        for theme in themes:
            assembled_url = f"https://www.lego.com/en-us/themes/{theme}"

            # https://www.lego.com/en-us/themes/star-wars/page=2&offset=0
            print(f'\n=== Starting theme: {theme} ===')
            
            page_number = 1
            sets_scraped_from_theme = 0
            page_count = MAX_PAGES_DEFAULT
            
            while page_number <= page_count:
                try:
                    print(f'Scraping page {page_number} of {theme}')
                    
                    if page_number == 1:
                        # We are on the first page
                        await navigate_to_page(page, assembled_url)
                    else:
                        # Hit the URL of the next page
                        next_page_url = build_page_url(assembled_url, page_number)
                        print(f"Next page URL: {next_page_url}")
                        await navigate_to_page(page, next_page_url)
                    
                    
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")

                    # Debug: Check what's actually on the page
                    real_url = page.url
                    print(f"Current URL: {real_url}")

                    # Handle age gate or cookie consent
                    if 'age-gate' in real_url:
                        print('Age gate encountered!')
                        await handle_age_gate(page)
                        # After handling age gate, we need to navigate to the actual page
                        if page_number == 1:
                            await navigate_to_page(page, assembled_url)
                        else:
                            next_page_url = build_page_url(assembled_url, page_number)
                            await navigate_to_page(page, next_page_url)
                        # Get fresh content after navigation
                        content = await page.content()
                        soup = BeautifulSoup(content, "html.parser")
                        real_url = page.url
                        print(f"After age gate handling, URL: {real_url}")
                        
                    elif 'consent-modal' in real_url:
                        print('Cookie consent encountered!')
                        await handle_cookie_consent(page)
                        # After handling cookie consent, we need to navigate to the actual page
                        if page_number == 1:
                            await navigate_to_page(page, assembled_url)
                        else:
                            next_page_url = build_page_url(assembled_url, page_number)
                            await navigate_to_page(page, next_page_url)
                        # Get fresh content after navigation
                        content = await page.content()
                        soup = BeautifulSoup(content, "html.parser")
                        real_url = page.url
                        print(f"After cookie consent handling, URL: {real_url}")

                    # Get page count (only on first page)
                    if page_number == 1:
                        try:
                            # Find all pagination page links
                            page_selector_elements = soup.find_all('a', attrs={"data-test": lambda x: x and "pagination-page" in x})
                            page_count = len(page_selector_elements)
                            print(f"Total pages found: {page_count}")
                            
                            # If no pagination found, assume single page
                            if page_count == 0:
                                page_count = 1
                                print("No pagination found, assuming single page")
                        except Exception as e:
                            print(f"Error getting page count: {e}")
                            page_count = 1

                    
                    sets = soup.find_all("li", class_="Grid_grid-item__Dguxr", attrs={"data-test": "product-item"})
                    
                    # # If no sets found, try alternative selectors
                    # if len(sets) == 0:
                    #     print("No sets found with primary selector, trying alternatives...")
                    #     sets = soup.find_all("li", attrs={"data-test": "product-item"})
                    #     print(f"Found {len(sets)} with data-test='product-item'")
                        
                    #     if len(sets) == 0:
                    #         sets = soup.find_all("li", class_="Grid_grid-item__Dguxr")
                    #         print(f"Found {len(sets)} with class 'Grid_grid-item__Dguxr'")
                    
                    print(f"Found {len(sets)} product items on page {page_number}")

                    if len(sets) == 0:
                        print("No products found, stopping pagination")
                        # Create directory if it doesn't exist
                        os.makedirs("html_files", exist_ok=True)
                        # write the html to a file for further inspection
                        with open(f"html_files/{theme}_{page_number}.html", "w", encoding='utf-8') as f:
                            f.write(content)
                        print(f"HTML saved to html_files/{theme}_{page_number}.html for inspection")
                        break
                    
                    # Process each set
                    for set_item in sets:
                        try:
                            # Find the link
                            link_element = set_item.find('a')
                            if not link_element:
                                continue
                                
                            url_extension = link_element.get('href', '')
                            
                            # Ensure that the set is a product (not an ad)
                            if 'product' not in url_extension:
                                print(f"Skipping non-product: {url_extension}")
                                continue

                            # This is also an ad check.
                            if '?icmp=' in url_extension:
                                print(f"Skipping ad: {url_extension}")
                                continue
                                
                            url = f"https://www.lego.com{url_extension}"
                            item_number = url.split(sep = '-')[-1]
                            
                            # Find product name
                            name_element = set_item.find('h3')
                            set_name = name_element.get_text(strip=True) if name_element else "Unknown"

                            availability_element = set_item.find("div", attrs={"data-test": "product-leaf-action-row"})
                            availability = availability_element.get_text(strip=True) if availability_element else "Unknown"
                            
                            # Find price
                            price_element = set_item.find('div', class_="ProductLeaf_priceRow__kwpxi")

                            if price_element is None:
                                print(f"No price element found: {url_extension}")

                                msrp = None
                                sale_price = None
                                continue

                            # Check if price_element contains a discount percentage (a sale price)
                            if "%" in price_element.get_text(strip=True):
                                base_price = price_element.get_text(strip=True)

                                pattern = r'(\$\d+\.\d{2})(\$\d+\.\d{2})(\d+% OFF)'
                                match = re.match(pattern, base_price)
                                
                                if match:
                                    msrp = match.group(1)
                                    sale_price = match.group(2)
                                    discount_percentage = match.group(3)
                                else:
                                    print(f"Could not parse base price: {base_price}")
                                    msrp = None
                                    sale_price = None
                                    discount_percentage = None
                            
                            elif "Insiders" in price_element.get_text(strip=True):
                                # Regex function to extract the msrp (the first number that ends in .99) and the sale price (the immediately following number that ends in .99)
                                print(f"Insiders price element: {price_element.get_text(strip=True)}")
                                pattern = r'(\$\d+\.\d{2})(\$\d+\.\d{2})'
                                match = re.match(pattern, price_element.get_text(strip=True))
                                if match:
                                    msrp = match.group(1)
                                    sale_price = match.group(2)
                                else:
                                    print(f"Could not parse base price: {price_element.get_text(strip=True)}")
                                    msrp = None


                            else:
                                msrp = price_element.get_text(strip=True)
                                sale_price = msrp

                            # Find piece count
                            piece_count_element = set_item.find('span', attrs={"data-test": "product-leaf-piece-count-label"})
                            piece_count = piece_count_element.get_text(strip=True) if piece_count_element else "Piece count not found"

                            if 'Key Chain' in set_name:
                                piece_count = 1
                            
                            return_data.append({
                                "set_name": set_name,
                                "msrp": msrp,
                                "sale_price": sale_price,
                                "availability": availability,
                                "piece_count": piece_count,
                                "url": url,
                                "item_number": item_number
                            })


                            print(f"  {set_name} - {msrp} - {sale_price} - {piece_count}")
                            total_sets += 1

                            sets_scraped_from_theme += 1
                            
                        except Exception as e:
                            print(f"  Error processing product: {e}")
                            continue
                    


                    if page_number == page_count:
                        print("We have scraped all sets from this theme, stopping pagination")
                        break
                    else:
                        page_number += 1
                        
                except Exception as e:
                    print(f"Error on page {page_number}: {e}")
                    error_count += 1
                    
            print(f"Finished scraping {theme} - Total pages: {page_number}")

        await browser.close()
        print('Browser closed!')
        print(f"Error count: {error_count}")

        return return_data

if __name__ == "__main__":
    return_data = asyncio.run(scrape_lego())
    df = pd.DataFrame(return_data)

    if not df.empty:
        # Convert the msrp and sale_price to float for CSV
        # Note: Supabase client will handle conversion
        df['msrp'] = df['msrp'].apply(lambda x: float(str(x).replace('$', '').replace(',', '')) if pd.notna(x) and str(x) != 'None' else None)
        df['sale_price'] = df['sale_price'].apply(lambda x: float(str(x).replace('$', '').replace(',', '')) if pd.notna(x) and str(x) != 'None' else None)
        
        # Save to CSV as backup
        print(f"Saving {len(df)} sets to lego_store_overview.csv.")
        df.to_csv("lego_store_overview.csv", index=False)
        if os.path.exists("lego_store_overview.csv"):
            print("lego_store_overview.csv saved successfully")
        else:
            print("lego_store_overview.csv was not saved - investigate!")
        
        # Save to Supabase
        supabase = get_supabase_client()
        if supabase:
            success = upsert_lego_sets(supabase, return_data)
            if success:
                print("✅ LEGO sets successfully saved to Supabase")
            else:
                print("❌ Failed to save LEGO sets to Supabase")
        else:
            print("⚠️  Supabase client not available, skipping database write")
    else:
        print("No sets were found to save to lego_store_overview.csv")
