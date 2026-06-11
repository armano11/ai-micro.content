"""
Image Service — FLUX.1-schnell via NVIDIA NIM genai endpoint.

Performance: connection pooling, higher concurrency, retries with backoff.
Cascade: NVIDIA → Pollinations → local fallback.
"""

import asyncio
import random
import base64
import urllib.parse
from contextlib import asynccontextmanager

import httpx
from pathlib import Path
from PIL import Image, ImageDraw

from app.config.settings import settings
from app.utils.file_utils import get_project_file_path
from app.utils.logger import get_logger

logger = get_logger(__name__)

# The correct NVIDIA NIM genai endpoint for FLUX
FLUX_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"

# ─── Reusable connection pool ───
_pool_lock = asyncio.Lock()
_nvidia_pool: httpx.AsyncClient | None = None
_poll_pool: httpx.AsyncClient | None = None


async def _get_nvidia_client() -> httpx.AsyncClient:
    global _nvidia_pool
    if _nvidia_pool is None or _nvidia_pool.is_closed:
        async with _pool_lock:
            if _nvidia_pool is None or _nvidia_pool.is_closed:
                _nvidia_pool = httpx.AsyncClient(
                    timeout=60.0,
                    limits=httpx.Limits(max_connections=6, max_keepalive_connections=4),
                )
    return _nvidia_pool


async def _get_pollinations_client() -> httpx.AsyncClient:
    global _poll_pool
    if _poll_pool is None or _poll_pool.is_closed:
        async with _pool_lock:
            if _poll_pool is None or _poll_pool.is_closed:
                _poll_pool = httpx.AsyncClient(
                    timeout=45.0,
                    limits=httpx.Limits(max_connections=8, max_keepalive_connections=6),
                )
    return _poll_pool


class ImageService:

    @staticmethod
    async def generate_character_base(
        project_id: str, character_desc: str, style: str = "Cinematic"
    ) -> Path:
        output = get_project_file_path(project_id, "character_base.png")
        prompt = (
            f"{style} vertical portrait study of: {character_desc}. "
            "Clean dark background, soft side studio lighting, highly detailed face, "
            "cinematic movie still."
        )
        return await ImageService._generate(output, prompt, tag="character")

    @staticmethod
    async def generate_scene_image(
        project_id: str, scene_number: int, prompt: str, style: str = "Cinematic"
    ) -> Path:
        output = get_project_file_path(project_id, f"scene_{scene_number}.png")
        styled = f"{style} style, vertical 9:16, {prompt}"
        return await ImageService._generate(output, styled, tag=f"scene_{scene_number}")

    @staticmethod
    async def generate_all_images(
        project_id: str, scenes: list,
        character_desc: str | None = None, style: str = "Cinematic"
    ) -> list[Path]:
        logger.info(f"Image pipeline starting for {project_id}...")

        # Character base generation (non-blocking, don't gate scenes on it)
        char_task = None
        if character_desc:
            char_task = asyncio.create_task(
                ImageService.generate_character_base(project_id, character_desc, style)
            )

        # Higher concurrency: 3 parallel image requests
        sem = asyncio.Semaphore(3)

        async def worker(sc):
            async with sem:
                return await ImageService.generate_scene_image(
                    project_id, sc.scene_number, sc.image_prompt, style
                )

        paths = await asyncio.gather(*(worker(s) for s in scenes))

        # Wait for character base if it was started
        if char_task:
            try:
                await char_task
            except Exception as e:
                logger.warning(f"Character base failed: {e}")

        logger.info(f"All {len(paths)} images generated.")
        return paths

    # ─────────── cascade: NVIDIA → Pollinations → fallback ───────────

    @staticmethod
    async def _generate(output: Path, prompt: str, tag: str = "") -> Path:
        # 1) NVIDIA FLUX.1-schnell
        if settings.nvidia_configured:
            logger.info(f"[{tag}] Trying NVIDIA FLUX.1-schnell...")
            try:
                data = await ImageService._nvidia_flux(prompt)
                if data:
                    output.write_bytes(data)
                    logger.info(f"[{tag}] NVIDIA FLUX success ({len(data):,} bytes)")
                    return output
            except Exception as e:
                logger.warning(f"[{tag}] NVIDIA FLUX failed: {e}")

        # 2) Pollinations AI (free, keyless)
        logger.info(f"[{tag}] Trying Pollinations...")
        try:
            data = await ImageService._pollinations(prompt)
            if data:
                output.write_bytes(data)
                logger.info(f"[{tag}] Pollinations success")
                return output
        except Exception as e:
            logger.warning(f"[{tag}] Pollinations failed: {e}")

        # 3) Local gradient placeholder
        logger.info(f"[{tag}] Local fallback placeholder")
        ImageService._local_fallback(output, prompt, tag)
        return output

    # ─────────── NVIDIA FLUX.1-schnell ───────────

    @staticmethod
    async def _nvidia_flux(prompt: str, retries: int = 2) -> bytes | None:
        """
        Call the correct NVIDIA genai endpoint for FLUX.1-schnell.
        Includes retry with exponential backoff for transient failures.
        """
        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            "steps": 4,
            "seed": random.randint(0, 999_999),
        }

        client = await _get_nvidia_client()

        for attempt in range(retries + 1):
            try:
                r = await client.post(FLUX_URL, headers=headers, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    arts = data.get("artifacts", [])
                    if arts and "base64" in arts[0]:
                        return base64.b64decode(arts[0]["base64"])
                    logger.warning(f"FLUX 200 but unexpected keys: {list(data.keys())}")
                    return None
                elif r.status_code in (429, 502, 503) and attempt < retries:
                    wait = 2 ** attempt + random.random()
                    logger.warning(f"FLUX {r.status_code}, retrying in {wait:.1f}s...")
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.warning(f"FLUX {r.status_code}: {r.text[:300]}")
                    return None
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt < retries:
                    wait = 2 ** attempt + random.random()
                    logger.warning(f"FLUX network error: {e}, retrying in {wait:.1f}s...")
                    await asyncio.sleep(wait)
                else:
                    raise
        return None

    # ─────────── Pollinations ───────────

    @staticmethod
    async def _pollinations(prompt: str) -> bytes | None:
        encoded = urllib.parse.quote(f"cinematic 9:16 vertical drama, {prompt}")
        seed = random.randint(1, 999_999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=912&nologo=true&seed={seed}"
        client = await _get_pollinations_client()
        r = await client.get(url)
        if r.status_code == 200:
            return r.content
        return None

    # ─────────── Local fallback ───────────

    @staticmethod
    def _local_fallback(out: Path, prompt: str, tag: str = ""):
        w, h = 1024, 1792
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            r = int(8 + 22 * y / h)
            g = int(6 + 12 * y / h)
            b = int(20 + 30 * y / h)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        draw.rectangle([(20, 20), (w - 20, h - 20)], outline="#d4af37", width=4)
        label = tag.upper().replace("_", " ") or "IMAGE"
        draw.text((w // 2, 200), label, fill="#d4af37", anchor="ms", font_size=72)
        words = prompt.split()
        lines, cur = [], []
        for word in words:
            if len(" ".join(cur + [word])) * 14 < w - 140:
                cur.append(word)
            else:
                lines.append(" ".join(cur))
                cur = [word]
        if cur:
            lines.append(" ".join(cur))
        y_t = h // 2 - 80
        for line in lines[:8]:
            draw.text((w // 2, y_t), line, fill="#e0e0e0", anchor="ms", font_size=32)
            y_t += 46
        draw.text((w // 2, h - 120), "AI MICRO-DRAMA STUDIO", fill="#d4af37", anchor="ms", font_size=28)
        img.save(out, "PNG")
