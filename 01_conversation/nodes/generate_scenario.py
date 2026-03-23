"""대화 노드: 레벨과 장소로 시나리오를 생성한다."""

import json

from ..prompts.scenario import build_system_prompt, build_user_message
from services.llm_service import llm_service
from ..state import ConversationState


def _fallback_bundle(level: str, location: str) -> dict:
    """LLM 응답 파싱 실패 시 사용하는 기본 시나리오 번들.

    level에 따라 A의 mission 난이도를 달리한다.
    """
    mission_by_level = {
        "Beginner": f"{location}이 어디에 있는지 알고 싶어요.",
        "Intermediate": f"{location}에서 필요한 정보를 얻고 싶어요.",
        "Advanced": f"{location}에서 상대방과 자연스럽게 대화하고 싶어요.",
    }
    mission_a = mission_by_level.get(level, f"{location}에서 필요한 정보를 얻고 싶어요.")
    return {
        "scenario_title": f"{location}에서의 대화",
        "dialogue_function": ["일상 묻기"],
        "relationship_type": "낯선 사람",
        "personas": {
            "A": {
                "name": "리사",
                "age": "21",
                "gender": "여",
                "role": "대학생",
                "mission": mission_a,
            },
            "B": {
                "name": "민수",
                "age": "24",
                "gender": "남",
                "role": "대학생",
                "mission": "상대방을 도와주고 싶어요.",
            },
        },
    }


def generate_scenario(state: ConversationState) -> ConversationState:
    """사용자 레벨과 선택한 장소로 시나리오 텍스트를 생성한다.

    요구사항 2/3번을 함께 반영:
    - 한국어 수준 + 장소 기반 시나리오
    - 대화 참여자 A/B 페르소나 동시 생성
    """

    # user_profile을 먼저 언팩해서 이후 코드에서 가독성을 높인다.
    profile = state.get("user_profile", {})
    level = profile.get("korean_level", "Beginner")
    location = state.get("location", "한강")

    raw = llm_service.generate_text(
        system_prompt=build_system_prompt(korean_level=level),
        user_prompt=build_user_message(location=location, korean_level=level),
    )

    # 파싱 실패에 대비해 폴백 번들을 먼저 준비하고, 성공 시 덮어쓴다.
    bundle = _fallback_bundle(level=level, location=location)
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                bundle["scenario_title"] = parsed.get("scenario_title", bundle["scenario_title"])
                bundle["dialogue_function"] = parsed.get("dialogue_function", bundle["dialogue_function"])
                bundle["relationship_type"] = parsed.get("relationship_type", bundle["relationship_type"])
                personas = parsed.get("personas")
                if isinstance(personas, dict) and "A" in personas and "B" in personas:
                    bundle["personas"] = personas
    except json.JSONDecodeError:
        pass

    state["scenario_title"] = bundle["scenario_title"]
    state["dialogue_function"] = bundle["dialogue_function"]
    state["relationship_type"] = bundle["relationship_type"]
    state["personas"] = bundle["personas"]
    return state
