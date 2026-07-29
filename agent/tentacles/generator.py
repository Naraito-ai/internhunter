from typing import Dict, Any, List
from agent.brain import brain
from agent.memory import memory_store

def generate_job_artifacts(listing: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates personalized cover letter and application answers at scrape time,
    storing them into the listing dict and saving immediately to applied_jobs.json.
    """
    memory_store.add_log("INFO", f"Generating cover letter & Q&A answers for {listing.get('title')} @ {listing.get('company')}", "generator")

    cover_letter = brain.generate_cover_letter(listing, profile)
    answers = brain.generate_application_answers(listing, profile)

    listing["cover_letter"] = cover_letter
    listing["generated_answers"] = answers
    listing["status"] = listing.get("status", "new")

    # Persist immediately to applied_jobs.json
    memory_store.save_job(listing)
    return listing
