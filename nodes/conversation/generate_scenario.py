"""Conversation node: generate scenario from level and location."""

import json

from prompts.conversation.prompt_templates import (
    SCENARIO_SYSTEM_PROMPT,
    SCENARIO_USER_PROMPT_TEMPLATE,
)
from services.llm_service import llm_service
from states.conversation_state import ConversationState


def _fallback_bundle(level: str, location: str) -> dict:
    style_by_level = {
        "초급": "짧고 쉬운 문장, 일상 단어 중심",
        "중급": "중간 길이 문장, 연결어미와 상황 설명 포함",
        "고급": "긴 문장, 추상 표현과 미묘한 뉘앙스 포함",
    }
    style = style_by_level.get(level, style_by_level["초급"])
    return {
        "scenario": (
            f"장소는 {location}이며, 두 사람이 특정한 목적을 두고 대화합니다. "
            f"대화 난이도는 {level}이고 말투는 '{style}'를 유지합니다."
        ),
        "conflict": "작은 오해나 갈등이 발생하나 대화를 통해 풀어나갈 수 있는 상황",
        "personas": {
            "A": {
                "name": "지민",
                "job": "회사원",
                "age": 28,
                "gender": "여성",
                "goal": f"{location}에서 필요한 정보를 정확히 얻기",
                "stance": "정보를 빨리 얻고자 즉각적으로 행동하려는 성향",
            },
            "B": {
                "name": "민수",
                "job": "대학생",
                "age": 24,
                "gender": "남성",
                "goal": f"{location}에서 상대를 도와 문제를 해결하기",
                "stance": "신중하게 상황을 관찰하고 상대를 배려하려는 성향",
            },
        },
    }


def generate_scenario(state: ConversationState) -> ConversationState:
    """Build scenario text from user level and selected location.

    요구사항 2/3번을 함께 반영:
    - 한국어 수준 + 장소 기반 시나리오
    - 대화 참여자 A/B 페르소나 동시 생성
    """

    level = state.get("user_profile", {}).get("korean_level", "초급")
    location = state.get("location", "공원")

    raw = llm_service.generate_text(
        system_prompt=SCENARIO_SYSTEM_PROMPT,
        user_prompt=SCENARIO_USER_PROMPT_TEMPLATE.format(
            level=level, location=location
        ),
    )

    bundle = _fallback_bundle(level=level, location=location)
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                bundle["scenario"] = parsed.get("scenario", bundle["scenario"])
                bundle["conflict"] = parsed.get("conflict", bundle.get("conflict"))
                personas = parsed.get("personas")
                if isinstance(personas, dict) and "A" in personas and "B" in personas:
                    bundle["personas"] = personas
    except json.JSONDecodeError:
        pass

    state["scenario"] = bundle["scenario"]
    state["conflict"] = bundle.get("conflict", "")
    state["personas"] = bundle["personas"]
    return state
