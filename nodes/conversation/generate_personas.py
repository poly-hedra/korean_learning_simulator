"""Conversation node: generate personas for A/B participants."""

from states.conversation_state import ConversationState


def generate_personas(state: ConversationState) -> ConversationState:
    """Create two personas with consistent schema.

    요구사항 3번: 이름/직업/나이/성별/대화 목적.
    실제 few-shot은 LLM 프롬프트로 확장 가능하도록 구조를 고정합니다.
    """

    # generate_scenario에서 이미 A/B를 만든 경우 그대로 유지한다.
    if state.get("personas"):
        return state

    location = state.get("location", "공원")

    state["personas"] = {
        "A": {
            "name": "지민",
            "job": "회사원",
            "age": 28,
            "gender": "여성",
            "goal": f"{location}에서 필요한 정보를 정확히 얻기",
        },
        "B": {
            "name": "민수",
            "job": "대학생",
            "age": 24,
            "gender": "남성",
            "goal": f"{location}에서 상대를 도와 문제를 해결하기",
        },
    }
    return state
