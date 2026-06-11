from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ProjectCreateRequest(BaseModel):
    premise: str = Field(
        ..., example="A poor student discovers a phone that predicts the future."
    )
    language: str = Field(
        default="English",
        description="Output language for narration and script (e.g. English, Hindi, Spanish, French, German, Japanese, Korean, Arabic)",
    )
    genre: Optional[str] = Field(
        default="Basic",
        description="The story genre (e.g., Funny, Thriller, Basic)",
    )
    voice: Optional[str] = Field(
        default=None,
        description="Optional Edge-TTS voice override. Auto-detected from language when omitted.",
    )
    image_style: Optional[str] = Field(
        default="Cinematic",
        description="Visual style for image prompts",
    )


class ContinueEpisodeRequest(BaseModel):
    """Request body for generating the next episode from an existing project."""
    parent_project_id: str = Field(
        ..., description="The project_id of the previous episode to continue from."
    )
    language: Optional[str] = Field(
        default=None,
        description="Override language (defaults to parent project's language).",
    )
    voice: Optional[str] = Field(
        default=None,
        description="Optional Edge-TTS voice override.",
    )
    image_style: Optional[str] = Field(
        default="Cinematic",
        description="Visual style for image prompts.",
    )


class CustomStoryRequest(BaseModel):
    """Request body for generating a video from a user-provided story structure."""
    story: Dict[str, Any] = Field(
        ...,
        description="Full story JSON matching the Story schema: {title, hook, characters, scenes, ending_cliffhanger}",
    )
    language: Optional[str] = Field(
        default="English",
        description="Language for TTS voice selection.",
    )
    voice: Optional[str] = Field(
        default=None,
        description="Optional Edge-TTS voice override.",
    )
    image_style: Optional[str] = Field(
        default="Cinematic",
        description="Visual style for image prompts.",
    )


class ProjectResponse(BaseModel):
    project_id: str = Field(..., description="Unique ID for this drama project")
    title: str = Field(..., description="Story title")
    video_path: str = Field(..., description="Path to the generated MP4 video")
    thumbnail_path: str = Field(..., description="Path to the generated PNG thumbnail")
    duration: float = Field(..., description="Duration of the video in seconds")
    status: str = Field(default="completed", description="Generation status")


class ProjectDetailsResponse(BaseModel):
    project_id: str
    title: str
    premise: str
    status: str
    duration: float
    video_url: str
    thumbnail_url: str
    story: Dict[str, Any]
    social: Dict[str, Any]
    created_at: str
