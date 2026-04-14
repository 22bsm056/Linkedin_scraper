import re
from typing import List, Optional
from bs4 import BeautifulSoup
from routers.profile import ExtractedData, ProfileData, ExperienceData, EducationData, SkillData
from scraper.cleaner import ProfileCleaner

class ProfileParser:
    def __init__(self, html: str, url: str):
        self.soup = BeautifulSoup(html, "html.parser")
        self.url = url
        self.cleaner = ProfileCleaner()

    def parse(self, request) -> ExtractedData:
        # Focus on workspace or main content to avoid sidebar/nav noise
        main_content = self.soup.find("main", id="workspace") or \
                       self.soup.find("div", {"role": "main"}) or \
                       self.soup
        
        data = ExtractedData(
            profile=self.parse_profile_base(main_content, self.url)
        )
        
        if request.include_experience:
            data.experience = self.parse_experience(str(self.soup))
            
        if request.include_education:
            data.education = self.parse_education(str(self.soup))
            
        if request.include_skills:
            data.skills = self.parse_skills(str(self.soup))
        
        return data

    def parse_profile_base(self, soup_node, url: str) -> ProfileData:
        # 1. Name Strategy - Focus on the top-card area
        full_name = ""
        # Look for the primary identity heading
        name_node = soup_node.find("h1", class_=re.compile("text-heading-xlarge")) or \
                    soup_node.find("h2", class_=re.compile("text-heading-xlarge"))
        
        if not name_node:
            # Fallback: Find the first H1 that isn't empty
            for h1 in soup_node.find_all("h1"):
                txt = h1.get_text(strip=True)
                if txt and "notifications" not in txt.lower():
                    name_node = h1
                    break

        if name_node:
            full_name = self.cleaner.clean_text(name_node.get_text())
            # Strip titles/pronouns in parens often found in LinkedIn names
            full_name = re.split(r'\s+·\s+|\s+\(', full_name)[0]

        # 2. Headline Strategy
        headline = ""
        headline_elem = soup_node.find("div", class_=re.compile("text-body-medium")) or \
                        soup_node.find("p", class_=re.compile("headline|subline", re.I))
        if headline_elem:
            headline = self.cleaner.clean_text(headline_elem.get_text())

        # 3. Location Strategy
        location = ""
        loc_elem = soup_node.find("span", class_=re.compile("text-body-small.*inline t-black--light"))
        if loc_elem:
            location = self.cleaner.clean_text(loc_elem.get_text())

        # 4. Connections & Followers
        connections = None
        followers = None
        conn_text = soup_node.find(text=re.compile(r"\d+[\+,]?\s+connections", re.I))
        if conn_text:
            match = re.search(r"(\d+)", conn_text)
            if match: connections = int(match.group(1))

        foll_text = soup_node.find(text=re.compile(r"[\d,]+\s+followers", re.I))
        if foll_text:
            match = re.search(r"([\d,]+)", foll_text)
            if match: followers = int(match.group(1).replace(",", ""))

        # 5. About
        summary = ""
        about_section = soup_node.find("section", id="about-section") or \
                        soup_node.find("section", class_=re.compile("about", re.I))
        if about_section:
            summary_node = about_section.find("div", class_=re.compile("inline-show-more-text")) or \
                           about_section.find("span", {"aria-hidden": "true"})
            if summary_node:
                summary = self.cleaner.clean_text(summary_node.get_text(separator="\n"))

        parts = full_name.split(" ", 1)
        return ProfileData(
            firstName=parts[0] if parts else None,
            lastName=parts[1] if len(parts) > 1 else None,
            headline=headline,
            summary=summary,
            location=location,
            connections=connections,
            followers=followers,
            profileUrl=url
        )

    def parse_experience(self, html: str) -> List[ExperienceData]:
        raw_items = self._extract_section(html, "experience")
        for item in raw_items:
            item.description = self.cleaner.clean_text(item.description)
            item.title = self.cleaner.clean_text(item.title)
            item.company = self.cleaner.clean_text(item.company)
            item.duration = self.cleaner.extract_duration(item.duration)
        return raw_items

    def parse_education(self, html: str) -> List[EducationData]:
        raw_items = self._extract_section(html, "education")
        for item in raw_items:
            item.school = self.cleaner.clean_text(item.school)
            item.degree = self.cleaner.clean_text(item.degree)
            item.field = self.cleaner.clean_text(item.field)
        return raw_items

    def parse_skills(self, html: str) -> List[SkillData]:
        raw_items = self._extract_section(html, "skills")
        # De-duplicate skills based on cleaned names
        unique_skills = {}
        for skill in raw_items:
            clean_name = self.cleaner.clean_text(skill.name)
            if clean_name and clean_name.lower() not in unique_skills:
                skill.name = clean_name
                unique_skills[clean_name.lower()] = skill
        return list(unique_skills.values())

    def _extract_section(self, html: str, section_type: str) -> List[any]:
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Strategy 1: Look for detail items (div with componentkey entity-collection-item)
        items = soup.find_all("div", {"componentkey": re.compile(r"entity-collection-item")})
        
        # Strategy 2: Fallback to LazyColumn children
        if not items:
            lazy_col = soup.find("div", {"data-component-type": "LazyColumn"})
            if lazy_col:
                items = lazy_col.find_all("div", recursive=False)

        # Strategy 3: Original list item strategy
        if not items:
            items = soup.find_all("li", class_=re.compile("pvs-list__item|artdeco-list__item"))

        for item in items:
            try:
                # Extract all text blocks that are likely field values
                # LinkedIn often puts clean text in aria-hidden="true" spans to avoid screen-reader repetition
                spans = item.find_all("span", {"aria-hidden": "true"})
                text_lines = []
                for s in spans:
                    t = s.get_text(strip=True)
                    if t and t not in text_lines and not t.startswith("…") and t != "more":
                        text_lines.append(t)
                
                # Fallback: if no spans, look for paragraphs
                if not text_lines:
                    ps = item.find_all(["p", "span"], class_=re.compile(r"text-body|text-heading"))
                    text_lines = [p.get_text(strip=True) for p in ps if p.get_text(strip=True)]

                if not text_lines: continue

                if section_type == "experience":
                    # Check for grouped roles (same company, multiple positions)
                    # Grouped roles usually have a nested list or a specific structure
                    sub_items = item.find_all("li", class_=re.compile("pvs-list__item"))
                    if sub_items:
                        company = text_lines[0]
                        for sub in sub_items:
                            sub_spans = [s.get_text(strip=True) for s in sub.find_all("span", {"aria-hidden": "true"}) if s.get_text(strip=True)]
                            if sub_spans:
                                results.append(ExperienceData(
                                    title=sub_spans[0],
                                    company=company,
                                    duration=sub_spans[1] if len(sub_spans) > 1 else "",
                                    description=self._extract_desc_internal(sub)
                                ))
                    else:
                        # Single role
                        # Title is usually first, Company second, Dates third
                        results.append(ExperienceData(
                            title=text_lines[0],
                            company=text_lines[1] if len(text_lines) > 1 else "",
                            duration=text_lines[2] if len(text_lines) > 2 else "",
                            description=self._extract_desc_internal(item)
                        ))

                elif section_type == "education":
                    results.append(EducationData(
                        school=text_lines[0],
                        degree=text_lines[1] if len(text_lines) > 1 else "",
                        field=text_lines[2] if len(text_lines) > 2 and "–" not in text_lines[2] else ""
                    ))

                elif section_type == "skills":
                    # In skills detail page, first line is almost always the skill name
                    # Filter out noise like "Endorsed by..."
                    skill_name = text_lines[0]
                    if not any(x in skill_name.lower() for x in ["endorsed by", "skills", "endorsement"]):
                        results.append(SkillData(name=skill_name, endorsements=0))
            except Exception:
                continue

        return results

    def _extract_desc_internal(self, node):
        # Look for the description container
        desc_node = node.find("div", {"data-testid": "expandable-text-box"}) or \
                    node.find("span", {"data-testid": "expandable-text-box"}) or \
                    node.find("div", class_=re.compile("inline-show-more-text"))
        
        if desc_node:
            # Remove "more" and "..." buttons from description text
            for btn in desc_node.find_all("button"):
                btn.decompose()
            return desc_node.get_text(separator="\n", strip=True)
        return ""
