"""대화 워크플로용 API 라우터."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.orchestrator import orchestrator

router = APIRouter(prefix="/conversation", tags=["conversation"])


class StartConversationRequest(BaseModel):
    user_id: str = Field(..., description="고유 사용자 ID")
    country: str
    korean_level: str = Field(..., description="Beginner/Intermediate/Advanced")
    has_korean_media_experience: bool
    location: str = Field(..., description="예: 병원/공원/학교/콘서트장")
    selected_role: str | None = Field(default=None, description="A 또는 B")


class StartConversationResponse(BaseModel):
    user_profile: dict[str, Any] = Field(
        ...,
        description="사용자 프로필 정보",
        examples=[
            {
                "user_id": "string",
                "country": "string",
                "korean_level": "string",
                "has_korean_media_experience": True,
                "selected_role": "string",
            }
        ],
    )
    location: str = Field(
        ..., description="예: 병원/공원/학교/콘서트장", examples=["병원"]
    )
    scenario_title: str = Field(
        ...,
        description="시나리오 제목",
        examples=["한강 공원에서 벚꽃 감상을 계획한 친구들의 대화"],
    )
    scenario_description: str = Field(
        ...,
        description="시나리오 설명",
        examples=[
            "한강 공원에서 함께한 친구들의 대화입니다. 지우는 마리가 벚꽃 감상을 추천할 코스 순서가 궁금합니다."
        ],
    )
    personas: dict[str, dict[str, Any]] = Field(
        ...,
        description="대화 참여자 정보",
        examples=[
            {
                "A": {
                    "name": "지은",
                    "age": "23",
                    "gender": "여",
                    "role": "친구",
                    "mission": "한강 벚꽃 감상을 함께할 코스를 물어보고 싶어요.",
                },
                "B": {
                    "name": "마루야마 다카코",
                    "age": "25",
                    "gender": "여",
                    "role": "친구",
                    "mission": "한강 벚꽃 코스 순서와 주의사항을 알려주고 싶어요.",
                },
            }
        ],
    )

    conversation_log: list[dict[str, str]] = Field(
        ...,
        description="대화 로그",
        examples=[
            {
                "speaker": "ai",
                "role": "A",
                "name": "지은",
                "utterance": '"한강에서 벚꽃 구경 갈 건데 같이 갈래? 코스 추천 좀 해줄 수 있어?"',
            }
        ],
    )

    turn_count: int = Field(..., description="현재 턴 수", examples=[0])
    turn_limit: int = Field(..., description="총 턴 수 제한", examples=[7])
    location_context: str = Field(
        ...,
        description="장소에 대한 맥락 정보",
        examples=[
            "한강 공원에서는 삼겹살과 볶음밥을 곁들여 먹으며 아이스 커피와 팥빙수로 더위를 식힐 수 있습니다. 벚꽃 철이 되면 여의도 벚꽃 거리와 반포대교 달빛 무지개 분수를 감상할 수 있으며 자전거 타기 또는 피크닉 매트 깔고 낮잠을 즐기기 좋습니다. 낮과 밤의 분위기가 극명하게 달라지는데 낮에는 가족들과 함께한 활기찬 피크닉 장소가 밤이 되면 연인끼리의 로맨틱한 데이트 장소로 바뀝니다. 봄과 가을철 주말에 붐비는 편이며 여름철에는 야간에 반짝이는 조명이 환상적인 풍경을 선사합니다. 공원 산책을 마치며 다음엔 카페에서 디저트와 함께 전망을 즐기면서 일정을 마무리할 계획이라고 제안할 수 있습니다.  \n\n광장 시장에서는 튀김과 떡볶이로 저녁을 해결한 뒤 현지에서 생산된 장신구와 소품가게에서 선물을 고르기 적합합니다. 재래시장의 떠들썩한 분위기와 생동감 넘치는 협상이 특색이며 오전에 방문하면 상인들과의 유쾌한 대화를 나누는 재미를 느낄 수 있습니다. 비 오는 날에는 우산을 쓴 채 복고 감성의 간판과 골목을 거닐며 사진 촬영하기 좋습니다. 다음 번에는 전통 찻집에서 차 한 잔 마시며 시장 이야기를 나누자고 약속할 수 있습니다.  \n\n홍대 거리에서는 김밥과 호떡을 사 먹으며 스트리트 공연을 관람할 수 있고, 벽화와 그래피티가 가득한 골목에서 사진 촬영하기 좋습니다. 밤마다 클럽과 라이브 카페의 음악 소리가 거리를 가득 채우며 젊은 에너지 넘치는 분위기를 느낄 수 있습니다. 주말 저녁에는 인파가 가장 많아 미리 방문 시간을 계획하는 것이 좋고, 가을에는 야외 테라스에서 맥주를 즐기며 선선한 바람을 맞기 최적입니다. 다음 번에는 함께 공연장 예매해 라이브를 보며 놀자고 제안하는 것이 자연스러울 것입니다.",
        ],
    )
    relationship_type: str = Field(..., description="관계 유형", examples=["친구"])
    dialogue_function: list[str] = Field(
        ..., description="대화 기능", examples=[["취소 문의"]]
    )
    is_finished: bool = Field(..., description="대화 종료 여부", examples=[False])
    latest_ai_response: str = Field(
        ...,
        description="AI의 최신 응답",
        examples=["한강에서 벚꽃 구경 갈 건데 같이 갈래? 코스 추천 좀 해줄 수 있어?"],
    )


class TurnRequest(BaseModel):
    user_id: str
    user_input: str


class TurnResponse(BaseModel):
    conversation_log: list[dict[str, str]] = Field(
        ...,
        description="AI 응답이 추가된 전체 대화 로그",
        examples=[
            [
                {"speaker": "ai", "role": "A", "name": "지은", "utterance": "안녕!"},
                {
                    "speaker": "user",
                    "role": "B",
                    "name": "다카코",
                    "utterance": "안녕하세요!",
                },
            ]
        ],
    )
    turn_count: int = Field(..., description="현재까지 진행된 턴 수", examples=[1])
    turn_limit: int = Field(..., description="총 턴 수 제한", examples=[7])
    is_finished: bool = Field(..., description="대화 종료 여부", examples=[False])
    latest_ai_response: str = Field(
        ...,
        description="이번 턴의 AI 응답 문장",
        examples=["코스는 여의도 벚꽃길 → 반포대교 순으로 가면 좋아!"],
    )


@router.post("/start", response_model=StartConversationResponse)
def start_conversation(req: StartConversationRequest) -> StartConversationResponse:
    try:
        return orchestrator.start_session(
            user_id=req.user_id,
            country=req.country,
            korean_level=req.korean_level,
            has_korean_media_experience=req.has_korean_media_experience,
            location=req.location,
            selected_role=req.selected_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/turn", response_model=TurnResponse)
def conversation_turn(req: TurnRequest) -> TurnResponse:
    try:
        return orchestrator.continue_turn(
            user_id=req.user_id, user_input=req.user_input
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
