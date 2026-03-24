"""어휘 평가용 토크나이징/정규화 전처리 유틸."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

PREDICATE_TAGS = {"VV", "VA", "VX", "XSV", "XSA"}
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
    form = getattr(token, "form", "")
    lemma = getattr(token, "lemma", "")

    if tag in PREDICATE_TAGS:
        base = lemma or form
        return base if base.endswith("다") else f"{base}다"

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
        if token.tag in DISPLAY_POS_TAGS:
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
    kind_hints = TAG_KIND_HINTS.get(token_tag, [])
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
