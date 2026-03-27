"""평가 워크플로용 API 라우터."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.orchestrator import orchestrator

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluateRequest(BaseModel):
    user_id: str
    week: int


class EvaluateResponse(BaseModel):
    conversation_log: list[dict[str, Any]] = Field(
        default_factory=list, description="평가 대상 대화 로그"
    )
    location: str = Field(default="", description="대화가 진행된 장소")
    scenario_title: str = Field(default="", description="시나리오 제목")
    highlighted_log: list[dict[str, Any]] = Field(
        default_factory=list, description="오류 하이라이트가 반영된 대화 로그"
    )
    total_score_10: float = Field(default=0.0, description="10점 만점 기준 총점")
    tier: str = Field(default="", description="평가 티어")
    feedback: str = Field(default="", description="평가 피드백")
    llm_summary: str = Field(default="", description="LLM 요약 코멘트")
    SCK_match_count: int = Field(default=0, description="SCK 일치 토큰 수")
    SCK_total_tokens: int = Field(default=0, description="SCK 비교 대상 토큰 수")
    SCK_match_rate: float = Field(default=0.0, description="SCK 일치율(퍼센트, 0~100)")
    SCK_level_counts: dict[str, int] = Field(
        default_factory=dict, description="난이도 레벨별 일치 수"
    )
    SCK_level_word_counts: dict[str, Any] = Field(
        default_factory=dict, description="난이도 레벨별 사용 단어 빈도 정보"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_log": [
                    {
                        "speaker": "ai",
                        "role": "B",
                        "name": "지훈",
                        "utterance": "안녕하세요! 수상택시 정류장을 찾고 계신가요?",
                    },
                    {
                        "speaker": "user",
                        "role": "A",
                        "name": "마크",
                        "utterance": "네 맞아요 수상택시가 한강에 새롭게 생겼다고 들어서 타보고 싶어요",
                    },
                ],
                "location": "한강",
                "scenario_title": "한강에서 처음 만난 두 사람의 대화",
                "highlighted_log": [
                    {
                        "speaker": "user",
                        "utterance": "네 맞아요 [오류: 수상택시 -> 수상 택시]가 한강에 새롭게 생겼다고 들어서 타보고 싶어요",
                    },
                    {
                        "speaker": "user",
                        "utterance": "[오류: 안내원님도 -> 안내원 님도] 가끔 타시나요? 뉴스를 보니 이용객이 저조하다던데요",
                    },
                ],
                "total_score_10": 9.44,
                "tier": "Intermediate <A>",
                "feedback": "[점수 산출 근거]\n- 가중치 합산: 어휘(10.0 x 0.30 = 3.0) + 맥락(10.0 x 0.50 = 5.0) + 맞춤법(7.2 x 0.20 = 1.44)",
                "llm_summary": "대화에서 지훈은 마크에게 수상택시 정류장 위치를 정확히 안내하고, 날씨와 이동 경로에 대한 친절한 조언을 제공하며 맥락을 일관되게 유지했습니다.",
                "SCK_match_count": 35,
                "SCK_total_tokens": 37,
                "SCK_match_rate": 94.59,
                "SCK_level_counts": {"1": 16, "2": 9, "3": 4, "4": 2, "5": 3, "6": 1},
                "SCK_level_word_counts": {
                    "1": {"걸리다": 1, "공원": 1, "괜찮다": 1},
                    "2": {"한강": 1, "다리": 1},
                    "3": {"꽤": 1, "안내원": 1},
                },
            }
        }
    }


@router.post("/run", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    try:
        return orchestrator.evaluate_session(user_id=req.user_id, week=req.week)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
