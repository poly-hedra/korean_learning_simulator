"""평가 노드: LLM 기반 맞춤법 검사 (20%) 및 오류 강조."""

from __future__ import annotations

import json
from typing import Any

from services.llm_service import llm_service
from ..state import EvaluationState


_SPELLING_SYSTEM_PROMPT = (
    "너는 한국어 맞춤법 평가기다. "
    "사용자 문장에서 맞춤법 오류를 찾고 최소 수정안을 제시한다. "
    "띄어쓰기 오류는 감점 대상에서 제외한다. "
    "반드시 JSON 객체만 출력한다."
)


def _mark_basic_typos(text: str) -> tuple[str, int]:
    """LLM 실패 시 사용할 최소 규칙 기반 폴백."""

    typo_map = {
        "됫": "됐",
        "되요": "돼요",
        "안녕하새요": "안녕하세요",
    }

    typo_count = 0
    highlighted = text

    for wrong, right in typo_map.items():
        if wrong in highlighted:
            highlighted = highlighted.replace(wrong, f"[오류:{wrong}->{right}]")
            typo_count += 1

    return highlighted, typo_count


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed


def _build_spelling_prompt(text: str) -> str:
    return (
        "아래 한국어 문장을 맞춤법 관점에서 검사하라.\\n"
        "출력은 반드시 JSON 객체 한 개만 출력한다.\\n"
        "키 스키마:\\n"
        "{\\n"
        '  "error_count": 정수,\\n'
        '  "items": [\\n'
        '    {"original": "오류표현", "corrected": "수정표현"}\\n'
        "  ]\\n"
        "}\\n"
        "규칙:\\n"
        "- 띄어쓰기 오류는 제외한다\\n"
        "- 같은 오류 반복은 필요한 만큼 포함 가능\\n"
        "- 오류가 없으면 error_count=0, items=[]\\n"
        "- 설명문 없이 JSON만 출력\\n\\n"
        f"문장: {text}"
    )


def _apply_llm_highlight(text: str, items: list[dict[str, str]]) -> tuple[str, int]:
    highlighted = text
    typo_count = 0

    for item in items:
        wrong = str(item.get("original", "")).strip()
        right = str(item.get("corrected", "")).strip()
        if not wrong or not right:
            continue
        if wrong not in highlighted:
            continue
        highlighted = highlighted.replace(wrong, f"[오류:{wrong}->{right}]", 1)
        typo_count += 1

    return highlighted, typo_count


def _evaluate_user_utterance_with_llm(text: str) -> tuple[str, int]:
    raw = llm_service.generate_text(
        system_prompt=_SPELLING_SYSTEM_PROMPT,
        user_prompt=_build_spelling_prompt(text),
    )
    parsed = _extract_json_object(raw)
    if not parsed:
        return _mark_basic_typos(text)

    items = parsed.get("items", [])
    if not isinstance(items, list):
        return _mark_basic_typos(text)

    normalized_items: list[dict[str, str]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        normalized_items.append(
            {
                "original": str(row.get("original", "")).strip(),
                "corrected": str(row.get("corrected", "")).strip(),
            }
        )

    highlighted, marked_count = _apply_llm_highlight(text, normalized_items)
    if marked_count == 0:
        return text, 0

    return highlighted, marked_count


def evaluate_spelling(state: EvaluationState) -> EvaluationState:
    highlighted_log: list[dict[str, str]] = []
    typo_total = 0
    user_turns = 0

    for turn in state.get("conversation_log", []):
        speaker = turn.get("speaker", "")
        utterance = turn.get("utterance", "")

        if speaker == "user":
            user_turns += 1
            highlighted, typos = _evaluate_user_utterance_with_llm(utterance)
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
