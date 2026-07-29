import os
import json
import time
import asyncio
import discord
from discord import app_commands
from typing import Dict, Any, Optional, List
from agent.memory import memory_store


class DiscordNotifier:
    """
    Discord Bot integration using discord.py for sending rich job embed alerts
    and handling slash commands (including /setup) concurrently alongside FastAPI.
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True          # needed to create channels / categories
        intents.guild_messages = True  # needed to read messages in guilds
        self.bot = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.bot)
        self.is_connected = False
        self.channel_id = None
        self._setup_events()
        self._register_commands()

    # ── Events ──────────────────────────────────────────────────────────────

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            self.is_connected = True
            try:
                await self.tree.sync()
                memory_store.add_log(
                    "SUCCESS",
                    f"Discord Bot online as {self.bot.user}. All slash commands synced.",
                    "discord"
                )
            except Exception as e:
                memory_store.add_log("WARNING", f"Slash command sync failed: {str(e)}", "discord")

    # ── Slash Commands ───────────────────────────────────────────────────────

    def _register_commands(self):

        # ── /setup ──────────────────────────────────────────────────────────
        @self.tree.command(
            name="setup",
            description="🚀 One-command InternHunter server setup — creates category, channels & saves config"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_cmd(interaction: discord.Interaction):
            """
            Creates the full InternHunter workspace on the Discord server:
              • Category  : 🎯 InternHunter
              • #📢-alerts       → receives job match embeds
              • #📜-activity-log → receives system/heartbeat logs
              • #⚙️-commands     → bot command usage channel
            Saves the alerts channel ID back into .env and memory automatically.
            """
            await interaction.response.defer(ephemeral=False)
            guild = interaction.guild

            # ── 1. Create or reuse category ──────────────────────────────────
            category = discord.utils.get(guild.categories, name="🎯 InternHunter")
            if not category:
                category = await guild.create_category(
                    "🎯 InternHunter",
                    reason="InternHunter /setup"
                )

            async def make_channel(name: str, topic: str) -> discord.TextChannel:
                existing = discord.utils.get(guild.text_channels, name=name, category=category)
                if existing:
                    return existing
                return await guild.create_text_channel(
                    name,
                    category=category,
                    topic=topic,
                    reason="InternHunter /setup"
                )

            # ── 2. Create the three channels ─────────────────────────────────
            alerts_ch  = await make_channel("📢-alerts",       "InternHunter job match alerts — scored and filtered by your profile")
            log_ch     = await make_channel("📜-activity-log", "InternHunter heartbeat & scraper activity feed")
            cmd_ch     = await make_channel("⚙️-commands",     "Use InternHunter slash commands here")

            # ── 3. Persist alerts channel ID into .env ────────────────────────
            self.channel_id = alerts_ch.id
            _update_env_channel_id(str(alerts_ch.id))
            memory_store.add_log(
                "SUCCESS",
                f"Discord setup complete. Alerts channel → #{alerts_ch.name} ({alerts_ch.id})",
                "discord"
            )

            # ── 4. Welcome embed in #📢-alerts ────────────────────────────────
            alert_embed = discord.Embed(
                title="🎯 InternHunter is Live in this Server!",
                description=(
                    "This channel will receive **real-time internship alerts** "
                    "scored against your profile by Groq Llama 3.3.\n\n"
                    "Every alert includes:\n"
                    "• 🟢/🟡 colour-coded fit score\n"
                    "• Match reasons & missing skills\n"
                    "• Direct apply link\n"
                    "• Commands to pull your cover letter & answers instantly"
                ),
                color=0x00ff88
            )
            alert_embed.add_field(name="Scrape Sources", value="Internshala • Unstop • LinkedIn", inline=True)
            alert_embed.add_field(name="Cycle Frequency", value=f"Every {os.getenv('RUN_INTERVAL_MINUTES', 30)} minutes", inline=True)
            alert_embed.add_field(name="Min Fit Score", value=f"{os.getenv('MIN_FIT_SCORE', 60)}%", inline=True)
            alert_embed.set_footer(text="InternHunter • Autonomous Internship Agent")
            await alerts_ch.send(embed=alert_embed)

            # ── 5. Info embed in #📜-activity-log ─────────────────────────────
            log_embed = discord.Embed(
                title="📜 Activity Log Feed",
                description=(
                    "This channel mirrors the live console from your FastAPI dashboard.\n"
                    "Heartbeat pulses, scraper cycles, scoring decisions, and errors will appear here."
                ),
                color=0x06b6d4
            )
            await log_ch.send(embed=log_embed)

            # ── 6. Command reference embed in #⚙️-commands ────────────────────
            cmd_embed = discord.Embed(
                title="⚙️ InternHunter Slash Commands",
                color=0x8b5cf6
            )
            commands_list = [
                ("/setup",               "Runs this server setup again"),
                ("/status",              "Agent status, metrics & last run time"),
                ("/preferences",         "View your current search preferences"),
                ("/runnow",              "Trigger an immediate scrape cycle"),
                ("/pause",               "Pause the automated heartbeat"),
                ("/resume",              "Resume the automated heartbeat"),
                ("/coverletter {job_id}","Fetch generated cover letter for a job"),
                ("/answers {job_id}",    "Fetch application screening answers"),
            ]
            for cmd, desc in commands_list:
                cmd_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
            cmd_embed.set_footer(text="Use these commands from any channel in this server")
            await cmd_ch.send(embed=cmd_embed)

            # ── 7. Setup complete confirmation ────────────────────────────────
            done_embed = discord.Embed(
                title="✅ Server Setup Complete!",
                color=0x00ff88
            )
            done_embed.add_field(name="📢 Alerts Channel",  value=alerts_ch.mention,  inline=True)
            done_embed.add_field(name="📜 Activity Log",    value=log_ch.mention,      inline=True)
            done_embed.add_field(name="⚙️ Commands Channel", value=cmd_ch.mention,    inline=True)
            done_embed.add_field(
                name="Next Step",
                value=f"Use `/runnow` in {cmd_ch.mention} to start your first scrape cycle!",
                inline=False
            )
            done_embed.set_footer(text=f"Alerts will be posted to {alerts_ch.name} (ID saved to .env)")
            await interaction.followup.send(embed=done_embed)

        @setup_cmd.error
        async def setup_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You need **Administrator** permission to run `/setup`.", ephemeral=True
                )
            else:
                await interaction.response.send_message(f"❌ Setup failed: {str(error)}", ephemeral=True)

        # ── /coverletter ─────────────────────────────────────────────────────
        @self.tree.command(name="coverletter", description="Fetch the generated cover letter for an internship listing")
        async def coverletter_cmd(interaction: discord.Interaction, job_id: str):
            """Returns the pre-generated personalized cover letter for the given job ID."""
            job = memory_store.get_job_by_id(job_id)
            if not job:
                await interaction.response.send_message(f"❌ Job `{job_id}` not found.", ephemeral=True)
                return
            letter = job.get("cover_letter", "No cover letter generated yet.")
            msg = f"📄 **Cover Letter — {job.get('title')} @ {job.get('company')}**\n```\n{letter}\n```"
            await interaction.response.send_message(msg[:2000])

        # ── /answers ─────────────────────────────────────────────────────────
        @self.tree.command(name="answers", description="Fetch generated application screening answers for a listing")
        async def answers_cmd(interaction: discord.Interaction, job_id: str):
            """Returns pre-generated answers to common application screening questions."""
            job = memory_store.get_job_by_id(job_id)
            if not job:
                await interaction.response.send_message(f"❌ Job `{job_id}` not found.", ephemeral=True)
                return
            answers = job.get("generated_answers", {})
            formatted = f"📝 **Application Answers — {job.get('title')} @ {job.get('company')}**\n\n"
            for q, a in answers.items():
                formatted += f"**Q: {q}**\n> {a}\n\n"
            await interaction.response.send_message(formatted[:2000])

        # ── /status ──────────────────────────────────────────────────────────
        @self.tree.command(name="status", description="Show InternHunter agent status and today's metrics")
        async def status_cmd(interaction: discord.Interaction):
            """Displays a status embed with agent health, scrape counts, and fit score average."""
            stats = memory_store.get_stats()
            from agent.heartbeat import heartbeat
            status_label = "🟢 Running" if heartbeat.is_running else "🟡 Paused"

            embed = discord.Embed(
                title="🎯 InternHunter Agent Status",
                color=0x00ff88 if heartbeat.is_running else 0xffaa00
            )
            embed.add_field(name="Agent",               value=status_label,                              inline=True)
            embed.add_field(name="Scraped Today",        value=str(stats.get("total_scraped_today", 0)), inline=True)
            embed.add_field(name="Alerts Sent Today",    value=str(stats.get("listings_alerted_today", 0)), inline=True)
            embed.add_field(name="Total Applied",        value=str(stats.get("total_applied", 0)),       inline=True)
            embed.add_field(name="Avg Fit Score",        value=f"{stats.get('avg_fit_score', 0)}%",      inline=True)
            embed.add_field(name="Cycles Run",           value=str(heartbeat.cycle_count),               inline=True)
            embed.add_field(name="Last Run",             value=heartbeat.last_run or "Never",            inline=False)
            embed.set_footer(text=f"Heartbeat interval: {os.getenv('RUN_INTERVAL_MINUTES', 30)} min | Min score: {os.getenv('MIN_FIT_SCORE', 60)}%")
            await interaction.response.send_message(embed=embed)

        # ── /preferences ─────────────────────────────────────────────────────
        @self.tree.command(name="preferences", description="Show current internship search preferences")
        async def preferences_cmd(interaction: discord.Interaction):
            """Displays active search filters from preferences.json."""
            prefs = memory_store.get_preferences()
            embed = discord.Embed(title="⚙️ InternHunter Search Preferences", color=0x3b82f6)
            embed.add_field(name="🎯 Target Roles",    value="\n".join(f"• {r}" for r in prefs.get("target_roles", [])) or "None set", inline=False)
            embed.add_field(name="📍 Locations",       value=", ".join(prefs.get("locations", [])) or "Any",    inline=True)
            embed.add_field(name="💼 Work Priority",   value=" › ".join(prefs.get("work_type_priority", [])),   inline=True)
            embed.add_field(name="💰 Min Stipend",     value=f"₹{prefs.get('min_stipend', 0)}/month",           inline=True)
            embed.add_field(name="🛠️ Skills Matching", value=", ".join(prefs.get("skills_to_match", [])) or "All", inline=False)
            await interaction.response.send_message(embed=embed)

        # ── /runnow ──────────────────────────────────────────────────────────
        @self.tree.command(name="runnow", description="Trigger an immediate scrape + score + alert cycle")
        async def runnow_cmd(interaction: discord.Interaction):
            """Starts a manual scrape cycle immediately outside the scheduled heartbeat."""
            await interaction.response.send_message("⚡ Scrape cycle fired! Check #📜-activity-log for live progress.")
            from agent.heartbeat import heartbeat
            asyncio.create_task(heartbeat.trigger_manual_cycle())

        # ── /pause ───────────────────────────────────────────────────────────
        @self.tree.command(name="pause", description="Pause the automated 30-minute scrape heartbeat")
        async def pause_cmd(interaction: discord.Interaction):
            """Pauses the APScheduler heartbeat until /resume is called."""
            from agent.heartbeat import heartbeat
            heartbeat.stop()
            await interaction.response.send_message("⏸️ InternHunter heartbeat paused. Use `/resume` to restart.")

        # ── /resume ──────────────────────────────────────────────────────────
        @self.tree.command(name="resume", description="Resume the automated scrape heartbeat")
        async def resume_cmd(interaction: discord.Interaction):
            """Resumes the APScheduler heartbeat."""
            from agent.heartbeat import heartbeat
            heartbeat.start()
            await interaction.response.send_message("▶️ InternHunter heartbeat resumed.")

    # ── Bot Lifecycle ────────────────────────────────────────────────────────

    async def start_bot(self):
        """Connects the Discord bot using the token from .env."""
        token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        channel_raw = os.getenv("DISCORD_CHANNEL_ID", "").strip()

        if channel_raw.isdigit():
            self.channel_id = int(channel_raw)

        if not token or token == "your_discord_bot_token_here":
            memory_store.add_log("WARNING", "DISCORD_BOT_TOKEN not set in .env — bot standing by.", "discord")
            return

        try:
            memory_store.add_log("INFO", "Connecting Discord bot...", "discord")
            await self.bot.start(token)
        except Exception as e:
            memory_store.add_log("ERROR", f"Discord bot failed to start: {str(e)}", "discord")

    # ── Alert Sender ─────────────────────────────────────────────────────────

    async def send_job_alert(self, listing: Dict[str, Any]):
        """
        Sends a rich Discord embed alert for a qualifying internship listing.
        Green embed for fit_score >= 80, yellow for 60-79.
        """
        if not self.is_connected or not self.channel_id:
            memory_store.add_log(
                "WARNING",
                f"Alert skipped for '{listing.get('title')}' — bot not connected or channel not configured. Run /setup.",
                "discord"
            )
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
            embed.description = (
                f"**{fit_score}% Match** | "
                f"Recommendation: `{listing.get('recommendation', 'apply').upper()}`"
            )

            loc_str = (
                f"📍 {listing.get('location', 'Remote')} | "
                f"{listing.get('work_type', 'remote').upper()} | "
                f"{listing.get('stipend', 'N/A')}"
            )
            embed.add_field(name="Job Details", value=loc_str, inline=False)

            reasons = listing.get("match_reasons", [])
            embed.add_field(
                name="✅ Why You Match",
                value="\n".join(f"• {r}" for r in reasons) or "• Strong skills alignment",
                inline=False
            )

            missing = listing.get("missing_skills", [])
            embed.add_field(
                name="⚠️ Missing Skills",
                value="\n".join(f"• {m}" for m in missing) or "None — strong match!",
                inline=False
            )
            embed.add_field(
                name="🔗 Apply Link",
                value=f"[Click Here to Apply]({listing.get('url')})",
                inline=False
            )
            embed.set_footer(
                text=f"Platform: {listing.get('platform')} | Posted: {listing.get('posted_at')} | ID: {listing.get('id')}"
            )

            await channel.send(embed=embed)
            await channel.send(
                f"> Use `/coverletter {listing.get('id')}` or `/answers {listing.get('id')}` to get your tailored content."
            )

            listing["alerted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            memory_store.save_job(listing)
            memory_store.add_log(
                "SUCCESS",
                f"Discord alert sent → {listing.get('title')} @ {listing.get('company')} ({fit_score}% match)",
                "discord"
            )
        except Exception as e:
            memory_store.add_log(
                "ERROR",
                f"Failed to send Discord alert for {listing.get('title')}: {str(e)}",
                "discord"
            )


# ── Helper: update DISCORD_CHANNEL_ID in .env file ──────────────────────────

def _update_env_channel_id(channel_id: str):
    """
    Persists the newly created alerts channel ID into the .env file
    so that alerts survive a bot restart after /setup.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            updated = []
            found = False
            for line in lines:
                if line.startswith("DISCORD_CHANNEL_ID="):
                    updated.append(f"DISCORD_CHANNEL_ID={channel_id}\n")
                    found = True
                else:
                    updated.append(line)
            if not found:
                updated.append(f"DISCORD_CHANNEL_ID={channel_id}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(updated)
            # Also update the running process environment
            os.environ["DISCORD_CHANNEL_ID"] = channel_id
    except Exception as e:
        pass  # Non-critical — channel_id is already set in memory


notifier = DiscordNotifier()
