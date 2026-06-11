from pydantic import BaseModel, Field
from typing import List

class Character(BaseModel):
    name: str = Field(..., description="Name of the character")
    description: str = Field(..., description="Visual and narrative description of the character")

class Scene(BaseModel):
    scene_number: int = Field(..., description="Sequence number of the scene (1 to 5)")
    description: str = Field(..., description="Details about the setting and character action")
    narration: str = Field(..., description="Narrator script to be spoken in this scene")
    image_prompt: str = Field(..., description="Highly detailed cinematic prompt for generating the scene image")

class Story(BaseModel):
    title: str = Field(..., description="Dramatic title of the micro-drama episode")
    hook: str = Field(..., description="Opening attention grabber (first 3 seconds)")
    characters: List[Character] = Field(..., description="List of characters appearing in the story")
    scenes: List[Scene] = Field(..., description="Chronological breakdown of the 5 scenes")
    ending_cliffhanger: str = Field(..., description="Unresolved dramatic ending statement or question")
