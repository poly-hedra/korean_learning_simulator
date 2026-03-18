"""API router for conversation workflow."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.main import orchestrator

router = APIRouter(prefix="/conversation", tags=["conversation"])


class StartConversationRequest(BaseModel):
    user_id: str = Field(..., description="고유 사용자 ID")
    country: str
    korean_level: str = Field(..., description="초급/중급/고급")
    has_korean_media_experience: bool
    location: str = Field(..., description="예: 병원/공원/학교/콘서트장")
    selected_role: str | None = Field(default=None, description="A 또는 B")


class TurnRequest(BaseModel):
    user_id: str
    user_input: str


@router.post("/start")
def start_conversation(req: StartConversationRequest) -> dict:
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


@router.post("/turn")
def conversation_turn(req: TurnRequest) -> dict:
    try:
        return orchestrator.continue_turn(
            user_id=req.user_id, user_input=req.user_input
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
