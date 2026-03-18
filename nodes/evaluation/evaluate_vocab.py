"""Evaluation node: vocabulary diversity (30%)."""

from services.rag_service import rag_service
from states.evaluation_state import EvaluationState


def evaluate_vocab(state: EvaluationState) -> EvaluationState:
    """Score vocabulary diversity from user utterances only."""

    user_utterances = [
        turn["utterance"]
        for turn in state.get("conversation_log", [])
        if turn.get("speaker") == "user"
    ]
    state["vocab_score"] = rag_service.vocab_diversity_score(user_utterances)
    return state
