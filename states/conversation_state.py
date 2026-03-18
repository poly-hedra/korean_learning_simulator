"""State schema for conversation graph."""

from typing import TypedDict

from states.base_state import BaseState


class ConversationState(BaseState, total=False):
    """Conversation workflow state.

    graph 내부에서 단계별로 누적되는 값을 선언적으로 표현합니다.
    """

    ai_opening: str
    user_input: str
    latest_ai_response: str
    is_finished: bool
