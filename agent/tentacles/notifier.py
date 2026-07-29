import os
import time
import asyncio
import discord
from discord import app_commands
from typing import Dict, Any, Optional, List
from agent.memory import memory_store

class DiscordNotifier:
    """
    Discord Bot integration using discord.py for sending rich job embed alerts
    and handling slash commands concurrently alongside FastAPI.
    """
    def __init__(self):
        intents = discord.Intents.default()
        self.bot = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.bot)
        self.is_connected = False
        self.channel_id = None
        self._setup_events()
        self._register_commands()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            self.is_connected = True
            try:
                await self.tree.sync()
                memory_store.add_log("SUCCESS", f"Discord Bot connected as {self.bot.user} and slash commands synced.", "discord")
            except Exception as e:
                memory_store.add_log("WARNING", f"Failed to sync slash commands: {str(e)}", "discord")

    def _register_commands(self):
        @self.tree.command(name="coverletter", description="Fetch generated cover letter for an internship")
        async def coverletter_cmd(interaction: discord.Interaction, job_id: str):
            job = memory_store.get_job_by_id(job_id)
            if not job:
                await interaction.response.send_message(f"❌ Job with ID `{job_id}` not found.", ephemeral=True)
                return
            letter = job.get("cover_letter", "No cover letter generated.")
            msg = f"📄 **Cover Letter for {job.get('title')} @ {job.get('company')}**\n```text\n{letter}\n```"
            await interaction.response.send_message(msg[:2000])

        @self.tree.command(name="answers", description="Fetch generated application screening answers")
        async def answers_cmd(interaction: discord.Interaction, job_id: str):
            job = memory_store.get_job_by_id(job_id)
            if not job:
                await interaction.response.send_message(f"❌ Job with ID `{job_id}` not found.", ephemeral=True)
                return
            answers = job.get("generated_answers", {})
            formatted = f"📝 **Application Answers for {job.get('title')} @ {job.get('company')}**\n\n"
            for q, a in answers.items():
                formatted += f"**Q: {q}**\n> {a}\n\n"
            await interaction.response.send_message(formatted[:2000])

        @self.tree.command(name="status", description="Show InternHunter status and metrics")
        async def status_cmd(interaction: discord.Interaction):
            stats = memory_store.get_stats()
            from agent.heartbeat import heartbeat
            status_label = "🟢 Running" if heartbeat.is_running else "🟡 Paused"

            embed = discord.Embed(
                title="🎯 InternHunter Agent Status",
                color=0x00ff88 if heartbeat.is_running else 0xffaa00
            )
            embed.add_field(name="Status", value=status_label, inline=True)
            embed.add_field(name="Listings Scraped Today", value=str(stats.get("total_scraped_today", 0)), inline=True)
            embed.add_field(name="Alerts Sent Today", value=str(stats.get("listings_alerted_today", 0)), inline=True)
            embed.add_field(name="Total Applied All Time", value=str(stats.get("total_applied", 0)), inline=True)
            embed.add_field(name="Average Fit Score", value=f"{stats.get('avg_fit_score', 0)}%", inline=True)
            embed.set_footer(text=f"Cycle Interval: {os.getenv('RUN_INTERVAL_MINUTES', 30)} minutes")
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="preferences", description="Show current internship search preferences")
        async def preferences_cmd(interaction: discord.Interaction):
            prefs = memory_store.get_preferences()
            embed = discord.Embed(title="⚙️ Current InternHunter Preferences", color=0x3b82f6)
            embed.add_field(name="Target Roles", value=", ".join(prefs.get("target_roles", [])), inline=False)
            embed.add_field(name="Work Types", value=" > ".join(prefs.get("work_type_priority", [])), inline=True)
            embed.add_field(name="Locations", value=", ".join(prefs.get("locations", [])), inline=True)
            embed.add_field(name="Min Stipend", value=f"₹{prefs.get('min_stipend', 0)}/month", inline=True)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="runnow", description="Trigger an immediate scrape and alert cycle")
        async def runnow_cmd(interaction: discord.Interaction):
            await interaction.response.send_message("⚡ Scrape cycle started! Running in background...")
            from agent.heartbeat import heartbeat
            asyncio.create_task(heartbeat.trigger_manual_cycle())

        @self.tree.command(name="pause", description="Pause automated heartbeat cycle")
        async def pause_cmd(interaction: discord.Interaction):
            from agent.heartbeat import heartbeat
            heartbeat.stop()
            await interaction.response.send_message("⏸️ Agent heartbeat paused.")

        @self.tree.command(name="resume", description="Resume automated heartbeat cycle")
        async def resume_cmd(interaction: discord.Interaction):
            from agent.heartbeat import heartbeat
            heartbeat.start()
            await interaction.response.send_message("▶️ Agent heartbeat resumed.")

    async def start_bot(self):
        token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        channel_raw = os.getenv("DISCORD_CHANNEL_ID", "").strip()

        if channel_raw.isdigit():
            self.channel_id = int(channel_raw)

        if not token or token == "your_discord_bot_token_here":
            memory_store.add_log("WARNING", "Discord bot token not set in .env. Bot standing by.", "discord")
            return

        try:
            memory_store.add_log("INFO", "Connecting Discord bot...", "discord")
            await self.bot.start(token)
        except Exception as e:
            memory_store.add_log("ERROR", f"Discord bot failed to start: {str(e)}", "discord")

    async def send_job_alert(self, listing: Dict[str, Any]):
        """
        Sends a rich Discord embed alert for a qualifying job listing.
        """
        if not self.is_connected or not self.channel_id:
            memory_store.add_log("WARNING", f"Discord alert skipped for '{listing.get('title')}': Bot not connected or DISCORD_CHANNEL_ID not set.", "discord")
            return

        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.channel_id)

            if not channel:
                return

            fit_score = listing.get("fit_score", 70)
            color = 0x00ff88 if fit_score >= 80 else 0xffaa00

            embed = discord.Embed(
                title=f"🎯 {listing.get('title')} @ {listing.get('company')}",
                url=listing.get("url", "https://internshala.com"),
                color=color
            )
            embed.description = f"**{fit_score}% Match** | Recommendation: `{listing.get('recommendation', 'apply').upper()}`"

            loc_str = f"📍 {listing.get('location', 'Remote')} | {listing.get('work_type', 'remote').upper()} | {listing.get('stipend', 'N/A')}"
            embed.add_field(name="Job Details", value=loc_str, inline=False)

            reasons = listing.get("match_reasons", [])
            reasons_text = "\n".join([f"• {r}" for r in reasons]) if reasons else "• High skills match"
            embed.add_field(name="✅ Why You Match", value=reasons_text[:1024], inline=False)

            missing = listing.get("missing_skills", [])
            missing_text = "\n".join([f"• {m}" for m in missing]) if missing else "None — strong match!"
            embed.add_field(name="⚠️ Missing Skills", value=missing_text[:1024], inline=False)

            embed.add_field(name="🔗 Apply Link", value=f"[Click Here to Apply]({listing.get('url')})", inline=False)
            embed.set_footer(text=f"Platform: {listing.get('platform')} | Job ID: {listing.get('id')}")

            await channel.send(embed=embed)
            await channel.send(f"Use `/coverletter {listing.get('id')}` or `/answers {listing.get('id')}` to get generated content.")

            listing["alerted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            memory_store.save_job(listing)
            memory_store.add_log("SUCCESS", f"Sent Discord alert for {listing.get('title')} @ {listing.get('company')}", "discord")
        except Exception as e:
            memory_store.add_log("ERROR", f"Failed to send Discord alert for {listing.get('title')}: {str(e)}", "discord")

notifier = DiscordNotifier()
