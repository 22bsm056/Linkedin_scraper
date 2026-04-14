import asyncio
import sys
import os

# Add directory to sys.path to ensure absolute imports work
PROJECT_ROOT = 'c:\\Users\\Dell\\Desktop\\Linkedin_scraper'
sys.path.append(PROJECT_ROOT)

from scraper.engine import ScraperEngine
from routers.profile import ProfileRequest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def main():
    # Construct a real ProfileRequest matching the API expectations
    # url: str
    # include_experience: bool = True
    # include_education: bool = True
    # include_skills: bool = True
    req = ProfileRequest(
        url="https://www.linkedin.com/in/shubham-k1umar",
        include_experience=True,
        include_education=True,
        include_skills=True
    )
    
    # Initialize Engine (Uses context manager internally)
    engine = ScraperEngine()
    
    print(f"Scraping started for: {req.url}")
    try:
        # 1. Scrape (Returns ExtractedData)
        data = await engine.scrape(req)
        
        if not data:
            print("Failed to extract data.")
            return

        print("Data scraped successfully!")
        print(f"Name: {data.profile.firstName} {data.profile.lastName}")
        print(f"Experience items found: {len(data.experience)}")
        
        # 2. Exporting to PDF is handled by the user/API layer usually, 
        # but let's do it here for the final check.
        from scraper.exporter import ProfileExporter
        exporter = ProfileExporter()
        pdf_path = exporter.generate_pdf(data, req.url)
        print(f"Final PDF available at: {pdf_path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during scraping session: {e}")

if __name__ == "__main__":
    asyncio.run(main())
