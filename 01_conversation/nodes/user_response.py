"""대화 노드: 사용자 발화를 로그에 추가한다."""

from ..state import ConversationState


def user_response(state: ConversationState) -> ConversationState:
    """현재 사용자 입력을 하나의 사용자 턴으로 기록한다."""

    text = state.get("user_input", "").strip()
    if text:
        # 이력 라벨을 더 명확히 하기 위해 사용자 턴에 선택 역할과 페르소나 이름을 함께 기록
        selected_role = state.get("user_profile", {}).get("selected_role", "A")
        personas = state.get("personas", {})
        name = personas.get(selected_role, {}).get("name", "사용자")
        state.setdefault("conversation_log", []).append(
            {
                "speaker": "user",
                "role": selected_role,
                "name": name,
                "utterance": text,
            }
        )
        state["turn_count"] = state.get("turn_count", 0) + 1
    return state
