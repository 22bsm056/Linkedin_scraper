import re
from bs4 import BeautifulSoup
from routers.profile import ExtractedData, ProfileData, ExperienceData, EducationData, SkillData, RecommendationData

class ProfileParser:
    def __init__(self, html: str, url: str):
        self.soup = BeautifulSoup(html, "html.parser")
        self.url = url

    def parse(self, request) -> ExtractedData:
        # Note: LinkedIn DOM is heavily obfuscated and changes frequently.
        # This implementation uses multiple fallbacks for robustness.
        
        data = ExtractedData(
            profile=ProfileData(profileUrl=self.url)
        )
        
        # --- Profile Extraction ---
        # 1. Name Extraction (h1 or h2 with randomized classes)
        name_elem = self.soup.find("h1") or self.soup.find("h2", class_=re.compile(r"b143311d|text-heading-xlarge", re.I))
        if not name_elem:
            # Fallback: look for the first strong header in the top card
            top_card = self.soup.find("section", componentkey=re.compile(r"Topcard", re.I))
            if top_card:
                name_elem = top_card.find(["h1", "h2", "p"], class_=re.compile(r"text-heading|b143311d", re.I))

        if name_elem:
            full_name = name_elem.get_text(separator=" ", strip=True)
            # Remove parenthetical names like "shubham (Shubham Singh) Kumar" -> "shubham Kumar"
            full_name = re.sub(r'\(.*?\)', '', full_name).replace('  ', ' ').strip()
            name_parts = full_name.split(maxsplit=1)
            data.profile.firstName = name_parts[0] if len(name_parts) > 0 else ""
            data.profile.lastName = name_parts[1] if len(name_parts) > 1 else ""

        # 2. Headline Extraction
        # Look for the element immediately following the name or with specific class patterns
        headline_elem = self.soup.find(["div", "p"], class_=re.compile(r"text-body-medium|headline|_12259b14", re.I))
        if headline_elem:
            data.profile.headline = headline_elem.get_text(strip=True)

        # 3. Location Extraction
        # Look for the element with location-like text, but avoid pronouns
        location_candidates = self.soup.find_all(["span", "p"], class_=re.compile(r"text-body-small inline|location|_76d1f132", re.I))
        for cand in location_candidates:
            text = cand.get_text(strip=True)
            # Skip pronouns (usually looks like "He/Him", "She/Her", etc.)
            if re.search(r"^(He/Him|She/Her|They/Them|He/His|She/Hers)$", text, re.I):
                continue
            if text and len(text) > 2:
                # Clean up location (it might have dots or extra spacing)
                text = re.sub(r'^\s*·\s*', '', text)
                data.profile.location = text
                break


        # 4. Connections Extraction
        conn_elem = self.soup.find(string=re.compile(r'connections', re.I))
        if conn_elem:
            num = re.search(r'(\d+)', conn_elem)
            if num:
                data.profile.connections = int(num.group(1))

        # --- Experience Extraction ---
        if request.include_experience:
            for exp_dict in self._parse_experience():
                data.experience.append(ExperienceData(**exp_dict))

        # --- Education Extraction ---
        if request.include_education:
            for edu_dict in self._parse_education():
                data.education.append(EducationData(**edu_dict))

        # --- Skills Extraction ---
        if request.include_skills:
            for skill_name in self._parse_skills():
                data.skills.append(SkillData(name=skill_name, endorsements=0))
        
        return data


    def _parse_experience(self):
        experiences = []
        # Look for both main profile cards and detail page items
        # Heuristic 1: pvs-list items (common in detail pages and modern main pages)
        items = self.soup.find_all('li', class_=re.compile(r'pvs-list__paged-list-item|experience-item'))
        
        for item in items:
            # Skip if it's not actually an experience item (e.g., belongs to education)
            # Find the closest parent section or look for keywords
            section = item.find_parent('section')
            if section:
                header = section.find(['h2', 'h3'])
                if header and 'Experience' not in header.get_text():
                    # If we are in a detail page, the section might not have the "Experience" header if it's the only section
                    # But the URL or the container might have markers
                    pass

            title_elem = item.find('div', {'display-flex': True, 'flex-column': True}) or item
            
            # Extract Title - Look for the boldest text
            title = "Unknown Role"
            title_node = item.find('span', {'aria-hidden': 'true'})
            if title_node:
                title = title_node.get_text(strip=True)

            # Extract Company
            company = "Unknown Company"
            company_node = item.find('span', class_='t-14 t-normal')
            if company_node:
                company_text = company_node.get_text(strip=True).split('·')[0].strip()
                company = company_text

            # Extract Dates and Location
            date_range = ""
            location = ""
            meta_nodes = item.find_all('span', class_='t-14 t-normal t-black--light')
            for node in meta_nodes:
                text = node.get_text(strip=True)
                if any(m in text.lower() for m in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'present', ' - ']):
                    date_range = text
                elif text and not date_range: # Fallback if dates not found yet
                     date_range = text
                else:
                    location = text

            if title != "Unknown Role" or company != "Unknown Company":
                experiences.append({
                    "title": title,
                    "company": company,
                    "startDate": date_range.split('-')[0].strip() if '-' in date_range else date_range,
                    "endDate": date_range.split('-')[1].strip() if '-' in date_range else "",
                    "duration": ""
                })
        
        # Deduplicate and filter (sometimes items are captured twice or are sub-items)
        unique_exp = []
        seen = set()
        for exp in experiences:
            key = f"{exp['title']}|{exp['company']}"
            if key not in seen:
                unique_exp.append(exp)
                seen.add(key)
        
        return unique_exp

    def _parse_education(self):
        education = []
        # Similar logic to experience but looking for education markers
        items = self.soup.find_all('li', class_=re.compile(r'pvs-list__paged-list-item|education-item'))
        for item in items:
            # Check if it's in an education context
            text_content = item.get_text().lower()
            if 'university' in text_content or 'college' in text_content or 'school' in text_content or 'degree' in text_content:
                school = "Unknown School"
                school_node = item.find('span', {'aria-hidden': 'true'})
                if school_node:
                    school = school_node.get_text(strip=True)
                
                degree = ""
                degree_node = item.find('span', class_='t-14 t-normal')
                if degree_node:
                    degree = degree_node.get_text(strip=True)

                date_range = ""
                date_node = item.find('span', class_='t-14 t-normal t-black--light')
                if date_node:
                    date_range = date_node.get_text(strip=True)

                education.append({
                    "school": school,
                    "degree": degree
                })
        
        return education

    def _parse_skills(self):
        skills = []
        # Skills are often just spans with text in a list
        skill_nodes = self.soup.find_all('div', class_=re.compile(r'display-flex align-items-center t-16 t-black t-bold'))
        for node in skill_nodes:
            skill_name = node.get_text(strip=True)
            if skill_name and skill_name not in skills:
                skills.append(skill_name)
        
        # Fallback for detail pages
        if not skills:
            items = self.soup.find_all('li', class_=re.compile(r'pvs-list__paged-list-item'))
            for item in items:
                skill_node = item.find('span', {'aria-hidden': 'true'})
                if skill_node:
                    text = skill_node.get_text(strip=True)
                    # Heuristic: skills are usually short and don't contain " - " or dates
                    if 0 < len(text) < 50 and not any(char.isdigit() for char in text):
                        if text not in skills:
                            skills.append(text)

        return skills
