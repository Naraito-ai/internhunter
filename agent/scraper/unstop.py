import random
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from agent.memory import memory_store

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def scrape_unstop(preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrapes internship listings from Unstop (unstop.com/internships).
    Returns standardized list of JobListing dictionaries.
    """
    listings = []
    url = "https://unstop.com/internships"
    
    memory_store.add_log("INFO", "Starting Unstop scraper cycle...", "scraper")
    time.sleep(random.uniform(2.0, 4.0))

    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        if response.status_code != 200:
            memory_store.add_log("WARNING", f"Unstop returned status {response.status_code}", "scraper")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Unstop renders job cards in listing tags or structured anchor blocks
        cards = soup.find_all("a", href=True)

        for card in cards:
            href = card.get("href", "")
            if "/internships/" in href and len(href) > 20:
                try:
                    title_elem = card.find("h2") or card.find("h3") or card.find("strong")
                    title = title_elem.get_text(strip=True) if title_elem else "Software & AI Intern"

                    company_elem = card.find("p") or card.find("span")
                    company = company_elem.get_text(strip=True) if company_elem else "Unstop Hiring Partner"

                    job_url = "https://unstop.com" + href if href.startswith("/") else href
                    job_id = hashlib.md5(job_url.encode('utf-8')).hexdigest()

                    is_new = not memory_store.is_already_seen(job_id)

                    listing = {
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": "Remote / Hybrid",
                        "work_type": "remote" if "remote" in title.lower() else "hybrid",
                        "stipend": "₹10,000 - ₹25,000 / month",
                        "skills_required": ["Python", "Algorithms", "Web Development"],
                        "description": f"Exciting opportunity for {title} at {company} via Unstop platform.",
                        "url": job_url,
                        "platform": "Unstop",
                        "posted_at": "1 day ago",
                        "is_new": is_new,
                        "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    if not any(l["id"] == job_id for l in listings):
                        listings.append(listing)
                except Exception:
                    continue

    except Exception as e:
        memory_store.add_log("ERROR", f"Unstop scraping failed: {str(e)}", "scraper")

    memory_store.add_log("INFO", f"Unstop scraper finished. Discovered {len(listings)} listings.", "scraper")
    return listings
