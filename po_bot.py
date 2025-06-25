# po_bot.py
import asyncio
import json
import os
from playwright.async_api import async_playwright

SESSION_FILE = "po_auth.json"
TARGET_URL = "https://pocketoption.com/en/cabinet/demo-quick-high-low/"

async def run_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = None

        if os.path.exists(SESSION_FILE):
            print("🔁 Loading saved session...")
            with open(SESSION_FILE, "r") as f:
                context = await browser.new_context(storage_state=json.load(f))
        else:
            print("🔓 No session found. Logging in manually...")
            context = await browser.new_context()

        page = await context.new_page()
        print("🌍 Navigating to Pocket Option...")
        await page.goto(TARGET_URL, timeout=90000)

        if not os.path.exists(SESSION_FILE):
            print("⏳ Waiting for login...")
            for _ in range(300):
                cookies = await context.cookies()
                if any(c['name'] == 'ci_session' for c in cookies):
                    print("✅ Login detected. Saving session...")
                    storage = await context.storage_state()
                    with open(SESSION_FILE, "w") as f:
                        json.dump(storage, f)
                    break
                await asyncio.sleep(1)

        print("✅ Logged in and ready.")

if __name__ == "__main__":
    asyncio.run(run_all())
