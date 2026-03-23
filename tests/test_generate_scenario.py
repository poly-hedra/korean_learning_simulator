import json
from importlib import import_module

generate_scenario = import_module(
    "01_conversation.nodes.generate_scenario"
).generate_scenario

# 상태는 일반 dict로 사용한다 (ConversationState는 TypedDict)
state = {
    "user_profile": {"korean_level": "Beginner"},
    "location": "카페",
}

result = generate_scenario(state)
# 구 scenario/conflict → scenario_title/relationship_type/dialogue_function 으로 구조 변경
output = {
    "scenario_title": result.get("scenario_title"),
    "relationship_type": result.get("relationship_type"),
    "dialogue_function": result.get("dialogue_function"),
    "personas": result.get("personas"),
}
print(json.dumps(output, ensure_ascii=False, indent=2))
