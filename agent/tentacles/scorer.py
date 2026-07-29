import os
from typing import Dict, Any, List
from agent.brain import brain
from agent.memory import memory_store

def score_and_filter_listings(listings: List[Dict[str, Any]], profile: Dict[str, Any], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates each job listing against candidate profile & preferences using LLM scoring.
    Filters listings based on MIN_FIT_SCORE (default 60) and recommendation != 'skip'.
    """
    min_score = int(os.getenv("MIN_FIT_SCORE", 60))
    qualifying = []
    
    memory_store.add_log("INFO", f"Scoring {len(listings)} newly scraped listings...", "scorer")

    for listing in listings:
        try:
            score_data = brain.score_listing(listing, profile, preferences)
            
            listing["fit_score"] = score_data.get("fit_score", 0)
            listing["match_reasons"] = score_data.get("match_reasons", [])
            listing["missing_skills"] = score_data.get("missing_skills", [])
            listing["recommendation"] = score_data.get("recommendation", "maybe")

            if listing["fit_score"] >= min_score and listing["recommendation"] != "skip":
                qualifying.append(listing)
        except Exception as e:
            memory_store.add_log("WARNING", f"Failed to score listing {listing.get('title')}: {str(e)}", "scorer")
            continue

    memory_store.add_log("INFO", f"Scoring finished. {len(qualifying)} out of {len(listings)} passed threshold (Score >= {min_score}).", "scorer")
    return qualifying
