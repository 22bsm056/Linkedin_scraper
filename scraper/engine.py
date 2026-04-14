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
                await asyncio.sleep(3) # Initial settle
                
                # Check for redirect or landing page error
                current_url = page.url.lower().rstrip('/')
                if "/in/" not in current_url:
                    print(f"WARNING: Unexpected landing page: {current_url}")
                    await page.screenshot(path="wrong_landing.png")
                
                # Wait for the main identity card (Top Card)
                # LinkedIn often loads the skeletal page first then rehydrates
                print("Waiting for profile identity card...")
                try:
                    await page.wait_for_selector("[componentkey*='Topcard'], .profile-top-card, #workspace", timeout=15000)
                except:
                    print("Note: Specific top-card selector not found, proceeding with raw DOM.")

                await self._scroll_page(page)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Navigation fallback: {e}")

            # 3. Capture Main Page
            print("Capturing main profile view...")
            await self._scroll_fast(page)
            main_html = await page.content()
            
            # 4. PARALLEL DETAIL FETCHING (High Performance)
            # We fetch all major sections concurrently in new pages within the same context
            print("Fetching details (Experience, Education, Skills) in parallel...")
            
            async def fetch_section(section_type):
                detail_page = await context.new_page()
                try:
                    section_url = f"{profile_url}/details/{section_type}/"
                    await detail_page.goto(section_url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(1) # Minimal settle
                    await self._scroll_fast(detail_page)
                    return await detail_page.content()
                except Exception as e:
                    print(f"Warning: Failed to fetch {section_type} detail: {e}")
                    return ""
                finally:
                    await detail_page.close()

            sections = ["experience", "education", "skills"]
            html_results = await asyncio.gather(*(fetch_section(s) for s in sections))
            
            details_map = dict(zip(sections, html_results))

            # 5. Merge and Parse
            merged_html = main_html
            for s_type, s_html in details_map.items():
                if s_html:
                    merged_html += f"\n<!-- SECTION_{s_type.upper()} -->\n{s_html}"

            parser = ProfileParser(merged_html, profile_url)
            data = parser.parse(request)
            
            return data

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

    async def _scroll_fast(self, page: Page):
        """Fast scrolling to trigger lazy rehydration."""
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 400;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 50);
                });
            }
        """)
        await asyncio.sleep(0.5)

    async def _scroll_page(self, page: Page):
        """Standard human-like scrolling (fallback)."""
        for _ in range(2):
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(0.5)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.5)
