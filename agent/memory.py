import os
import json
import time
from typing import Dict, Any, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")
PREFERENCES_FILE = os.path.join(DATA_DIR, "preferences.json")
APPLIED_JOBS_FILE = os.path.join(DATA_DIR, "applied_jobs.json")
LOGS_FILE = os.path.join(DATA_DIR, "activity_logs.json")

class MemoryStore:
    """
    Handles file-based JSON persistence for student profiles, preferences,
    scraped internship listings, and execution activity logs.
    """
    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        """Ensures all default JSON storage files exist with sensible student defaults."""
        if not os.path.exists(PROFILE_FILE):
            default_profile = {
                "full_name": "Sai Varshith Uduthalaboina",
                "email": "saivarshithuduthalaboina@gmail.com",
                "phone": "+91 98765 43210",
                "linkedin": "https://linkedin.com/in/saivarshith",
                "github": "https://github.com/Naraito-ai",
                "portfolio": "https://naraito-portfolio.dev",
                "skills": ["Python", "FastAPI", "Machine Learning", "PyTorch", "React", "SQL", "Git", "REST APIs"],
                "experience_summary": "B.Tech AI/ML Final Year Student with hands-on experience building autonomous agents, backend APIs, and web scrapers.",
                "education": "B.Tech in Artificial Intelligence & Machine Learning (2022-2026)",
                "resume_text": "B.Tech AI/ML Student skilled in Python, FastAPI, Machine Learning, Deep Learning, SQL, and Web Scraping. Built multiple full-stack AI agents, discord automation tools, and predictive models."
            }
            self.save_profile(default_profile)

        if not os.path.exists(PREFERENCES_FILE):
            default_preferences = {
                "target_roles": ["AI Intern", "Python Developer", "Machine Learning Intern", "Backend Developer Intern", "Software Engineer Intern"],
                "work_type_priority": ["remote", "hybrid", "onsite"],
                "locations": ["Remote", "Bangalore", "Hyderabad", "Mumbai", "Delhi NCR"],
                "min_stipend": 5000,
                "skills_to_match": ["Python", "FastAPI", "Machine Learning", "AI", "SQL", "React"],
                "blacklisted_companies": ["UnpaidScamCorp"],
                "blacklisted_domains": ["spam-agency.com"],
                "alert_new_only": True
            }
            self.save_preferences(default_preferences)

        if not os.path.exists(APPLIED_JOBS_FILE):
            with open(APPLIED_JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

        if not os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_profile(self) -> Dict[str, Any]:
        """Retrieves user profile data."""
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves user profile data."""
        current = self.get_profile()
        current.update(data)
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return current

    def get_preferences(self) -> Dict[str, Any]:
        """Retrieves internship preferences."""
        try:
            with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves updated internship preferences."""
        current = self.get_preferences()
        current.update(data)
        with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return current

    def get_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves all tracked and applied internship listings."""
        try:
            with open(APPLIED_JOBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single internship listing by ID."""
        jobs = self.get_jobs()
        return jobs.get(job_id)

    def is_already_seen(self, job_id: str) -> bool:
        """Checks if a job listing has already been processed and saved."""
        jobs = self.get_jobs()
        return job_id in jobs

    def save_job(self, job: Dict[str, Any]):
        """Saves or updates a job listing in memory."""
        jobs = self.get_jobs()
        job_id = job.get("id")
        if not job_id:
            return
        jobs[job_id] = job
        with open(APPLIED_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)

    def update_job_status(self, job_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Updates the status (e.g. 'applied', 'new', 'ignored') of a specific job listing."""
        jobs = self.get_jobs()
        if job_id in jobs:
            jobs[job_id]["status"] = status
            if status == "applied":
                jobs[job_id]["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(APPLIED_JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(jobs, f, indent=2)
            return jobs[job_id]
        return None

    def add_log(self, level: str, message: str, category: str = "general"):
        """Adds a log entry to activity_logs.json, maintaining a maximum of 100 entries."""
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

        entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "level": level,
            "category": category,
            "message": message
        }
        logs.insert(0, entry)
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs[:100], f, indent=2)
        return entry

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent activity logs."""
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
                return logs[:limit]
        except Exception:
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Calculates aggregate statistics across all scraped and applied jobs."""
        jobs = self.get_jobs()
        job_list = list(jobs.values())
        
        today_str = time.strftime("%Y-%m-%d")
        scraped_today = [j for j in job_list if j.get("discovered_at", "").startswith(today_str)]
        applied_list = [j for j in job_list if j.get("status") == "applied"]
        alerted_today = [j for j in job_list if j.get("alerted_at", "").startswith(today_str)]
        
        scores = [j.get("fit_score", 0) for j in job_list if "fit_score" in j]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        platform_breakdown = {}
        for j in job_list:
            plat = j.get("platform", "Unknown")
            platform_breakdown[plat] = platform_breakdown.get(plat, 0) + 1

        return {
            "total_scraped_today": len(scraped_today),
            "total_applied": len(applied_list),
            "total_jobs_tracked": len(job_list),
            "avg_fit_score": avg_score,
            "platform_breakdown": platform_breakdown,
            "listings_alerted_today": len(alerted_today)
        }

memory_store = MemoryStore()
