# InternHunter 🎯 — Autonomous AI Internship Automation Agent

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama--3.3--70B-f05032?style=flat)
![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-5865F2?style=flat&logo=discord&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

InternHunter is an autonomous AI agent that continuously monitors Internshala, Unstop, and LinkedIn for matching internship roles, evaluates candidate fit using Groq's Llama 3.3 70B model, pre-generates tailored cover letters, and dispatches instant alerts via Discord.

---

## 🛠️ Architecture Flow

```text
┌─────────────────────────────────────────────────────────────┐
│                       InternHunter Engine                   │
└─────────────────────────────────────────────────────────────┘
  ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐
  │  Internshala     │    │     Unstop      │    │     LinkedIn     │
  └────────┬─────────┘    └────────┬────────┘    └────────┬─────────┘
           │                       │                      │
           └───────────────────────┼──────────────────────┘
                                   ▼
                       ┌──────────────────────┐
                       │  Scraper Aggregator  │
                       └──────────┬───────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │    Brain (Groq Llama 3.3)  │
                    │   - Evaluates Fit Score    │
                    │   - Drafts Cover Letter    │
                    │   - Answers Screening Qs   │
                    └─────────────┬──────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
      ┌──────────────────────┐        ┌──────────────────────┐
      │  Discord Bot Alert   │        │  FastAPI Dashboard   │
      │  (Rich Embeds &      │        │  (Live Feed &        │
      │   Slash Commands)    │        │   Preferences UI)    │
      └──────────────────────┘        └──────────────────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │ User Reviews & Applies   │
                     └──────────────────────────┘
```

---

## ✨ Features

- 🕵️ **Multi-Platform Scraping**: Concurrently scrapes Internshala, Unstop, and public LinkedIn feeds without API rate limits.
- 🧠 **LLM Fit Scoring**: Scores every listing (0-100%) against candidate skills and flags missing requirements using Groq Llama 3.3.
- ✍️ **Automated Content Generation**: Drafts a 150-word targeted cover letter and application Q&A answers at scrape time.
- 💬 **Discord Bot & Slash Commands**: Sends rich color-coded embeds to Discord with slash commands to retrieve generated text.
- ⏱️ **Heartbeat Scheduler**: Runs full background cycles every 30 minutes via APScheduler with thread pool execution.
- 📊 **Single-Page Dashboard**: Vanilla JS dark theme interface for monitoring listings, updating search filters, and tracking stats.
- 📁 **Zero-Database Persistence**: Uses clean JSON file storage for profiles, preferences, jobs, and execution logs.

---

## 📁 Project Structure

```text
internhunter/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── data/
│   ├── profile.json
│   ├── preferences.json
│   └── applied_jobs.json
├── agent/
│   ├── __init__.py
│   ├── brain.py
│   ├── memory.py
│   ├── heartbeat.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── internshala.py
│   │   ├── unstop.py
│   │   └── linkedin.py
│   └── tentacles/
│       ├── __init__.py
│       ├── scorer.py
│       ├── generator.py
│       └── notifier.py
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## ⚡ Quickstart

1. **Clone the repository**
   ```bash
   git clone https://github.com/Naraito-ai/internhunter.git
   cd internhunter
   ```

2. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```
   *Add your Groq API key, Discord bot token, and Discord channel ID to `.env`.*

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch InternHunter**
   ```bash
   python main.py
   ```

5. **Open Dashboard**
   Navigate to `http://localhost:8000` in your web browser.

---

## ⚙️ Environment Variables

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq API Key from console.groq.com | `gsk_x9K...` |
| `GROQ_MODEL` | LLM model identifier | `llama-3.3-70b-versatile` |
| `DISCORD_BOT_TOKEN` | Discord Bot token from Developer Portal | `MTI...` |
| `DISCORD_CHANNEL_ID` | Target channel ID for Discord alerts | `123456789012345678` |
| `RUN_INTERVAL_MINUTES` | Minutes between automated scrape cycles | `30` |
| `MIN_FIT_SCORE` | Minimum score threshold for alerts | `60` |
| `PORT` | FastAPI server port | `8000` |

---

## 🤖 Discord Slash Commands

| Command | Description |
| :--- | :--- |
| `/coverletter {job_id}` | Returns the pre-generated cover letter for the specified job ID in a code block. |
| `/answers {job_id}` | Returns formatted application screening answers for the specified job ID. |
| `/status` | Displays an embed with current agent status, scrape metrics, and average fit score. |
| `/preferences` | Displays the active search role filters, work type priority, and stipend preferences. |
| `/runnow` | Triggers an immediate scrape and evaluation cycle. |
| `/pause` | Temporarily pauses the background heartbeat scheduler. |
| `/resume` | Resumes the background heartbeat scheduler. |

---

## 🔌 REST API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the static single-page dashboard UI. |
| `/api/profile` | `GET / POST` | Fetch or update user profile and resume text. |
| `/api/preferences` | `GET / POST` | Fetch or update target role filters and min stipend. |
| `/api/jobs` | `GET` | Fetch tracked jobs (filters: `platform`, `min_score`, `work_type`, `is_new`). |
| `/api/jobs/{job_id}` | `GET` | Fetch single job detail including cover letter and answers. |
| `/api/jobs/{job_id}/apply` | `POST` | Mark job status as applied and save timestamp. |
| `/api/stats` | `GET` | Fetch aggregate stats (scraped today, total applied, avg score). |
| `/api/logs` | `GET` | Fetch last 50 activity log entries. |
| `/api/run-now` | `POST` | Trigger an immediate manual scrape cycle. |

---

## 💡 Why I Built This

As a final-year B.Tech AI/ML student, I found myself spending 2-3 hours every day manually checking multiple internship portals, reading generic job descriptions, and writing repetitive cover letters.

I decided to solve my own problem by building an autonomous agent. InternHunter handles the tedious monitoring and initial content draft generation so I can focus on honing my technical skills and preparing for technical interviews. Building this project helped me gain practical experience in async Python architecture, LLM tool integration, web parsing, and event-driven Discord bots.

---

## 🖼️ Screenshots

> **[Dashboard Screenshot]**
> *(Add a screenshot of the FastAPI dashboard at `http://localhost:8000`)*

> **[Discord Alert Screenshot]**
> *(Add a screenshot of a color-coded Discord embed alert)*

---

## 🗺️ Roadmap

- [ ] **Email Digest Summary**: Send a daily morning email summary of top matching internships.
- [ ] **Resume PDF Auto-Attach**: Auto-select and format tailored PDF resumes per domain.
- [ ] **Fit Score Trend Graph**: Visual dashboard charts showing market demand across target skills over time.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
