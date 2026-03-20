"""평가 단계용 점수 계산 헬퍼."""

from app.config import settings


class ScoringService:
    """레벨 기준 가중 점수와 티어를 계산한다."""

    def total_score_10(self, vocab: float, context: float, spelling: float) -> float:
        total = (
            vocab * settings.score_weight_vocab
            + context * settings.score_weight_context
            + spelling * settings.score_weight_spelling
        )
        return round(total, 2)

    def tier_for_level(self, korean_level: str, total_score_10: float) -> str:
        """초급/중급/고급 구간에 따라 티어를 반환한다."""

        # 공통 임계치 (10점 만점)
        if total_score_10 >= 9.0:
            suffix = "A"
        elif total_score_10 >= 7.5:
            suffix = "B"
        elif total_score_10 >= 6.0:
            suffix = "C"
        else:
            suffix = "D"

        return f"{korean_level} <{suffix}>"


scoring_service = ScoringService()
