"""
Subtitle Service — generate SRT file from word boundary data.

Handles cases where Edge-TTS provides no word boundaries
(e.g. non-Latin scripts) by falling back to duration-proportional estimation.
"""

from pathlib import Path
from typing import List, Dict, Any

from app.utils.file_utils import get_project_file_path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SubtitleService:

    @staticmethod
    def format_srt_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0.0
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds % 1) * 1000))
        if ms >= 1000:
            s += 1
            ms -= 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    def generate_srt(
        project_id: str,
        scenes_word_boundaries: List[List[Dict[str, Any]]],
        scene_durations: List[float],
        scene_narrations: List[str] | None = None,
    ) -> Path:
        """
        Build a master subtitles.srt from word boundary events.

        If word boundaries are empty (common with non-Latin Edge-TTS voices),
        falls back to splitting narration text into timed chunks based on duration.
        """
        logger.info(f"Generating subtitles for {project_id}...")

        # Check if we have ANY word boundaries at all
        total_words = sum(len(wb) for wb in scenes_word_boundaries)

        if total_words > 0:
            captions = SubtitleService._from_word_boundaries(
                scenes_word_boundaries, scene_durations
            )
        else:
            # Fallback: estimate from narration text + durations
            logger.warning("No word boundaries from TTS — using duration-based estimation.")
            captions = SubtitleService._from_narration_text(
                scene_narrations or [], scene_durations
            )

        # Format SRT
        srt_lines = []
        for i, cap in enumerate(captions):
            srt_lines.append(str(i + 1))
            srt_lines.append(
                f"{SubtitleService.format_srt_time(cap['start'])} --> "
                f"{SubtitleService.format_srt_time(cap['end'])}"
            )
            srt_lines.append(cap["text"].strip())
            srt_lines.append("")

        output = get_project_file_path(project_id, "subtitles.srt")
        output.write_text("\n".join(srt_lines), encoding="utf-8")
        logger.info(f"Saved {len(captions)} captions -> {output}")
        return output

    # ─────────── from real word boundaries ───────────

    @staticmethod
    def _from_word_boundaries(
        scenes_wb: List[List[Dict]], scene_durations: List[float]
    ) -> List[Dict]:
        all_words = []
        offset = 0.0
        for idx, wbs in enumerate(scenes_wb):
            for w in wbs:
                all_words.append({
                    "start": w["start"] + offset,
                    "end": w["end"] + offset,
                    "text": w["text"],
                })
            offset += scene_durations[idx]

        # Group into 3-word caption segments
        captions = []
        group: List[Dict] = []
        for word in all_words:
            if not group:
                group.append(word)
                continue
            gap = word["start"] - group[-1]["end"]
            dur = word["end"] - group[0]["start"]
            if len(group) >= 3 or dur > 1.5 or gap > 0.4:
                captions.append({
                    "start": group[0]["start"],
                    "end": group[-1]["end"],
                    "text": " ".join(w["text"] for w in group),
                })
                group = [word]
            else:
                group.append(word)
        if group:
            captions.append({
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "text": " ".join(w["text"] for w in group),
            })
        return captions

    # ─────────── fallback: duration-proportional ───────────

    @staticmethod
    def _from_narration_text(
        narrations: List[str], durations: List[float]
    ) -> List[Dict]:
        """Split narration text into ~3-word chunks timed proportionally."""
        captions = []
        offset = 0.0

        for narr, dur in zip(narrations, durations):
            words = narr.split()
            if not words:
                offset += dur
                continue

            # Split into chunks of 3 words
            chunks = []
            for i in range(0, len(words), 3):
                chunks.append(" ".join(words[i : i + 3]))

            total_chars = max(sum(len(c) for c in chunks), 1)
            t = offset
            for chunk in chunks:
                chunk_dur = (len(chunk) / total_chars) * dur
                captions.append({
                    "start": round(t, 3),
                    "end": round(t + chunk_dur, 3),
                    "text": chunk,
                })
                t += chunk_dur
            offset += dur

        return captions
