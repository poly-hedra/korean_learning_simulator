"""Session resource API."""

from fastapi import APIRouter, HTTPException

from app.schemas.session import (
    CreateSessionRequest,
    CreateTurnRequest,
    EvaluationResponse,
    SelectRoleRequest,
    SessionStateResponse,
)
from app.usecases.learning_orchestrator import orchestrator

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionStateResponse)
def create_session(req: CreateSessionRequest) -> SessionStateResponse:
    try:
        return orchestrator.create_session(
            user_id=req.user_id,
            country=req.country,
            korean_level=req.korean_level,
            has_korean_media_experience=req.has_korean_media_experience,
            location=req.location,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=SessionStateResponse)
def get_session(session_id: str) -> SessionStateResponse:
    try:
        return orchestrator.get_session_state(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{session_id}/role", response_model=SessionStateResponse)
def select_role(session_id: str, req: SelectRoleRequest) -> SessionStateResponse:
    try:
        return orchestrator.select_role_and_opening(
            session_id=session_id,
            selected_role=req.selected_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/turns", response_model=SessionStateResponse)
def create_turn(session_id: str, req: CreateTurnRequest) -> SessionStateResponse:
    try:
        return orchestrator.continue_turn(session_id=session_id, user_input=req.user_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/evaluation", response_model=EvaluationResponse)
def evaluate_session(session_id: str) -> EvaluationResponse:
    try:
        return orchestrator.evaluate_session(session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
