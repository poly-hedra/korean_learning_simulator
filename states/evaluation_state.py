"""State schema for evaluation graph."""

from typing import TypedDict

from states.base_state import BaseState


class EvaluationState(BaseState, total=False):
    """Evaluation state with per-metric scores and feedback."""

    vocab_score: float
    context_score: float
    spelling_score: float
    total_score_10: float
    tier: str
    feedback: str
    highlighted_log: list[dict[str, str]]
