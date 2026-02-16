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
from src.generation.sow_matcher import get_math_units
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

    For English:
    - Uses lesson_type and lesson_number (page_start)
    - Automatically selects appropriate textbooks based on lesson type
    - Retrieves relevant SOW strategies

    For Mathematics:
    - Uses unit_number and course_book_pages/workbook_pages
    - Retrieves unit content from Math SOW
    - Fetches specified textbook pages
    """
    # RBAC Check
    user_role = current_user.get("role", "").lower() if current_user.get("role") else ""
    user_subject = current_user.get("subject", "")
    is_approved = current_user.get("is_approved", False)
    user_id = current_user.get("id")

    # 0. Rate Limiting Check (20 lesson plans per week per teacher)
    weekly_count = db.count_weekly_lesson_plans(user_id) if user_id else 0
    if weekly_count >= 20:
        raise HTTPException(
            status_code=403,
            detail=f"Weekly generation limit reached ({weekly_count}/20). Your limit resets in 7 days from your oldest lesson plan this week."
        )

    # 1. Check user approval and role
    if user_role == "teacher":
        # Teachers can now generate for any subject (restriction removed)
        pass
    elif user_role == "principal":
        if not is_approved:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Principal account not yet approved."
            )
    else:
        # Deny unknown roles
        raise HTTPException(
            status_code=403,
            detail="Unauthorized role"
        )

    # Check if this is a Math request (unit-based) or English request (lesson-type based)
    if request.subject == Subject.MATHEMATICS:
        # Math flow: requires unit_number and course_book_pages
        if not request.unit_number:
            raise HTTPException(
                status_code=400,
                detail="Mathematics requires unit_number to be specified"
            )

        # Resolve and validate book_types (default to both if not provided)
        book_types = request.book_types if request.book_types else ["CB", "AB"]
        valid_book_types = {"CB", "AB"}
        invalid = [bt for bt in book_types if bt not in valid_book_types]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid book_types: {invalid}. Must be 'CB' (Course Book) or 'AB' (Activity Book)."
            )
        if not book_types:
            raise HTTPException(
                status_code=400,
                detail="At least one book type must be selected ('CB' or 'AB')."
            )

        # Validate that required page fields are present for selected book types
        if "CB" in book_types and not request.course_book_pages:
            raise HTTPException(
                status_code=400,
                detail="Course Book pages are required when Course Book is selected."
            )
        if "AB" in book_types and not request.workbook_pages:
            raise HTTPException(
                status_code=400,
                detail="Activity Book pages are required when Activity Book is selected."
            )

        # Require at least one page input
        if not request.course_book_pages and not request.workbook_pages:
            raise HTTPException(
                status_code=400,
                detail="Mathematics requires at least course_book_pages or workbook_pages to be specified"
            )

        # Generate Math lesson plan
        response = generator.generate_math(
            grade=request.grade,
            unit_number=request.unit_number,
            course_book_pages=request.course_book_pages,
            workbook_pages=request.workbook_pages,
            book_types=book_types,
            created_by_id=user_id
        )
    else:
        # English flow: requires lesson_type and page_start (lesson_number)
        if not request.lesson_type:
            raise HTTPException(
                status_code=400,
                detail="English requires lesson_type to be specified"
            )
        if request.page_start is None:
            raise HTTPException(
                status_code=400,
                detail="English requires page_start (lesson_number) to be specified"
            )

        # Validate lesson type for subject
        if not is_valid_lesson_type(request.subject, request.lesson_type):
            valid_types = get_available_lesson_types(request.subject)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid lesson type '{request.lesson_type.value}' for {request.subject.value}. "
                       f"Valid types: {[t.value for t in valid_types]}"
            )

        # Generate English lesson plan
        response = generator.generate(
            grade=request.grade,
            subject=request.subject.value,
            lesson_type=request.lesson_type,
            page_start=request.page_start,
            page_end=request.page_end,
            topic=request.topic,
            created_by_id=user_id
        )

    return response


class UnitInfo(BaseModel):
    """Unit information for Math UI"""
    unit_number: int
    unit_title: str


class UnitsResponse(BaseModel):
    """Response listing available units for Math"""
    grade: str
    subject: str
    units: List[UnitInfo]


@router.get("/units/{grade}", response_model=UnitsResponse)
async def get_math_units_for_grade(grade: str):
    """
    Get available Math units/chapters from SOW for a given grade.
    Used by frontend to populate the unit selector for Mathematics.
    """
    subject = "Mathematics"

    # Fetch Math SOW for the grade
    sow_entries = db.get_sow_by_subject(subject, grade)

    if not sow_entries:
        return UnitsResponse(
            grade=grade,
            subject=subject,
            units=[]
        )

    # Get the first SOW entry
    sow_data = sow_entries[0]
    extraction = sow_data.get("extraction", {})

    if not extraction:
        return UnitsResponse(
            grade=grade,
            subject=subject,
            units=[]
        )

    # Get units from the Math SOW
    units = get_math_units(extraction)

    return UnitsResponse(
        grade=grade,
        subject=subject,
        units=[
            UnitInfo(unit_number=u["unit_number"], unit_title=u["unit_title"])
            for u in units
        ]
    )


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


@router.get("/weekly-usage")
async def get_weekly_usage(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current user's weekly lesson plan usage.
    Returns count of lesson plans created this week and the weekly limit.
    """
    user_id = current_user.get("id")
    weekly_count = db.count_weekly_lesson_plans(user_id) if user_id else 0
    weekly_limit = 20

    return {
        "used": weekly_count,
        "limit": weekly_limit,
        "remaining": max(0, weekly_limit - weekly_count),
        "percentage": round((weekly_count / weekly_limit) * 100, 1) if weekly_limit > 0 else 0
    }


@router.get("/history")
async def get_lesson_plan_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    subject: Optional[Subject] = None,
    lesson_type: Optional[str] = None,
    limit: int = 50
):
    """Get history of generated lesson plans for the authenticated user"""
    from src.db.client import db
    user_id = current_user.get("id")
    plans = db.list_lesson_plans_by_user(
        user_id=user_id,
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
