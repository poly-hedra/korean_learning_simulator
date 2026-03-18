"""Application orchestration service.

요구한 0~9 단계 중 실제 흐름 제어를 담당합니다.
라우터는 이 오케스트레이터를 호출만 하도록 얇게 유지합니다.
"""

from __future__ import annotations

from copy import deepcopy

from app.config import settings
from database.models import SessionRecord
from database.repository import repository
from graphs.conversation.conversation_graph import build_conversation_graph
from graphs.evaluation.evaluation_graph import build_evaluation_graph
from graphs.review.review_graph import build_review_graph
from nodes.conversation.ai_response import ai_response
from nodes.conversation.user_response import user_response
from services.llm_service import llm_service


class LearningOrchestrator:
    """Controls conversation/evaluation/review workflows."""

    def __init__(self) -> None:
        self.conversation_graph = build_conversation_graph()
        self.evaluation_graph = build_evaluation_graph()
        self.review_graph = build_review_graph()

        # 세션별 진행 중 상태 (데모용 인메모리)
        self.active_states: dict[str, dict] = {}

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

        profile = repository.upsert_user_profile(
            user_id=user_id,
            country=country,
            korean_level=korean_level,
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
            "turn_limit": settings.turn_limit_by_level.get(korean_level, 7),
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
            korean_level=evaluated.get("user_profile", {}).get("korean_level", "초급"),
            location=evaluated.get("location", ""),
            scenario=evaluated.get("scenario", ""),
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

        # 추가: LLM을 사용한 요약 분석(어휘/맥락/맞춤법) 및 진행 로그
        progress_log: list[dict] = []
        try:
            progress_log.append({"pct": 5, "msg": "평가 시작"})

            # 대화 전체를 문자열로 준비 (AI+사용자 모두)
            convo = evaluated.get("conversation_log", [])
            convo_text = "\n".join(
                f"{turn.get('speaker')}({turn.get('name', '')}): {turn.get('utterance', '')}"
                for turn in convo
            )
            progress_log.append({"pct": 30, "msg": "대화 로그 준비 완료"})

            system_prompt = (
                "너는 한국어 학습 시뮬레이터의 평가 보조자다. "
                "다음 대화를 어휘 다양성, 맥락 일관성, 맞춤법 측면에서 분석해라. "
                "분석 결과를 한국어로 2~3문장으로 요약하라. 각 항목의 강점이나 약점은 간단히 언급하고, "
                "전체 점수와 티어를 반영한 권장 개선점을 한 문장으로 덧붙여라. 출력은 순수한 한국어 텍스트만으로 하라."
            )

            user_prompt = (
                f"총점: {evaluated.get('total_score_10', 0)}/10, 티어: {evaluated.get('tier', '')}.\n"
                f"대화: \n{convo_text}\n"
                "위 내용을 바탕으로 2~3문장으로 요약해줘."
            )

            progress_log.append({"pct": 60, "msg": "LLM 분석 요청 중"})
            llm_out = llm_service.generate_text(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            progress_log.append({"pct": 95, "msg": "LLM 응답 수신"})

            evaluated["llm_summary"] = llm_out
        except Exception as exc:  # fallback: 안전하게 처리
            evaluated["llm_summary"] = "요약 생성 중 오류가 발생했습니다."
            progress_log.append({"pct": 100, "msg": f"요약 실패: {str(exc)}"})

        progress_log.append({"pct": 100, "msg": "평가 완료"})
        evaluated["progress_log"] = progress_log

        self.active_states[user_id] = evaluated
        return evaluated

    def build_weekly_review(self, user_id: str) -> dict:
        """9단계: 약점 세션 선택 + 초성 퀴즈 + 플래시카드 생성."""

        profile = repository.users.get(user_id)
        if not profile:
            raise ValueError("user profile not found")

        state = {
            "user_profile": {
                "user_id": profile.user_id,
                "country": profile.country,
                "korean_level": profile.korean_level,
                "has_korean_media_experience": profile.has_korean_media_experience,
                "selected_role": profile.selected_role,
            }
        }
        return self.review_graph.invoke(state)


orchestrator = LearningOrchestrator()
