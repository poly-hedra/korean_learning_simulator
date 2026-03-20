"""그래프 전반에서 공통으로 사용하는 상태 정의."""

from typing import Any, TypedDict


class DialogueTurn(TypedDict):
    """대화 로그의 한 턴."""

    speaker: str
    utterance: str


class UserProfile(TypedDict):
    """첫 방문 시에만 수집하는 정보."""

    user_id: str
    country: str
    korean_level: str
    has_korean_media_experience: bool
    selected_role: str


class BaseState(TypedDict, total=False):
    """여러 워크플로에서 공유하는 필드."""

    user_profile: UserProfile
    location: str
    scenario: str
    personas: dict[str, dict[str, Any]]
    conversation_log: list[DialogueTurn]
    turn_count: int
    turn_limit: int
