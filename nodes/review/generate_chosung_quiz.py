"""Review node: generate chosung quiz from prior dialogue lines."""

from __future__ import annotations

import json
import random
import re

from services.llm_service import LLMService
from states.review_state import ReviewState

_CHOSUNG = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]
_WORD_PATTERN = re.compile(r"[가-힣]{2,}")
_STOPWORDS = {
    "저는",
    "제가",
    "우리",
    "그리고",
    "하지만",
    "정말",
    "조금",
    "지금",
    "오늘",
    "그럼",
    "이제",
    "있어요",
    "있습니다",
    "해주세요",
    "괜찮아요",
}
_TRIM_SUFFIXES = [
    "겠어요",
    "을게요",
    "ㄹ게요",
    "게요",
    "까요",
    "할까요",
    "했어요",
    "해요",
    "하세요",
    "입니다",
    "있어요",
    "에서는",
    "에서",
    "으로",
    "에게",
    "한테",
    "처럼",
    "까지",
    "부터",
    "보다",
    "으로",
    "라고",
    "이고",
    "이면",
    "인데",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "도",
    "만",
]
_BAD_TARGET_SUFFIXES = [
    "게요",
    "까요",
    "했어요",
    "할까요",
    "해요",
    "아요",
    "어요",
    "네요",
    "세요",
]
_MAX_QUIZZES = 5
_CHOICE_MODEL_NAME = "solar-pro2"

_chosung_choice_llm = LLMService(model_name=_CHOICE_MODEL_NAME)


def _to_chosung(word: str) -> str:
    result: list[str] = []
    for ch in word:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = (code - 0xAC00) // 588
            result.append(_CHOSUNG[idx])
    return "".join(result)


def _extract_candidate_words(sessions: list[dict]) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for session in sessions:
        for turn in session.get("conversation_log", []):
            utterance = turn.get("utterance", "")
            for match in _WORD_PATTERN.finditer(utterance):
                word = _normalize_word(match.group(0))
                if len(word) < 2 or word in _STOPWORDS or word in seen:
                    continue
                seen.add(word)
                words.append(word)
    return words


def _chosung_signature(word: str) -> str:
    return _to_chosung(word)


def _parse_llm_choices(raw: str, answer: str) -> list[str]:
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []

    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    distractors: list[str] = []
    target_signature = _chosung_signature(answer)
    for item in parsed:
        word = str(item).strip()
        if (
            len(word) < 2
            or len(word) != len(answer)
            or word == answer
            or not _WORD_PATTERN.fullmatch(word)
            or _chosung_signature(word) != target_signature
            or word in distractors
        ):
            continue
        distractors.append(word)
    return distractors[:3]


def _generate_llm_distractors(
    answer: str, candidates: list[str], excluded_words: set[str]
) -> list[str]:
    signature = _chosung_signature(answer)
    candidate_hint = [
        word
        for word in candidates
        if word != answer
        and len(word) == len(answer)
        and _chosung_signature(word) == signature
        and word not in excluded_words
    ][:10]

    system_prompt = (
        "너는 한국어 초성 퀴즈 보기 생성기다. "
        "정답과 같은 초성을 가진 실제 한국어 단어 보기 3개를 만든다. "
        "반드시 JSON 배열만 출력한다."
    )
    user_prompt = (
        f"정답: {answer}\n"
        f"정답 초성: {signature}\n"
        f"정답 글자 수: {len(answer)}\n"
        "규칙:\n"
        "- 정답과 같은 초성 패턴을 가진 실제 존재하는 한국어 단어 3개를 생성\n"
        "- 정답과 같은 글자 수를 유지\n"
        "- 정답과 동일한 단어는 금지\n"
        "- 보기들은 서로 달라야 함\n"
        "- 없는 말, 조합한 말, 어색한 비표준어는 금지\n"
        '- 설명 없이 JSON 배열만 출력. 예: ["너무", "노모", "넝마"]\n'
        f"제외 단어: {', '.join(sorted(excluded_words)) if excluded_words else '없음'}\n"
        f"참고 후보: {', '.join(candidate_hint) if candidate_hint else '없음'}"
    )
    raw = _chosung_choice_llm.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    return _parse_llm_choices(raw, answer)


def _build_choices(answer: str, candidates: list[str]) -> list[str]:
    distractors: list[str] = []
    excluded_words = {answer}

    for _ in range(2):
        generated = _generate_llm_distractors(answer, candidates, excluded_words)
        for word in generated:
            if word not in excluded_words:
                distractors.append(word)
                excluded_words.add(word)
            if len(distractors) >= 3:
                break
        if len(distractors) >= 3:
            break

    if len(distractors) < 3:
        same_signature_candidates = [
            word
            for word in candidates
            if word != answer
            and len(word) == len(answer)
            and _chosung_signature(word) == _chosung_signature(answer)
            and word not in distractors
        ]
        distractors.extend(same_signature_candidates[: 3 - len(distractors)])

    if len(distractors) < 3:
        return []

    ordered_choices = [answer]
    if distractors:
        ordered_choices.insert(0, distractors[0])
    if len(distractors) >= 2:
        ordered_choices.append(distractors[1])
    if len(distractors) >= 3:
        ordered_choices.append(distractors[2])

    final_choices = ordered_choices[:4]
    random.shuffle(final_choices)
    return final_choices


def _replace_target_with_chosung(utterance: str, raw_target: str, answer: str) -> str:
    if answer and answer in utterance:
        return utterance.replace(answer, _to_chosung(answer), 1)
    return utterance.replace(raw_target, _to_chosung(raw_target), 1)


def _normalize_word(word: str) -> str:
    normalized = word
    for suffix in _TRIM_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 2:
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def _pick_target(utterance: str) -> str | None:
    matches = [match.group(0) for match in _WORD_PATTERN.finditer(utterance)]
    filtered = []
    for word in matches:
        normalized = _normalize_word(word)
        if len(normalized) < 2 or normalized in _STOPWORDS:
            continue
        filtered.append(word)
    if not filtered:
        return None

    preferred = [
        word
        for word in filtered
        if not any(word.endswith(suffix) for suffix in _BAD_TARGET_SUFFIXES)
    ]
    pool = preferred or filtered
    pool.sort(key=lambda word: len(_normalize_word(word)), reverse=True)
    return pool[0]


def generate_chosung_quiz(state: ReviewState) -> ReviewState:
    quizzes: list[dict] = []
    sessions = state.get("selected_weak_sessions", [])
    candidate_words = _extract_candidate_words(sessions)

    for session in sessions:
        for turn in session.get("conversation_log", []):
            utterance = turn.get("utterance", "")
            target = _pick_target(utterance)
            if not target:
                continue

            answer = _normalize_word(target)
            if len(answer) < 2:
                continue

            choices = _build_choices(answer, candidate_words)
            if len(choices) < 4:
                continue

            masked = _replace_target_with_chosung(utterance, target, answer)
            speaker = turn.get("speaker", "unknown")
            quizzes.append(
                {
                    "question": (
                        "다음은 앞에서 나온 대화 문장입니다. "
                        "초성으로 바뀐 부분에 들어갈 원래 단어는 무엇인가요?\n"
                        f"[{speaker}] {masked}"
                    ),
                    "answer": answer,
                    "choices": choices,
                    "original_sentence": utterance,
                }
            )
            if len(quizzes) >= _MAX_QUIZZES:
                break
        if len(quizzes) >= _MAX_QUIZZES:
            break

    state["chosung_quiz"] = quizzes
    return state
