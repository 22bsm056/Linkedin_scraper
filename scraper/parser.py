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
        # Extract base identity first to set up search filters (target_name)
        # Search TopCard area primarily
        top_card = self.soup.find("section", {"componentkey": re.compile(r"Topcard", re.I)}) or \
                   self.soup.find("section", class_=re.compile(r"top-card", re.I)) or \
                   self.soup.find("div", class_=re.compile(r"top-card", re.I))
        
        profile_root = top_card if top_card else self.soup
        
        profile_data = self.parse_profile_base(profile_root, self.url)
        self.target_name = profile_data.firstName + " " + profile_data.lastName
        
        data = ExtractedData(profile=profile_data)
        
        # HOUSEKEEPING: Decompose noise globally before section parsing
        for noise in self.soup.find_all(["aside", "nav", "footer"]):
            noise.decompose()
        for noise in self.soup.find_all(["div", "section"], componentkey=re.compile(r"Aside|Browsemap|Ads|Connect|Toast|Activity|Featured", re.I)):
            noise.decompose()

        if request.include_experience:
            data.experience = self.parse_experience()
            
        if request.include_education:
            data.education = self.parse_education()
            
        if request.include_skills:
            data.skills = self.parse_skills()
        
        return data

    def parse_profile_base(self, soup_node, url: str) -> ProfileData:
        # 1. Name Strategy - Prioritize the primary identity header in this section
        full_name = ""
        # Strategy A: Use ARIA label from the profile photo (very reliable)
        photo_node = soup_node.find("div", aria_label=True, class_=re.compile(r"photo|image|avatar", re.I)) or \
                     soup_node.find("img", alt=re.compile(r"(photo|image) of", re.I))
        if photo_node:
            full_name = photo_node.get("aria-label", photo_node.get("alt", ""))
            full_name = full_name.replace("Profile photo of ", "").replace("Profile photo", "").strip()

        # Strategy B: Look for H1/H2 identity header
        if not full_name:
            name_node = soup_node.find(["h1", "h2"], class_=re.compile(r"text-heading-xlarge|_2fc92d05", re.I))
            if name_node:
                full_name = name_node.get_text(strip=True)

        full_name = self.cleaner.clean_text(full_name)
        # Strip common noise markers like "· 2nd" or "[Verified]"
        full_name = re.split(r'\s+·\s+|\s+\[', full_name)[0]
        
        # Strip nickname/parenthetical name: "shubham (Shubham Singh) Kumar" -> "shubham Kumar"
        full_name = re.sub(r'\(.*?\)', '', full_name).strip()
        full_name = re.sub(r'\s{2,}', ' ', full_name)

        # Identity split
        parts = full_name.split()
        first_name = parts[0] if len(parts) > 0 else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # 2. Headline Strategy
        headline = ""
        # Search specifically within the soup_node for the headline
        headline_elem = soup_node.find(lambda t: t.name in ["div", "p"] and any(c in str(t.get('class', [])) for c in ["text-body-medium", "headline", "subline"]))
        if headline_elem:
            headline = self.cleaner.clean_text(headline_elem.get_text())

        # 3. Location Strategy
        location = ""
        loc_elem = soup_node.find(lambda t: t.name in ["span", "div"] and "location" in str(t.get('class', [])).lower())
        if not loc_elem:
            # Fallback for loc specifically in top-card
            loc_elem = soup_node.find("span", class_=re.compile("black--light"))
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

    def parse_experience(self) -> List[ExperienceData]:
        raw_items = self._extract_section("experience")
        for item in raw_items:
            item.description = self.cleaner.clean_text(item.description)
            item.title = self.cleaner.clean_text(item.title)
            item.company = self.cleaner.clean_text(item.company)
            item.duration = self.cleaner.extract_duration(item.duration)
        return raw_items

    def parse_education(self) -> List[EducationData]:
        raw_items = self._extract_section("education")
        for item in raw_items:
            item.school = self.cleaner.clean_text(item.school)
            item.degree = self.cleaner.clean_text(item.degree)
            item.field = self.cleaner.clean_text(item.field)
        return raw_items

    def parse_skills(self) -> List[SkillData]:
        raw_items = self._extract_section("skills")
        # De-duplicate skills based on cleaned names
        unique_skills = {}
        for skill in raw_items:
            clean_name = self.cleaner.clean_text(skill.name)
            if clean_name and clean_name.lower() not in unique_skills and len(clean_name) > 2:
                skill.name = clean_name
                unique_skills[clean_name.lower()] = skill
        return list(unique_skills.values())

    def _extract_section(self, section_type: str) -> List[any]:
        # 1. Collect all potential containers globally in the soup
        # We search for several patterns that LinkedIn uses for professional data sections
        containers = self.soup.find_all(["section", "div"], {"componentkey": re.compile(rf"{section_type}DetailsSection", re.I)})
        containers += self.soup.find_all(["section", "div"], {"componentkey": re.compile(rf"^{section_type}$", re.I)})
        containers += self.soup.find_all(["section", "div"], id=re.compile(rf"^{section_type}", re.I))
        
        # 2. Add containers found by section header text
        header_nodes = self.soup.find_all(lambda t: t.name in ["h1", "h2", "h3", "p", "span"] and section_type.lower() == t.get_text(strip=True).lower())
        for hn in header_nodes:
            c = hn.find_parent(["section", "div", "main"], class_=re.compile("artdeco-card|pvs-list|scaffold-layout|workspace", re.I))
            if c and c not in containers:
                containers.append(c)
        
        # 3. If we found nothing specific, search the whole soup (noise already removed)
        if not containers:
            containers = [self.soup]

        results = []
        valid_items = []
        
        for container in containers:
            # Aggregate items from all matching containers
            items = container.find_all("div", {"componentkey": re.compile(r"entity-collection-item")})
            items += container.find_all(["li", "div"], class_=re.compile("pvs-list__item|artdeco-list__item"))
            items += container.find_all(["div", "li", "section"], role=re.compile("listitem|article"))
            
            # Fallback for LazyColumn
            if not items:
                lazy_cols = container.find_all("div", {"data-component-type": "LazyColumn"})
                for lc in lazy_cols:
                    items += lc.find_all("div", recursive=False)

            for it in items:
                # HEURISTIC: Skip if it looks like an activity/reaction post (e.g. '8 comments')
                item_text = it.get_text().lower()
                if " reaction" in item_text and " comment" in item_text:
                    continue
                
                # Deduplicate by looking at content or object identity
                if any(it.get_text() == v.get_text() for v in valid_items):
                    continue
                
                valid_items.append(it)
        
        for item in valid_items:
            try:
                # Use stripped_strings for robust text collection
                text_lines = [s.strip() for s in item.stripped_strings if len(s.strip()) > 1]
                # Filter out single character lines and common noise
                text_lines = [l for l in text_lines if not l.startswith("…") and l.lower() != "more"]
                
                # Filter out the 'identity' block that often appears at top of SDUI detail pages
                # If the first few lines are just personal names, skip
                if len(text_lines) > 0 and self.target_name and self.target_name.lower() in text_lines[0].lower():
                    # Check if this is the large identity card (it usually has pronouns or followers nearby)
                    if any("follower" in l.lower() or "pronoun" in l.lower() or "connect" in l.lower() for l in text_lines[:5]):
                        continue

                if not text_lines: continue

                if section_type == "experience":
                    # Determine if it's a grouped role or single role
                    # Grouped roles have a 'role-description' or nested items
                    sub_items = item.find_all(["li", "div"], class_=re.compile("pvs-list__item|artdeco-list__item"))
                    if sub_items and len(sub_items) > 0 and len(text_lines) > 0:
                        company = text_lines[0]
                        for sub in sub_items:
                            sub_text = [s.get_text(strip=True) for s in sub.find_all(["span", "p"]) if s.get_text(strip=True)]
                            if len(sub_text) >= 1:
                                results.append(ExperienceData(
                                    title=sub_text[0],
                                    company=company,
                                    duration=sub_text[1] if len(sub_text) > 1 else "",
                                    description=self._extract_desc_internal(sub)
                                ))
                    else:
                        # Single role mapping: Title, Company, Duration
                        # HEURISTIC: If first line contains 'at' or '·', it might be malformed, but usually it's [Title, Company, Date]
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
                        duration=text_lines[2] if len(text_lines) > 2 else ""
                    ))
                
                elif section_type == "skills":
                    results.append(SkillData(name=text_lines[0]))

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
