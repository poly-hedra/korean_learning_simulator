"""평가 노드: 어휘 다양성 (30%)."""

from services.rag_service import rag_service
from ..state import EvaluationState


def evaluate_vocab(state: EvaluationState) -> EvaluationState:
    """사용자 발화만 기준으로 어휘 다양성 점수를 계산한다."""

    user_utterances = [
        turn["utterance"]
        for turn in state.get("conversation_log", [])
        if turn.get("speaker") == "user"
    ]
    return {"vocab_score": rag_service.vocab_diversity_score(user_utterances)}
