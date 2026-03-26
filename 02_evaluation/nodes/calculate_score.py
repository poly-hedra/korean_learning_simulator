"""평가 노드: 가중 점수를 집계하고 피드백을 생성한다."""

import re

from services.scoring_service import scoring_service
from ..state import EvaluationState


_SPELLING_MARK_PATTERN = re.compile(r"\[오류:([^\]-]+)->([^\]]+)\]")


def _format_spelling_examples(highlighted_log: list[dict[str, str]]) -> str:
    """강조 로그에서 오류->교정 패턴을 모아 요약 문자열을 만든다."""

    counts: dict[tuple[str, str], int] = {}
    for turn in highlighted_log:
        utterance = turn.get("utterance", "")
        for wrong, corrected in _SPELLING_MARK_PATTERN.findall(utterance):
            key = (wrong.strip(), corrected.strip())
            if not key[0] or not key[1]:
                continue
            counts[key] = counts.get(key, 0) + 1

    if not counts:
        return "  - 없음"

    parts = [
        f"  - {wrong} -> {corrected} ({count}회)"
        for (wrong, corrected), count in sorted(
            counts.items(), key=lambda x: (-x[1], x[0][0])
        )
    ]
    return "\n".join(parts)


def calculate_score(state: EvaluationState) -> EvaluationState:
    vocab = state.get("vocab_score", 0.0)
    context = state.get("context_score", 0.0)
    spelling = state.get("spelling_score", 0.0)
    match_rate = float(state.get("SCK_match_rate", 0.0))
    match_count = int(state.get("SCK_match_count", 0))
    total_tokens = int(state.get("SCK_total_tokens", 0))

    context_hit_location = float(state.get("context_hit_location", 0.0))
    context_hit_scenario = float(state.get("context_hit_scenario", 0.0))
    context_length_bonus = float(state.get("context_length_bonus", 0.0))

    spelling_typo_total = int(state.get("spelling_typo_total", 0))
    spelling_user_turns = int(state.get("spelling_user_turns", 0))
    spelling_penalty_ratio = float(state.get("spelling_penalty_ratio", 0.0))
    highlighted_log = state.get("highlighted_log", [])
    spelling_examples = _format_spelling_examples(highlighted_log)

    total = scoring_service.total_score_10(
        vocab=vocab, context=context, spelling=spelling
    )
    level = state.get("user_profile", {}).get("korean_level", "Beginner")
    tier = scoring_service.tier_for_level(level, total)

    state["total_score_10"] = total
    state["tier"] = tier

    weighted_vocab = round(vocab * 0.30, 2)
    weighted_context = round(context * 0.50, 2)
    weighted_spelling = round(spelling * 0.20, 2)

    if match_rate >= 60:
        vocab_reason = "대화에서 어휘 사용 폭이 넓고, SCK 기준 일치율이 높습니다."
    elif match_rate >= 35:
        vocab_reason = "기본 어휘는 사용했지만, 다양한 어휘 확장 여지가 있습니다."
    else:
        vocab_reason = "반복 어휘 비중이 높아 어휘 다양성 점수가 낮게 계산되었습니다."

    if context_hit_location >= 1.0 and context_hit_scenario >= 1.0:
        context_reason = "장소/시나리오 핵심어가 잘 반영되어 맥락 일치도가 높습니다."
    elif context_hit_location < 1.0 and context_hit_scenario < 1.0:
        context_reason = (
            "장소/시나리오 키워드 반영이 부족해 맥락 점수가 감점되었습니다."
        )
    elif context_hit_location < 1.0:
        context_reason = "장소 관련 언급이 부족해 맥락 점수의 일부가 감점되었습니다."
    else:
        context_reason = (
            "시나리오 핵심어 반영이 약해 맥락 점수의 일부가 감점되었습니다."
        )

    if context_length_bonus >= 1.0:
        context_length_reason = (
            "사용자 발화 수가 충분해 길이 보너스를 최대치로 받았습니다."
        )
    else:
        context_length_reason = (
            "사용자 발화 수가 적어 길이 보너스가 일부만 반영되었습니다."
        )

    if spelling_typo_total == 0:
        spelling_reason = "맞춤법 오류가 감지되지 않아 감점이 없었습니다."
    elif spelling_penalty_ratio < 0.5:
        spelling_reason = "맞춤법 오류가 일부 있어 소폭 감점되었습니다."
    else:
        spelling_reason = "맞춤법 오류 비율이 높아 감점 폭이 커졌습니다."

    # 요구사항 8-b: 요약 피드백 + 총점 반환
    state["feedback"] = (
        "[점수 산출 근거]\n"
        f"- 가중치 합산: 어휘({vocab} x 0.30 = {weighted_vocab}) + "
        f"맥락({context} x 0.50 = {weighted_context}) + "
        f"맞춤법({spelling} x 0.20 = {weighted_spelling})\n"
        f"- 어휘: SCK 일치율 {match_rate}% ({match_count}/{total_tokens}) 기준. {vocab_reason}\n"
        f"- 맥락: 장소반영 {context_hit_location}, 시나리오반영 {context_hit_scenario}, "
        f"길이보너스 {context_length_bonus}. {context_reason} {context_length_reason}\n"
        f"- 맞춤법: 오류 {spelling_typo_total}개 / 사용자 발화 {spelling_user_turns}회, "
        f"감점비율 {spelling_penalty_ratio}. {spelling_reason}\n"
        f"  오류 상세:\n{spelling_examples}"
    )
    return state
