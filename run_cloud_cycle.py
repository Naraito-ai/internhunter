import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent.memory import memory_store
from agent.heartbeat import heartbeat
from agent.tentacles.notifier import notifier

async def main():
    print("🚀 Running InternHunter 24/7 Cloud Scrape & Alert Cycle...")
    
    # Connect bot briefly to allow sending DMs / channel messages
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if token:
        asyncio.create_task(notifier.start_bot())
        # wait 3 seconds for Discord bot login
        await asyncio.sleep(4)
    
    # Run 1 full scrape -> score -> notify cycle for all registered users
    await heartbeat.run_cycle()
    print("✅ Cycle completed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
