"""주간 복습 워크플로용 API 라우터."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.orchestrator import orchestrator

router = APIRouter(prefix="/review", tags=["review"])


class WeeklyReviewRequest(BaseModel):
    user_id: str


@router.post("/weekly")
def weekly_review(req: WeeklyReviewRequest) -> dict:
    try:
        return orchestrator.build_weekly_review(user_id=req.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
