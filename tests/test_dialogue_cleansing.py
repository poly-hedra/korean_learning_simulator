from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module


dialogue_cleansing = import_module("app.domain.evaluation.dialogue_cleansing")


@dataclass
class DummyToken:
    form: str
    tag: str
    lemma: str = ""


def test_base_pos_tag_and_predicate_normalization():
    assert dialogue_cleansing.base_pos_tag("VV-R") == "VV"

    token = DummyToken(form="드셨어요", tag="VV-R", lemma="드시다")
    assert dialogue_cleansing.normalize_token_for_vocab(token) == "들다"


def test_build_normalized_tokens_keeps_display_pos_only():
    tokens = [
        DummyToken(form="한강", tag="NNP"),
        DummyToken(form="드셨어요", tag="VV", lemma="드시다"),
        DummyToken(form="!", tag="SF"),
    ]

    assert dialogue_cleansing.build_normalized_tokens(tokens) == ["한강", "들다"]


def test_resolve_entry_by_pos_filters_homonym_with_tag_hint():
    vocab_entries = {
        "눈": [
            {"index": "1_1", "kind": "명사", "example": "눈이 와요"},
            {"index": "1_2", "kind": "동사", "example": "눈을 뜨다"},
        ]
    }
    homonyms = {
        "눈": [
            {"index": "1_1", "kind": "명사"},
            {"index": "1_2", "kind": "동사"},
        ]
    }

    selected = dialogue_cleansing.resolve_entry_by_pos(
        match_key="눈",
        token_tag="NNG",
        vocab_entries=vocab_entries,
        homonyms=homonyms,
    )

    assert selected == {"index": "1_1", "kind": "명사", "example": "눈이 와요"}


def test_resolve_entries_by_pos_rejects_non_homonym_when_pos_mismatch():
    vocab_entries = {
        "예쁘다": [
            {"index": "1_3", "kind": "형용사", "example": "꽃이 예쁘다"},
        ]
    }

    selected = dialogue_cleansing.resolve_entries_by_pos(
        match_key="예쁘다",
        token_tag="NNG",
        vocab_entries=vocab_entries,
        homonyms={},
    )

    assert selected == []


def test_expand_vocab_word_forms_removes_numeric_suffixes():
    assert dialogue_cleansing.expand_vocab_word_forms("정말02/정말01") == ["정말", "정말"]
