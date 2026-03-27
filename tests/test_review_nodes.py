from __future__ import annotations

from importlib import import_module

from database.models import SessionRecord
from database.repository import repository


select_weak_logs_module = import_module("03_review.nodes.select_weak_logs")
generate_flashcards_module = import_module("03_review.nodes.generate_flashcards")
generate_chosung_quiz_module = import_module("03_review.nodes.generate_chosung_quiz")


def test_select_weak_logs_returns_lowest_three_sessions():
    repository.save_session(
        SessionRecord("user-1", 1, "Beginner", "한강", "s1", [], 8.5, "Beginner <B>")
    )
    repository.save_session(
        SessionRecord("user-1", 2, "Beginner", "명동", "s2", [], 5.2, "Beginner <D>")
    )
    repository.save_session(
        SessionRecord("user-1", 3, "Beginner", "편의점", "s3", [], 6.7, "Beginner <C>")
    )
    repository.save_session(
        SessionRecord("user-1", 4, "Beginner", "공원", "s4", [], 4.1, "Beginner <D>")
    )

    result = select_weak_logs_module.select_weak_logs(
        {"user_profile": {"user_id": "user-1"}}
    )

    assert [session["week"] for session in result["selected_weak_sessions"]] == [4, 2, 3]


def test_generate_flashcards_prefers_llm_output_but_filters_invalid_rows(monkeypatch):
    raw = """
    [
      {"word": "한강", "meaning": "Han River", "example": "한강에서 라면을 먹었어요."},
      {"word": "그리고", "meaning": "and", "example": "그리고 사진도 찍었어요."},
      {"word": "라면", "meaning": "ramen", "example": "한강에서 라면을 먹었어요."}
    ]
    """
    monkeypatch.setattr(
        generate_flashcards_module.llm_service,
        "generate_text",
        lambda **_: raw,
    )

    state = {
        "user_profile": {"user_id": "user-1"},
        "selected_weak_sessions": [
            {
                "week": 1,
                "location": "한강",
                "conversation_log": [
                    {"speaker": "user", "utterance": "한강에서 라면을 먹었어요."},
                    {"speaker": "user", "utterance": "반포한강공원에서 사진을 찍었어요."},
                ],
            }
        ],
    }

    result = generate_flashcards_module.generate_flashcards(state)

    assert result["flashcards"] == [
        {"front": "한강", "back": "Meaning: Han River\nExample: 한강에서 라면을 먹었어요."},
        {"front": "라면", "back": "Meaning: ramen\nExample: 한강에서 라면을 먹었어요."},
    ]


def test_generate_flashcards_uses_fallback_when_llm_output_is_invalid(monkeypatch):
    repository.save_wrong_words(
        user_id="user-1",
        week=1,
        wrong_words=[{"word": "반포한강공원", "meaning": "Banpo Hangang Park"}],
    )
    monkeypatch.setattr(
        generate_flashcards_module.llm_service,
        "generate_text",
        lambda **_: "not-json",
    )

    state = {
        "user_profile": {"user_id": "user-1"},
        "selected_weak_sessions": [
            {
                "week": 1,
                "location": "한강",
                "conversation_log": [
                    {"speaker": "user", "utterance": "반포한강공원에서 사진을 찍었어요."},
                ],
            }
        ],
    }

    result = generate_flashcards_module.generate_flashcards(state)

    assert result["flashcards"] == [
        {
            "front": "반포한강공원",
            "back": "Meaning: Banpo Hangang Park\nExample: 반포한강공원에서 사진을 찍었어요.",
        },
        {
            "front": "사진",
            "back": "Meaning: Used in conversation context\nExample: 반포한강공원에서 사진을 찍었어요.",
        },
        {
            "front": "찍었어요",
            "back": "Meaning: Used in conversation context\nExample: 반포한강공원에서 사진을 찍었어요.",
        },
    ]


def test_generate_chosung_quiz_creates_multiple_choice_question(monkeypatch):
    monkeypatch.setattr(
        generate_chosung_quiz_module,
        "_generate_llm_distractors",
        lambda answer, candidates, excluded_words: ["지하철", "자물쇠", "조명등"],
    )

    state = {
        "selected_weak_sessions": [
            {
                "week": 1,
                "conversation_log": [
                    {"speaker": "ai", "utterance": "한강에서 자전거를 타요."},
                    {"speaker": "user", "utterance": "좋아요."},
                ],
            }
        ]
    }

    result = generate_chosung_quiz_module.generate_chosung_quiz(state)

    assert len(result["chosung_quiz"]) == 1
    quiz = result["chosung_quiz"][0]
    assert quiz["answer"] == "자전거"
    assert len(quiz["choices"]) == 4
    assert "ㅈㅈㄱ" in quiz["question"]
    assert "자전거" in quiz["choices"]
