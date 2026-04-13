import asyncio
import random
from routers.profile import ProfileRequest, ExtractedData
from scraper.browser import BrowserManager
from scraper.parser import ProfileParser

class ScraperEngine:
    async def scrape(self, request: ProfileRequest) -> ExtractedData:
        manager = BrowserManager()
        try:
            await manager.start()
            context, page = await manager.new_page()
            
            # Go to profile
            try:
                response = await page.goto(request.url, wait_until="domcontentloaded", timeout=20000)
            except Exception as e:
                print(f"goto timed out or failed: {e}")
                response = None
                
            # Basic Error Checking based on HTTP status or URL redirects
            if response is not None and response.status == 404:
                raise Exception("404 Not Found: Profile doesn't exist or URL is invalid.")
                
            url = page.url
            if "authwall" in url or "login" in url:
                raise Exception("403 Forbidden: Account restricted or profile is completely private. (Authwall detected)")
                
            if response is not None and response.status == 429:
                raise Exception("429 Too Many Requests: Proxy IP burned or rate limit reached.")
            
            # Human Emulation: Random delays and natural scrolling
            await asyncio.sleep(random.uniform(2.0, 4.0))
            await self._scroll_page(page)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Extract HTML
            html = await page.content()
            with open('scraped.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            # Parse HTML
            parser = ProfileParser(html, request.url)
            data = parser.parse(request)
            
            return data
            
        finally:
            await manager.close()

    async def _scroll_page(self, page):
        """Simulate realistic scrolling to trigger lazy loading."""
        last_height = await page.evaluate("document.body.scrollHeight")
        while True:
            # Scroll down down by a random amount
            scroll_step = random.randint(300, 700)
            await page.evaluate(f"window.scrollBy(0, {scroll_step});")
            
            # Random sleep
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            new_height = await page.evaluate("document.body.scrollHeight")
            current_scroll = await page.evaluate("window.scrollY + window.innerHeight")
            
            if current_scroll >= new_height:
                break
