"""대화 그래프용 상태 스키마."""

from states.base_state import BaseState


class ConversationState(BaseState, total=False):
    """대화 워크플로 상태.

    graph 내부에서 단계별로 누적되는 값을 선언적으로 표현합니다.
    """

    # generate_location_context 노드가 채운다.
    # 장소별 활동·명소·트렌드를 LLM이 자유 생성 → generate_scenario 프롬프트에 컨텍스트로 주입.
    # 하드코딩 없이 어떤 장소든 풍부한 시나리오를 만들기 위해 도입.
    location_context: str

    # 구 scenario 단일 문자열에서 분리된 필드들; generate_scenario 노드가 채운다
    relationship_type: str  # 예: "친구", "선배-후배", "낯선 사람"
    dialogue_function: list[str]  # 예: ["장소 묻기"], ["취향 묻기", "기분 묻기"]
    ai_opening: str
    user_input: str
    latest_ai_response: str
    is_finished: bool
