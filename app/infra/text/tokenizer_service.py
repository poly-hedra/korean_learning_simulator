"""한국어 학습 복습 기능용 토크나이저 헬퍼."""

from __future__ import annotations

import re


class TokenizerService:
    """대화 텍스트에 대한 경량 어절 토크나이징을 제공한다."""

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
        """텍스트를 공백 기준 어절형 토큰으로 분리한다."""

        tokens: list[str] = []
        for chunk in text.split():
            token = self._edge_punct_pattern.sub("", chunk.strip())
            if len(token) >= 2:
                tokens.append(token)
        return tokens

    def normalize_eojeol(self, token: str) -> str:
        """일반 조사/어미를 제거해 기본형에 가까운 복습 토큰을 만든다."""

        normalized = self._edge_punct_pattern.sub("", token.strip())
        for suffix in self._trim_suffixes:
            if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 2:
                normalized = normalized[: -len(suffix)]
                break
        return normalized

    def tokenize_words(self, text: str) -> list[str]:
        """텍스트에서 단어형 토큰을 추출한다.

        공백 단위 어절 대신 문장 내부 단어 후보를 추출합니다.
        """

        words: list[str] = []
        for raw in self._word_pattern.findall(text):
            token = self._edge_punct_pattern.sub("", raw.strip())
            if len(token) >= 2:
                words.append(token)
        return words

    def is_noun_like(self, token: str) -> bool:
        """한국어 학습용 명사형 단어인지 휴리스틱으로 판별한다."""

        t = token.strip().lower()
        if len(t) < 2:
            return False

        # 플래시카드가 명사 중심이 되도록 일반 용언/활용형을 제외한다.
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
