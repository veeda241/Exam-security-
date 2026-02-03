"""
ExamGuard Pro - API Dependencies
Shared dependencies for FastAPI endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from database import get_db
from api.models import ExamSession, Student


# API Key authentication (optional)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)) -> Optional[str]:
    """Validate API key if provided"""
    # For now, just return the key - implement validation as needed
    return api_key


async def require_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Require valid API key"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    # Add actual validation here
    return api_key


async def get_current_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> ExamSession:
    """Get and validate current exam session"""
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


async def get_active_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> ExamSession:
    """Get and validate active exam session"""
    session = await get_current_session(session_id, db)
    
    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )
    
    return session


async def get_student(
    student_id: str,
    db: AsyncSession = Depends(get_db)
) -> Student:
    """Get and validate student"""
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    return student


class Pagination:
    """Pagination parameters"""
    
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 1000)  # Max 1000 items per page


def get_pagination(skip: int = 0, limit: int = 100) -> Pagination:
    """Get pagination parameters"""
    return Pagination(skip=skip, limit=limit)
