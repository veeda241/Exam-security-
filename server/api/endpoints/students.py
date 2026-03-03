"""
ExamGuard Pro - Students Endpoint
API routes for student management
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from models.student import Student
from api.schemas import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter()


@router.post("/", response_model=StudentResponse)
async def create_student(
    student_data: StudentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new student"""
    
    # Check if email already exists
    result = await db.execute(
        select(Student).where(Student.email == student_data.email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create student
    new_student = Student(
        name=student_data.name,
        email=student_data.email
    )
    
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    
    return new_student


@router.get("/", response_model=List[StudentResponse])
async def list_students(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all students with pagination"""
    
    result = await db.execute(
        select(Student)
        .offset(skip)
        .limit(limit)
        .order_by(Student.created_at.desc())
    )
    students = result.scalars().all()
    
    return students


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific student by ID"""
    
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    student_data: StudentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update student information"""
    
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Update fields if provided
    if student_data.name is not None:
        student.name = student_data.name
    if student_data.email is not None:
        # Check email uniqueness
        email_check = await db.execute(
            select(Student).where(
                Student.email == student_data.email,
                Student.id != student_id
            )
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        student.email = student_data.email
    
    await db.commit()
    await db.refresh(student)
    
    return student


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a student"""
    
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    await db.delete(student)
    await db.commit()
    
    return {"message": "Student deleted successfully", "id": student_id}
