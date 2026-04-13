import random
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async
from config import settings
from scraper.auth import cookie_manager

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
]

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None

    async def start(self):
        self.playwright = await async_playwright().start()
        
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
        
        proxies = settings.get_proxy_list()
        proxy_config = None
        if proxies:
            proxy_url = random.choice(proxies)
            proxy_config = {"server": proxy_url}
            
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=launch_args,
            proxy=proxy_config
        )

    async def new_page(self) -> tuple[BrowserContext, Page]:
        context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": random.randint(1366, 1920), "height": random.randint(768, 1080)}
        )
        
        # Inject li_at cookie if available
        li_at = cookie_manager.get_current_cookie()
        if li_at:
            await context.add_cookies([
                {
                    "name": "li_at",
                    "value": li_at,
                    "domain": ".linkedin.com",
                    "path": "/"
                }
            ])

        page = await context.new_page()
        await stealth_async(page)
        
        return context, page

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
