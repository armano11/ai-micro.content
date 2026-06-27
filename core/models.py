from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json
import uuid


@dataclass
class PlatformSpec:
    name: str
    max_chars: int
    tone: str
    hashtag_limit: int
    supports_thread: bool = False
    supports_carousel: bool = False
    best_practices: list = field(default_factory=list)


@dataclass
class ScoreBreakdown:
    readability: float = 0.0
    sentiment: float = 0.0
    engagement: float = 0.0
    platform_fit: float = 0.0
    hook_strength: float = 0.0
    cta_presence: float = 0.0
    overall: float = 0.0
    grade: str = ""
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


@dataclass
class ContentVariant:
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    platform: str = ""
    content: str = ""
    hashtags: list = field(default_factory=list)
    score: Optional[ScoreBreakdown] = None
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MultiplexResult:
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    original_text: str = ""
    topic: str = ""
    variants: list = field(default_factory=list)
    original_score: Optional[ScoreBreakdown] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "original_text": self.original_text,
            "topic": self.topic,
            "created_at": self.created_at,
            "original_score": {
                "readability": self.original_score.readability,
                "sentiment": self.original_score.sentiment,
                "engagement": self.original_score.engagement,
                "overall": self.original_score.overall,
                "grade": self.original_score.grade,
            } if self.original_score else None,
            "variants": [
                {
                    "platform": v.platform,
                    "content": v.content,
                    "hashtags": v.hashtags,
                    "score": {
                        "readability": v.score.readability,
                        "sentiment": v.score.sentiment,
                        "engagement": v.score.engagement,
                        "platform_fit": v.score.platform_fit,
                        "hook_strength": v.score.hook_strength,
                        "overall": v.score.overall,
                        "grade": v.score.grade,
                        "issues": v.score.issues,
                        "suggestions": v.score.suggestions,
                    } if v.score else None,
                }
                for v in self.variants
            ],
        }
