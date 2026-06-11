from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path
from app.services.video_service import VideoService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/video", tags=["video"])

class VideoAssembleRequest(BaseModel):
    project_id: str
    image_paths: List[str]
    audio_paths: List[str]
    srt_path: str

@router.post("/assemble")
async def assemble_video(request: VideoAssembleRequest):
    """Assembles image slides, audio, and subtitles into the final vertical video."""
    try:
        images = [Path(p) for p in request.image_paths]
        audios = [Path(p) for p in request.audio_paths]
        srt = Path(request.srt_path)
        
        final_video_path = await VideoService.assemble_video(
            project_id=request.project_id,
            image_paths=images,
            audio_paths=audios,
            srt_path=srt
        )
        
        return {
            "project_id": request.project_id,
            "video_path": str(final_video_path),
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error in video assembly route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
