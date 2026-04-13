import asyncio
import sys

# Add directory to sys.path to ensure absolute imports work
sys.path.append('c:\\Users\\Dell\\Desktop\\Linkedin_scraper')

from scraper.engine import ScraperEngine
from routers.profile import ProfileRequest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def main():
    engine = ScraperEngine()
    req = ProfileRequest(url="https://www.linkedin.com/in/shubham-k1umar")
    print("Scraping started...")
    try:
        data = await engine.scrape(req)
        print("Data scraped successfully!")
        print(data.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error scraping: {e}")

if __name__ == "__main__":
    asyncio.run(main())
