import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str = "AzentZeroSecretToken123"
    
    # Can parse comma separated proxies
    proxies: str = ""
    
    # LinkedIn Credentials
    linkedin_email: str = ""
    linkedin_password: str = ""
    
    # Limits how many scrapes per active session before rotation (though now handled via persistent storage)
    rate_limit_max_per_cookie: int = 100

    def get_proxy_list(self) -> List[str]:
        if not self.proxies:
            return []
        return [p.strip() for p in self.proxies.split(",") if p.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
