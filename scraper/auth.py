import time
from typing import Optional
from config import settings

class CookieManager:
    """Manages the pool of li_at cookies for rotation."""
    
    def __init__(self):
        self.cookies = settings.get_cookie_list()
        self.current_index = 0
        self.usage_count = 0
        
    def get_current_cookie(self) -> Optional[str]:
        if not self.cookies:
            return None
        return self.cookies[self.current_index]
        
    def increment_usage(self):
        if not self.cookies:
            return
        self.usage_count += 1
        if self.usage_count >= settings.rate_limit_max_per_cookie:
            self.rotate_cookie()
            
    def rotate_cookie(self):
        if not self.cookies:
            return
        self.current_index = (self.current_index + 1) % len(self.cookies)
        self.usage_count = 0
        
    def get_usage_stats(self) -> dict:
        remaining = settings.rate_limit_max_per_cookie - self.usage_count if self.cookies else 0
        reset_time = int(time.time() * 1000) + 3600000 # dummy reset logic
        return {
            "rateLimitRemaining": remaining,
            "rateLimitReset": reset_time
        }

cookie_manager = CookieManager()
