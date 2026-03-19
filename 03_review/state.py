"""State schema for weekly review graph."""

from typing import TypedDict

from states.base_state import BaseState


class ReviewState(BaseState, total=False):
    """Review state used to build quizzes and flashcards."""

    selected_weak_sessions: list[dict]
    chosung_quiz: list[dict]
    flashcards: list[dict]
