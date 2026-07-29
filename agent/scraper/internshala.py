import random
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from agent.memory import memory_store

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def scrape_internshala(preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrapes internship listings from Internshala matching target roles in preferences.
    Returns standardized list of JobListing dictionaries.
    """
    listings = []
    target_roles = preferences.get("target_roles", ["python", "machine learning", "web development"])
    
    memory_store.add_log("INFO", "Starting Internshala scraper cycle...", "scraper")

    for role in target_roles[:2]: # Query first two key roles
        time.sleep(random.uniform(2.0, 5.0)) # Human-like delay
        query_keyword = role.lower().replace(" ", "-").replace("intern", "").strip("-")
        url = f"https://internshala.com/internships/{query_keyword}-internship/"

        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            if response.status_code != 200:
                memory_store.add_log("WARNING", f"Internshala returned status {response.status_code} for {url}", "scraper")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="individual_internship")

            for card in cards:
                try:
                    title_elem = card.find("h3", class_="job-internship-name") or card.find("a", class_="view_detail_button")
                    company_elem = card.find("p", class_="company-name") or card.find("div", class_="company_name")
                    loc_elem = card.find("a", class_="location_link") or card.find("div", id="location_names")
                    stipend_elem = card.find("span", class_="stipend")

                    link_elem = card.find("a", class_="view_detail_button") or card.find("a", href=True)
                    if not title_elem or not link_elem:
                        continue

                    job_url = "https://internshala.com" + link_elem["href"] if link_elem["href"].startswith("/") else link_elem["href"]
                    job_id = hashlib.md5(job_url.encode('utf-8')).hexdigest()

                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else "Internshala Employer"
                    location = loc_elem.get_text(strip=True) if loc_elem else "Remote / India"
                    stipend = stipend_elem.get_text(strip=True) if stipend_elem else "Disclosed in interview"

                    work_type = "remote" if "work from home" in location.lower() or "remote" in location.lower() else "onsite"

                    is_new = not memory_store.is_already_seen(job_id)

                    listing = {
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "work_type": work_type,
                        "stipend": stipend,
                        "skills_required": [role, "Python", "Problem Solving"],
                        "description": f"Internship position for {title} at {company}. Location: {location}. Stipend: {stipend}.",
                        "url": job_url,
                        "platform": "Internshala",
                        "posted_at": "Recently posted",
                        "is_new": is_new,
                        "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    listings.append(listing)
                except Exception as card_err:
                    continue

        except Exception as e:
            memory_store.add_log("ERROR", f"Internshala scraping failed for {url}: {str(e)}", "scraper")

    memory_store.add_log("INFO", f"Internshala scraper finished. Discovered {len(listings)} listings.", "scraper")
    return listings
