"""
Script to check the Part-out-Value (POV) of LEGO sets from BrickLink.

This script includes rate limiting and failure detection to prevent brown-outs.

FEATURES IMPLEMENTED:
====================
1. Detection Mechanisms:
   - 1C: Consecutive failure tracking - Monitors consecutive failures and pauses if threshold reached
   - 1D: HTTP status code checks - Detects rate limiting via HTTP status codes (429, 503, etc.)

2. Prevention Mechanisms:
   - 2A: Adaptive rate limiting - Automatically adjusts delays based on success/failure (exponential backoff)
   - 2B: Request throttling - Enforces max requests per minute limit
   - 2D: Graceful degradation - Pauses for extended period when too many failures detected

CONFIGURATION:
=============
All rate limiting parameters are defined as constants at the top of this file.
Adjust them to tune the behavior:
- BASE_WAIT_TIME_MS: Starting delay between requests
- MAX_REQUESTS_PER_MINUTE: Hard limit on request rate
- MAX_CONSECUTIVE_FAILURES: Threshold for extended pause
- EXTENDED_PAUSE_SECONDS: How long to pause when threshold reached
- And more... (see constants section below)
"""
import asyncio
import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Page, Response
from bs4 import BeautifulSoup

# Import supabase_client
try:
    from supabase_client import get_supabase_client, upsert_pov_data
except ImportError:
    # Fallback if supabase_client is not available
    def get_supabase_client():
        return None
    def upsert_pov_data(*args, **kwargs):
        return False

# ============================================================================
# CONFIGURATION CONSTANTS - Adjust these to tune rate limiting behavior
# ============================================================================

# Base wait time between requests (milliseconds)
# This is the starting delay. It will increase if failures are detected.
BASE_WAIT_TIME_MS = 5000  # 5 seconds

# Maximum wait time between requests (milliseconds)
# Prevents delays from growing too large
MAX_WAIT_TIME_MS = 60000  # 60 seconds (1 minute)

# Minimum wait time between requests (milliseconds)
# Even after successful requests, we maintain a minimum delay
MIN_WAIT_TIME_MS = 3000  # 3 seconds

# Wait time jitter percentage (0.0 to 1.0)
# Adds randomness to delays to avoid predictable patterns
# Example: 0.2 means ±20% random variation
WAIT_JITTER_PERCENT = 0.2

# Exponential backoff multiplier
# When a failure occurs, delay is multiplied by this factor
# Example: 2.0 means delays double after each failure
BACKOFF_MULTIPLIER = 2.0

# Success delay reduction factor
# After successful requests, delay is reduced by this factor
# Example: 0.9 means delay decreases by 10% after each success
SUCCESS_REDUCTION_FACTOR = 0.9

# Request throttling: Maximum requests per minute
# This enforces a hard limit on request rate
MAX_REQUESTS_PER_MINUTE = 10

# Consecutive failure threshold
# If we hit this many consecutive failures, we pause for an extended period
MAX_CONSECUTIVE_FAILURES = 3

# Extended pause time when max failures reached (seconds)
# When we hit MAX_CONSECUTIVE_FAILURES, we pause for this long
EXTENDED_PAUSE_SECONDS = 300  # 5 minutes

# HTTP status codes that indicate rate limiting or blocking
# These will trigger failure tracking and backoff
RATE_LIMIT_STATUS_CODES = [429, 503, 502, 504]  # Too Many Requests, Service Unavailable, etc.

# Page load timeout (milliseconds)
PAGE_LOAD_TIMEOUT = 60000  # 60 seconds

# User agent string
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"


class RateLimiter:
    """
    Manages adaptive rate limiting with exponential backoff and request throttling.
    
    This class tracks:
    - Current delay between requests (adapts based on success/failure)
    - Request timestamps for throttling (max requests per minute)
    - Consecutive failures for graceful degradation
    """
    
    def __init__(self):
        # Current delay in milliseconds - starts at base, adapts based on results
        self.current_delay_ms = BASE_WAIT_TIME_MS
        
        # Track request timestamps for throttling (requests per minute limit)
        # We keep a rolling window of recent request times
        self.request_timestamps = []
        
        # Track consecutive failures for graceful degradation
        self.consecutive_failures = 0
        
    def get_delay_ms(self) -> float:
        """
        Get the current delay with jitter applied.
        
        Returns:
            Delay in milliseconds with random jitter added
        """
        # Calculate jitter amount (±WAIT_JITTER_PERCENT)
        jitter_range = self.current_delay_ms * WAIT_JITTER_PERCENT
        jitter = random.uniform(-jitter_range, jitter_range)
        
        # Apply jitter and ensure we stay within min/max bounds
        delay = self.current_delay_ms + jitter
        delay = max(MIN_WAIT_TIME_MS, min(delay, MAX_WAIT_TIME_MS))
        
        return delay
    
    def record_success(self):
        """
        Called after a successful request.
        
        Reduces delay gradually (but not below minimum) and resets failure counter.
        This allows us to speed up when things are working well.
        """
        # Reduce delay by SUCCESS_REDUCTION_FACTOR, but don't go below minimum
        self.current_delay_ms = max(
            MIN_WAIT_TIME_MS,
            self.current_delay_ms * SUCCESS_REDUCTION_FACTOR
        )
        
        # Reset failure counter on success
        self.consecutive_failures = 0
        
    def record_failure(self):
        """
        Called after a failed request.
        
        Increases delay using exponential backoff and increments failure counter.
        This slows us down when we're hitting rate limits.
        """
        # Increase delay using exponential backoff
        self.current_delay_ms = min(
            MAX_WAIT_TIME_MS,
            self.current_delay_ms * BACKOFF_MULTIPLIER
        )
        
        # Increment consecutive failure counter
        self.consecutive_failures += 1
        
    def should_pause_extended(self) -> bool:
        """
        Check if we should pause for an extended period due to too many failures.
        
        Returns:
            True if we've hit the consecutive failure threshold
        """
        return self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES
    
    async def wait_for_throttle(self):
        """
        Enforce request throttling (max requests per minute).
        
        If we've made too many requests recently, wait until we're under the limit.
        This prevents us from exceeding the hard rate limit even if individual
        requests are successful.
        """
        now = time.time()
        one_minute_ago = now - 60
        
        # Remove timestamps older than 1 minute (keep only recent requests)
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > one_minute_ago]
        
        # If we're at the limit, wait until the oldest request is more than 1 minute old
        if len(self.request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
            oldest_request = min(self.request_timestamps)
            wait_until = oldest_request + 60  # Wait until 1 minute after oldest request
            wait_time = max(0, wait_until - now)
            
            if wait_time > 0:
                print(f"⏸️  Throttling: {len(self.request_timestamps)} requests in last minute. "
                      f"Waiting {wait_time:.1f} seconds to stay under {MAX_REQUESTS_PER_MINUTE} req/min limit...")
                await asyncio.sleep(wait_time)
        
        # Record this request timestamp
        self.request_timestamps.append(time.time())
    
    async def wait(self):
        """
        Wait for the appropriate delay based on current state.
        
        This combines:
        - Adaptive delay (based on success/failure)
        - Jitter (randomness)
        - Request throttling (max per minute)
        """
        # First, enforce request throttling (max requests per minute)
        await self.wait_for_throttle()
        
        # Then, wait for the adaptive delay with jitter
        delay_ms = self.get_delay_ms()
        delay_seconds = delay_ms / 1000.0
        
        print(f"⏳ Waiting {delay_seconds:.2f} seconds (current delay: {self.current_delay_ms/1000:.2f}s, "
              f"consecutive failures: {self.consecutive_failures})")
        
        await asyncio.sleep(delay_seconds)


def detect_rate_limit(response: Optional[Response], content: str) -> Tuple[bool, str]:
    """
    Detect if we're being rate limited or blocked (Detection 1D: HTTP Status Codes).
    
    Checks:
    - HTTP status codes that indicate rate limiting (429, 503, etc.)
    - Response content for error indicators
    
    Args:
        response: Playwright Response object (may be None if request failed)
        content: HTML content of the page
        
    Returns:
        Tuple of (is_rate_limited: bool, reason: str)
    """
    # Check HTTP status code (Detection 1D)
    if response:
        status = response.status
        
        # Check for rate limiting status codes
        if status in RATE_LIMIT_STATUS_CODES:
            return True, f"HTTP {status} status code indicates rate limiting"
        
        # Check for other error status codes
        if status >= 400:
            return True, f"HTTP {status} error status code"
    
    # Check content for rate limit indicators
    content_lower = content.lower()
    
    # Look for common rate limit/block messages
    rate_limit_keywords = [
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "service unavailable",
        "access denied",
        "blocked",
        "captcha",
        "please try again later"
    ]
    
    for keyword in rate_limit_keywords:
        if keyword in content_lower:
            return True, f"Content contains rate limit indicator: '{keyword}'"
    
    return False, ""


async def fetch_pov_page(page: Page, item_number: str) -> Tuple[Optional[BeautifulSoup], Optional[Response], bool]:
    """
    Fetch and parse a POV page for a given item number.
    
    This function now includes:
    - HTTP status code checking (Detection 1D)
    - Response validation
    
    Args:
        page: Playwright page object
        item_number: LEGO set item number to check
        
    Returns:
        Tuple of (soup: BeautifulSoup or None, response: Response or None, is_rate_limited: bool)
        - soup: Parsed HTML if successful, None if failed
        - response: HTTP response object
        - is_rate_limited: True if rate limiting detected
    """
    bricklink_url = f"https://www.bricklink.com/catalogPOV.asp?itemType=S&itemNo={item_number}&itemSeq=1&itemQty=1&breakType=M&itemCondition=N"
    print(f"Checking POV for {item_number} at {bricklink_url}")
    
    try:
        # Navigate to page and capture response
        response = await page.goto(bricklink_url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
        
        # Wait a bit for page to fully load
        await page.wait_for_timeout(2000)
        
        # Get page content
        content = await page.content()
        
        # Check for rate limiting (Detection 1D: HTTP Status Codes)
        is_rate_limited, reason = detect_rate_limit(response, content)
        
        if is_rate_limited:
            print(f"⚠️  Rate limit detected for {item_number}: {reason}")
            return None, response, True
        
        # Parse and return
        soup = BeautifulSoup(content, "html.parser")
        return soup, response, False
        
    except Exception as e:
        print(f"❌ Error fetching page for {item_number}: {e}")
        return None, None, False


async def check_pov_custom(item_numbers: List[str]) -> List[Dict[str, Any]]:
    """
    Check POV for multiple item numbers with rate limiting.
    
    Features implemented:
    - 1C: Consecutive failure tracking
    - 1D: HTTP status code checks
    - 2A: Adaptive rate limiting with exponential backoff
    - 2B: Request throttling (max requests per minute)
    - 2D: Graceful degradation on rate limits
    
    Args:
        item_numbers: List of LEGO set item numbers to check
        
    Returns:
        List of dictionaries containing POV data for each item
    """
    if not item_numbers:
        print("⚠️  No items to process")
        return []
    
    print(f"📊 Processing {len(item_numbers)} items")
    
    # Initialize rate limiter (2A: Adaptive rate limiting, 2B: Request throttling)
    rate_limiter = RateLimiter()

    item_info = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        
        # Loop over each set (item) that was passed in
        for idx, item_number in enumerate(item_numbers, 1):
            print(f"\n[{idx}/{len(item_numbers)}] Processing {item_number}")
            
            try:
                # Wait before making request (2A: Adaptive rate limiting, 2B: Request throttling)
                await rate_limiter.wait()
                
                # Check for extended pause needed (2D: Graceful degradation)
                if rate_limiter.should_pause_extended():
                    print(f"⚠️  {rate_limiter.consecutive_failures} consecutive failures detected!")
                    print(f"⏸️  Pausing for {EXTENDED_PAUSE_SECONDS} seconds to avoid brown-out...")
                    await asyncio.sleep(EXTENDED_PAUSE_SECONDS)
                    # Reset failure counter after extended pause
                    rate_limiter.consecutive_failures = 0
                    rate_limiter.current_delay_ms = BASE_WAIT_TIME_MS  # Reset to base delay
                
                # Fetch page with rate limit detection (1D: HTTP status code checks)
                soup, response, is_rate_limited = await fetch_pov_page(page, item_number)
                
                # Handle rate limiting detection (1D: HTTP Status Codes)
                if is_rate_limited:
                    print(f"❌ Rate limit detected for {item_number}")
                    rate_limiter.record_failure()  # 2A: Exponential backoff
                    # 1C: Consecutive failure tracking happens in record_failure()
                    continue
                
                # Check if we got valid content
                if soup is None:
                    print(f"❌ No content received for {item_number}")
                    rate_limiter.record_failure()  # 2A: Exponential backoff
                    # 1C: Consecutive failure tracking
                    continue
                
                # Parse POV data
                all_text = soup.find_all('font')

                # Validate we got expected data (additional check for brown-out)
                if not all_text:
                    print(f"⚠️  No POV data found for {item_number} - may indicate blocking")
                    rate_limiter.record_failure()  # 2A: Exponential backoff
                    # 1C: Consecutive failure tracking
                    continue
                
                pov_data = parse_results_to_table(all_text, item_number)
                
                if pov_data:
                    item_info.append(pov_data)
                    
                    # Record success (2A: Adaptive rate limiting - reduces delay)
                    rate_limiter.record_success()
                    print(f"✅ Successfully processed {item_number}")
                else:
                    print(f"⚠️  Failed to parse POV data for {item_number}")
                    rate_limiter.record_failure()  # 2A: Exponential backoff
                    # 1C: Consecutive failure tracking
                    
            except Exception as e:
                print(f"❌ Error checking POV for {item_number}: {e}")
                rate_limiter.record_failure()  # 2A: Exponential backoff
                # 1C: Consecutive failure tracking
                continue
        
        await browser.close()
    
    print(f"\n✅ Completed processing. {len(item_info)} items retrieved.")
    
    return item_info

def parse_results_to_table(results: List, item_number: str) -> Dict[str, Any]:
    """
    Parse a single set's POV results into a dictionary.
    
    Args:
        results: List of BeautifulSoup font elements containing POV data
        item_number: The item number being parsed
        
    Returns:
        Dictionary with POV data, or None if parsing fails
    """
    if not results:
        print(f'No results given for {item_number}!')
        return None

    print(f'Parsing results for {item_number}...')
    
    pov_past_6_months = None
    pov_past_6_months_volume = None
    pov_current_listings = None
    pov_current_listings_volume = None

    for line in results:
        line_text = line.get_text()
        
        if '$' in line_text:
            if pov_past_6_months is None:
                pov_past_6_months = line_text
            else:
                pov_current_listings = line_text
        
        if 'Including' in line_text:
            parts = line_text.split(' ')
            if len(parts) >= 5:
                if pov_past_6_months_volume is None:
                    pov_past_6_months_volume = f"{parts[1]}|{parts[4]}"
                else:
                    pov_current_listings_volume = f"{parts[1]}|{parts[4]}"
    
    print('--------------------------------')
    print(f"POV for {item_number}: {pov_past_6_months} - {pov_current_listings} "
          f"with volumes {pov_past_6_months_volume} - {pov_current_listings_volume}")
    print('--------------------------------')
    
    return {
                "item_number": item_number,
                "pov_past_6_months": pov_past_6_months,
                "pov_past_6_months_volume": pov_past_6_months_volume,
                "pov_current_listings": pov_current_listings,
                "pov_current_listings_volume": pov_current_listings_volume
            }

if __name__ == "__main__":
    """
    Standalone execution for testing purposes.
    Note: This is primarily used by run_all_scrapers.py
    """
    import pandas as pd
    
    csv_path = "lego_store_overview.csv"
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} not found. Cannot run POV check.")
        exit(1)
    
    # Load and clean sets data
    sets_df = pd.read_csv(csv_path)
    print(f"Initial set count: {len(sets_df)}")

    # Remove duplicate rows
    sets_df = sets_df.drop_duplicates(keep='first')
    # Drop rows where the item_number is None
    sets_df = sets_df[sets_df['item_number'].notna()]
    sets_df = sets_df[sets_df['piece_count'] != 'Piece count not found']
    # Convert piece_count to int
    sets_df['piece_count'] = pd.to_numeric(sets_df['piece_count'], errors='coerce')
    # Drop rows where piece count is < 10
    sets_df = sets_df[sets_df['piece_count'] >= 10]

    print(f"Cleaned set count: {len(sets_df)}")

    item_numbers = sets_df["item_number"].tolist()
    
    # For testing, limit to first 5 items
    test_items = item_numbers[:5] if len(item_numbers) > 5 else item_numbers
    print(f"Testing with {len(test_items)} items...\n")
    
    results_table = asyncio.run(check_pov_custom(test_items))
    
    if not results_table:
        print("⚠️  No POV data retrieved in this run")
    
    if results_table:
        pov_df = pd.DataFrame(results_table)
        print(f"\nRetrieved POV data for {len(pov_df)} sets in this run")

        # Join the pov_df with the sets_df on the item_number column
        df_complete = sets_df.merge(pov_df, on='item_number', how='left')

        # Save the dataframe to a csv file as backup
        df_complete.to_csv('pov.csv', index=False)
        print('✅ CSV saved successfully!')
        
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