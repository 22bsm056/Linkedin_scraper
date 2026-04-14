import asyncio
import random
import os
from playwright.async_api import Page
from routers.profile import ProfileRequest, ExtractedData
from scraper.browser import BrowserManager
from scraper.parser import ProfileParser

class ScraperEngine:
    def __init__(self):
        self.browser_manager = BrowserManager()

    async def scrape(self, request: ProfileRequest) -> ExtractedData:
        # headless=False is strongly recommended for LinkedIn
        async with self.browser_manager.get_session(headless=False) as context:
            # Persistent context keeps at least one page open
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Step 1: Check Session
            print("Checking session validity...")
            try:
                await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Initial navigation warning: {e}")

            async def check_is_logged_in():
                try:
                    indicator = await page.query_selector(".global-nav, .feed-identity-module, [data-test-global-nav-icon]")
                    if indicator: return True
                    if "/feed" in page.url or "/mynetwork" in page.url: return True
                    return False
                except:
                    return False

            is_logged_in = await check_is_logged_in()
            print(f"Logged in: {is_logged_in} (Current URL: {page.url})")

            # Step 2: Login if needed
            if not is_logged_in:
                print("Session expired or missing. Triggering human-like login...")
                from config import settings
                if not settings.linkedin_email or not settings.linkedin_password:
                    raise Exception("LinkedIn credentials missing in .env")

                await page.goto("https://www.linkedin.com/login", wait_until="networkidle", timeout=45000)
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                if await check_is_logged_in():
                    print("Immediate redirect to feed. Session restored.")
                else:
                    # Handle "Sign in using another account"
                    other_acc = await page.query_selector("button:has-text('Sign in using another account')")
                    if other_acc:
                        print("Bypassing 'Welcome Back' screen...")
                        await self._human_click(page, other_acc)
                        await asyncio.sleep(random.uniform(1, 2))

                    print(f"Attempting login for {settings.linkedin_email}...")
                    try:
                        await page.wait_for_selector("#username", timeout=15000)
                        
                        # Human-like typing
                        await self._human_type(page, "#username", settings.linkedin_email)
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                        await self._human_type(page, "#password", settings.linkedin_password)
                        await asyncio.sleep(random.uniform(0.8, 1.5))
                        
                        await page.click("button[type='submit']")
                        print("Credentials submitted. Waiting for authentication...")
                        await page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception as e:
                        if await check_is_logged_in():
                            print("Login form not found but session seems active.")
                        else:
                            await page.screenshot(path="login_error.png")
                            raise Exception(f"Login failed: {e}")

                    # Final verification
                    if not await check_is_logged_in():
                        if "/checkpoint" in page.url:
                            await page.screenshot(path="login_checkpoint.png")
                            raise Exception("Security checkpoint (2FA) detected. Please solve manually in the browser window.")
                        else:
                            await page.screenshot(path="login_failed_final.png")
                            raise Exception("Failed to reach authenticated state.")

            # Step 3: Navigate to Profile
            profile_url = request.url.rstrip('/')
            print(f"Navigating to profile: {profile_url}")
            try:
                # Use domcontentloaded as networkidle often times out on LinkedIn due to background telemetry
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5) # Give it some time to settle
            except Exception as e:
                print(f"Navigation fallback: {e}")

            await self._scroll_page(page)
            main_html = await page.content()
            with open("scraped.html", "w", encoding="utf-8") as f:
                f.write(main_html)

            # Step 4: Detail pages
            detail_data = {}
            for section in ["experience", "education", "skills"]:
                print(f"Extracting details: {section}...")
                section_url = f"{profile_url}/details/{section}/"
                try:
                    await page.goto(section_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(3)
                    await self._scroll_page(page)
                    html = await page.content()
                    detail_data[section] = html
                    with open(f"details_{section}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception as e:
                    print(f"Section {section} failed: {e}")
                    detail_data[section] = ""

            # Step 5: Merge and Parse
            full_html = main_html
            for section, html in detail_data.items():
                full_html += f"\n<!-- SECTION_{section.upper()} -->\n{html}"

            parser = ProfileParser(full_html, request.url)
            result = parser.parse(request)
            
            return result

    async def _human_type(self, page: Page, selector: str, text: str):
        """Simulates human typing with varied speed and occasional pauses."""
        await page.click(selector)
        # Clear existing
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        for char in text:
            await page.keyboard.type(char, delay=random.randint(50, 150))
            if random.random() > 0.9:  # Occasional pause
                await asyncio.sleep(random.uniform(0.1, 0.4))

    async def _human_click(self, page: Page, element):
        """Moves mouse to element before clicking."""
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            await page.mouse.move(x, y, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y)

    async def _scroll_page(self, page: Page):
        """Human-like scrolling."""
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(600, 1100))
            await asyncio.sleep(random.uniform(0.7, 1.4))
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
