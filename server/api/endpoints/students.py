from datetime import datetime
from typing import List
import uuid

from fastapi import APIRouter, HTTPException

from supabase_client import get_supabase
from api.schemas import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter()
supabase = get_supabase()


def _local_students(limit: int = 100) -> List[dict]:
    from api.endpoints import sessions as session_store

    with session_store._LOCAL_STORE_LOCK:
        students = list(session_store._LOCAL_STUDENTS.values())
    return students[:limit]


def _store_local_student(student_data: StudentCreate) -> dict:
    from api.endpoints import sessions as session_store
    from api.endpoints.sessions import _store_local_student as persist_local_student

    student_id = student_data.id or str(uuid.uuid4())
    persist_local_student(
        student_id,
        student_data.name,
        student_data.email or f"{student_id}@examguard.internal",
    )

    with session_store._LOCAL_STORE_LOCK:
        record = session_store._LOCAL_STUDENTS[student_id].copy()

    record.setdefault("department", student_data.department)
    record.setdefault("year", student_data.year)
    return record


@router.post("", response_model=StudentResponse)
async def create_student(student_data: StudentCreate):
    """Create a new student via Supabase"""
    if supabase is None:
        return _store_local_student(student_data)

    try:
        if student_data.id:
            res = supabase.table("students").select("id").eq("id", student_data.id).execute()
            if res.data:
                raise HTTPException(status_code=400, detail="Student ID already registered")

        if student_data.email:
            res = supabase.table("students").select("id").eq("email", student_data.email).execute()
            if res.data:
                raise HTTPException(status_code=400, detail="Email already registered")

        student_args = {
            "name": student_data.name,
            "email": student_data.email,
            "department": student_data.department,
            "year": student_data.year,
        }

        if student_data.id:
            student_args["id"] = student_data.id

        res = supabase.table("students").insert(student_args).execute()

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create student")

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Students] Supabase create failed, using local fallback: {e}")
        return _store_local_student(student_data)


@router.get("", response_model=List[StudentResponse])
async def list_students(limit: int = 100):
    """Get all students from Supabase"""
    if supabase is None:
        return _local_students(limit)

    try:
        res = supabase.table("students").select("*").limit(limit).order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"[Students] Supabase list failed, using local fallback: {e}")
        return _local_students(limit)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: str):
    """Get a specific student by ID from Supabase"""
    if supabase is None:
        students = _local_students()
        match = next((student for student in students if student.get("id") == student_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="Student not found")
        return match

    try:
        res = supabase.table("students").select("*").eq("id", student_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Student not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Students] Supabase get failed, using local fallback: {e}")
        students = _local_students()
        match = next((student for student in students if student.get("id") == student_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="Student not found")
        return match


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(student_id: str, student_data: StudentUpdate):
    """Update student information in Supabase"""
    if supabase is None:
        from api.endpoints import sessions as session_store

        with session_store._LOCAL_STORE_LOCK:
            student = session_store._LOCAL_STUDENTS.get(student_id)
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            if student_data.name is not None:
                student["name"] = student_data.name
            if student_data.email is not None:
                student["email"] = student_data.email
            if student_data.department is not None:
                student["department"] = student_data.department
            if student_data.year is not None:
                student["year"] = student_data.year
            return student.copy()

    try:
        res = supabase.table("students").select("*").eq("id", student_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Student not found")

        updates = {}
        if student_data.name is not None:
            updates["name"] = student_data.name
        if student_data.email is not None:
            email_check = supabase.table("students").select("id").eq("email", student_data.email).neq("id", student_id).execute()
            if email_check.data:
                raise HTTPException(status_code=400, detail="Email already in use")
            updates["email"] = student_data.email

        if not updates:
            return res.data[0]

        update_res = supabase.table("students").update(updates).eq("id", student_id).execute()
        return update_res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{student_id}")
async def delete_student(student_id: str):
    """Delete a student from Supabase"""
    if supabase is None:
        from api.endpoints import sessions as session_store

        with session_store._LOCAL_STORE_LOCK:
            if student_id not in session_store._LOCAL_STUDENTS:
                raise HTTPException(status_code=404, detail="Student not found")
            del session_store._LOCAL_STUDENTS[student_id]
        return {"message": "Student deleted successfully", "id": student_id}

    try:
        supabase.table("students").delete().eq("id", student_id).execute()
        return {"message": "Student deleted successfully", "id": student_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
