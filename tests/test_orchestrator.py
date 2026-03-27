from __future__ import annotations

from importlib import import_module

from app.infra.persistence.repository import repository


orchestrator_module = import_module("app.usecases.learning_orchestrator")
LearningOrchestrator = orchestrator_module.LearningOrchestrator


class FakeGraph:
    def __init__(self, payload: dict):
        self.payload = payload

    def invoke(self, state: dict) -> dict:
        merged = dict(state)
        merged.update(self.payload)
        return merged


def test_start_session_normalizes_level_and_saves_active_state(monkeypatch):
    monkeypatch.setattr(
        orchestrator_module,
        "build_conversation_graph",
        lambda: FakeGraph({"scenario_title": "한강 시나리오"}),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "build_evaluation_graph",
        lambda: FakeGraph({}),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "build_review_graph",
        lambda: FakeGraph({}),
    )

    orchestrator = LearningOrchestrator()
    state = orchestrator.create_session(
        user_id="user-1",
        country="KR",
        korean_level="초급",
        has_korean_media_experience=True,
        location="한강",
    )

    assert state["user_profile"]["korean_level"] == "Beginner"
    assert state["scenario_title"] == "한강 시나리오"
    assert state["session_id"] in orchestrator.active_sessions


def test_continue_turn_marks_session_finished_when_turn_limit_reached(monkeypatch):
    monkeypatch.setattr(
        orchestrator_module,
        "build_conversation_graph",
        lambda: FakeGraph({}),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "build_evaluation_graph",
        lambda: FakeGraph({}),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "build_review_graph",
        lambda: FakeGraph({}),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "user_response",
        lambda state: {
            **state,
            "turn_count": 1,
            "conversation_log": [{"speaker": "user", "utterance": state["user_input"]}],
        },
    )
    monkeypatch.setattr(
        orchestrator_module,
        "ai_response",
        lambda state: {
            **state,
            "turn_count": 1,
            "conversation_log": state["conversation_log"]
            + [{"speaker": "ai", "utterance": "반가워요"}],
        },
    )

    orchestrator = LearningOrchestrator()
    orchestrator.active_sessions["session-1"] = {
        "user_profile": {"user_id": "user-1"},
        "turn_limit": 1,
        "turn_count": 0,
        "conversation_log": [],
    }

    result = orchestrator.continue_turn("session-1", "안녕하세요")

    assert result["is_finished"] is True
    assert result["conversation_log"][-1]["speaker"] == "ai"


def test_evaluate_session_persists_session_wrong_words_and_summary(monkeypatch):
    monkeypatch.setattr(
        orchestrator_module,
        "build_conversation_graph",
        lambda: FakeGraph({}),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "build_evaluation_graph",
        lambda: FakeGraph(
            {
                "user_profile": {"korean_level": "Beginner"},
                "location": "한강",
                "scenario_title": "한강 대화",
                "conversation_log": [
                    {"speaker": "user", "name": "민지", "utterance": "안녕하세요"},
                ],
                "highlighted_log": [
                    {
                        "speaker": "user",
                        "utterance": "[오류: 자전거를->자전거를요] 타고 싶어요",
                    }
                ],
                "total_score_10": 8.8,
                "tier": "Beginner <B>",
            }
        ),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "build_review_graph",
        lambda: FakeGraph({}),
    )
    monkeypatch.setattr(
        orchestrator_module.llm_service,
        "generate_text",
        lambda **_: "요약 문장",
    )

    repository.upsert_user_profile(
        user_id="user-1",
        country="KR",
        korean_level="Beginner",
        has_korean_media_experience=True,
    )

    orchestrator = LearningOrchestrator()
    orchestrator.active_sessions["session-1"] = {
        "user_profile": {"user_id": "user-1"},
        "conversation_log": [],
    }

    result = orchestrator.evaluate_session("session-1")

    assert result["llm_summary"] == "요약 문장"
    assert repository.sessions_by_user["user-1"][0].scenario_title == "한강 대화"
    assert repository.wrong_words_by_user["user-1"][0].word == "자전거를"
