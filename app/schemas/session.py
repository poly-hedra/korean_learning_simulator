"""Session-centric API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., description="고유 사용자 ID")
    country: str
    korean_level: str = Field(..., description="Beginner/Intermediate/Advanced")
    has_korean_media_experience: bool
    location: str


class SelectRoleRequest(BaseModel):
    selected_role: str = Field(..., description="A 또는 B")


class CreateTurnRequest(BaseModel):
    user_input: str


class SessionStateResponse(BaseModel):
    session_id: str
    user_profile: dict[str, Any]
    location: str = ""
    scenario_title: str = ""
    scenario_description: str = ""
    personas: dict[str, dict[str, Any]] = Field(default_factory=dict)
    conversation_log: list[dict[str, Any]] = Field(default_factory=list)
    turn_count: int = 0
    turn_limit: int = 0
    is_finished: bool = False
    relationship_type: str = ""
    dialogue_function: list[str] = Field(default_factory=list)
    latest_ai_response: str = ""
    location_context: str = ""


class EvaluationResponse(BaseModel):
    session_id: str
    conversation_log: list[dict[str, Any]] = Field(default_factory=list)
    location: str = ""
    scenario_title: str = ""
    highlighted_log: list[dict[str, Any]] = Field(default_factory=list)
    total_score_10: float = 0.0
    tier: str = ""
    feedback: str = ""
    llm_summary: str = ""
    SCK_match_count: int = 0
    SCK_total_tokens: int = 0
    SCK_match_rate: float = 0.0
    SCK_level_counts: dict[str, int] = Field(default_factory=dict)
    SCK_level_word_counts: dict[str, Any] = Field(default_factory=dict)
