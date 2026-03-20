"""평가 그래프용 상태 스키마."""

from typing import TypedDict

from states.base_state import BaseState


class EvaluationState(BaseState, total=False):
    """지표별 점수와 피드백을 담는 평가 상태."""

    vocab_score: float
    context_score: float
    spelling_score: float
    total_score_10: float
    tier: str
    feedback: str
    highlighted_log: list[dict[str, str]]
