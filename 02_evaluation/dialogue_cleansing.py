"""어휘 평가용 토크나이징/정규화 전처리 유틸."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

PREDICATE_TAGS = {"VV", "VA", "VX", "XSV", "XSA"}

# Kiwi가 존칭형으로 인해 올바른 원형을 복원하지 못하는 경우의 교정 테이블
# 주의: 드세다(6_8773, 형용사 "고집이 드세다")는 실제 표제어이므로 교정 대상에서 제외
# 드세요 -> 드세/VA(오분석) -> 드세다 는 교정 불가 (드세다가 실제 단어이므로 충돌)
_LEMMA_CORRECTIONS: dict[str, str] = {
    "드시다": "들다",  # 드셨어요/드십시오/드시나요 등 -> 들다04 (1_189)
}

MAIN_POS_TAGS = {"NNG", "NNP", "NNB", "NP", "NR", "VV", "VA", "MAG", "MAJ"}
DISPLAY_POS_TAGS = MAIN_POS_TAGS | {"MAG", "MAJ"}
TAG_KIND_HINTS = {
    "MAG": ["부사"],
    "MAJ": ["부사"],
    "NNG": ["명사", "의존명사"],
    "NNP": ["명사"],
    "NNB": ["의존명사", "명사"],
    "NP": ["대명사"],
    "NR": ["수사"],
    "VV": ["동사"],
    "VA": ["형용사"],
}


def base_pos_tag(tag: str) -> str:
    """Kiwi 세부 태그 접미(예: VV-R)를 제거한 기본 품사를 반환한다."""

    return str(tag).split("-", 1)[0]


def is_main_pos_tag(tag: str) -> bool:
    """어휘 평가 매칭 대상 품사인지 판별한다."""

    return base_pos_tag(tag) in MAIN_POS_TAGS


def is_display_pos_tag(tag: str) -> bool:
    """표시용 정규화 토큰에 포함할 품사인지 판별한다."""

    return base_pos_tag(tag) in DISPLAY_POS_TAGS


def canonicalize_word(text: str) -> str:
    """어휘 매칭용 표준 형태로 정규화한다.

    - 유니코드 정규화(NFC)
    - 앞뒤 공백 제거
    - 말미 숫자 접미 제거 (예: 정말02 -> 정말)
    """

    normalized = unicodedata.normalize("NFC", str(text)).strip()
    return re.sub(r"\d+$", "", normalized)


def expand_vocab_word_forms(raw_word: str) -> list[str]:
    """vocabulary word 필드에서 매칭 가능한 표제어 목록을 추출한다.

    예) "정말02/정말01" -> ["정말", "정말"]
    """

    parts = re.split(r"[\/|,]", str(raw_word))
    forms = [canonicalize_word(part) for part in parts]
    return [form for form in forms if form]


def normalize_token_for_vocab(token: Any) -> str:
    """동사/형용사 계열은 사전형으로 정규화해 사전 매칭에 사용한다."""

    tag = getattr(token, "tag", "")
    base_tag = base_pos_tag(tag)
    form = getattr(token, "form", "")
    lemma = getattr(token, "lemma", "")

    if base_tag in PREDICATE_TAGS:
        # Kiwi lemma가 있으면 이를 사용하되, 오분석은 교정
        if lemma:
            raw = lemma if lemma.endswith("다") else f"{lemma}다"
            return _LEMMA_CORRECTIONS.get(raw, raw)
        return form

    return form


def build_original_tokens(tokens: list[Any]) -> list[str]:
    """구두점을 제외한 원문 토크나이징 결과를 반환한다."""

    return [token.form for token in tokens if not token.tag.startswith("S")]


def build_normalized_tokens(tokens: list[Any]) -> list[str]:
    """표시용 기본형 토큰 목록을 반환한다.

    동사/형용사는 사전형으로 바꾸고, 부사는 그대로 유지한다.
    """

    normalized_tokens: list[str] = []
    for token in tokens:
        if is_display_pos_tag(token.tag):
            normalized_tokens.append(normalize_token_for_vocab(token))
    return normalized_tokens


def resolve_entry_by_pos(
    match_key: str,
    token_tag: str,
    vocab_entries: dict[str, list[dict[str, str]]],
    homonyms: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    """동음이의어는 Kiwi 품사로 1차 필터링해 단일 후보면 즉시 확정한다."""

    if match_key not in vocab_entries:
        return None

    # 동음이의어가 아니면 단일 엔트리로 바로 확정.
    if match_key not in homonyms:
        return vocab_entries[match_key][0]

    candidates = homonyms[match_key]
    kind_hints = TAG_KIND_HINTS.get(base_pos_tag(token_tag), [])
    filtered = [
        candidate
        for candidate in candidates
        if any(hint in str(candidate.get("kind", "")) for hint in kind_hints)
    ]

    # 품사 필터 결과가 단일 후보면 LLM 없이 확정.
    if len(filtered) == 1:
        selected_index = str(filtered[0].get("index", ""))
        for entry in vocab_entries[match_key]:
            if entry["index"] == selected_index:
                return entry

    return None
