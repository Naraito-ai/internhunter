import random
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from agent.memory import memory_store

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def scrape_linkedin(preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses LinkedIn public job listings without authentication or official API.
    Returns standardized list of JobListing dictionaries.
    """
    listings = []
    target_roles = preferences.get("target_roles", ["AI Intern", "Python Developer"])
    location = preferences.get("locations", ["India"])[0] if preferences.get("locations") else "India"

    memory_store.add_log("INFO", "Starting LinkedIn public jobs scraper cycle...", "scraper")

    for role in target_roles[:2]:
        time.sleep(random.uniform(2.0, 5.0))
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobCards?keywords={role}&location={location}&f_JT=I"

        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            if response.status_code != 200:
                memory_store.add_log("WARNING", f"LinkedIn public feed returned status {response.status_code}", "scraper")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("li")

            for card in cards:
                try:
                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    loc_elem = card.find("span", class_="job-search-card__location")
                    link_elem = card.find("a", class_="base-card__full-link") or card.find("a", href=True)

                    if not title_elem or not link_elem:
                        continue

                    job_url = link_elem["href"].split("?")[0]
                    job_id = hashlib.md5(job_url.encode('utf-8')).hexdigest()

                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else "LinkedIn Employer"
                    job_loc = loc_elem.get_text(strip=True) if loc_elem else location

                    work_type = "remote" if "remote" in job_loc.lower() or "remote" in title.lower() else "onsite"
                    is_new = not memory_store.is_already_seen(job_id)

                    listing = {
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "work_type": work_type,
                        "stipend": "Disclosed upon application",
                        "skills_required": [role, "Python", "Engineering"],
                        "description": f"LinkedIn Internship opportunity for {title} at {company} ({job_loc}).",
                        "url": job_url,
                        "platform": "LinkedIn",
                        "posted_at": "Just now",
                        "is_new": is_new,
                        "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    listings.append(listing)
                except Exception:
                    continue

        except Exception as e:
            memory_store.add_log("ERROR", f"LinkedIn scraper failed for {url}: {str(e)}", "scraper")

    memory_store.add_log("INFO", f"LinkedIn scraper finished. Discovered {len(listings)} listings.", "scraper")
    return listings
