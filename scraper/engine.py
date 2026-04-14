import asyncio
import random
import os
from routers.profile import ProfileRequest, ExtractedData
from scraper.browser import BrowserManager
from scraper.parser import ProfileParser


class ScraperEngine:
    async def scrape(self, request: ProfileRequest) -> ExtractedData:
        manager = BrowserManager()
        try:
            await manager.start()
            context, page = await manager.new_page()

            # Step 1: Check session validity by visiting the feed
            print("Checking session validity at https://www.linkedin.com/feed/...")
            try:
                await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
            except Exception:
                pass

            async def check_is_logged_in():
                # Check for common indicators of a logged-in state
                # Often LinkedIn shows a 'Join' nudge even if logged in, so we check for Feed indicators
                title = await page.title()
                content = await page.content()
                
                is_feed = "feed" in page.url or "Feed" in title
                has_nav = await page.query_selector("[data-testid='primary-nav']") is not None or await page.query_selector(".global-nav") is not None
                
                # If we see the feed or the nav, we are likely logged in
                return is_feed and has_nav

            is_logged_in = await check_is_logged_in()
            print(f"Logged in: {is_logged_in}")

            # Step 2: If not logged in, perform automated login
            if not is_logged_in:
                print("Session expired or missing. Triggering automated login flow...")
                if os.path.exists("session.json"):
                    try:
                        os.remove("session.json")
                    except Exception:
                        pass


                from config import settings
                if not settings.linkedin_email or not settings.linkedin_password:
                    raise Exception(
                        "403 Forbidden: Authwall detected but LINKEDIN_EMAIL/LINKEDIN_PASSWORD "
                        "are not set in your .env file."
                    )

                # Navigate to LinkedIn login page
                print("Navigating to https://www.linkedin.com/login")
                await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                print(f"Current URL: {page.url}")
                
                # Check for selectors with fallbacks
                try:
                    # If we see "Sign in using another account", click it to get to the standard form
                    other_account_btn = await page.query_selector(".signin-other-account, button:has-text('Sign in using another account')")
                    if other_account_btn:
                        print("Remembered account screen detected. Clicking 'Sign in using another account'...")
                        await other_account_btn.click()
                        await asyncio.sleep(random.uniform(1.0, 2.0))

                    # Generic selector attempts
                    username_field = await page.wait_for_selector("#username, input[name='session_key']", timeout=10000)
                    password_field = await page.wait_for_selector("#password, input[name='session_password']", timeout=10000)
                    submit_button = await page.wait_for_selector(".btn__primary--large, button[type='submit']", timeout=10000)
                    
                    print(f"Filling credentials for: {settings.linkedin_email}")
                    # Clear fields first if they have garbage
                    await username_field.click(click_count=3)
                    await page.keyboard.press("Backspace")
                    await username_field.fill(settings.linkedin_email)
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                    
                    await password_field.fill(settings.linkedin_password)
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                    await submit_button.click()
                except Exception as e:

                    login_html = await page.content()
                    with open("login_failure.html", "w", encoding="utf-8") as f:
                        f.write(login_html)
                    print(f"Login elements not found. Saved login_failure.html for debugging. Error: {e}")
                    raise Exception(f"Login page structure changed or CAPTCHA detected. Check login_failure.html.")

                print("Login submitted. Waiting for session to establish...")


                # Wait for the global nav (sign-in success indicator)
                try:
                    await page.wait_for_selector(".global-nav", timeout=30000)
                    print("Login confirmed via .global-nav selector.")
                except Exception as nav_err:
                    print(f"Global-nav selector wait failed: {nav_err}. Checking URL...")
                    await asyncio.sleep(5)

                final_url = page.url
                if "/login" in final_url or "/checkpoint" in final_url:
                    raise Exception(
                        "403 Forbidden: Login failed — wrong credentials, CAPTCHA, or 2FA required."
                    )

                # Persist authenticated session — future runs skip login entirely
                await context.storage_state(path="session.json")
                print("Session persisted to session.json. Future runs will skip login.")

            # Step 4: Final navigation (re-navigate to ensure we're on the profile)
            print(f"Re-navigating to profile: {request.url}")
            try:
                await page.goto(request.url, wait_until="networkidle", timeout=30000)
            except Exception:
                await page.goto(request.url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)

            # Step 5: Extract basic profile HTML
            print("Scrolling and extracting basic profile info...")
            await self._scroll_page(page)
            main_html = await page.content()
            
            # Step 6: Detailed Scraping (navigate to sub-pages for more info)
            # This is more robust as LinkedIn often limits the view on the main profile page
            full_html = main_html
            
            detail_categories = []
            if request.include_experience: detail_categories.append("experience")
            if request.include_education: detail_categories.append("education")
            if request.include_skills: detail_categories.append("skills")
            
            base_url = request.url.rstrip("/")
            for category in detail_categories:
                detail_url = f"{base_url}/details/{category}/"
                print(f"Navigating to detailed {category}: {detail_url}")
                try:
                    # Random delay between detail pages to avoid throttling
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                    try:
                        await page.goto(detail_url, wait_until="networkidle", timeout=30000)
                    except Exception:
                        await page.goto(detail_url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(2)

                    await self._scroll_page(page)
                    category_html = await page.content()
                    # Append unique sections to the full_html
                    full_html += f"\n<!-- CATEGORY_{category.upper()} -->\n" + category_html
                except Exception as e:
                    print(f"Could not load {category} details: {e}")


            with open("scraped.html", "w", encoding="utf-8") as f:
                f.write(full_html)
            print("HTML saved to scraped.html for inspection.")

            # Step 7: Parse and return structured profile data
            parser = ProfileParser(full_html, request.url)
            data = parser.parse(request)
            return data


        finally:
            await manager.close()

    async def _scroll_page(self, page):
        """Simulate realistic incremental scrolling to trigger lazy loading."""
        while True:
            scroll_step = random.randint(300, 700)
            await page.evaluate(f"window.scrollBy(0, {scroll_step});")
            await asyncio.sleep(random.uniform(0.5, 1.5))

            new_height = await page.evaluate("document.body.scrollHeight")
            current_scroll = await page.evaluate("window.scrollY + window.innerHeight")

            if current_scroll >= new_height:
                break
