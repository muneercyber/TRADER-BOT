from playwright.sync_api import sync_playwright
import pandas as pd
import time

def get_live_candle_data(asset_name: str) -> pd.DataFrame:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://pocketoption.com/en/cabinet/demo/")
            time.sleep(10)  # Let the chart load

            # This JS is a placeholder — update selectors according to real DOM
            candles = page.evaluate("""() => {
                return [...document.querySelectorAll('.chart-candles .candle')].map(c => ({
                    time: c.getAttribute('data-time'),
                    open: parseFloat(c.getAttribute('data-open')),
                    high: parseFloat(c.getAttribute('data-high')),
                    low: parseFloat(c.getAttribute('data-low')),
                    close: parseFloat(c.getAttribute('data-close')),
                    volume: parseFloat(c.getAttribute('data-volume'))
                }))
            }""")
            browser.close()

            if not candles:
                return pd.DataFrame()

            df = pd.DataFrame(candles)
            df = df.dropna()
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            return df.tail(50)  # Limit to last 50 for indicators
    except Exception as e:
        print(f"[SCRAPER ERROR] {e}")
        return pd.DataFrame()
