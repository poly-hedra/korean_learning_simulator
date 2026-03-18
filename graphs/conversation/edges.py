"""Edge conditions for conversation graph."""

from states.conversation_state import ConversationState
from app.config import settings


def should_continue_conversation(state: ConversationState) -> str:
    """Return next edge label based on turn limit.

    요구사항 5번: 난이도별 턴 제한을 초과하면 종료.
    """

    turn_count = state.get("turn_count", 0)

    # 우선 세션 상태에 설정된 turn_limit을 사용합니다 (LearningOrchestrator에서 설정됨).
    turn_limit = state.get("turn_limit")
    if turn_limit is None:
        # 상태에 없다면 사용자 프로필의 난이도별 설정을 참고합니다.
        level = state.get("user_profile", {}).get("korean_level")
        turn_limit = settings.turn_limit_by_level.get(level, 7)

    if turn_count >= turn_limit:
        return "end"
    return "continue"
