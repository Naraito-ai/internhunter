import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.memory import memory_store
from agent.scraper.internshala import scrape_internshala
from agent.scraper.unstop import scrape_unstop
from agent.scraper.linkedin import scrape_linkedin
from agent.tentacles.scorer import score_and_filter_listings
from agent.tentacles.generator import generate_job_artifacts
from agent.tentacles.notifier import notifier


class AgentHeartbeat:
    """
    APScheduler Heartbeat — runs a full scrape → score → generate → DM cycle
    for EVERY registered Discord user at the configured interval.
    """

    def __init__(self):
        self.scheduler   = AsyncIOScheduler()
        self.is_running  = False
        self.cycle_count = 0
        self.last_run    = None
        self.executor    = ThreadPoolExecutor(max_workers=3)

    def start(self):
        if not self.is_running:
            interval = int(os.getenv("RUN_INTERVAL_MINUTES", 30))
            self.scheduler.add_job(self.run_cycle, "interval", minutes=interval, id="scrape_cycle")
            self.scheduler.start()
            self.is_running = True
            memory_store.add_log("INFO", f"Heartbeat started ({interval}-min interval, multi-user mode).", "heartbeat")

    def stop(self):
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            memory_store.add_log("INFO", "Heartbeat paused.", "heartbeat")

    async def trigger_manual_cycle(self, user_id: str = None):
        """Trigger immediately for a specific user (Discord /runnow) or all users (scheduler)."""
        await self.run_cycle(user_id=user_id)

    async def run_cycle(self, user_id: str = None):
        """
        Full pipeline for one user (if user_id given) or all registered users.
        Scrapers run once and are shared across users to avoid duplicate requests.
        Each user is scored independently and gets a DM with their own matches.
        """
        self.cycle_count += 1
        self.last_run = time.strftime("%Y-%m-%d %H:%M:%S")

        # ── Decide which users to run for ────────────────────────────────────
        if user_id:
            users = [str(user_id)]
        else:
            users = memory_store.get_all_users()
            if not users:
                memory_store.add_log("WARNING", "No registered users found. Have someone run /myprofile on Discord first.", "heartbeat")
                return

        memory_store.add_log("INFO", f"=== Cycle #{self.cycle_count} | Running for {len(users)} user(s) ===", "heartbeat")

        # ── Scrape once — shared across all users ─────────────────────────────
        # Use merged preferences (all target roles from all users) for broad scraping
        merged_prefs = _merge_preferences(users)

        loop = asyncio.get_event_loop()
        try:
            results = await asyncio.gather(
                loop.run_in_executor(self.executor, scrape_internshala, merged_prefs),
                loop.run_in_executor(self.executor, scrape_unstop,      merged_prefs),
                loop.run_in_executor(self.executor, scrape_linkedin,    merged_prefs),
                return_exceptions=True
            )
        except Exception as e:
            memory_store.add_log("ERROR", f"Scraper error: {str(e)}", "heartbeat")
            results = [[], [], []]

        all_listings = []
        for res in results:
            if isinstance(res, list):
                all_listings.extend(res)

        memory_store.add_log("INFO", f"Scraped {len(all_listings)} total listings.", "heartbeat")

        # ── Score and alert each user independently ───────────────────────────
        for uid in users:
            await self._run_for_user(uid, all_listings)

        memory_store.add_log("SUCCESS", f"=== Cycle #{self.cycle_count} complete ===", "heartbeat")

    async def _run_for_user(self, user_id: str, all_listings: list):
        """Score all listings against one user's profile and DM them their matches."""
        profile = memory_store.get_profile(user_id)
        prefs   = memory_store.get_preferences(user_id)

        if not profile.get("full_name"):
            return  # user registered but hasn't filled profile yet

        # Filter already-seen listings for this user
        alert_new_only = prefs.get("alert_new_only", True)
        unseen = (
            [l for l in all_listings if not memory_store.is_already_seen(l["id"], user_id)]
            if alert_new_only else all_listings
        )

        qualifying = score_and_filter_listings(unseen, profile, prefs)

        alerted = 0
        for listing in qualifying:
            generate_job_artifacts(listing, profile)
            memory_store.save_job(listing, user_id)
            await notifier.send_job_alert_to_user(listing, user_id)
            alerted += 1

        if alerted:
            memory_store.add_log(
                "SUCCESS",
                f"User {user_id} → {alerted} alert(s) sent | {len(qualifying)} qualifying out of {len(unseen)} unseen",
                "heartbeat"
            )
        else:
            memory_store.add_log(
                "INFO",
                f"User {user_id} → no new qualifying listings this cycle.",
                "heartbeat"
            )


def _merge_preferences(user_ids: list) -> dict:
    """Merge all users' target_roles and locations so scraper casts a wide net."""
    all_roles = set()
    all_locs  = set()
    min_stip  = 0

    for uid in user_ids:
        p = memory_store.get_preferences(uid)
        all_roles.update(p.get("target_roles", []))
        all_locs.update(p.get("locations", []))
        min_stip = min(min_stip, p.get("min_stipend", 0))

    return {
        "target_roles":        list(all_roles) or ["Intern", "Software Intern"],
        "locations":           list(all_locs)  or ["Remote"],
        "work_type_priority":  ["remote", "hybrid", "onsite"],
        "min_stipend":         min_stip,
        "skills_to_match":     [],
        "blacklisted_companies": [],
        "alert_new_only":      False,  # handled per-user above
    }


heartbeat = AgentHeartbeat()
