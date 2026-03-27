"""주간 복습 워크플로용 API 라우터."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.orchestrator import orchestrator

router = APIRouter(prefix="/review", tags=["review"])


class WeeklyReviewRequest(BaseModel):
    user_id: str


class WeeklyReviewResponse(BaseModel):
    user_profile: dict[str, Any] = Field(
        default_factory=dict, description="복습 생성에 사용된 사용자 프로필"
    )
    selected_weak_sessions: list[dict[str, Any]] = Field(
        default_factory=list, description="선정된 약점 세션 목록"
    )
    chosung_quiz: list[dict[str, Any]] = Field(
        default_factory=list, description="생성된 초성 퀴즈"
    )
    flashcards: list[dict[str, Any]] = Field(
        default_factory=list, description="생성된 플래시카드"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_profile": {
                    "user_id": "poly",
                    "country": "korea",
                    "korean_level": "Intermediate",
                    "has_korean_media_experience": False,
                    "selected_role": "A",
                },
                "selected_weak_sessions": [
                    {
                        "week": 1,
                        "location": "한강",
                        "tier": "Intermediate <A>",
                        "total_score_10": 9.44,
                        "scenario_title": "한강에서 처음 만난 두 사람의 대화",
                    }
                ],
                "chosung_quiz": [
                    {
                        "question": "안녕하세요! ㅅㅅㅌㅅ 정류장을 찾고 계신가요?",
                        "options": ["수상공연", "수상택시", "수상택배", "수상훈련"],
                        "answer": "수상택시",
                    },
                    {
                        "question": "네, 새로 생긴 수상택시 정류장은 ㅂㅍㅎㄱㄱㅇ 쪽에 있어요.",
                        "options": ["버스", "바로", "반포한강공원", "보이실"],
                        "answer": "반포한강공원",
                    },
                ],
                "flashcards": [
                    {
                        "word": "수상택시",
                        "meaning": "water taxi",
                        "example": "네 맞아요 수상택시가 한강에 새롭게 생겼다고 들어서 타보고 싶어요",
                    },
                    {
                        "word": "한강",
                        "meaning": "Han River",
                        "example": "네 맞아요 수상택시가 한강에 새롭게 생겼다고 들어서 타보고 싶어요",
                    },
                    {
                        "word": "반포한강공원",
                        "meaning": "Banpo Hangang Park",
                        "example": "반포한강공원! 여기서 그렇게 멀지 않네요 안내해 주셔서 감사합니다",
                    },
                    {
                        "word": "한강 다리",
                        "meaning": "Han River bridge",
                        "example": "한강 다리는 건너는데 시간이 꽤 걸릴텐데 괜찮으신가요?",
                    },
                    {
                        "word": "이용객",
                        "meaning": "user/visitor",
                        "example": "안내원님도 가끔 타시나요? 뉴스를 보니 이용객이 저조하다던데요",
                    },
                ],
            }
        }
    }


@router.post("/weekly", response_model=WeeklyReviewResponse)
def weekly_review(req: WeeklyReviewRequest) -> WeeklyReviewResponse:
    try:
        return orchestrator.build_weekly_review(user_id=req.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
