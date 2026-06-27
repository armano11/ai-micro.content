from pydantic_settings import BaseSettings
from pathlib import Path
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    nvidia_api_key: str = Field(default="", validation_alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias="NVIDIA_BASE_URL",
    )
    content_model: str = Field(
        default="meta/llama-3.3-70b-instruct", validation_alias="CONTENT_MODEL"
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    data_dir: Path = BASE_DIR / "data"
    exports_dir: Path = BASE_DIR / "exports"

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.nvidia_api_key and "your_" not in self.nvidia_api_key)

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key and "your_" not in self.openai_api_key)

    @property
    def ai_configured(self) -> bool:
        return self.nvidia_configured or self.openai_configured

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
settings.data_dir.mkdir(exist_ok=True)
settings.exports_dir.mkdir(exist_ok=True)
