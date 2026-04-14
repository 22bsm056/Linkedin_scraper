import re
from typing import List, Optional

class ProfileCleaner:
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        
        # Remove noisy "See more/less" strings
        text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
        text = re.sub(r"see less", "", text, flags=re.IGNORECASE)
        
        # Remove endorsement artifacts (e.g., "· 5 endorsements")
        text = re.sub(r"·\s*\d+\s+endorsement[s]?", "", text, flags=re.IGNORECASE)
        
        # Remove multiple newlines and extra spaces
        text = re.sub(r"\n\s+", "\n", text)
        text = re.sub(r"\s{2,}", " ", text)
        
        return text.strip()

    @staticmethod
    def clean_list(items: List[str]) -> List[str]:
        """Removes duplicates and cleans each item in a list."""
        seen = set()
        cleaned = []
        for item in items:
            c = ProfileCleaner.clean_text(item)
            if c and c.lower() not in seen:
                cleaned.append(c)
                seen.add(c.lower())
        return cleaned

    @staticmethod
    def extract_duration(text: str) -> str:
        """Attempts to isolate the duration (e.g., '1 yr 2 mos') from a larger string."""
        if not text: return ""
        # Match patterns like "Jan 2020 - Present · 4 yrs 4 mos"
        match = re.search(r"·\s*(.*)$", text)
        if match:
            return match.group(1).strip()
        return text.strip()
