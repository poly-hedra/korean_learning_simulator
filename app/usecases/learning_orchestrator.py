"""Application-level orchestrator for session-based learning workflows."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from queue import Empty, Queue
from threading import Lock
from typing import Iterator
from uuid import uuid4

from app.config import settings
from app.domain.conversation.workflow import (
    ai_response,
    build_conversation_graph,
    user_response,
)
from app.domain.evaluation.workflow import build_evaluation_graph
from app.domain.review.workflow import (
    build_review_graph,
    generate_chosung_quiz,
    generate_flashcards,
    select_weak_logs,
)
from app.infra.ai.service import llm_service
from app.infra.persistence.models import SessionRecord
from app.infra.persistence.repository import repository


class LearningOrchestrator:
    """대화/평가/복습 유스케이스를 제어한다."""

    def __init__(self) -> None:
        self.conversation_graph = build_conversation_graph()
        self.evaluation_graph = build_evaluation_graph()
        self.review_graph = build_review_graph()
        self.active_sessions: dict[str, dict] = {}

    def _build_review_base_state(self, user_id: str) -> dict:
        profile = repository.users.get(user_id)
        if not profile:
            raise ValueError("user profile not found")

        return {
            "user_profile": {
                "user_id": profile.user_id,
                "country": profile.country,
                "korean_level": profile.korean_level,
                "has_korean_media_experience": profile.has_korean_media_experience,
                "selected_role": profile.selected_role,
            }
        }

    def _serialize_session_state(self, session_id: str, state: dict) -> dict:
        serialized = deepcopy(state)
        serialized["session_id"] = session_id
        return serialized

    def create_session(
        self,
        user_id: str,
        country: str,
        korean_level: str,
        has_korean_media_experience: bool,
        location: str,
    ) -> dict:
        """0~3 단계: 첫 정보 수집 + 장소 + 시나리오 + 페르소나 생성."""

        # korean_level이 Literal["Beginner", "Intermediate", "Advanced"]로 타입 고정되면
        # 아래 level_alias 변환 로직(6줄) 제거 가능
        level_alias = {
            "초급": "Beginner",
            "중급": "Intermediate",
            "고급": "Advanced",
        }
        canonical_level = level_alias.get(korean_level, korean_level)

        profile = repository.upsert_user_profile(
            user_id=user_id,
            country=country,
            korean_level=canonical_level,
            has_korean_media_experience=has_korean_media_experience,
        )

        initial_state = {
            "user_profile": {
                "user_id": user_id,
                "country": profile.country,
                "korean_level": profile.korean_level,
                "has_korean_media_experience": profile.has_korean_media_experience,
                "selected_role": "",
            },
            "location": location,
            "conversation_log": [],
            "turn_count": 0,
            "turn_limit": settings.turn_limit_by_level.get(canonical_level, 7),
            "is_finished": False,
        }

        prepared = self.conversation_graph.invoke(initial_state)
        session_id = str(uuid4())
        self.active_sessions[session_id] = deepcopy(prepared)
        return self._serialize_session_state(session_id, prepared)

    def get_session_state(self, session_id: str) -> dict:
        if session_id not in self.active_sessions:
            raise ValueError("session not found")
        return self._serialize_session_state(
            session_id, self.active_sessions[session_id]
        )

    def select_role_and_opening(self, session_id: str, selected_role: str) -> dict:
        if session_id not in self.active_sessions:
            raise ValueError("session not found")

        state = deepcopy(self.active_sessions[session_id])
        state.setdefault("user_profile", {})["selected_role"] = selected_role
        repository.set_selected_role(
            user_id=state.get("user_profile", {}).get("user_id", ""),
            role=selected_role,
        )

        state = ai_response(state)
        self.active_sessions[session_id] = state
        return self._serialize_session_state(session_id, state)

    def continue_turn(self, session_id: str, user_input: str) -> dict:
        if session_id not in self.active_sessions:
            raise ValueError("session not found")

        state = deepcopy(self.active_sessions[session_id])
        state["user_input"] = user_input

        state = user_response(state)
        if state.get("turn_count", 0) > state.get("turn_limit", 7):
            state["is_finished"] = True
            self.active_sessions[session_id] = state
            return self._serialize_session_state(session_id, state)

        state = ai_response(state)
        if state.get("turn_count", 0) >= state.get("turn_limit", 7):
            state["is_finished"] = True

        self.active_sessions[session_id] = state
        return self._serialize_session_state(session_id, state)

    def evaluate_session(self, session_id: str) -> dict:
        if session_id not in self.active_sessions:
            raise ValueError("session not found")

        state = deepcopy(self.active_sessions[session_id])
        user_id = state.get("user_profile", {}).get("user_id", "")
        week = repository.next_week_for_user(user_id)
        evaluated = self.evaluation_graph.invoke(state)

        record = SessionRecord(
            session_id=session_id,
            user_id=user_id,
            week=week,
            korean_level=evaluated.get("user_profile", {}).get(
                "korean_level", "Beginner"
            ),
            location=evaluated.get("location", ""),
            scenario_title=evaluated.get("scenario_title", ""),
            conversation_log=evaluated.get("conversation_log", []),
            total_score_10=evaluated.get("total_score_10", 0.0),
            tier=evaluated.get("tier", ""),
        )
        repository.save_session(record)

        wrong_words: list[dict] = []
        for turn in evaluated.get("highlighted_log", []):
            utter = turn.get("utterance", "")
            if "[오류:" in utter:
                chunks = [part for part in utter.split("[오류:") if "->" in part]
                for chunk in chunks:
                    wrong = chunk.split("->", maxsplit=1)[0].strip()
                    if wrong:
                        wrong_words.append(
                            {"word": wrong, "meaning": "사용자 오타 교정 단어"}
                        )
        repository.save_wrong_words(user_id=user_id, week=week, wrong_words=wrong_words)

        try:
            conversation_log = evaluated.get("conversation_log", [])
            conversation_text = "\n".join(
                f"{turn.get('speaker')}({turn.get('name', '')}): {turn.get('utterance', '')}"
                for turn in conversation_log
            )

            system_prompt = (
                "너는 한국어 학습 시뮬레이터의 평가 보조자다. "
                "다음 대화 전체를 파악해서 어휘 사용의 다양성, 문법적/ 상황적으로 잘못된 어휘가 사용되지 않았는지 여부, "
                "처음 부터 끝까지 맥락의 일관되게 유지 되는지 등으로 분석해라. "
                "분석 결과를 한국어로 2~3문장으로 요약하고 따뜻한 피드백을 다양한 이모지와 함께 덧붙여라."
                "출력은 순수한 한국어 텍스트만으로 하라."
            )
            user_prompt = (
                f"총점: {evaluated.get('total_score_10', 0)}/10, 티어: {evaluated.get('tier', '')}.\n"
                f"대화: \n{conversation_text}\n"
                "위 내용을 바탕으로 2~3문장으로 요약해줘."
            )
            evaluated["llm_summary"] = llm_service.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            evaluated["llm_summary"] = "요약 생성 중 오류가 발생했습니다."

        self.active_sessions[session_id] = evaluated
        serialized = deepcopy(evaluated)
        serialized["session_id"] = session_id
        return serialized

    def build_weekly_review(self, user_id: str) -> dict:
        state = self._build_review_base_state(user_id=user_id)
        return self.review_graph.invoke(state)

    def get_user_profile(self, user_id: str) -> dict:
        profile = repository.users.get(user_id)
        if not profile:
            raise ValueError("user profile not found")
        return {
            "user_id": profile.user_id,
            "country": profile.country,
            "korean_level": profile.korean_level,
            "has_korean_media_experience": profile.has_korean_media_experience,
            "selected_role": profile.selected_role,
            "latest_tier": profile.latest_tier,
        }

    def get_weekly_stats(self, user_id: str) -> dict:
        profile = repository.users.get(user_id)
        if not profile:
            raise ValueError("user profile not found")
        sessions = repository.sessions_by_user.get(user_id, [])
        conversation_count = len(sessions)
        average_score = (
            round(
                sum(session.total_score_10 for session in sessions)
                / conversation_count,
                2,
            )
            if conversation_count
            else 0.0
        )
        return {
            "user_id": user_id,
            "conversation_count": conversation_count,
            "average_score": average_score,
            "latest_tier": profile.latest_tier,
        }

    def get_review_count(self, user_id: str) -> dict:
        review = self.build_weekly_review(user_id)
        return {
            "user_id": user_id,
            "chosung_quiz_count": len(review.get("chosung_quiz", [])),
            "flashcard_count": len(review.get("flashcards", [])),
        }

    def build_weekly_review_with_progress(
        self, user_id: str
    ) -> Iterator[dict[str, object]]:
        state = self._build_review_base_state(user_id=user_id)

        yield {"pct": 5, "msg": "복습 준비를 시작하는 중"}
        yield {"pct": 15, "msg": "복습할 약점 세션을 고르는 중"}
        state = select_weak_logs(state)
        selected_count = len(state.get("selected_weak_sessions", []))
        yield {"pct": 20, "msg": f"약점 세션 {selected_count}개 선택 완료"}

        if not selected_count:
            yield {
                "pct": 100,
                "msg": "복습할 세션이 없어 준비를 마쳤습니다",
                "review": state,
            }
            return

        progress_queue: Queue[tuple[str, float, str]] = Queue()
        progress_lock = Lock()
        task_progress = {"chosung": 0.0, "flashcards": 0.0}
        task_message = {
            "chosung": "초성 퀴즈 준비 대기 중",
            "flashcards": "플래시카드 준비 대기 중",
        }

        def publish_progress(task_name: str, progress: float, message: str) -> None:
            clamped = max(0.0, min(1.0, progress))
            with progress_lock:
                task_progress[task_name] = clamped
                task_message[task_name] = message
            progress_queue.put((task_name, clamped, message))

        parallel_base_state = deepcopy(state)
        with ThreadPoolExecutor(max_workers=2) as executor:
            chosung_future = executor.submit(
                generate_chosung_quiz,
                deepcopy(parallel_base_state),
                lambda progress, message: publish_progress(
                    "chosung", progress, message
                ),
            )
            flashcards_future = executor.submit(
                generate_flashcards,
                deepcopy(parallel_base_state),
                lambda progress, message: publish_progress(
                    "flashcards", progress, message
                ),
            )

            last_pct = 20
            while True:
                try:
                    progress_queue.get(timeout=0.1)
                except Empty:
                    if chosung_future.done() and flashcards_future.done():
                        break
                    continue

                with progress_lock:
                    average_progress = (
                        task_progress["chosung"] + task_progress["flashcards"]
                    ) / 2
                    pct = max(last_pct, min(99, 20 + int(average_progress * 79)))
                    msg = f"{task_message['chosung']} | {task_message['flashcards']}"

                if pct > last_pct:
                    last_pct = pct
                    yield {"pct": pct, "msg": msg}

            chosung_state = chosung_future.result()
            flashcards_state = flashcards_future.result()

        state["chosung_quiz"] = chosung_state.get("chosung_quiz", [])
        state["flashcards"] = flashcards_state.get("flashcards", [])

        yield {"pct": 100, "msg": "복습 항목 준비 완료", "review": state}


orchestrator = LearningOrchestrator()
