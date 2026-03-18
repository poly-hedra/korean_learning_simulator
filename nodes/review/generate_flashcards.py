"""Review node: generate flashcards from conversation vocabulary."""

from __future__ import annotations

import json

from database.repository import repository
from services.llm_service import llm_service
from services.tokenizer_service import tokenizer_service
from states.review_state import ReviewState

_STOPWORDS = {
    "그래서",
    "그냥",
    "정말",
    "지금",
    "오늘",
    "저는",
    "제가",
    "우리",
    "너무",
    "조금",
    "같이",
    "이거",
    "그거",
    "저거",
    "그리고",
    "하지만",
    "입니다",
    "있어요",
    "있습니다",
    "해주세요",
    "괜찮아요",
    "저",
    "나",
    "그",
    "것",
}
_MAX_FLASHCARDS = 5


def _build_conversation_text(selected_sessions: list[dict]) -> str:
    lines: list[str] = []
    for session in selected_sessions:
        lines.append(
            f"[week={session.get('week', '')}, location={session.get('location', '')}]"
        )
        for turn in session.get("conversation_log", []):
            speaker = turn.get("speaker", "unknown")
            name = turn.get("name", "")
            utterance = turn.get("utterance", "")
            label = f"{speaker}({name})" if name else speaker
            lines.append(f"{label}: {utterance}")
    return "\n".join(lines)


def _extract_candidate_words(selected_sessions: list[dict]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    for session in selected_sessions:
        for turn in session.get("conversation_log", []):
            for token in tokenizer_service.tokenize_words(turn.get("utterance", "")):
                normalized = tokenizer_service.normalize_eojeol(token)
                lowered = normalized.lower()
                if (
                    len(normalized) < 2
                    or lowered in _STOPWORDS
                    or lowered in seen
                    or not tokenizer_service.is_noun_like(normalized)
                ):
                    continue
                seen.add(lowered)
                candidates.append(normalized)

    return candidates


def _fallback_flashcards(selected_sessions: list[dict], user_id: str) -> list[dict]:
    word_pool = repository.get_wrong_word_pool(user_id)
    known_meanings = {row.word: row.meaning for row in word_pool if row.word}
    allowed_tokens = _extract_candidate_words(selected_sessions)
    used_tokens: set[str] = set()

    flashcards: list[dict] = []
    for session in selected_sessions:
        for turn in session.get("conversation_log", []):
            utterance = turn.get("utterance", "")
            for word in tokenizer_service.tokenize_words(utterance):
                normalized = tokenizer_service.normalize_eojeol(word)
                if (
                    normalized not in allowed_tokens
                    or normalized in used_tokens
                    or not tokenizer_service.is_noun_like(normalized)
                ):
                    continue
                used_tokens.add(normalized)
                meaning = known_meanings.get(normalized, "Used in conversation context")
                flashcards.append(
                    {
                        "front": normalized,
                        "back": f"Meaning: {meaning}\nExample: {utterance}",
                    }
                )
                if len(flashcards) >= _MAX_FLASHCARDS:
                    return flashcards
    return flashcards


def _parse_flashcards(raw: str, allowed_tokens: set[str]) -> list[dict]:
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

    flashcards: list[dict] = []
    seen: set[str] = set()
    for row in parsed:
        if not isinstance(row, dict):
            continue
        word = tokenizer_service.normalize_eojeol(str(row.get("word", "")).strip())
        meaning = str(row.get("meaning", "")).strip()
        example = str(row.get("example", "")).strip()
        if not word or not meaning or word not in allowed_tokens or word in seen:
            continue
        seen.add(word)
        back = f"Meaning: {meaning}"
        if example:
            back = f"{back}\nExample: {example}"
        flashcards.append({"front": word, "back": back})
    return flashcards


def generate_flashcards(state: ReviewState) -> ReviewState:
    user_id = state.get("user_profile", {}).get("user_id", "")
    selected_sessions = state.get("selected_weak_sessions", [])

    if not selected_sessions:
        state["flashcards"] = []
        return state

    conversation_text = _build_conversation_text(selected_sessions)
    candidate_words = _extract_candidate_words(selected_sessions)
    if not candidate_words:
        state["flashcards"] = []
        return state

    system_prompt = (
        "너는 한국어 학습용 복습 플래시카드 생성기다. "
        "대화 로그에서 학습 가치가 있는 단어만 골라 영어 뜻을 정리한다. "
        "반드시 JSON 배열만 출력한다."
    )
    user_prompt = (
        "아래 대화 로그를 보고 학습용 플래시카드를 최대 5개 생성해라.\n"
        "출력 형식은 JSON 배열이며 각 원소는 word, meaning, example 키를 가져야 한다.\n"
        "규칙:\n"
        "- word는 반드시 아래 후보 단어 목록에 있는 항목만 선택\n"
        "- 단어는 명사 위주로 선택\n"
        "- meaning은 영어로 쉬운 뜻풀이\n"
        "- example은 대화 로그에 나온 원문 그대로 또는 거의 그대로 사용\n"
        "- 조사/접속사/활용형 용언 같은 학습 가치가 낮은 표현은 제외\n"
        "- 중복 없이 출력\n"
        "- 설명문 없이 JSON만 출력\n\n"
        f"후보 단어: {', '.join(candidate_words)}\n\n"
        f"대화 로그:\n{conversation_text}"
    )

    raw = llm_service.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    flashcards = _parse_flashcards(raw, set(candidate_words))
    if not flashcards:
        flashcards = _fallback_flashcards(selected_sessions, user_id)

    state["flashcards"] = flashcards[:_MAX_FLASHCARDS]
    return state
