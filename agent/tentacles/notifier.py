import os
import re
import json
import time
import asyncio
import discord
from discord import app_commands, ui
from typing import Dict, Any, Optional, List
from agent.memory import memory_store


# ╔══════════════════════════════════════════════════════════════════╗
# ║          DISCORD MODALS — in-Discord profile setup forms         ║
# ╚══════════════════════════════════════════════════════════════════╝

class ProfileModal(ui.Modal, title="👤 Your Basic Info"):
    """Step 1 — fills name, email, linkedin, github, education."""
    full_name  = ui.TextInput(label="Full Name",          placeholder="Rahul Sharma",                         required=True,  max_length=100)
    email      = ui.TextInput(label="Email",              placeholder="rahul@gmail.com",                      required=True,  max_length=100)
    linkedin   = ui.TextInput(label="LinkedIn URL",       placeholder="https://linkedin.com/in/rahul",        required=False, max_length=200)
    github     = ui.TextInput(label="GitHub URL",         placeholder="https://github.com/rahul",             required=False, max_length=200)
    education  = ui.TextInput(label="Degree / Education", placeholder="B.Tech AI & ML, 2022–2026, VIT",       required=False, max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        memory_store.save_profile({
            "full_name":  str(self.full_name),
            "email":      str(self.email),
            "linkedin":   str(self.linkedin),
            "github":     str(self.github),
            "education":  str(self.education),
            "discord_id": uid,
            "discord_tag": str(interaction.user),
        }, user_id=uid)

        embed = discord.Embed(title="✅ Basic info saved!", color=0x00ff88)
        embed.description = (
            f"**Name:** {self.full_name}\n"
            f"**Email:** {self.email}\n\n"
            "Next → run `/myresume` to paste your skills and resume text."
        )
        embed.set_footer(text="Step 1/3 complete")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ResumeModal(ui.Modal, title="📄 Your Resume & Skills"):
    """Step 2 — resume text, skills, experience summary."""
    skills      = ui.TextInput(
        label="Your Skills (comma-separated)",
        placeholder="Python, FastAPI, Machine Learning, PyTorch, React, SQL",
        required=True, max_length=500
    )
    experience  = ui.TextInput(
        label="One-line experience summary",
        placeholder="Final year B.Tech AI/ML student — built AI agents, APIs, bots",
        required=True, max_length=300
    )
    resume_text = ui.TextInput(
        label="Paste your Resume (plain text)",
        placeholder="Copy your resume from Word/PDF and paste here. AI uses this for cover letters.",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        skill_list = [s.strip() for s in str(self.skills).split(",") if s.strip()]
        memory_store.save_profile({
            "skills":              skill_list,
            "experience_summary":  str(self.experience),
            "resume_text":         str(self.resume_text),
        }, user_id=uid)

        embed = discord.Embed(title="✅ Resume & Skills saved!", color=0x00ff88)
        embed.add_field(name="Skills Added", value=", ".join(skill_list[:10]) + ("…" if len(skill_list) > 10 else ""), inline=False)
        embed.description = "\nNext → run `/myprefs` to set your target roles, locations and min stipend."
        embed.set_footer(text="Step 2/3 complete")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PrefsModal(ui.Modal, title="🎯 Job Search Preferences"):
    """Step 3 — target roles, locations, work type, min stipend."""
    target_roles = ui.TextInput(
        label="Target Roles (comma-separated)",
        placeholder="AI Intern, ML Intern, Backend Developer Intern",
        required=True, max_length=400
    )
    locations = ui.TextInput(
        label="Preferred Locations (comma-separated)",
        placeholder="Remote, Bangalore, Hyderabad",
        required=False, max_length=300,
        default="Remote"
    )
    work_type = ui.TextInput(
        label="Work Type Priority (comma-separated)",
        placeholder="remote, hybrid, onsite",
        required=False, max_length=100,
        default="remote, hybrid, onsite"
    )
    min_stipend = ui.TextInput(
        label="Minimum Stipend (₹/month, enter 0 for any)",
        placeholder="5000",
        required=False, max_length=10,
        default="5000"
    )
    blacklist = ui.TextInput(
        label="Blacklisted Companies (comma-separated, optional)",
        placeholder="ScamCorp, UnpaidStartup",
        required=False, max_length=400
    )

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)

        roles_list    = [r.strip() for r in str(self.target_roles).split(",") if r.strip()]
        locs_list     = [l.strip() for l in str(self.locations).split(",")    if l.strip()]
        wt_list       = [w.strip().lower() for w in str(self.work_type).split(",") if w.strip()]
        blacklist_list = [b.strip() for b in str(self.blacklist).split(",")   if b.strip()]

        try:
            stipend = float(re.sub(r"[^\d.]", "", str(self.min_stipend)) or "0")
        except ValueError:
            stipend = 0.0

        prefs = {
            "target_roles":         roles_list,
            "locations":            locs_list or ["Remote"],
            "work_type_priority":   wt_list   or ["remote", "hybrid", "onsite"],
            "min_stipend":          stipend,
            "skills_to_match":      memory_store.get_profile(uid).get("skills", []),
            "blacklisted_companies": blacklist_list,
            "blacklisted_domains":  [],
            "alert_new_only":       True,
        }
        memory_store.save_preferences(prefs, user_id=uid)

        embed = discord.Embed(
            title="🎉 Setup Complete! InternHunter is now hunting for you.",
            color=0x00ff88
        )
        embed.add_field(name="🎯 Target Roles",   value=", ".join(roles_list),          inline=False)
        embed.add_field(name="📍 Locations",       value=", ".join(locs_list),           inline=True)
        embed.add_field(name="💰 Min Stipend",     value=f"₹{int(stipend):,}/month",     inline=True)
        embed.add_field(name="💼 Work Priority",   value=" › ".join(wt_list),            inline=True)
        embed.description = (
            "\n\nThe agent will DM you every time it finds a match above your score threshold.\n"
            "Use `/runnow` to trigger your first scan immediately!"
        )
        embed.set_footer(text="Step 3/3 complete ✅ You're fully registered")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║                     DISCORD NOTIFIER BOT                         ║
# ╚══════════════════════════════════════════════════════════════════╝

class DiscordNotifier:
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds       = True
        intents.guild_messages = True
        self.bot         = discord.Client(intents=intents)
        self.tree        = app_commands.CommandTree(self.bot)
        self.is_connected = False
        self.channel_id  = None
        self._setup_events()
        self._register_commands()

    # ── Events ───────────────────────────────────────────────────────────────

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            self.is_connected = True
            try:
                await self.tree.sync()
                memory_store.add_log("SUCCESS", f"Discord bot online as {self.bot.user}. Commands synced.", "discord")
            except Exception as e:
                memory_store.add_log("WARNING", f"Command sync failed: {e}", "discord")

    # ── Commands ─────────────────────────────────────────────────────────────

    def _register_commands(self):

        # ── /myprofile ────────────────────────────────────────────────────────
        @self.tree.command(name="myprofile", description="📝 Set your name, email, LinkedIn, GitHub and education")
        async def myprofile_cmd(interaction: discord.Interaction):
            """Opens a modal to fill your basic personal info. Takes 30 seconds."""
            await interaction.response.send_modal(ProfileModal())

        # ── /myresume ─────────────────────────────────────────────────────────
        @self.tree.command(name="myresume", description="📄 Paste your resume + add your skills list")
        async def myresume_cmd(interaction: discord.Interaction):
            """Opens a modal to paste your resume text and skills. AI uses this for cover letters."""
            await interaction.response.send_modal(ResumeModal())

        # ── /myprefs ──────────────────────────────────────────────────────────
        @self.tree.command(name="myprefs", description="🎯 Set your target roles, locations, stipend, work type")
        async def myprefs_cmd(interaction: discord.Interaction):
            """Opens a modal to configure what kind of internships to hunt for."""
            await interaction.response.send_modal(PrefsModal())

        # ── /whoami ───────────────────────────────────────────────────────────
        @self.tree.command(name="whoami", description="👀 See your current saved profile and preferences")
        async def whoami_cmd(interaction: discord.Interaction):
            """Shows your complete current profile as a private embed."""
            uid   = str(interaction.user.id)
            prof  = memory_store.get_profile(uid)
            prefs = memory_store.get_preferences(uid)

            if not prof.get("full_name"):
                await interaction.response.send_message(
                    "❌ You don't have a profile yet!\nRun these 3 commands in order:\n"
                    "1️⃣ `/myprofile` → basic info\n"
                    "2️⃣ `/myresume` → resume + skills\n"
                    "3️⃣ `/myprefs` → target roles + preferences",
                    ephemeral=True
                )
                return

            embed = discord.Embed(title=f"👤 {prof.get('full_name')}'s InternHunter Profile", color=0x8b5cf6)
            embed.add_field(name="📧 Email",      value=prof.get("email", "—"),     inline=True)
            embed.add_field(name="🎓 Education",  value=prof.get("education", "—"), inline=True)
            embed.add_field(name="🐙 GitHub",     value=prof.get("github", "—"),    inline=True)
            embed.add_field(name="💼 LinkedIn",   value=prof.get("linkedin", "—"),  inline=True)
            embed.add_field(
                name="🛠️ Skills",
                value=", ".join(prof.get("skills", [])) or "None added",
                inline=False
            )
            embed.add_field(
                name="🎯 Target Roles",
                value="\n".join(f"• {r}" for r in prefs.get("target_roles", [])) or "Not set",
                inline=False
            )
            embed.add_field(name="📍 Locations",   value=", ".join(prefs.get("locations", [])) or "Any", inline=True)
            embed.add_field(name="💰 Min Stipend", value=f"₹{int(prefs.get('min_stipend', 0)):,}/mo",    inline=True)
            embed.add_field(name="💼 Work Type",   value=" › ".join(prefs.get("work_type_priority", [])), inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # ── /runnow ───────────────────────────────────────────────────────────
        @self.tree.command(name="runnow", description="⚡ Trigger a scrape cycle just for you right now")
        async def runnow_cmd(interaction: discord.Interaction):
            """Starts a manual scan cycle for YOUR profile. Results DM'd to you."""
            uid = str(interaction.user.id)
            if not memory_store.user_exists(uid):
                await interaction.response.send_message(
                    "⚠️ You're not registered yet!\nComplete setup first:\n"
                    "1️⃣ `/myprofile` → 2️⃣ `/myresume` → 3️⃣ `/myprefs`",
                    ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"⚡ Starting a scan just for you, {interaction.user.mention}! "
                "I'll DM you any matches I find 🎯",
                ephemeral=True
            )
            from agent.heartbeat import heartbeat
            asyncio.create_task(heartbeat.trigger_manual_cycle(user_id=uid))

        # ── /mystats ──────────────────────────────────────────────────────────
        @self.tree.command(name="mystats", description="📊 See your personal InternHunter stats")
        async def mystats_cmd(interaction: discord.Interaction):
            uid   = str(interaction.user.id)
            stats = memory_store.get_stats(uid)
            from agent.heartbeat import heartbeat

            embed = discord.Embed(title="📊 Your InternHunter Stats", color=0x06b6d4)
            embed.add_field(name="Found Today",    value=str(stats.get("total_scraped_today", 0)),    inline=True)
            embed.add_field(name="Alerts Sent",    value=str(stats.get("listings_alerted_today", 0)), inline=True)
            embed.add_field(name="Total Tracked",  value=str(stats.get("total_jobs_tracked", 0)),     inline=True)
            embed.add_field(name="Avg Fit Score",  value=f"{stats.get('avg_fit_score', 0)}%",         inline=True)
            embed.add_field(name="Total Applied",  value=str(stats.get("total_applied", 0)),          inline=True)
            embed.add_field(name="Last Run",       value=heartbeat.last_run or "Never",               inline=True)
            embed.set_footer(text=f"Heartbeat every {os.getenv('RUN_INTERVAL_MINUTES', 30)} min")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # ── /coverletter ──────────────────────────────────────────────────────
        @self.tree.command(name="coverletter", description="📄 Get your cover letter for a specific job ID")
        async def coverletter_cmd(interaction: discord.Interaction, job_id: str):
            uid = str(interaction.user.id)
            job = memory_store.get_job_by_id(job_id, uid)
            if not job:
                await interaction.response.send_message(f"❌ Job `{job_id}` not found in your tracked jobs.", ephemeral=True)
                return
            letter = job.get("cover_letter", "No cover letter generated yet.")
            msg = f"📄 **Cover Letter — {job.get('title')} @ {job.get('company')}**\n```\n{letter[:1800]}\n```"
            await interaction.response.send_message(msg, ephemeral=True)

        # ── /answers ─────────────────────────────────────────────────────────
        @self.tree.command(name="answers", description="📝 Get application screening answers for a job ID")
        async def answers_cmd(interaction: discord.Interaction, job_id: str):
            uid = str(interaction.user.id)
            job = memory_store.get_job_by_id(job_id, uid)
            if not job:
                await interaction.response.send_message(f"❌ Job `{job_id}` not found in your tracked jobs.", ephemeral=True)
                return
            answers = job.get("generated_answers", {})
            formatted = f"📝 **Application Answers — {job.get('title')} @ {job.get('company')}**\n\n"
            for q, a in answers.items():
                formatted += f"**Q: {q}**\n> {a}\n\n"
            await interaction.response.send_message(formatted[:2000], ephemeral=True)

        # ── /status ───────────────────────────────────────────────────────────
        @self.tree.command(name="status", description="🟢 Agent system status and registered user count")
        async def status_cmd(interaction: discord.Interaction):
            from agent.heartbeat import heartbeat
            users     = memory_store.get_all_users()
            state     = "🟢 Running" if heartbeat.is_running else "🟡 Paused"
            embed     = discord.Embed(title="🎯 InternHunter System Status", color=0x00ff88 if heartbeat.is_running else 0xffaa00)
            embed.add_field(name="Agent",            value=state,                 inline=True)
            embed.add_field(name="Registered Users", value=str(len(users)),       inline=True)
            embed.add_field(name="Cycles Run",        value=str(heartbeat.cycle_count), inline=True)
            embed.add_field(name="Last Run",          value=heartbeat.last_run or "Never", inline=False)
            embed.set_footer(text=f"Interval: {os.getenv('RUN_INTERVAL_MINUTES', 30)} min | Min score: {os.getenv('MIN_FIT_SCORE', 60)}%")
            await interaction.response.send_message(embed=embed)

        # ── /pause / /resume ──────────────────────────────────────────────────
        @self.tree.command(name="pause", description="⏸️ Pause automated heartbeat (admin)")
        @app_commands.checks.has_permissions(administrator=True)
        async def pause_cmd(interaction: discord.Interaction):
            from agent.heartbeat import heartbeat
            heartbeat.stop()
            await interaction.response.send_message("⏸️ Heartbeat paused. Use `/resume` to restart.")

        @self.tree.command(name="resume", description="▶️ Resume automated heartbeat (admin)")
        @app_commands.checks.has_permissions(administrator=True)
        async def resume_cmd(interaction: discord.Interaction):
            from agent.heartbeat import heartbeat
            heartbeat.start()
            await interaction.response.send_message("▶️ Heartbeat resumed.")

        # ── /setup ────────────────────────────────────────────────────────────
        @self.tree.command(name="setup", description="🚀 One-command server setup — creates channels (admin only)")
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_cmd(interaction: discord.Interaction):
            await interaction.response.defer()
            guild = interaction.guild

            category = discord.utils.get(guild.categories, name="🎯 InternHunter")
            if not category:
                category = await guild.create_category("🎯 InternHunter")

            async def make_ch(name, topic):
                ch = discord.utils.get(guild.text_channels, name=name, category=category)
                return ch or await guild.create_text_channel(name, category=category, topic=topic)

            alerts_ch = await make_ch("📢-alerts",       "InternHunter job match DMs + pings")
            log_ch    = await make_ch("📜-activity-log", "Heartbeat and scraper activity")
            cmd_ch    = await make_ch("⚙️-commands",     "Use InternHunter slash commands here")

            self.channel_id = alerts_ch.id
            _update_env_channel_id(str(alerts_ch.id))

            # Welcome messages
            welcome = discord.Embed(title="🎯 InternHunter is Live!", color=0x00ff88)
            welcome.description = (
                "**How to get started (takes 2 minutes):**\n\n"
                "1️⃣ `/myprofile` → Enter your name, email, GitHub, LinkedIn\n"
                "2️⃣ `/myresume` → Paste your resume + add your skills\n"
                "3️⃣ `/myprefs` → Set target roles, locations, stipend\n"
                "4️⃣ `/runnow` → Trigger your first scan\n\n"
                "✅ Each person sets up **their own** profile.\n"
                "📬 Matches get **DM'd** directly to you — personal and private."
            )
            welcome.set_footer(text="InternHunter • Autonomous AI Internship Agent")
            await alerts_ch.send(embed=welcome)

            cmd_embed = discord.Embed(title="⚙️ All Commands", color=0x8b5cf6)
            cmds = [
                ("/myprofile",           "Set your basic info (name, email, GitHub etc)"),
                ("/myresume",            "Paste your resume and add skills"),
                ("/myprefs",             "Set target roles, locations, stipend"),
                ("/whoami",              "See your full saved profile"),
                ("/runnow",              "Trigger a scan just for you"),
                ("/mystats",             "Your personal match stats"),
                ("/coverletter {id}",    "Fetch your cover letter for a job"),
                ("/answers {id}",        "Fetch application answers for a job"),
                ("/status",              "Agent system status"),
            ]
            for cmd, desc in cmds:
                cmd_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
            await cmd_ch.send(embed=cmd_embed)

            done = discord.Embed(title="✅ Server Setup Complete!", color=0x00ff88)
            done.add_field(name="Alerts",    value=alerts_ch.mention, inline=True)
            done.add_field(name="Logs",      value=log_ch.mention,    inline=True)
            done.add_field(name="Commands",  value=cmd_ch.mention,    inline=True)
            done.add_field(
                name="Next",
                value=f"Tell your friends to type `/myprofile` in {cmd_ch.mention} to register!",
                inline=False
            )
            await interaction.followup.send(embed=done)

        @setup_cmd.error
        async def setup_error(interaction, error):
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message("❌ You need **Administrator** to run `/setup`.", ephemeral=True)

    # ── Bot Lifecycle ─────────────────────────────────────────────────────────

    async def start_bot(self):
        token     = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        ch_raw    = os.getenv("DISCORD_CHANNEL_ID", "").strip()
        if ch_raw.isdigit():
            self.channel_id = int(ch_raw)
        if not token or token == "your_discord_bot_token_here":
            memory_store.add_log("WARNING", "DISCORD_BOT_TOKEN not set. Bot standing by.", "discord")
            return
        try:
            memory_store.add_log("INFO", "Connecting Discord bot...", "discord")
            await self.bot.start(token)
        except Exception as e:
            memory_store.add_log("ERROR", f"Discord bot error: {str(e)}", "discord")

    # ── Alert Senders ────────────────────────────────────────────────────────

    async def send_job_alert_to_user(self, listing: Dict[str, Any], user_id: str):
        """DMs a job alert embed directly to the user's Discord inbox."""
        if not self.is_connected:
            return
        try:
            discord_user = await self.bot.fetch_user(int(user_id))
            if not discord_user:
                return

            fit_score = listing.get("fit_score", 70)
            color     = 0x00ff88 if fit_score >= 80 else 0xffaa00

            embed = discord.Embed(
                title=f"🎯 {listing.get('title')} @ {listing.get('company')}",
                url=listing.get("url", "https://internshala.com"),
                color=color
            )
            embed.description = (
                f"**{fit_score}% Match** | `{listing.get('recommendation', 'apply').upper()}`"
            )
            embed.add_field(
                name="Details",
                value=f"📍 {listing.get('location')} | {listing.get('work_type','').upper()} | {listing.get('stipend','N/A')}",
                inline=False
            )
            embed.add_field(
                name="✅ Why you match",
                value="\n".join(f"• {r}" for r in listing.get("match_reasons", [])) or "• Strong skill alignment",
                inline=False
            )
            missing = listing.get("missing_skills", [])
            if missing:
                embed.add_field(name="⚠️ Gap", value="\n".join(f"• {m}" for m in missing), inline=False)

            embed.add_field(name="🔗 Apply", value=f"[Open Listing]({listing.get('url')})", inline=False)
            embed.set_footer(text=f"{listing.get('platform')} | ID: {listing.get('id')}")

            await discord_user.send(embed=embed)
            await discord_user.send(
                f"> `/coverletter {listing.get('id')}` — get your cover letter\n"
                f"> `/answers {listing.get('id')}` — get your application answers"
            )

            listing["alerted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            memory_store.save_job(listing, user_id)
            memory_store.add_log("SUCCESS", f"DM sent to user {user_id} → {listing.get('title')} ({fit_score}%)", "discord")

        except discord.Forbidden:
            memory_store.add_log("WARNING", f"Cannot DM user {user_id} — they may have DMs disabled.", "discord")
        except Exception as e:
            memory_store.add_log("ERROR", f"Failed to DM user {user_id}: {str(e)}", "discord")

    async def send_job_alert(self, listing: Dict[str, Any]):
        """Legacy: send to configured channel (used when channel_id is set)."""
        if not self.is_connected or not self.channel_id:
            return
        try:
            channel = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
            if not channel:
                return
            fit_score = listing.get("fit_score", 70)
            embed = discord.Embed(
                title=f"🎯 {listing.get('title')} @ {listing.get('company')}",
                url=listing.get("url"), color=0x00ff88 if fit_score >= 80 else 0xffaa00
            )
            embed.description = f"**{fit_score}% Match**"
            embed.add_field(name="Apply", value=f"[Click here]({listing.get('url')})", inline=False)
            await channel.send(embed=embed)
        except Exception as e:
            memory_store.add_log("ERROR", f"Channel alert failed: {str(e)}", "discord")


# ── Helper ────────────────────────────────────────────────────────────────────

def _update_env_channel_id(channel_id: str):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    try:
        if os.path.exists(env_path):
            lines = open(env_path, encoding="utf-8").readlines()
            updated, found = [], False
            for line in lines:
                if line.startswith("DISCORD_CHANNEL_ID="):
                    updated.append(f"DISCORD_CHANNEL_ID={channel_id}\n")
                    found = True
                else:
                    updated.append(line)
            if not found:
                updated.append(f"DISCORD_CHANNEL_ID={channel_id}\n")
            open(env_path, "w", encoding="utf-8").writelines(updated)
            os.environ["DISCORD_CHANNEL_ID"] = channel_id
    except Exception:
        pass


notifier = DiscordNotifier()
