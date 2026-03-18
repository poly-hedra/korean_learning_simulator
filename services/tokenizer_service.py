"""Tokenizer helpers for Korean learning review features."""

from __future__ import annotations

import re


class TokenizerService:
    """Provide lightweight eojeol tokenization for dialogue text."""

    _edge_punct_pattern = re.compile(r"^[^A-Za-z가-힣0-9]+|[^A-Za-z가-힣0-9]+$")
    _word_pattern = re.compile(r"[A-Za-z가-힣0-9]+")
    _trim_suffixes = [
        "할까요",
        "했어요",
        "해요",
        "하세요",
        "입니다",
        "있어요",
        "습니다",
        "에서는",
        "에서",
        "으로",
        "에게",
        "한테",
        "처럼",
        "까지",
        "부터",
        "보다",
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

    def tokenize_eojeol(self, text: str) -> list[str]:
        """Split text into whitespace-delimited eojeol-like tokens."""

        tokens: list[str] = []
        for chunk in text.split():
            token = self._edge_punct_pattern.sub("", chunk.strip())
            if len(token) >= 2:
                tokens.append(token)
        return tokens

    def normalize_eojeol(self, token: str) -> str:
        """Trim common particles/endings to produce a base-like review token."""

        normalized = self._edge_punct_pattern.sub("", token.strip())
        for suffix in self._trim_suffixes:
            if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 2:
                normalized = normalized[: -len(suffix)]
                break
        return normalized

    def tokenize_words(self, text: str) -> list[str]:
        """Extract word-like tokens from text.

        공백 단위 어절 대신 문장 내부 단어 후보를 추출합니다.
        """

        words: list[str] = []
        for raw in self._word_pattern.findall(text):
            token = self._edge_punct_pattern.sub("", raw.strip())
            if len(token) >= 2:
                words.append(token)
        return words

    def is_noun_like(self, token: str) -> bool:
        """Heuristic check for noun-like Korean learning words."""

        t = token.strip().lower()
        if len(t) < 2:
            return False

        # Filter common predicates/conjugations so cards stay noun-focused.
        blocked_suffixes = (
            "하다",
            "해요",
            "했다",
            "합니다",
            "되다",
            "돼요",
            "입니다",
            "있다",
            "없다",
            "같다",
            "싶다",
        )
        return not any(t.endswith(s) for s in blocked_suffixes)


tokenizer_service = TokenizerService()
