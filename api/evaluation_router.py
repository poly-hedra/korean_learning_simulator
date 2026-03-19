"""API router for evaluation workflow."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.orchestrator import orchestrator

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluateRequest(BaseModel):
    user_id: str
    week: int


@router.post("/run")
def evaluate(req: EvaluateRequest) -> dict:
    try:
        return orchestrator.evaluate_session(user_id=req.user_id, week=req.week)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
