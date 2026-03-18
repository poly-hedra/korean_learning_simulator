"""Evaluation node: context coherence (50%)."""

from states.evaluation_state import EvaluationState


def evaluate_context(state: EvaluationState) -> EvaluationState:
    """Heuristic context score based on scenario/location anchoring.

    실제 운영에서는 LLM judge 혹은 별도 context classifier로 교체 가능합니다.
    """

    scenario = state.get("scenario", "")
    location = state.get("location", "")

    user_utterances = [
        turn["utterance"]
        for turn in state.get("conversation_log", [])
        if turn.get("speaker") == "user"
    ]
    if not user_utterances:
        state["context_score"] = 0.0
        return state

    joined = " ".join(user_utterances)
    hit_location = 1.0 if location and location in joined else 0.6
    hit_scenario = 1.0 if any(word in joined for word in scenario.split()[:3]) else 0.7
    length_bonus = min(1.0, len(user_utterances) / 4)

    # 0~10 스케일
    score = 10.0 * ((hit_location * 0.4) + (hit_scenario * 0.3) + (length_bonus * 0.3))
    state["context_score"] = round(score, 2)
    return state
