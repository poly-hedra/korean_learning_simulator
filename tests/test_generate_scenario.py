import json
from importlib import import_module

generate_scenario = import_module(
    "01_conversation.nodes.generate_scenario"
).generate_scenario

# Use a plain dict as state (ConversationState is a TypedDict)
state = {
    "user_profile": {"korean_level": "Beginner"},
    "location": "카페",
}

result = generate_scenario(state)
output = {
    "scenario": result.get("scenario"),
    "conflict": result.get("conflict"),
    "personas": result.get("personas"),
}
print(json.dumps(output, ensure_ascii=False, indent=2))
