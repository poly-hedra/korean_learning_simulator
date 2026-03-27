"""User-centric API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    user_id: str
    country: str
    korean_level: str
    has_korean_media_experience: bool
    selected_role: str = "A"
    latest_tier: str = ""


class WeeklyStatsResponse(BaseModel):
    user_id: str
    conversation_count: int = 0
    average_score: float = 0.0
    latest_tier: str = ""


class WeeklyReviewResponse(BaseModel):
    user_profile: dict[str, Any] = Field(default_factory=dict)
    selected_weak_sessions: list[dict[str, Any]] = Field(default_factory=list)
    chosung_quiz: list[dict[str, Any]] = Field(default_factory=list)
    flashcards: list[dict[str, Any]] = Field(default_factory=list)


class ReviewCountResponse(BaseModel):
    user_id: str
    chosung_quiz_count: int = 0
    flashcard_count: int = 0
