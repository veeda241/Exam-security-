from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas.session import SessionCreate, SessionResponse
# from app.db.supabase import get_supabase_client

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def create_session(session_in: SessionCreate):
    """Start a new exam session"""
    # Implementation will go here
    return {"id": "new-uuid", "status": "active"}

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get details of a specific session"""
    return {"id": session_id, "status": "active"}
