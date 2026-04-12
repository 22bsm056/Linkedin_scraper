import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str = "AzentZeroSecretToken123"
    
    # Can parse comma separated proxies
    proxies: str = ""
    
    # Comma separated li_at cookies
    li_at_cookies: str = ""
    
    # Limits how many scrapes per active cookie before rotation
    rate_limit_max_per_cookie: int = 100

    def get_proxy_list(self) -> List[str]:
        if not self.proxies:
            return []
        return [p.strip() for p in self.proxies.split(",") if p.strip()]

    def get_cookie_list(self) -> List[str]:
        if not self.li_at_cookies:
            return []
        return [c.strip() for c in self.li_at_cookies.split(",") if c.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
