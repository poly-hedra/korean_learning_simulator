"""평가 노드: 맥락 일관성 (50%)."""

from ..state import EvaluationState


def evaluate_context(state: EvaluationState) -> EvaluationState:
    """시나리오/장소 정합성을 기준으로 맥락 점수를 휴리스틱으로 계산한다.

    실제 운영에서는 LLM judge 혹은 별도 context classifier로 교체 가능합니다.
    """

    scenario = state.get(
        "scenario_title", ""
    )  # 구 "scenario" 키 → "scenario_title"로 변경
    location = state.get("location", "")

    user_utterances = [
        turn["utterance"]
        for turn in state.get("conversation_log", [])
        if turn.get("speaker") == "user"
    ]
    if not user_utterances:
        return {
            "context_score": 0.0,
            "context_hit_location": 0.0,
            "context_hit_scenario": 0.0,
            "context_length_bonus": 0.0,
        }

    joined = " ".join(user_utterances)
    hit_location = 1.0 if location and location in joined else 0.6
    hit_scenario = 1.0 if any(word in joined for word in scenario.split()[:3]) else 0.7
    length_bonus = min(1.0, len(user_utterances) / 4)

    # 0~10 스케일
    score = 10.0 * ((hit_location * 0.4) + (hit_scenario * 0.3) + (length_bonus * 0.3))
    return {
        "context_score": round(score, 2),
        "context_hit_location": round(hit_location, 2),
        "context_hit_scenario": round(hit_scenario, 2),
        "context_length_bonus": round(length_bonus, 2),
    }
