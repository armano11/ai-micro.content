from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.story_models import Story
from app.services.story_service import StoryService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/story", tags=["story"])

class StoryRequest(BaseModel):
    premise: str

@router.post("/generate", response_model=Story)
async def generate_story(request: StoryRequest):
    """Generates a structured 5-scene drama based on a story premise."""
    try:
        story = await StoryService.generate_story(request.premise)
        return story
    except Exception as e:
        logger.error(f"Error in story generation route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
