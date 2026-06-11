from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.image_service import ImageService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/image", tags=["image"])

class ScenePrompt(BaseModel):
    scene_number: int
    image_prompt: str

class ImageGenerationRequest(BaseModel):
    project_id: str
    scenes: List[ScenePrompt]

@router.post("/generate")
async def generate_images(request: ImageGenerationRequest):
    """Generates images for all scenes and saves them in the project folder."""
    try:
        image_paths = await ImageService.generate_all_images(request.project_id, request.scenes)
        return {
            "project_id": request.project_id,
            "images": [str(p) for p in image_paths],
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error in image generation route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
