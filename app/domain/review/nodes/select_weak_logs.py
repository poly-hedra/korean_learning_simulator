"""복습 노드: 사용자 기준 최저 점수 세션 1~3개를 선택한다."""

from app.infra.persistence.repository import repository
from ..state import ReviewState


def select_weak_logs(state: ReviewState) -> ReviewState:
    user_id = state.get("user_profile", {}).get("user_id", "")
    weak = repository.get_weekly_weak_sessions(user_id=user_id, top_k=3)
    return {
        "selected_weak_sessions": [
            {
                "week": s.week,
                "total_score_10": s.total_score_10,
                "conversation_log": s.conversation_log,
                "location": s.location,
            }
            for s in weak
        ]
    }
