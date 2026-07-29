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
    APScheduler Heartbeat module running full scrape -> score -> generate -> notify cycles
    at configured intervals (default 30 minutes).
    """
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.cycle_count = 0
        self.last_run = None
        self.executor = ThreadPoolExecutor(max_workers=3)

    def start(self):
        """Starts the periodic background scheduler."""
        if not self.is_running:
            interval = int(os.getenv("RUN_INTERVAL_MINUTES", 30))
            self.scheduler.add_job(self.run_cycle, 'interval', minutes=interval, id="scrape_cycle")
            self.scheduler.start()
            self.is_running = True
            memory_store.add_log("INFO", f"InternHunter Heartbeat started ({interval}-minute interval).", "heartbeat")

    def stop(self):
        """Pauses the background scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            memory_store.add_log("INFO", "InternHunter Heartbeat paused.", "heartbeat")

    async def trigger_manual_cycle(self):
        """Triggers an immediate scrape and evaluation cycle on demand."""
        await self.run_cycle()

    async def run_cycle(self):
        """Executes a full scraping, LLM scoring, artifact generation, and Discord alert cycle."""
        self.cycle_count += 1
        self.last_run = time.strftime("%Y-%m-%d %H:%M:%S")
        memory_store.add_log("INFO", f"=== Starting Scrape Cycle #{self.cycle_count} ===", "heartbeat")

        profile = memory_store.get_profile()
        preferences = memory_store.get_preferences()

        # Run scrapers concurrently in thread pool to prevent blocking event loop
        loop = asyncio.get_event_loop()
        try:
            results = await asyncio.gather(
                loop.run_in_executor(self.executor, scrape_internshala, preferences),
                loop.run_in_executor(self.executor, scrape_unstop, preferences),
                loop.run_in_executor(self.executor, scrape_linkedin, preferences),
                return_exceptions=True
            )
        except Exception as e:
            memory_store.add_log("ERROR", f"Scraper execution error: {str(e)}", "heartbeat")
            results = [[], [], []]

        all_listings = []
        for res in results:
            if isinstance(res, list):
                all_listings.extend(res)

        memory_store.add_log("INFO", f"Discovered {len(all_listings)} total listings across all platforms.", "heartbeat")

        # Filter out already alerted/applied listings if alert_new_only is set
        alert_new_only = preferences.get("alert_new_only", True)
        unseen_listings = [l for l in all_listings if not memory_store.is_already_seen(l["id"])] if alert_new_only else all_listings

        # Score listings using Groq Brain
        qualifying = score_and_filter_listings(unseen_listings, profile, preferences)

        # Generate artifacts and send Discord notifications
        alerted_count = 0
        for listing in qualifying:
            generate_job_artifacts(listing, profile)
            await notifier.send_job_alert(listing)
            alerted_count += 1

        memory_store.add_log(
            "SUCCESS",
            f"=== Completed Cycle #{self.cycle_count} | Found: {len(all_listings)} | Qualifying: {len(qualifying)} | Alerts Sent: {alerted_count} ===",
            "heartbeat"
        )

heartbeat = AgentHeartbeat()
