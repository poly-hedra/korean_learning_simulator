"""평가 그래프용 상태 스키마."""

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
    tokenized_original_words: list[str]
    tokenized_normalized_words: list[str]
    SCK_correspondence: list[dict[str, str | int]]
    SCK_match_count: int
    SCK_total_tokens: int
    SCK_match_rate: float
    SCK_level_counts: dict[str, int]
    SCK_unresolved_homonyms: dict[str, int]
