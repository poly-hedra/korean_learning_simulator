"""RAG-like helper service.

실제 RAG(벡터DB + 검색 + 재순위화) 대신,
현재는 대화 로그 내 어휘 다양성을 근사 계산해 점수화합니다.
"""

import re


class RAGService:
    """Utility service for lexical diversity analysis."""

    token_pattern = re.compile(r"[A-Za-z가-힣]+")

    def vocab_diversity_score(self, utterances: list[str]) -> float:
        """Return 0~10 vocabulary diversity score.

        다양성 = 고유 토큰 수 / 전체 토큰 수 비율을 10점 환산.
        """

        tokens: list[str] = []
        for utter in utterances:
            tokens.extend(self.token_pattern.findall(utter.lower()))

        if not tokens:
            return 0.0

        unique_ratio = len(set(tokens)) / len(tokens)
        return round(min(10.0, unique_ratio * 10.0), 2)


rag_service = RAGService()
