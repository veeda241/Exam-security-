from fastapi import APIRouter, HTTPException
from typing import List

from supabase_client import get_supabase
from api.schemas import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter()
supabase = get_supabase()

@router.post("/", response_model=StudentResponse)
async def create_student(student_data: StudentCreate):
    """Create a new student via Supabase"""
    try:
        # Check if id already exists if provided
        if student_data.id:
            res = supabase.table("students").select("id").eq("id", student_data.id).execute()
            if res.data:
                raise HTTPException(status_code=400, detail="Student ID already registered")
                
        # Check if email already exists
        if student_data.email:
            res = supabase.table("students").select("id").eq("email", student_data.email).execute()
            if res.data:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create student
        student_args = {
            "name": student_data.name,
            "email": student_data.email,
            "department": student_data.department,
            "year": student_data.year
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[StudentResponse])
async def list_students(limit: int = 100):
    """Get all students from Supabase"""
    try:
        res = supabase.table("students").select("*").limit(limit).order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: str):
    """Get a specific student by ID from Supabase"""
    try:
        res = supabase.table("students").select("*").eq("id", student_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Student not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(student_id: str, student_data: StudentUpdate):
    """Update student information in Supabase"""
    try:
        # Check if student exists
        res = supabase.table("students").select("*").eq("id", student_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        updates = {}
        if student_data.name is not None:
            updates["name"] = student_data.name
        if student_data.email is not None:
            # Check uniqueness
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
    try:
        res = supabase.table("students").delete().eq("id", student_id).execute()
        return {"message": "Student deleted successfully", "id": student_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
