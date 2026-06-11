"""
Social Service — Generate viral social media copy via NVIDIA NIM LLM.
"""

import json
import httpx

from app.config.settings import settings
from app.utils.file_utils import save_json
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SocialService:
    @staticmethod
    async def generate_social_package(
        project_id: str,
        title: str,
        hook: str,
        cliffhanger: str,
        language: str = "English",
    ) -> dict:
        """Generate YouTube/Reel/Instagram copy. Falls back to template."""
        logger.info(f"Generating social package for {project_id}...")

        if not settings.nvidia_configured:
            pkg = SocialService._template(title, hook, cliffhanger)
            save_json(project_id, "social.json", pkg)
            return pkg

        system_prompt = (
            "You are a viral social media copywriter for short-form drama on TikTok, Reels, Shorts.\n"
            f"Write ALL copy in **{language}**.\n"
            "Return ONLY raw JSON — no markdown fences:\n"
            '{"youtube_title":"...","reel_title":"...","instagram_caption":"...","hashtags":["...",...]}'
        )
        user_prompt = f"Title: {title}\nHook: {hook}\nCliffhanger: {cliffhanger}"

        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.story_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 512,
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if r.status_code != 200:
                    raise Exception(f"NIM {r.status_code}")

                content = r.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1]).strip()

                pkg = json.loads(content)
                save_json(project_id, "social.json", pkg)
                return pkg
        except Exception as e:
            logger.warning(f"NIM social failed: {e}. Using template.")
            pkg = SocialService._template(title, hook, cliffhanger)
            save_json(project_id, "social.json", pkg)
            return pkg

    @staticmethod
    def _template(title: str, hook: str, cliffhanger: str) -> dict:
        t = title.replace('"', "").strip()
        return {
            "youtube_title": f"{t} | What happens next? #shorts",
            "reel_title": f"{t} #drama #viral",
            "instagram_caption": (
                f'"{hook}"\n\n'
                f"Watch the full story to find out what happens...\n\n"
                f"{cliffhanger}\n\n"
                "Tell us in the comments!"
            ),
            "hashtags": [
                "microdrama", "aistory", "shorts", "drama",
                "plottwist", "viral", "whatwouldyoudo", "ai",
            ],
        }
