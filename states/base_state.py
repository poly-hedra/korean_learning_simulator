"""Common state definitions shared across graphs."""

from typing import Any, TypedDict


class DialogueTurn(TypedDict):
    """One turn in conversation log."""

    speaker: str
    utterance: str


class UserProfile(TypedDict):
    """Information collected only on first visit."""

    user_id: str
    country: str
    korean_level: str
    has_korean_media_experience: bool
    selected_role: str


class BaseState(TypedDict, total=False):
    """Shared fields used by multiple workflows."""

    user_profile: UserProfile
    location: str
    scenario: str
    personas: dict[str, dict[str, Any]]
    conversation_log: list[DialogueTurn]
    turn_count: int
    turn_limit: int
