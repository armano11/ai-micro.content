from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.audio_service import AudioService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/audio", tags=["audio"])

class SceneNarration(BaseModel):
    scene_number: int
    narration: str

class AudioGenerationRequest(BaseModel):
    project_id: str
    scenes: List[SceneNarration]
    voice: Optional[str] = None

@router.post("/generate")
async def generate_audio(request: AudioGenerationRequest):
    """Generates audio files for all scenes and merges them into one narration.mp3."""
    try:
        audio_paths = []
        all_word_boundaries = []
        
        # 1. Generate audio clips sequentially to prevent overloading TTS API
        for scene in request.scenes:
            path, boundaries = await AudioService.generate_scene_audio(
                project_id=request.project_id,
                scene_number=scene.scene_number,
                text=scene.narration,
                voice=request.voice
            )
            audio_paths.append(path)
            all_word_boundaries.append(boundaries)
            
        # 2. Concatenate individual clips into the final master narration.mp3
        master_audio_path = await AudioService.concatenate_audios(request.project_id, audio_paths)
        
        # We also return paths and boundaries so the caller can calculate duration or generate SRT
        return {
            "project_id": request.project_id,
            "master_audio_path": str(master_audio_path),
            "individual_audio_paths": [str(p) for p in audio_paths],
            "word_boundaries": all_word_boundaries,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error in audio generation route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
