import json

from nodes.conversation.generate_scenario import generate_scenario

# Use a plain dict as state (ConversationState is a TypedDict)
state = {
    "user_profile": {"korean_level": "초급"},
    "location": "카페",
}

result = generate_scenario(state)
output = {
    "scenario": result.get("scenario"),
    "conflict": result.get("conflict"),
    "personas": result.get("personas"),
}
print(json.dumps(output, ensure_ascii=False, indent=2))
