import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import os

async def scrape_lego_details(url):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, timeout=60000)

        await page.wait_for_timeout(2000)

        content = await page.content()

        return content

if __name__ == "__main__":
    
    # open lego_store_overview.csv
    df = pd.read_csv("lego_store_overview.csv")
    for index, row in df.iterrows():
        url = row["url"]
        content = asyncio.run(scrape_lego_details(url))
        print(content)
