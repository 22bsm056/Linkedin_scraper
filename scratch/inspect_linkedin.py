import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.browser import BrowserManager
from config import settings

async def main():
    manager = BrowserManager()
    try:
        await manager.start()
        context, page = await manager.new_page()

        # Try to use existing session
        print("Navigating to https://www.linkedin.com/feed/")
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        if "login" in page.url or "checkpoint" in page.url:
            print("Not logged in. Logging in...")
            await page.goto("https://www.linkedin.com/login")
            await page.fill("#username", settings.linkedin_email)
            await page.fill("#password", settings.linkedin_password)
            await page.click("button[type='submit']")
            await page.wait_for_url("**/feed/**", timeout=30000)
            # Save session
            state = await context.storage_state(path="session.json")
            print("Logged in and session saved.")

        # Inspect Experience
        url = "https://www.linkedin.com/in/shubham-k1umar/details/experience/"
        print(f"Inspecting {url}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Get the pvs-list items
        items = await page.query_selector_all("li.pvs-list__paged-list-item")
        if items:
            print(f"Found {len(items)} experience items.")
            inner = await items[0].inner_html()
            with open("exp_sample.html", "w", encoding="utf-8") as f:
                f.write(inner)
            print("Saved first experience item to exp_sample.html")
        else:
            print("No experience items found with li.pvs-list__paged-list-item")
            # Try a broader selector
            content = await page.content()
            with open("exp_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved full experience page to exp_page.html")

        # Inspect Skills
        url = "https://www.linkedin.com/in/shubham-k1umar/details/skills/"
        print(f"Inspecting {url}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(3)
        items = await page.query_selector_all("li.pvs-list__paged-list-item")
        if items:
            print(f"Found {len(items)} skill items.")
            inner = await items[0].inner_html()
            with open("skill_sample.html", "w", encoding="utf-8") as f:
                f.write(inner)
            print("Saved first skill item to skill_sample.html")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
