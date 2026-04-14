import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await stealth_async(page)
        print("Navigating to profile...")
        await page.goto('https://www.linkedin.com/in/shubham-k1umar', wait_until="networkidle")
        print(f"Title: {await page.title()}")
        print(f"URL: {page.url}")
        content = await page.content()
        with open("public_view.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("HTML saved to public_view.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
