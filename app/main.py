"""
AI Micro-Drama Studio — FastAPI backend orchestrator (v3.0 — Turbo).

Performance upgrades:
  • Parallel audio + image generation (independent pipeline branches)
  • httpx connection pool reuse across requests
  • Concurrent social copy + thumbnail generation
  • Continue-episode & custom-story endpoints

Pipeline:
  Premise + Language
    → LLM Story Script  (NVIDIA NIM)
    → [ Edge-TTS Narration  ‖  FLUX.1-schnell Images ]   ← parallel
    → SRT Subtitles
    → FFmpeg Video Assembly + Subtitle Burn-in
    → [ PIL Thumbnail  ‖  Social Media Copy ]             ← parallel
"""

import asyncio
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.models.response_models import (
    ProjectCreateRequest,
    ProjectResponse,
    ContinueEpisodeRequest,
    CustomStoryRequest,
)
from app.routes import story, image, audio, video, project

from app.services.story_service import StoryService
from app.services.image_service import ImageService
from app.services.audio_service import AudioService
from app.services.subtitle_service import SubtitleService
from app.services.video_service import VideoService
from app.services.thumbnail_service import ThumbnailService
from app.services.social_service import SocialService

from app.utils.file_utils import save_json, load_json, get_project_dir
from app.utils.ffmpeg_utils import get_audio_duration, check_ffmpeg
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─────────── FastAPI app ───────────

app = FastAPI(
    title="AI Micro-Drama Studio API",
    description="Convert a story premise into a watchable vertical short drama video.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(story.router)
app.include_router(image.router)
app.include_router(audio.router)
app.include_router(video.router)
app.include_router(project.router)


@app.on_event("startup")
async def startup_event():
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static/projects",
        StaticFiles(directory=str(settings.projects_dir)),
        name="projects",
    )
    logger.info(f"Projects dir: {settings.projects_dir}")
    if await check_ffmpeg():
        logger.info("FFmpeg OK.")
    else:
        logger.warning("FFmpeg not detected — video assembly will fail.")


@app.get("/")
def root():
    return {"message": "AI Micro-Drama Studio API v3.0 — /docs for Swagger UI"}


# ─────────── shared pipeline core ───────────

async def _run_pipeline(
    project_id: str,
    story_obj,
    request_voice: str | None,
    request_style: str,
    lang: str,
    premise: str,
    parent_project_id: str | None = None,
) -> ProjectResponse:
    """Core pipeline shared by generate / continue / custom-story endpoints."""

    save_json(project_id, "story.json", story_obj.model_dump())
    logger.info(f"  1/7 Story: {story_obj.title}")

    # ── 2 + 4.  Audio & Images in PARALLEL ──
    char_desc = (
        story_obj.characters[0].description if story_obj.characters else None
    )

    async def _audio_branch():
        audio_paths, all_boundaries = [], []
        for sc in story_obj.scenes:
            path, wb = await AudioService.generate_scene_audio(
                project_id=project_id,
                scene_number=sc.scene_number,
                text=sc.narration,
                language=lang,
                voice=request_voice,
            )
            audio_paths.append(path)
            all_boundaries.append(wb)
        await AudioService.concatenate_audios(project_id, audio_paths)
        scene_durations = [await get_audio_duration(p) for p in audio_paths]
        total_dur = sum(scene_durations)
        logger.info(f"  2/7 Audio: {total_dur:.1f}s  durations={scene_durations}")
        return audio_paths, all_boundaries, scene_durations, total_dur

    async def _image_branch():
        paths = await ImageService.generate_all_images(
            project_id, story_obj.scenes, char_desc, request_style
        )
        logger.info(f"  4/7 Images: {len(paths)} scenes")
        return paths

    (audio_paths, all_boundaries, scene_durations, total_dur), image_paths = (
        await asyncio.gather(_audio_branch(), _image_branch())
    )

    # ── 3. Subtitles ──
    narration_texts = [sc.narration for sc in story_obj.scenes]
    srt_path = SubtitleService.generate_srt(
        project_id, all_boundaries, scene_durations, narration_texts
    )
    logger.info(f"  3/7 Subtitles: {srt_path}")

    # ── 5. Video assembly ──
    final_video = await VideoService.assemble_video(
        project_id, image_paths, audio_paths, srt_path
    )
    logger.info(f"  5/7 Video: {final_video}")

    # ── 6 + 7.  Thumbnail & Social in PARALLEL ──
    async def _thumb():
        return ThumbnailService.generate_thumbnail(
            project_id, story_obj.title, image_paths
        )

    async def _social():
        return await SocialService.generate_social_package(
            project_id, story_obj.title, story_obj.hook,
            story_obj.ending_cliffhanger, lang,
        )

    thumb, social = await asyncio.gather(_thumb(), _social())
    logger.info(f"  6/7 Thumbnail: {thumb}")
    logger.info("  7/7 Social copy done.")

    # ── Save metadata ──
    meta = {
        "project_id": project_id,
        "title": story_obj.title,
        "premise": premise,
        "language": lang,
        "status": "completed",
        "duration": round(total_dur, 2),
        "video_path": str(final_video),
        "thumbnail_path": str(thumb),
        "created_at": datetime.now().isoformat(),
        "story": story_obj.model_dump(),
        "social": social,
    }
    if parent_project_id:
        meta["parent_project_id"] = parent_project_id

    save_json(project_id, "metadata.json", meta)

    return ProjectResponse(
        project_id=project_id,
        title=story_obj.title,
        video_path=f"/static/projects/{project_id}/final_video.mp4",
        thumbnail_path=f"/static/projects/{project_id}/thumbnail.png",
        duration=round(total_dur, 2),
        status="completed",
    )


# ─────────── main pipeline ───────────

@app.post("/generate-project", response_model=ProjectResponse)
async def generate_project(request: ProjectCreateRequest):
    """Full production pipeline: story → audio‖images → subs → video → thumb‖social."""

    project_id = uuid.uuid4().hex[:10]
    lang = request.language or "English"
    logger.info(f"▶ Pipeline start | id={project_id} lang={lang}")
    get_project_dir(project_id)

    try:
        # ── 1. Story ──
        story_obj = await StoryService.generate_story(request.premise, lang, genre=request.genre)

        return await _run_pipeline(
            project_id=project_id,
            story_obj=story_obj,
            request_voice=request.voice,
            request_style=request.image_style or "Cinematic",
            lang=lang,
            premise=request.premise,
        )

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        try:
            save_json(project_id, "metadata.json", {
                "project_id": project_id,
                "premise": request.premise,
                "status": "failed",
                "error": str(e),
                "created_at": datetime.now().isoformat(),
            })
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


# ─────────── continue episode ───────────

@app.post("/continue-episode", response_model=ProjectResponse)
async def continue_episode(request: ContinueEpisodeRequest):
    """Generate the next episode continuing from a previous project's cliffhanger."""

    parent_meta = load_json(request.parent_project_id, "metadata.json")
    if not parent_meta:
        raise HTTPException(status_code=404, detail="Parent project not found")

    parent_story = parent_meta.get("story", {})
    cliffhanger = parent_story.get("ending_cliffhanger", "")
    parent_title = parent_story.get("title", "")
    parent_premise = parent_meta.get("premise", "")
    lang = request.language or parent_meta.get("language", "English")

    continuation_premise = (
        f"This is Episode 2 continuing the story '{parent_title}'. "
        f"Original premise: {parent_premise}. "
        f"The last episode ended with: '{cliffhanger}'. "
        f"Continue the story with rising stakes and a new cliffhanger. "
        f"Keep the same main characters."
    )

    project_id = uuid.uuid4().hex[:10]
    logger.info(f"▶ Continue-Episode | parent={request.parent_project_id} -> {project_id}")
    get_project_dir(project_id)

    try:
        story_obj = await StoryService.generate_story(continuation_premise, lang)

        return await _run_pipeline(
            project_id=project_id,
            story_obj=story_obj,
            request_voice=request.voice,
            request_style=request.image_style or "Cinematic",
            lang=lang,
            premise=continuation_premise,
            parent_project_id=request.parent_project_id,
        )

    except Exception as e:
        logger.error(f"Continue-episode failed: {e}", exc_info=True)
        try:
            save_json(project_id, "metadata.json", {
                "project_id": project_id,
                "premise": continuation_premise,
                "status": "failed",
                "error": str(e),
                "created_at": datetime.now().isoformat(),
            })
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Continue-episode failed: {e}")


# ─────────── custom story ───────────

@app.post("/custom-story", response_model=ProjectResponse)
async def custom_story(request: CustomStoryRequest):
    """Skip LLM: user provides their own structured story JSON directly."""

    from app.models.story_models import Story

    project_id = uuid.uuid4().hex[:10]
    lang = request.language or "English"
    logger.info(f"▶ Custom-Story | id={project_id}")
    get_project_dir(project_id)

    try:
        story_obj = Story(**request.story)

        return await _run_pipeline(
            project_id=project_id,
            story_obj=story_obj,
            request_voice=request.voice,
            request_style=request.image_style or "Cinematic",
            lang=lang,
            premise=f"[Custom] {story_obj.title}",
        )

    except Exception as e:
        logger.error(f"Custom-story failed: {e}", exc_info=True)
        try:
            save_json(project_id, "metadata.json", {
                "project_id": project_id,
                "premise": "[Custom story input]",
                "status": "failed",
                "error": str(e),
                "created_at": datetime.now().isoformat(),
            })
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Custom-story failed: {e}")
