"""평가 노드: 맞춤법 검사 (20%) 및 오류 강조."""

from ..state import EvaluationState


def _mark_basic_typos(text: str) -> tuple[str, int]:
    """간단한 오탈자 표시기.

    - 반복된 공백
    - 자주 등장하는 잘못된 표기 예시(데모용)
    """

    typo_map = {
        "됫": "됐",
        "되요": "돼요",
        "안녕하새요": "안녕하세요",
    }

    typo_count = 0
    highlighted = text

    while "  " in highlighted:
        highlighted = highlighted.replace("  ", " ")
        typo_count += 1

    for wrong, right in typo_map.items():
        if wrong in highlighted:
            highlighted = highlighted.replace(wrong, f"[오류:{wrong}->{right}]")
            typo_count += 1

    return highlighted, typo_count


def evaluate_spelling(state: EvaluationState) -> EvaluationState:
    highlighted_log: list[dict[str, str]] = []
    typo_total = 0
    user_turns = 0

    for turn in state.get("conversation_log", []):
        speaker = turn.get("speaker", "")
        utterance = turn.get("utterance", "")

        if speaker == "user":
            user_turns += 1
            highlighted, typos = _mark_basic_typos(utterance)
            typo_total += typos
            highlighted_log.append({"speaker": speaker, "utterance": highlighted})
        else:
            highlighted_log.append({"speaker": speaker, "utterance": utterance})

    # 사용자 발화당 허용 오타 1개 기준의 간단한 감점 모델
    allowed = max(1, user_turns)
    penalty_ratio = min(1.0, typo_total / allowed)
    score = 10.0 * (1.0 - penalty_ratio * 0.7)

    return {
        "spelling_score": round(max(0.0, score), 2),
        "highlighted_log": highlighted_log,
    }
