"""User resource API."""

from fastapi import APIRouter, HTTPException

from app.schemas.user import (
    ReviewCountResponse,
    UserProfileResponse,
    WeeklyReviewResponse,
    WeeklyStatsResponse,
)
from app.usecases.learning_orchestrator import orchestrator

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(user_id: str) -> UserProfileResponse:
    try:
        return orchestrator.get_user_profile(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/weekly-stats", response_model=WeeklyStatsResponse)
def get_weekly_stats(user_id: str) -> WeeklyStatsResponse:
    try:
        return orchestrator.get_weekly_stats(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/review/weekly", response_model=WeeklyReviewResponse)
def get_weekly_review(user_id: str) -> WeeklyReviewResponse:
    try:
        return orchestrator.build_weekly_review(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/review/count", response_model=ReviewCountResponse)
def get_review_count(user_id: str) -> ReviewCountResponse:
    try:
        return orchestrator.get_review_count(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
