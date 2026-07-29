import os
import json
import time
from typing import Dict, Any, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_DIR = os.path.join(DATA_DIR, "users")
LOGS_FILE  = os.path.join(DATA_DIR, "activity_logs.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(USERS_DIR, exist_ok=True)


# ── Per-user file paths ──────────────────────────────────────────────────────

def _user_dir(user_id: str) -> str:
    d = os.path.join(USERS_DIR, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d

def _profile_path(user_id: str)  -> str: return os.path.join(_user_dir(user_id), "profile.json")
def _prefs_path(user_id: str)    -> str: return os.path.join(_user_dir(user_id), "preferences.json")
def _jobs_path(user_id: str)     -> str: return os.path.join(_user_dir(user_id), "jobs.json")


class MemoryStore:
    """
    File-based JSON persistence supporting multiple independent users,
    each identified by their Discord user ID.
    Also manages global activity logs.
    """

    def __init__(self):
        self._ensure_logs()

    def _ensure_logs(self):
        if not os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    # ── User Registry ────────────────────────────────────────────────────────

    def get_all_users(self) -> List[str]:
        """Returns all Discord user IDs that have a saved profile."""
        try:
            return [
                d for d in os.listdir(USERS_DIR)
                if os.path.isdir(os.path.join(USERS_DIR, d))
                and os.path.exists(_profile_path(d))
            ]
        except Exception:
            return []

    def user_exists(self, user_id: str) -> bool:
        return os.path.exists(_profile_path(str(user_id)))

    # ── Profile ──────────────────────────────────────────────────────────────

    def get_profile(self, user_id: str = "default") -> Dict[str, Any]:
        """Returns a user's profile. Falls back to legacy profile.json for 'default'."""
        path = _profile_path(str(user_id))
        # Legacy single-user fallback
        if user_id == "default":
            legacy = os.path.join(DATA_DIR, "profile.json")
            if not os.path.exists(path) and os.path.exists(legacy):
                path = legacy
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_profile(self, data: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
        """Saves or updates a user's profile."""
        path = _profile_path(str(user_id))
        current = self.get_profile(user_id)
        current.update(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return current

    # ── Preferences ──────────────────────────────────────────────────────────

    def get_preferences(self, user_id: str = "default") -> Dict[str, Any]:
        """Returns a user's internship search preferences."""
        path = _prefs_path(str(user_id))
        if user_id == "default":
            legacy = os.path.join(DATA_DIR, "preferences.json")
            if not os.path.exists(path) and os.path.exists(legacy):
                path = legacy
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "target_roles": [],
                "work_type_priority": ["remote", "hybrid", "onsite"],
                "locations": ["Remote"],
                "min_stipend": 0,
                "skills_to_match": [],
                "blacklisted_companies": [],
                "alert_new_only": True
            }

    def save_preferences(self, data: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
        """Saves or updates a user's search preferences."""
        path = _prefs_path(str(user_id))
        current = self.get_preferences(user_id)
        current.update(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return current

    # ── Jobs (per-user) ──────────────────────────────────────────────────────

    def get_jobs(self, user_id: str = "default") -> Dict[str, Dict[str, Any]]:
        """Returns all tracked listings for a user."""
        path = _jobs_path(str(user_id))
        if user_id == "default":
            legacy = os.path.join(DATA_DIR, "applied_jobs.json")
            if not os.path.exists(path) and os.path.exists(legacy):
                path = legacy
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_job_by_id(self, job_id: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
        return self.get_jobs(user_id).get(job_id)

    def is_already_seen(self, job_id: str, user_id: str = "default") -> bool:
        return job_id in self.get_jobs(user_id)

    def save_job(self, job: Dict[str, Any], user_id: str = "default"):
        """Saves or updates a listing in a user's job store."""
        path = _jobs_path(str(user_id))
        jobs = self.get_jobs(user_id)
        job_id = job.get("id")
        if not job_id:
            return
        jobs[job_id] = job
        with open(path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)

    def update_job_status(self, job_id: str, status: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
        path = _jobs_path(str(user_id))
        jobs = self.get_jobs(user_id)
        if job_id in jobs:
            jobs[job_id]["status"] = status
            if status == "applied":
                jobs[job_id]["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(jobs, f, indent=2)
            return jobs[job_id]
        return None

    # ── Logs (global) ────────────────────────────────────────────────────────

    def add_log(self, level: str, message: str, category: str = "general"):
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
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)[:limit]
        except Exception:
            return []

    # ── Stats (per-user or global) ───────────────────────────────────────────

    def get_stats(self, user_id: str = "default") -> Dict[str, Any]:
        jobs = self.get_jobs(user_id)
        job_list = list(jobs.values())
        today_str = time.strftime("%Y-%m-%d")

        scraped_today  = [j for j in job_list if j.get("discovered_at", "").startswith(today_str)]
        applied_list   = [j for j in job_list if j.get("status") == "applied"]
        alerted_today  = [j for j in job_list if j.get("alerted_at", "").startswith(today_str)]
        scores         = [j.get("fit_score", 0) for j in job_list if "fit_score" in j]
        avg_score      = round(sum(scores) / len(scores), 1) if scores else 0.0
        platform_breakdown = {}
        for j in job_list:
            plat = j.get("platform", "Unknown")
            platform_breakdown[plat] = platform_breakdown.get(plat, 0) + 1

        return {
            "total_scraped_today":    len(scraped_today),
            "total_applied":          len(applied_list),
            "total_jobs_tracked":     len(job_list),
            "avg_fit_score":          avg_score,
            "platform_breakdown":     platform_breakdown,
            "listings_alerted_today": len(alerted_today),
        }


memory_store = MemoryStore()
