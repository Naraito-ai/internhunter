import os
import asyncio
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from agent.memory import memory_store
from agent.heartbeat import heartbeat
from agent.tentacles.notifier import notifier

app = FastAPI(title="InternHunter 🎯 AI Internship Agent", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    """Starts the heartbeat scheduler and Discord bot background task on server startup."""
    memory_store.add_log("INFO", "InternHunter Agent system booting...", "system")
    heartbeat.start()
    # Launch Discord bot as concurrent background task
    asyncio.create_task(notifier.start_bot())

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shuts down scheduler."""
    heartbeat.stop()

@app.get("/")
async def serve_index():
    """Serves the single page dashboard HTML interface."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Pydantic Input Schemas
class ProfileUpdateModel(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    portfolio: Optional[str] = ""
    skills: List[str]
    experience_summary: Optional[str] = ""
    education: Optional[str] = ""
    resume_text: Optional[str] = ""

class PreferencesUpdateModel(BaseModel):
    target_roles: List[str]
    work_type_priority: List[str]
    locations: List[str]
    min_stipend: float
    skills_to_match: List[str]
    blacklisted_companies: Optional[List[str]] = []
    blacklisted_domains: Optional[List[str]] = []
    alert_new_only: Optional[bool] = True

# API Endpoints
@app.get("/api/profile")
async def get_profile():
    return memory_store.get_profile()

@app.post("/api/profile")
async def update_profile(profile: ProfileUpdateModel):
    updated = memory_store.save_profile(profile.dict())
    memory_store.add_log("SUCCESS", "Updated profile preferences.", "system")
    return updated

@app.get("/api/preferences")
async def get_preferences():
    return memory_store.get_preferences()

@app.post("/api/preferences")
async def update_preferences(prefs: PreferencesUpdateModel):
    updated = memory_store.save_preferences(prefs.dict())
    memory_store.add_log("SUCCESS", "Updated search preferences.", "system")
    return updated

@app.get("/api/jobs")
async def get_jobs(
    platform: Optional[str] = None,
    min_score: Optional[int] = None,
    work_type: Optional[str] = None,
    is_new: Optional[bool] = None
):
    jobs_dict = memory_store.get_jobs()
    job_list = list(jobs_dict.values())

    if platform:
        job_list = [j for j in job_list if j.get("platform", "").lower() == platform.lower()]
    if min_score is not None:
        job_list = [j for j in job_list if j.get("fit_score", 0) >= min_score]
    if work_type:
        job_list = [j for j in job_list if j.get("work_type", "").lower() == work_type.lower()]
    if is_new is not None:
        job_list = [j for j in job_list if j.get("is_new") == is_new]

    # Sort by fit_score descending
    job_list.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
    return job_list

@app.get("/api/jobs/{job_id}")
async def get_job_detail(job_id: str):
    job = memory_store.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    return job

@app.post("/api/jobs/{job_id}/apply")
async def mark_job_applied(job_id: str):
    updated = memory_store.update_job_status(job_id, "applied")
    if not updated:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    memory_store.add_log("SUCCESS", f"Marked job '{updated.get('title')}' as applied.", "system")
    return {"status": "success", "job": updated}

@app.get("/api/stats")
async def get_stats():
    stats = memory_store.get_stats()
    stats["last_run"] = heartbeat.last_run or "Never"
    stats["cycle_count"] = heartbeat.cycle_count
    stats["discord_connected"] = notifier.is_connected
    return stats

@app.get("/api/logs")
async def get_logs():
    return memory_store.get_logs(limit=50)

@app.post("/api/run-now")
async def trigger_run_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(heartbeat.trigger_manual_cycle)
    memory_store.add_log("INFO", "Manual scrape cycle requested via API.", "system")
    return {"status": "cycle started"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
