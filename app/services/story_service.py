"""
Story Service — LLM-powered script generation via NVIDIA NIM.

Pipeline:  premise + language  →  Llama / Nemotron  →  Story JSON
"""

import json
import httpx

from app.config.settings import settings
from app.models.story_models import Story
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StoryService:
    @staticmethod
    async def generate_story(premise: str, language: str = "English", genre: str = "Basic") -> Story:
        """
        Convert a one-line premise into a structured 5-scene micro-drama.
        Narration is written in *language*; image_prompts stay English.
        """
        logger.info(f"Generating story | lang={language} | genre={genre} | premise='{premise}'")

        if not settings.nvidia_configured:
            logger.warning("NVIDIA API key not configured — using mock story.")
            return StoryService._mock_story(premise)

        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # ── STEP 1: Generate pure flowing script ──
                step1_prompt = (
                    f"You are a master Screenwriter.\n"
                    f"Write a highly engaging, continuous flowing voiceover script based on this premise: '{premise}'.\n"
                    f"GENRE: {genre.upper()}. The tone and vocabulary MUST completely reflect this genre.\n"
                    f"CRITICAL RULES:\n"
                    f"1. The script MUST be exactly 80 to 90 words long. This guarantees a 30-second runtime.\n"
                    f"2. Write in a continuous, flowing monologue format.\n"
                    f"3. Write it entirely in **{language}**.\n"
                    f"Respond with NOTHING ELSE but the pure voiceover script text."
                )
                
                resp1 = await client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    json={
                        "model": settings.story_model,
                        "messages": [{"role": "user", "content": step1_prompt}],
                        "temperature": 0.8,
                        "max_tokens": 400,
                    },
                    headers=headers,
                )
                if resp1.status_code != 200:
                    raise Exception(f"NIM API Step 1 failed: {resp1.status_code}")
                    
                master_script = resp1.json()["choices"][0]["message"]["content"].strip()
                logger.info(f"Generated {len(master_script.split())}-word master script.")

                # ── STEP 2: Map script to 5-scene JSON ──
                step2_system = (
                    f"You are a Hollywood Story Director.\n"
                    f"Take the provided voiceover script and convert it into a 5-scene JSON storyboard.\n\n"
                    "Rules:\n"
                    "1. Split the exact text of the provided voiceover script naturally across the 5 scenes. Do NOT write new dialogue.\n"
                    "2. 'image_prompt': Extremely detailed, photorealistic, cinematic prompt in English for each scene. Include lighting, camera angle, and atmosphere. Keep it under 40 words. Avoid sensitive/risky terms (e.g., 'blood', 'kill', 'gun', physical fights).\n"
                    f"3. OUTPUT LANGUAGE: Everything EXCEPT the image_prompts must be written in **{language}**.\n\n"
                    "Respond with ONLY a valid JSON object. Do not wrap in markdown blocks.\n"
                    "Schema: {\n"
                    "  \"title\": \"...\",\n"
                    "  \"hook\": \"...\",\n"
                    "  \"characters\": [{\"name\": \"...\", \"description\": \"...\"}],\n"
                    "  \"scenes\": [{\"scene_number\": 1, \"description\": \"...\", \"narration\": \"...\", \"image_prompt\": \"...\"}],\n"
                    "  \"ending_cliffhanger\": \"...\"\n"
                    "}"
                )
                
                resp2 = await client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    json={
                        "model": settings.story_model,
                        "messages": [
                            {"role": "system", "content": step2_system},
                            {"role": "user", "content": f"Master Voiceover Script:\n\n{master_script}"},
                        ],
                        "temperature": 0.5,
                        "max_tokens": 1200,
                    },
                    headers=headers,
                )
                
                if resp2.status_code != 200:
                    raise Exception(f"NIM API Step 2 failed: {resp2.status_code}")

                content = resp2.json()["choices"][0]["message"]["content"].strip()

                import re
                
                # Robustly extract JSON using regex
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                else:
                    raise Exception("No JSON object found in LLM response")

                print("RAW LLM OUTPUT:", content)

                story_data = json.loads(content)
                return Story(**story_data)

        except Exception as e:
            logger.error(f"Story generation failed: {e}. Using mock.", exc_info=True)
            return StoryService._mock_story(premise)

    # ─────────── fallback mock ───────────

    @staticmethod
    def _mock_story(premise: str) -> Story:
        """High-quality deterministic mock for offline / demo testing."""
        return Story(
            title="The Echoes of Tomorrow",
            hook="He answered a call that hadn't been made yet.",
            characters=[
                {
                    "name": "Leo",
                    "description": "A tired, 20-year-old student in a faded hoodie, with dark circles under his eyes.",
                }
            ],
            scenes=[
                {
                    "scene_number": 1,
                    "description": "Leo in a dim, rain-slicked alley, picking up a cracked smartphone.",
                    "narration": "Leo was down to his last dollar when the phone rang in the rain. A voice whispered: Don't look up.",
                    "image_prompt": "Cinematic 9:16 shot of a 20-year-old tired student in a dark wet alley, bending down to pick up a glowing violet cracked smartphone. Raindrops hitting the ground, neon reflections, moody dramatic lighting.",
                },
                {
                    "scene_number": 2,
                    "description": "Leo looking at the phone screen showing tomorrow's news.",
                    "narration": "The screen showed tomorrow's news. A winning lottery number and a photo of his own empty bank account.",
                    "image_prompt": "Close-up 9:16 vertical shot of a cracked phone screen held by a young man. The screen glows brightly displaying digital futures charts and red text. Atmospheric smoke, high contrast lighting.",
                },
                {
                    "scene_number": 3,
                    "description": "Leo in his dorm room, staring at the phone as money floods his account.",
                    "narration": "He placed the bet. In minutes thousands flooded his account. He thought he was free.",
                    "image_prompt": "Cinematic vertical 9:16 shot of a young man on a messy bed staring at a glowing phone with wide eyes. Stacks of cash beside him, warm desk lamp light.",
                },
                {
                    "scene_number": 4,
                    "description": "A dark figure standing in Leo's doorway.",
                    "narration": "The phone vibrated again. A new alert: They know you have it. Run. A shadow fell across his door.",
                    "image_prompt": "Suspenseful 9:16 shot from inside a dim room looking towards a half-open door. A tall menacing shadow silhouette in a trench coat. Blue moonlight filtering through the window.",
                },
                {
                    "scene_number": 5,
                    "description": "Leo backed against a wall, phone counting down to zero.",
                    "narration": "The screen locked. A final message: To live you must delete your own past. Countdown starting: five four three...",
                    "image_prompt": "Dramatic vertical 9:16 close-up of a terrified young man clutching a glowing phone against a brick wall. The screen shows a red digital countdown 0:05. Hard shadows, cinematic realism.",
                },
            ],
            ending_cliffhanger="Will Leo press delete, or let the countdown end?",
        )
