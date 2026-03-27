from __future__ import annotations

import json
from importlib import import_module


generate_scenario_module = import_module("01_conversation.nodes.generate_scenario")


def test_generate_scenario_uses_parsed_llm_payload(monkeypatch):
    payload = {
        "scenario_title": "한강에서 자전거를 타는 대화",
        "scenario_description": "한강에서 만난 두 사람의 대화입니다.",
        "dialogue_function": ["[각자 목표] 취향 묻기", "경험 묻기"],
        "relationship_type": "친구",
        "personas": {
            "A": {
                "name": "민지",
                "age": "22",
                "gender": "여",
                "role": "친구",
                "mission": "자전거를 자주 타는지 묻고 싶어요.",
            },
            "B": {
                "name": "Alex",
                "age": "23",
                "gender": "남",
                "role": "친구",
                "mission": "좋아하는 코스를 알려주고 싶어요.",
            },
        },
    }

    monkeypatch.setattr(
        generate_scenario_module.llm_service,
        "generate_text",
        lambda **_: json.dumps(payload, ensure_ascii=False),
    )

    state = {
        "user_profile": {"korean_level": "Beginner"},
        "location": "한강",
    }

    result = generate_scenario_module.generate_scenario(state)

    assert result["scenario_title"] == payload["scenario_title"]
    assert result["scenario_description"] == payload["scenario_description"]
    assert result["dialogue_function"] == ["취향 묻기", "경험 묻기"]
    assert result["relationship_type"] == "친구"
    assert result["personas"]["A"]["name"] == "민지"


def test_generate_scenario_falls_back_when_llm_response_is_not_json(monkeypatch):
    monkeypatch.setattr(
        generate_scenario_module.llm_service,
        "generate_text",
        lambda **_: "not a json response",
    )

    state = {
        "user_profile": {"korean_level": "Advanced"},
        "location": "명동",
    }

    result = generate_scenario_module.generate_scenario(state)

    assert result["scenario_title"] == "명동에서의 대화"
    assert result["scenario_description"] == "명동에서 만난 두 사람의 대화입니다."
    assert result["personas"]["A"]["mission"] == "명동에서 상대방과 자연스럽게 대화하고 싶어요."
