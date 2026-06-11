from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application-wide configuration loaded from .env"""

    # Server
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")

    # NVIDIA NIM API
    nvidia_api_key: str = Field(default="", validation_alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias="NVIDIA_BASE_URL",
    )

    # LLM for story + social copy generation
    story_model: str = Field(
        default="meta/llama-3.3-70b-instruct",
        validation_alias="STORY_MODEL",
    )

    # Image generation (FLUX.1-schnell via NVIDIA NIM)
    image_model: str = Field(
        default="black-forest-labs/flux.1-schnell",
        validation_alias="IMAGE_MODEL",
    )

    # Hugging Face fallback
    hf_api_key: str = Field(default="", validation_alias="HF_API_KEY")
    hf_image_model: str = Field(
        default="stabilityai/stable-diffusion-xl-base-1.0",
        validation_alias="HF_IMAGE_MODEL",
    )

    # Edge-TTS default voice (English)
    default_voice: str = Field(
        default="en-US-ChristopherNeural",
        validation_alias="DEFAULT_VOICE",
    )

    # Filesystem
    projects_dir: Path = BASE_DIR / "projects"

    # --------------- helpers ---------------
    @property
    def nvidia_configured(self) -> bool:
        return bool(
            self.nvidia_api_key
            and self.nvidia_api_key.strip()
            and "your_" not in self.nvidia_api_key
        )

    @property
    def hf_configured(self) -> bool:
        return bool(
            self.hf_api_key
            and self.hf_api_key.strip()
            and "your_" not in self.hf_api_key
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
