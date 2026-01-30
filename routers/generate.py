"""
Generation Router - API endpoints for lesson plan generation
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.models import (
    Subject, LessonType, GenerateRequest, GenerateResponse
)
from src.generation.lesson_generator import generator
from src.generation.book_selector import (
    get_available_lesson_types,
    is_valid_lesson_type,
    LESSON_TYPE_DESCRIPTIONS
)
from src.db.client import db
# Authorization Import
from routers.authorization import get_current_user
from typing import Dict, Any


router = APIRouter(tags=["Generation"])


class LessonTypeInfo(BaseModel):
    """Lesson type information for UI"""
    type: str
    description: str


class LessonTypesResponse(BaseModel):
    """Response listing available lesson types"""
    subject: str
    lesson_types: List[LessonTypeInfo]


@router.post("/lesson-plan", response_model=GenerateResponse)
async def generate_lesson_plan(
    request: GenerateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate a lesson plan based on the provided parameters.

    - Automatically selects appropriate textbooks based on lesson type
    - Retrieves relevant SOW strategies
    - Generates comprehensive lesson plan using LLM
    """
    # RBAC Check
    user_role = current_user.get("role", "").lower() if current_user.get("role") else ""
    user_subject = current_user.get("subject", "")
    is_approved = current_user.get("is_approved", False)
    query_limit = current_user.get("query_limit", 0) or 0

    # 0. Rate Limiting Check
    if query_limit >= 20:
        raise HTTPException(
            status_code=403,
            detail="Maximum generation limit reached (20/20). Please contact support."
        )

    # 1. Teachers can only generate for their subject
    if user_role == "teacher":
        if user_subject != request.subject.value:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Teachers can only generate content for their assigned subject: {user_subject}"
            )
    # 2. Principals can generate for anything IF approved
    elif user_role == "principal":
        if not is_approved:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Principal account not yet approved."
            )
        pass
    else:
        # Deny unknown roles
        raise HTTPException(
            status_code=403,
            detail="Unauthorized role"
        )

    # Validate lesson type for subject
    if not is_valid_lesson_type(request.subject, request.lesson_type):
        valid_types = get_available_lesson_types(request.subject)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lesson type '{request.lesson_type.value}' for {request.subject.value}. "
                   f"Valid types: {[t.value for t in valid_types]}"
        )

    # Generate lesson plan
    response = generator.generate(
        grade=request.grade,
        subject=request.subject.value,
        lesson_type=request.lesson_type,
        page_start=request.page_start,
        page_end=request.page_end,
        topic=request.topic
    )

    # Increment query limit for the user
    if current_user and "id" in current_user:
        db.increment_query_limit(current_user["id"])

    return response


@router.get("/lesson-types/{subject}", response_model=LessonTypesResponse)
async def get_lesson_types(subject: Subject):
    """Get available lesson types for a subject"""
    types = get_available_lesson_types(subject)

    return LessonTypesResponse(
        subject=subject.value,
        lesson_types=[
            LessonTypeInfo(
                type=t.value,
                description=LESSON_TYPE_DESCRIPTIONS.get(t, "")
            )
            for t in types
        ]
    )


@router.get("/lesson-types")
async def get_all_lesson_types():
    """Get all available lesson types organized by subject"""
    result = {}

    for subject in Subject:
        types = get_available_lesson_types(subject)
        result[subject.value] = [
            {
                "type": t.value,
                "description": LESSON_TYPE_DESCRIPTIONS.get(t, "")
            }
            for t in types
        ]

    return result


@router.get("/history")
async def get_lesson_plan_history(
    subject: Optional[Subject] = None,
    lesson_type: Optional[str] = None,
    limit: int = 50
):
    """Get history of generated lesson plans"""
    from src.db.client import db

    plans = db.list_lesson_plans(
        subject=subject.value if subject else None,
        lesson_type=lesson_type,
        limit=limit
    )

    return {"plans": plans, "count": len(plans)}


@router.get("/lesson-plan/{plan_id}")
async def get_lesson_plan_by_id(plan_id: int):
    """Get a specific lesson plan by ID"""
    from src.db.client import db

    plan = db.get_lesson_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    return plan


class UpdateLessonPlanRequest(BaseModel):
    """Request to update lesson plan content"""
    html_content: str


@router.put("/lesson-plan/{plan_id}")
async def update_lesson_plan(plan_id: int, request: UpdateLessonPlanRequest):
    """Update the HTML content of a lesson plan"""
    from src.db.client import db

    # Check if plan exists
    plan = db.get_lesson_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    # Update the lesson plan
    success = db.update_lesson_plan(plan_id, request.html_content)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update lesson plan")

    return {
        "success": True,
        "message": "Lesson plan updated successfully",
        "plan_id": plan_id
    }
