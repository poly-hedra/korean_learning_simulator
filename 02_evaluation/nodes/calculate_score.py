"""평가 노드: 가중 점수를 집계하고 피드백을 생성한다."""

from services.scoring_service import scoring_service
from ..state import EvaluationState


def calculate_score(state: EvaluationState) -> EvaluationState:
    vocab = state.get("vocab_score", 0.0)
    context = state.get("context_score", 0.0)
    spelling = state.get("spelling_score", 0.0)

    total = scoring_service.total_score_10(
        vocab=vocab, context=context, spelling=spelling
    )
    level = state.get("user_profile", {}).get("korean_level", "Beginner")
    tier = scoring_service.tier_for_level(level, total)

    state["total_score_10"] = total
    state["tier"] = tier

    # 요구사항 8-b: 요약 피드백 + 총점 반환
    state["feedback"] = (
        f"총점 {total}/10, 티어 {tier}. "
        f"어휘다양성 {vocab}, 맥락 {context}, 맞춤법 {spelling}. "
        "틀린 단어를 복습 카드로 저장해 다음 주차 복습에 활용하세요."
    )
    return state
