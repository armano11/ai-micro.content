import json
import os
from pathlib import Path
from typing import Any, Dict, List
from app.config.settings import settings

def get_project_dir(project_id: str) -> Path:
    """Gets the path to a project directory, creating it if it doesn't exist."""
    project_path = settings.projects_dir / project_id
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path

def get_project_file_path(project_id: str, filename: str) -> Path:
    """Returns the full Path to a specific file inside a project directory."""
    return get_project_dir(project_id) / filename

def save_json(project_id: str, filename: str, data: Any) -> Path:
    """Saves a python dictionary/list to a JSON file in the project directory."""
    file_path = get_project_file_path(project_id, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return file_path

def load_json(project_id: str, filename: str) -> Any:
    """Loads a JSON file from the project directory. Returns None if it doesn't exist."""
    file_path = get_project_file_path(project_id, filename)
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_text(project_id: str, filename: str, content: str) -> Path:
    """Saves a string to a text file in the project directory."""
    file_path = get_project_file_path(project_id, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path

def load_text(project_id: str, filename: str) -> str:
    """Loads text from a file in the project directory. Returns empty string if it doesn't exist."""
    file_path = get_project_file_path(project_id, filename)
    if not file_path.exists():
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def list_projects() -> List[str]:
    """Lists all active project IDs (folders under settings.projects_dir)."""
    if not settings.projects_dir.exists():
        return []
    return [p.name for p in settings.projects_dir.iterdir() if p.is_dir()]
