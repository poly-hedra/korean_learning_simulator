from __future__ import annotations

from app.infra.ai.rag_service import rag_service
from app.infra.scoring.service import scoring_service
from app.infra.text.tokenizer_service import tokenizer_service


def test_scoring_service_uses_weighted_total_and_tier_boundaries():
    assert scoring_service.total_score_10(vocab=10.0, context=8.0, spelling=6.0) == 8.2
    assert scoring_service.tier_for_level("Beginner", 9.0) == "Beginner <A>"
    assert scoring_service.tier_for_level("Beginner", 7.5) == "Beginner <B>"
    assert scoring_service.tier_for_level("Beginner", 6.0) == "Beginner <C>"
    assert scoring_service.tier_for_level("Beginner", 5.99) == "Beginner <D>"


def test_tokenizer_service_handles_tokenize_normalize_and_noun_like():
    assert tokenizer_service.tokenize_eojeol("한강에서 라면을 먹었어요!") == [
        "한강에서",
        "라면을",
        "먹었어요",
    ]
    assert tokenizer_service.normalize_eojeol("반포한강공원에서") == "반포한강공원"
    assert tokenizer_service.tokenize_words("한강, 라면! A1") == ["한강", "라면", "A1"]
    assert tokenizer_service.is_noun_like("반포한강공원") is True
    assert tokenizer_service.is_noun_like("공부하다") is False


def test_rag_service_returns_vocab_diversity_score():
    score = rag_service.vocab_diversity_score(["한강 공원", "한강"])
    assert score == 6.67
