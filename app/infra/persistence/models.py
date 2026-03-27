"""Persistence models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    week: int
    korean_level: str
    location: str
    scenario_title: str
    conversation_log: list[dict]
    total_score_10: float
    tier: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WrongWordRecord:
    user_id: str
    word: str
    meaning: str
    source_session_week: int


@dataclass
class UserProfileRecord:
    user_id: str
    country: str
    korean_level: str
    has_korean_media_experience: bool
    selected_role: str = "A"
    latest_tier: str = ""
    extra: dict = field(default_factory=dict)
