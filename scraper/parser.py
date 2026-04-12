import re
from bs4 import BeautifulSoup
from routers.profile import ExtractedData, ProfileData, ExperienceData, EducationData, SkillData, RecommendationData

class ProfileParser:
    def __init__(self, html: str, url: str):
        self.soup = BeautifulSoup(html, "html.parser")
        self.url = url

    def parse(self, request) -> ExtractedData:
        # Note: LinkedIn DOM is heavily obfuscated and changes frequently.
        # This implementation provides a structural best-effort mapping using generic heuristics.
        
        data = ExtractedData(
            profile=ProfileData(profileUrl=self.url)
        )
        
        # --- Profile Extraction ---
        # Heuristic: top-card details
        h1 = self.soup.find("h1")
        if h1:
            name_parts = h1.get_text(strip=True).split(maxsplit=1)
            data.profile.firstName = name_parts[0] if len(name_parts) > 0 else ""
            data.profile.lastName = name_parts[1] if len(name_parts) > 1 else ""

        # Headline
        headline_div = self.soup.find("div", class_=re.compile("text-body-medium", re.I))
        if headline_div:
            data.profile.headline = headline_div.get_text(strip=True)

        # Location
        location_span = self.soup.find("span", class_=re.compile("text-body-small inline", re.I))
        if location_span:
            data.profile.location = location_span.get_text(strip=True)

        # Connections
        conn_str = self.soup.find(string=re.compile(r'\d+[\+]?\s+connections', re.I))
        if conn_str:
            num = re.search(r'(\d+)', conn_str)
            if num:
                data.profile.connections = int(num.group(1))

        # --- Experience Extraction ---
        if request.include_experience:
            # Look for experience section
            exp_section = self.soup.find("div", id=re.compile("experience", re.I))
            if exp_section:
                # Find list items representing jobs
                items = exp_section.find_all("li", class_=re.compile("artdeco-list__item", re.I))
                for item in items:
                    exp = ExperienceData()
                    
                    title_elem = item.find("span", class_="mr1 t-bold")
                    if title_elem:
                        exp.title = title_elem.get_text(strip=True)
                        
                    company_elem = item.find("span", class_="t-14 t-normal")
                    if company_elem:
                        exp.company = company_elem.get_text(strip=True).split('·')[0].strip()
                        
                    date_elem = item.find("span", class_="t-14 t-normal t-black--light")
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        parts = date_str.split('·')
                        if len(parts) > 0:
                            dates = parts[0].split('-')
                            exp.startDate = dates[0].strip()
                            if len(dates) > 1:
                                exp.endDate = dates[1].strip()
                        if len(parts) > 1:
                            exp.duration = parts[1].strip()
                            
                    data.experience.append(exp)

        # --- Education Extraction ---
        if request.include_education:
            edu_section = self.soup.find("div", id=re.compile("education", re.I))
            if edu_section:
                items = edu_section.find_all("li", class_=re.compile("artdeco-list__item", re.I))
                for item in items:
                    edu = EducationData()
                    school_elem = item.find("span", class_="mr1 hoverable-link-text t-bold")
                    if school_elem:
                        edu.school = school_elem.get_text(strip=True)
                    
                    degree_elem = item.find("span", class_="t-14 t-normal")
                    if degree_elem:
                        edu.degree = degree_elem.get_text(strip=True)
                        
                    date_elem = item.find("span", class_="t-14 t-normal t-black--light")
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        dates = date_str.split('-')
                        if len(dates) > 0:
                            try:
                                edu.startYear = int(re.search(r'\d{4}', dates[0]).group())
                            except: pass
                        if len(dates) > 1:
                            try:
                                edu.endYear = int(re.search(r'\d{4}', dates[1]).group())
                            except: pass
                            
                    data.education.append(edu)

        # --- Skills Extraction ---
        if request.include_skills:
            skills_section = self.soup.find("div", id=re.compile("skills", re.I))
            if skills_section:
                skill_items = skills_section.find_all("span", class_="mr1 hoverable-link-text t-bold")
                for s in skill_items:
                    name = s.get_text(strip=True)
                    data.skills.append(SkillData(name=name, endorsements=0)) # Endorsements hard to extract

        # --- Endorsements and Recommendations (Stubs) ---
        # Highly nested and dynamic, requires specific targeted scraping logic per profile layout.
        
        return data
