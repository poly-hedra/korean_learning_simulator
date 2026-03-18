"""Review node: select 1~3 lowest-score sessions for a user."""

from database.repository import repository
from states.review_state import ReviewState


def select_week_logs(state: ReviewState) -> ReviewState:
    user_id = state.get("user_profile", {}).get("user_id", "")
    weak = repository.get_weekly_weak_sessions(user_id=user_id, top_k=3)
    state["selected_weak_sessions"] = [
        {
            "week": s.week,
            "total_score_10": s.total_score_10,
            "conversation_log": s.conversation_log,
            "location": s.location,
        }
        for s in weak
    ]
    return state
