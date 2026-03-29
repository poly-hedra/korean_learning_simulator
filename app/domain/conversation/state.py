"""대화 그래프용 상태 스키마."""

from typing import TypedDict

from app.domain.shared.state import BaseState


class ConversationState(BaseState, total=False):
    """대화 워크플로 상태.

    graph 내부에서 단계별로 누적되는 값을 선언적으로 표현합니다.
    """

    # 구 scenario 단일 문자열에서 분리된 필드들; generate_scenario 노드가 채운다
    relationship_type: str       # 예: "친구", "선배-후배", "낯선 사람"
    dialogue_function: str       # 예: "장소 묻기"
    ai_opening: str
    user_input: str
    latest_ai_response: str
    is_finished: bool
