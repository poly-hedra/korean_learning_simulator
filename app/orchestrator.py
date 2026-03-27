"""애플리케이션 오케스트레이션 서비스.

요구한 0~9 단계 중 실제 흐름 제어를 담당합니다.
라우터는 이 오케스트레이터를 호출만 하도록 얇게 유지합니다.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from importlib import import_module
from queue import Empty, Queue
from threading import Lock
from typing import Iterator

from app.config import settings
from database.models import SessionRecord
from database.repository import repository
from services.llm_service import llm_service

build_conversation_graph = import_module(
    "01_conversation.graph"
).build_conversation_graph
build_evaluation_graph = import_module("02_evaluation.graph").build_evaluation_graph
build_review_graph = import_module("03_review.graph").build_review_graph
ai_response = import_module("01_conversation.nodes.ai_response").ai_response
user_response = import_module("01_conversation.nodes.user_response").user_response
select_weak_logs = import_module("03_review.nodes.select_weak_logs").select_weak_logs
generate_chosung_quiz = import_module(
    "03_review.nodes.generate_chosung_quiz"
).generate_chosung_quiz
generate_flashcards = import_module(
    "03_review.nodes.generate_flashcards"
).generate_flashcards


class LearningOrchestrator:
    """대화/평가/복습 워크플로를 제어한다."""

    def __init__(self) -> None:
        self.conversation_graph = build_conversation_graph()
        self.evaluation_graph = build_evaluation_graph()
        self.review_graph = build_review_graph()

        # 세션별 진행 중 상태 (데모용 인메모리)
        self.active_states: dict[str, dict] = {}

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

    def start_session(
        self,
        user_id: str,
        country: str,
        korean_level: str,
        has_korean_media_experience: bool,
        location: str,
        selected_role: str | None = None,
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
        if selected_role:
            repository.set_selected_role(user_id=user_id, role=selected_role)

        initial_state = {
            "user_profile": {
                "user_id": user_id,
                "country": profile.country,
                "korean_level": profile.korean_level,
                "has_korean_media_experience": profile.has_korean_media_experience,
                "selected_role": selected_role or "",
            },
            "location": location,
            "conversation_log": [],
            "turn_count": 0,
            "turn_limit": settings.turn_limit_by_level.get(canonical_level, 7),
            "is_finished": False,
        }

        prepared = self.conversation_graph.invoke(initial_state)
        self.active_states[user_id] = deepcopy(prepared)

        # API에서 기존처럼 selected_role을 함께 보내면 바로 첫 발화를 생성해준다.
        if selected_role:
            return self.select_role_and_opening(
                user_id=user_id, selected_role=selected_role
            )
        return prepared

    def select_role_and_opening(self, user_id: str, selected_role: str) -> dict:
        """4단계: 역할 선택 후 AI 첫 발화를 생성."""

        if user_id not in self.active_states:
            raise ValueError("active session not found; call /conversation/start first")

        state = deepcopy(self.active_states[user_id])
        state.setdefault("user_profile", {})["selected_role"] = selected_role
        repository.set_selected_role(user_id=user_id, role=selected_role)

        # 역할이 정해진 뒤에만 AI 시작 발화를 생성한다.
        state = ai_response(state)
        self.active_states[user_id] = state
        return state

    def continue_turn(self, user_id: str, user_input: str) -> dict:
        """5단계: 사용자 입력을 받아 턴 제한 내에서 대화를 진행."""

        if user_id not in self.active_states:
            raise ValueError("active session not found; call /conversation/start first")

        state = deepcopy(self.active_states[user_id])
        state["user_input"] = user_input

        # 사용자 발화 기록
        state = user_response(state)
        if state.get("turn_count", 0) > state.get("turn_limit", 7):
            state["is_finished"] = True
            self.active_states[user_id] = state
            return state

        # 턴 제한 전이면 AI 응답 생성
        state = ai_response(state)
        if state.get("turn_count", 0) >= state.get("turn_limit", 7):
            state["is_finished"] = True

        self.active_states[user_id] = state
        return state

    def evaluate_session(self, user_id: str, week: int) -> dict:
        """6~8 단계: 평가/점수/티어/피드백 생성 후 저장."""

        if user_id not in self.active_states:
            raise ValueError("active session not found")

        state = deepcopy(self.active_states[user_id])
        evaluated = self.evaluation_graph.invoke(state)

        record = SessionRecord(
            user_id=user_id,
            week=week,
            korean_level=evaluated.get("user_profile", {}).get(
                "korean_level", "Beginner"
            ),
            location=evaluated.get("location", ""),
            scenario_title=evaluated.get(
                "scenario_title", ""
            ),  # 구 scenario 키 → scenario_title
            conversation_log=evaluated.get("conversation_log", []),
            total_score_10=evaluated.get("total_score_10", 0.0),
            tier=evaluated.get("tier", ""),
        )
        repository.save_session(record)

        # 하이라이트된 사용자 발화에서 오류 토큰을 간단히 추출해 카드 풀로 저장.
        wrong_words: list[dict] = []
        for turn in evaluated.get("highlighted_log", []):
            utter = turn.get("utterance", "")
            if "[오류:" in utter:
                chunks = [p for p in utter.split("[오류:") if "->" in p]
                for c in chunks:
                    wrong = c.split("->", maxsplit=1)[0].strip()
                    if wrong:
                        wrong_words.append(
                            {"word": wrong, "meaning": "사용자 오타 교정 단어"}
                        )
        repository.save_wrong_words(user_id=user_id, week=week, wrong_words=wrong_words)

        # 추가: LLM을 사용한 요약 분석(어휘/맥락/맞춤법)
        try:
            # 대화 전체를 문자열로 준비 (AI+사용자 모두)
            convo = evaluated.get("conversation_log", [])
            convo_text = "\n".join(
                f"{turn.get('speaker')}({turn.get('name', '')}): {turn.get('utterance', '')}"
                for turn in convo
            )

            system_prompt = (
                "너는 한국어 학습 시뮬레이터의 평가 보조자다. "
                "다음 대화 전체를 파악해서 어휘 사용의 다양성, 문법적/ 상황적으로 잘못된 어휘가 사용되지 않았는지 여부, 처음 부터 끝까지 맥락의 일관되게 유지 되는지 등으로 분석해라. "
                "분석 결과를 한국어로 2~3문장으로 요약하고 따뜻한 피드백을 다양한 이모지와 함께 덧붙여라."
                "출력은 순수한 한국어 텍스트만으로 하라."
            )

            user_prompt = (
                f"총점: {evaluated.get('total_score_10', 0)}/10, 티어: {evaluated.get('tier', '')}.\n"
                f"대화: \n{convo_text}\n"
                "위 내용을 바탕으로 2~3문장으로 요약해줘."
            )

            llm_out = llm_service.generate_text(
                system_prompt=system_prompt, user_prompt=user_prompt
            )

            evaluated["llm_summary"] = llm_out
        except Exception:  # fallback: 안전하게 처리
            evaluated["llm_summary"] = "요약 생성 중 오류가 발생했습니다."

        self.active_states[user_id] = evaluated
        return evaluated

    def build_weekly_review(self, user_id: str) -> dict:
        """9단계: 약점 세션 선택 + 초성 퀴즈 + 플래시카드 생성."""

        state = self._build_review_base_state(user_id=user_id)
        return self.review_graph.invoke(state)

    def build_weekly_review_with_progress(
        self, user_id: str
    ) -> Iterator[dict[str, object]]:
        """터미널 UI용 진행 이벤트와 함께 주간 복습을 생성한다."""

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
                    _, _, _ = progress_queue.get(timeout=0.1)
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
