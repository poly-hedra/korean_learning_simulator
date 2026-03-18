"""Scoring helpers for evaluation phase."""

from app.config import settings


class ScoringService:
    """Calculate weighted score and tier by level."""

    def total_score_10(self, vocab: float, context: float, spelling: float) -> float:
        total = (
            vocab * settings.score_weight_vocab
            + context * settings.score_weight_context
            + spelling * settings.score_weight_spelling
        )
        return round(total, 2)

    def tier_for_level(self, korean_level: str, total_score_10: float) -> str:
        """Return tier segmented by beginner/intermediate/advanced."""

        # 공통 임계치 (10점 만점)
        if total_score_10 >= 9.0:
            suffix = "A"
        elif total_score_10 >= 7.5:
            suffix = "B"
        elif total_score_10 >= 6.0:
            suffix = "C"
        else:
            suffix = "D"

        return f"{korean_level}{suffix}"


scoring_service = ScoringService()
