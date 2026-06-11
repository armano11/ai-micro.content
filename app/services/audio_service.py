"""
Audio Service — Edge-TTS based multilingual narration engine.

Pipeline:  text + language  →  Edge-TTS  →  MP3 + word boundaries
"""

import asyncio
from pathlib import Path
from typing import List, Tuple, Dict, Any

import edge_tts

from app.config.settings import settings
from app.utils.file_utils import get_project_file_path
from app.utils.ffmpeg_utils import get_audio_duration
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ────────────────────────────────────────────────────────────
# Language → Edge-TTS voice mapping  (best-quality Neural voices)
# ────────────────────────────────────────────────────────────
VOICE_MAP: Dict[str, str] = {
    "english":    "en-US-ChristopherNeural",
    "hindi":      "hi-IN-MadhurNeural",
    "spanish":    "es-ES-AlvaroNeural",
    "french":     "fr-FR-HenriNeural",
    "german":     "de-DE-KillianNeural",
    "japanese":   "ja-JP-KeitaNeural",
    "korean":     "ko-KR-InJoonNeural",
    "arabic":     "ar-SA-HamedNeural",
    "portuguese": "pt-BR-AntonioNeural",
    "chinese":    "zh-CN-YunxiNeural",
    "italian":    "it-IT-DiegoNeural",
    "russian":    "ru-RU-DmitryNeural",
    "turkish":    "tr-TR-AhmetNeural",
    "bengali":    "bn-IN-BashkarNeural",
    "tamil":      "ta-IN-ValluvarNeural",
    "telugu":     "te-IN-MohanNeural",
    "urdu":       "ur-PK-AsadNeural",
}


def resolve_voice(language: str, voice_override: str | None = None) -> str:
    """Return the Edge-TTS voice name for the given language."""
    if voice_override:
        return voice_override
    key = language.strip().lower()
    return VOICE_MAP.get(key, settings.default_voice)


class AudioService:
    # ─────────── public API ───────────

    @staticmethod
    async def generate_scene_audio(
        project_id: str,
        scene_number: int,
        text: str,
        language: str = "English",
        voice: str | None = None,
    ) -> Tuple[Path, List[Dict[str, Any]]]:
        """
        Generate TTS audio for one scene via Edge-TTS.

        Returns (mp3_path, word_boundaries).
        """
        filename = f"scene_{scene_number}.mp3"
        output_path = get_project_file_path(project_id, filename)

        resolved_voice = resolve_voice(language, voice)
        logger.info(
            f"Scene {scene_number} | voice={resolved_voice} | lang={language}"
        )

        communicate = edge_tts.Communicate(text, resolved_voice)
        submaker = edge_tts.SubMaker()

        word_boundaries: List[Dict[str, Any]] = []
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
                    word_boundaries.append(
                        {
                            "start": chunk["offset"] / 10_000_000,
                            "end": (chunk["offset"] + chunk["duration"])
                            / 10_000_000,
                            "text": chunk["text"],
                        }
                    )

        logger.info(f"Scene {scene_number} audio saved -> {output_path}")
        return output_path, word_boundaries

    # ─────────── concatenation ───────────

    @staticmethod
    async def concatenate_audios(
        project_id: str, scene_audio_paths: List[Path]
    ) -> Path:
        """Binary-merge individual scene MP3s into a master narration.mp3."""
        output_path = get_project_file_path(project_id, "narration.mp3")
        logger.info(
            f"Concatenating {len(scene_audio_paths)} audio files -> {output_path}"
        )
        with open(output_path, "wb") as out:
            for p in scene_audio_paths:
                with open(p, "rb") as inp:
                    out.write(inp.read())
        logger.info("Audio concatenation complete.")
        return output_path

    # ─────────── utility ───────────

    @staticmethod
    def estimate_word_boundaries(
        text: str, duration: float
    ) -> List[Dict[str, Any]]:
        """Character-proportional word timing estimation (fallback)."""
        words = text.split()
        if not words or duration <= 0:
            return []
        total_chars = max(sum(len(w) for w in words), 1)
        boundaries: List[Dict[str, Any]] = []
        t = 0.0
        for w in words:
            wd = (len(w) / total_chars) * duration
            boundaries.append(
                {"start": round(t, 3), "end": round(t + wd, 3), "text": w}
            )
            t += wd
        return boundaries
