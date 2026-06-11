from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.utils.file_utils import list_projects, load_json, get_project_file_path
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("", response_model=List[str])
async def get_projects():
    """Lists all generated project IDs."""
    try:
        return list_projects()
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not list projects")

@router.get("/{project_id}")
async def get_project_details(project_id: str):
    """Retrieves all stored configuration, story info, and social pack for a project."""
    try:
        metadata = load_json(project_id, "metadata.json")
        if not metadata:
            # Check if directory exists, if so return a basic status
            proj_dir = get_project_file_path(project_id, "")
            if proj_dir.exists():
                return {
                    "project_id": project_id,
                    "status": "processing",
                    "message": "Project folder exists, but metadata is missing."
                }
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Enrich file paths or URLs if possible
        # Check if video exists
        video_path = get_project_file_path(project_id, "final_video.mp4")
        metadata["video_exists"] = video_path.exists()
        
        thumbnail_path = get_project_file_path(project_id, "thumbnail.png")
        metadata["thumbnail_exists"] = thumbnail_path.exists()
        
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
