import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth import stealth_async

class BrowserManager:
    def __init__(self, user_data_dir: str = "browser_data"):
        self.user_data_dir = os.path.abspath(user_data_dir)
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)
            
    @asynccontextmanager
    async def get_session(self, headless: bool = False):
        """
        Provides a persistent browser context. 
        Reuse existing session if available in user_data_dir.
        """
        async with async_playwright() as p:
            # We use launch_persistent_context to maintain session across runs
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--disable-notifications"
                ],
                no_viewport=False,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            # Apply stealth to the first page (or all pages if needed)
            # persistent_context creates one page by default
            if context.pages:
                await stealth_async(context.pages[0])
            
            try:
                yield context
            finally:
                # Close the context properly
                await context.close()

    async def clear_session(self):
        """Removes the persistent user data directory."""
        import shutil
        if os.path.exists(self.user_data_dir):
            shutil.rmtree(self.user_data_dir)
            os.makedirs(self.user_data_dir)
