"""Exams CRUD API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from deps import get_current_user, get_proctor_user, get_db
from schemas.exam import ExamCreate, ExamResponse, ExamUpdate

router = APIRouter()


@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_in: ExamCreate,
    user=Depends(get_proctor_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    row = {
        "title": exam_in.title,
        "created_by": user["id"],
        "starts_at": exam_in.starts_at.isoformat() if exam_in.starts_at else None,
        "duration_minutes": exam_in.duration_minutes,
        "ruleset": exam_in.ruleset.model_dump(),
    }
    res = db.table("exams").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create exam")
    return ExamResponse(**res.data[0])


@router.get("/", response_model=List[ExamResponse])
async def list_exams(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if user.get("role") in ("admin", "proctor"):
        res = db.table("exams").select("*").order("created_at", desc=True).execute()
    else:
        res = db.table("exams").select("*").order("created_at", desc=True).execute()
    return [ExamResponse(**row) for row in (res.data or [])]


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    res = db.table("exams").select("*").eq("id", exam_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Exam not found")
    return ExamResponse(**res.data[0])


@router.patch("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: str,
    exam_in: ExamUpdate,
    user=Depends(get_proctor_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    updates = exam_in.model_dump(exclude_unset=True)
    if "ruleset" in updates and updates["ruleset"] is not None:
        updates["ruleset"] = updates["ruleset"].model_dump() if hasattr(updates["ruleset"], "model_dump") else updates["ruleset"]

    res = db.table("exams").update(updates).eq("id", exam_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Exam not found")
    return ExamResponse(**res.data[0])
