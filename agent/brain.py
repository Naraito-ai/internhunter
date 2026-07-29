import os
import json
import requests
from typing import Dict, Any, List, Optional
from agent.memory import memory_store

class GroqBrain:
    """
    LLM Engine using Groq API (llama-3.3-70b-versatile) for scoring internship fit,
    generating personalized cover letters, and auto-composing interview/application answers.
    """
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.default_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def _get_api_key(self) -> str:
        """Retrieves the Groq API key from environment variables."""
        return os.getenv("GROQ_API_KEY", "").strip()

    def _call_groq(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """Sends a request to Groq API using requests."""
        api_key = self._get_api_key()
        if not api_key:
            memory_store.add_log("WARNING", "Groq API Key not found in .env. Using intelligent local evaluation.", "brain")
            return ""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 1500
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=25)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                memory_store.add_log("ERROR", f"Groq API error {response.status_code}: {response.text}", "brain")
                return ""
        except Exception as e:
            memory_store.add_log("ERROR", f"Groq API request failed: {str(e)}", "brain")
            return ""

    def score_listing(self, listing: Dict[str, Any], profile: Dict[str, Any], preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores an internship listing against candidate profile & preferences using LLM analysis.
        Returns JSON with fit_score (0-100), match_reasons, missing_skills, and recommendation.
        """
        system_prompt = "You are an internship fit analyzer. Return only valid JSON, no markdown."
        user_prompt = f"""
Analyze the following internship listing for candidate fit:

Candidate Profile:
- Skills: {json.dumps(profile.get('skills', []))}
- Experience Summary: {profile.get('experience_summary', '')}
- Education: {profile.get('education', '')}

Preferences:
- Target Roles: {json.dumps(preferences.get('target_roles', []))}
- Preferred Locations: {json.dumps(preferences.get('locations', []))}
- Minimum Stipend: {preferences.get('min_stipend', 0)}

Internship Listing:
- Title: {listing.get('title')}
- Company: {listing.get('company')}
- Location: {listing.get('location')}
- Work Type: {listing.get('work_type')}
- Stipend: {listing.get('stipend')}
- Required Skills: {json.dumps(listing.get('skills_required', []))}
- Description: {listing.get('description', '')[:1000]}

Return JSON format strictly:
{{
  "fit_score": integer (0-100),
  "match_reasons": ["string"],
  "missing_skills": ["string"],
  "recommendation": "apply" | "maybe" | "skip"
}}
"""
        raw_response = self._call_groq(system_prompt, user_prompt, temperature=0.1)

        if raw_response:
            try:
                cleaned = raw_response
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                parsed = json.loads(cleaned)
                return {
                    "fit_score": int(parsed.get("fit_score", 70)),
                    "match_reasons": parsed.get("match_reasons", ["Matches target skills"]),
                    "missing_skills": parsed.get("missing_skills", []),
                    "recommendation": parsed.get("recommendation", "apply")
                }
            except Exception as e:
                memory_store.add_log("WARNING", f"Failed to parse Groq score response: {str(e)}", "brain")

        # Heuristic fallback if Groq API key is not set or request failed
        matched_skills = [s for s in listing.get("skills_required", []) if s.lower() in [ps.lower() for ps in profile.get("skills", [])]]
        missing_skills = [s for s in listing.get("skills_required", []) if s.lower() not in [ps.lower() for ps in profile.get("skills", [])]]
        
        fit_score = 75 if matched_skills or "python" in listing.get("title", "").lower() or "ai" in listing.get("title", "").lower() else 60
        return {
            "fit_score": fit_score,
            "match_reasons": [f"Matches skills: {', '.join(matched_skills)}"] if matched_skills else ["Role aligns with candidate profile"],
            "missing_skills": missing_skills,
            "recommendation": "apply" if fit_score >= 60 else "skip"
        }

    def generate_cover_letter(self, listing: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """
        Generates a 150-word personalized cover letter tailored to the company and role.
        """
        system_prompt = "You are an expert career advisor. Generate a confident, 150-word cover letter in plain text."
        user_prompt = f"""
Write a personalized 150-word cover letter for candidate {profile.get('full_name')} applying for the {listing.get('title')} position at {listing.get('company')}.

Candidate Summary: {profile.get('experience_summary')}
Skills: {', '.join(profile.get('skills', []))}
Target Role: {listing.get('title')} at {listing.get('company')}

Requirements:
- Must explicitly mention company name '{listing.get('company')}' and role '{listing.get('title')}'.
- Mention 2-3 matching technical skills from profile.
- Tone: confident, direct, professional, not generic or sycophantic.
- Return plain text only. Max 150 words.
"""
        letter = self._call_groq(system_prompt, user_prompt, temperature=0.4)
        if letter:
            return letter

        return (
            f"Dear Hiring Manager at {listing.get('company')},\n\n"
            f"I am writing to express my strong interest in the {listing.get('title')} role. "
            f"As a {profile.get('education')} student specializing in {', '.join(profile.get('skills', [])[:3])}, "
            f"I have built robust projects and gained practical experience in full-stack development and machine learning. "
            f"I am eager to contribute my skills in {profile.get('skills', ['Python'])[0]} and problem-solving to {listing.get('company')}.\n\n"
            f"Sincerely,\n{profile.get('full_name')}"
        )

    def generate_application_answers(self, listing: Dict[str, Any], profile: Dict[str, Any], questions: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Generates tailored 2-3 sentence answers for screening/application questions.
        """
        if not questions:
            questions = [
                "Why do you want this internship?",
                "What relevant skills and experience do you have?",
                "What do you hope to learn from this internship?",
                "Where do you see yourself in 5 years?"
            ]

        system_prompt = "You are a career coach. Answer each question in 2-3 sentences based on profile data. Return JSON dict."
        user_prompt = f"""
Generate tailored application answers for candidate {profile.get('full_name')} applying to {listing.get('title')} at {listing.get('company')}.

Profile Summary: {profile.get('experience_summary')}
Skills: {', '.join(profile.get('skills', []))}

Questions to answer:
{json.dumps(questions)}

Return JSON object mapping each question string to a 2-3 sentence answer string.
"""
        raw = self._call_groq(system_prompt, user_prompt, temperature=0.3)
        if raw:
            try:
                cleaned = raw
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                return json.loads(cleaned)
            except Exception:
                pass

        # Fallback answers
        answers = {}
        for q in questions:
            if "why" in q.lower():
                answers[q] = f"I am excited to join {listing.get('company')} to apply my hands-on background in {', '.join(profile.get('skills', [])[:2])} to real-world projects."
            elif "skill" in q.lower() or "experience" in q.lower():
                answers[q] = f"I have built several projects using {', '.join(profile.get('skills', [])[:4])}, demonstrating strong technical problem-solving capabilities."
            elif "learn" in q.lower():
                answers[q] = f"I hope to deepen my industry knowledge in {listing.get('title')} domain practices and collaborate with experienced engineering teams."
            else:
                answers[q] = f"In 5 years, I aim to be a Lead AI Engineer building scalable intelligent software systems."
        return answers

brain = GroqBrain()
