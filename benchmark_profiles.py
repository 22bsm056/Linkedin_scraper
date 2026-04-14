import asyncio
import time
import sys
import os

PROJECT_ROOT = "c:\\Users\\Dell\\Desktop\\Linkedin_scraper"
sys.path.append(PROJECT_ROOT)

from scraper.engine import ScraperEngine
from routers.profile import ProfileRequest
from scraper.exporter import ProfileExporter

PROFILES = [
    "https://www.linkedin.com/in/googler-aakash/",
    "https://www.linkedin.com/in/aaron-p-saji/",
    "https://www.linkedin.com/in/shreya-gupta-5b0927284/",
    "https://www.linkedin.com/in/pratiksha-singh-228894281/",
    "https://www.linkedin.com/in/riteshpandey07/"
]

async def benchmark():
    engine = ScraperEngine()
    exporter = ProfileExporter()
    
    results = []
    
    print("="*60)
    print("LINKEDIN SCRAPER PERFORMANCE BENCHMARK")
    print("="*60)
    print(f"Testing {len(PROFILES)} profiles with parallel fetching and asset blocking...")
    
    for i, profile_url in enumerate(PROFILES):
        print(f"\n[{i+1}/{len(PROFILES)}] Target: {profile_url}")
        
        start_time = time.time()
        success = False
        error = None
        
        try:
            req = ProfileRequest(url=profile_url)
            data = await engine.scrape(req)
            
            if data:
                # Optional: Generate PDF as a stress test
                exporter.generate_pdf(data, profile_url)
                success = True
                items_found = len(data.experience) + len(data.education) + len(data.skills)
                print(f"   Success! Found {items_found} professional items.")
            else:
                error = "Empty data returned"
        except Exception as e:
            error = str(e)
            print(f"   Error: {e}")
            
        elapsed = time.time() - start_time
        results.append({
            "url": profile_url,
            "time": elapsed,
            "success": success,
            "error": error
        })
        
        print(f"   Time Taken: {elapsed:.2f} seconds")
        
        # Settle time between profiles to avoid detection
        if i < len(PROFILES) - 1:
            wait_time = 3
            print(f"   Waiting {wait_time}s for session safety...")
            await asyncio.sleep(wait_time)

    # FINAL REPORT
    print("\n" + "="*60)
    print("BENCHMARK REPORT")
    print("="*60)
    
    total_time = 0
    success_count = 0
    
    for r in results:
        status = "PASS" if r['success'] else "FAIL"
        print(f"{status} | {r['time']:.2f}s | {r['url']}")
        if r['success']:
            total_time += r['time']
            success_count += 1
            
    if success_count > 0:
        avg_time = total_time / success_count
        print("-" * 60)
        print(f"Average time for successful profiles: {avg_time:.2f} seconds")
    else:
        print("\nNo successful profiles found.")
    print("="*60)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(benchmark())
