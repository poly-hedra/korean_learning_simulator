"""Conversation node: append user utterance into log."""

from states.conversation_state import ConversationState


def user_response(state: ConversationState) -> ConversationState:
    """Record the current user input as one user turn."""

    text = state.get("user_input", "").strip()
    if text:
        # Attach the selected role and persona name to the user turn for clearer history labels
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
