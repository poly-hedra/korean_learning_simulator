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
    korean_level: str  # TODO: Literal["Beginner", "Intermediate", "Advanced"] 로 고정 필요
    has_korean_media_experience: bool
    selected_role: str


class BaseState(TypedDict, total=False):
    """여러 워크플로에서 공유하는 필드."""

    user_profile: UserProfile
    location: str
    # generate_scenario 노드가 채운다.
    # 대화 워크플로우뿐 아니라 평가 워크플로우 등 여러 곳에서 시나리오 맥락을 참조할 수 있도록 BaseState에 선언.
    scenario_title: str          # UI 카드·캐싱 키로 사용
    scenario_description: str    # 학습자용 상황 안내 문장, 평가 시 "의도한 상황"을 확인하는 기준으로도 활용
    personas: dict[str, dict[str, Any]]  # 페르소나 필드: job→role, goal→mission 으로 변경
    conversation_log: list[DialogueTurn]
    turn_count: int
    turn_limit: int
