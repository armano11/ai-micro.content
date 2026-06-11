"""
FFmpeg utilities — subprocess wrappers for video assembly.
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import List, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─────────── FFmpeg / FFprobe discovery ───────────

FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"
FFMPEG_FOUND = False


def locate_ffmpeg():
    """Locate ffmpeg/ffprobe: system PATH first, then WinGet packages."""
    global FFMPEG_PATH, FFPROBE_PATH, FFMPEG_FOUND

    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        FFMPEG_PATH, FFPROBE_PATH, FFMPEG_FOUND = "ffmpeg", "ffprobe", True
        logger.info("FFmpeg found in system PATH.")
        return

    local = os.environ.get("LOCALAPPDATA")
    if local:
        winget = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if winget.exists():
            logger.info(f"Searching WinGet packages: {winget}")
            for p in winget.glob("**/ffmpeg.exe"):
                fp = p.parent / "ffprobe.exe"
                if fp.is_file():
                    FFMPEG_PATH, FFPROBE_PATH, FFMPEG_FOUND = str(p), str(fp), True
                    logger.info(f"FFmpeg: {FFMPEG_PATH}")
                    logger.info(f"FFprobe: {FFPROBE_PATH}")
                    return

    logger.warning("FFmpeg not found. Video processing may fail.")


locate_ffmpeg()


# ─────────── subprocess runner ───────────

async def run_subprocess(
    cmd: List[str], cwd: Path | None = None
) -> Tuple[bool, str, str]:
    """Run a command asynchronously, returning (success, stdout, stderr)."""
    global FFMPEG_FOUND
    if not FFMPEG_FOUND:
        locate_ffmpeg()

    if cmd[0] == "ffmpeg":
        cmd[0] = FFMPEG_PATH
    elif cmd[0] == "ffprobe":
        cmd[0] = FFPROBE_PATH

    logger.info(f"CMD: {' '.join(cmd)}  CWD={cwd}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        ok = proc.returncode == 0
        out = stdout.decode("utf-8", errors="ignore").strip()
        err = stderr.decode("utf-8", errors="ignore").strip()
        if not ok:
            logger.error(f"CMD failed (code {proc.returncode}): {err[:500]}")
        return ok, out, err
    except Exception as e:
        logger.error(f"CMD exception: {e}")
        return False, "", str(e)


async def check_ffmpeg() -> bool:
    ok, _, _ = await run_subprocess(["ffmpeg", "-version"])
    return ok


# ─────────── audio duration ───────────

async def get_audio_duration(audio_path: Path) -> float:
    """Get duration in seconds via ffprobe, with file-size fallback."""
    if not audio_path.exists():
        logger.error(f"Audio missing: {audio_path}")
        return 0.0

    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    ok, out, _ = await run_subprocess(cmd)
    if ok:
        try:
            return float(out.strip())
        except ValueError:
            pass

    # fallback: estimate from file size (~128 kbps MP3)
    logger.warning("ffprobe failed; estimating duration from file size.")
    try:
        return max(3.0, round(audio_path.stat().st_size / 16_000, 1))
    except Exception:
        return 5.0


# ─────────── scene video ───────────

async def create_scene_video(
    image_path: Path, audio_path: Path, output_path: Path
) -> bool:
    """Loop image over audio → 1080×1920 MP4.  Runs in project dir with relative names."""
    cwd = image_path.parent
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path.name,
        "-i", audio_path.name,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path.name,
    ]
    ok, _, _ = await run_subprocess(cmd, cwd=cwd)
    return ok


# ─────────── concat ───────────

async def concatenate_videos(
    video_names: List[str], output_path: Path
) -> bool:
    """Concat via demuxer.  Runs in project dir."""
    cwd = output_path.parent
    txt = cwd / "concat_list.txt"
    txt.write_text(
        "\n".join(f"file '{n}'" for n in video_names), encoding="utf-8"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", txt.name,
        "-c", "copy",
        output_path.name,
    ]
    ok, _, _ = await run_subprocess(cmd, cwd=cwd)

    try:
        txt.unlink(missing_ok=True)
    except Exception:
        pass
    return ok


# ─────────── subtitle burn-in ───────────

def _ffmpeg_escape(path: Path) -> str:
    """
    Escape a Windows absolute path for the FFmpeg subtitles= filter.
    libass needs  C\\:/Users/...  (forward slashes, escaped colon).
    """
    s = str(path.resolve()).replace("\\", "/")
    s = s.replace(":", "\\:")
    return s


async def burn_subtitles_to_video(
    video_path: Path, srt_path: Path, output_path: Path
) -> bool:
    """
    Burn SRT subtitles into the video.
    Runs inside the project directory and uses relative path for subtitles
    to bypass Windows absolute path escaping limitations.
    """
    cwd = video_path.parent

    style = (
        "Alignment=10,Fontname=Arial,FontSize=20,Bold=1,"
        "PrimaryColour=&H00FFFF,OutlineColour=&H000000,Outline=2"
    )
    # Using the relative filename in cwd avoids colon separation issues on Windows
    vf = f"subtitles={srt_path.name}:force_style='{style}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path.name,
        "-vf", vf,
        "-c:a", "copy",
        output_path.name,
    ]
    ok, _, _ = await run_subprocess(cmd, cwd=cwd)
    return ok
