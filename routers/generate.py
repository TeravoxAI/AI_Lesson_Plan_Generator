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
from src.generation.router import router as ctx_router
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

    # Check subject and route accordingly
    if request.subject == Subject.COMPUTER_STUDIES:
        # CS flow: unit_number + lesson_number, no textbook
        if not request.cs_unit_number or not request.cs_lesson_number:
            raise HTTPException(
                status_code=400,
                detail="Computer Studies requires cs_unit_number and cs_lesson_number"
            )
        if not request.cs_selected_sections or not request.cs_selected_sections.get("section_ids"):
            raise HTTPException(
                status_code=400,
                detail="Computer Studies requires at least one teaching strategy to be selected"
            )
        response = generator.generate_cs(
            grade=request.grade,
            unit_number=request.cs_unit_number,
            lesson_number=request.cs_lesson_number,
            selected_sections=request.cs_selected_sections,
            teacher_instructions=request.teacher_instructions,
            created_by_id=user_id
        )
    elif request.subject == Subject.MATHEMATICS:
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
            teacher_instructions=request.teacher_instructions,
            created_by_id=user_id
        )
    elif request.subject == Subject.ENGLISH:
        # English flow
        if request.page_start is None:
            raise HTTPException(status_code=400, detail="English requires page_start (lesson_number) to be specified")

        # Require at least one exercise selected
        has_sections = (
            request.selected_sections is not None
            and len(request.selected_sections.get("exercise_ids", [])) > 0
        )
        if not has_sections:
            raise HTTPException(
                status_code=400,
                detail="English requires at least one exercise to be selected"
            )

        # Generate English lesson plan
        response = generator.generate(
            grade=request.grade,
            subject=request.subject.value,
            lesson_type=request.lesson_type,
            page_start=request.page_start,
            page_end=request.page_end,
            topic=request.topic,
            lb_pages=request.lb_pages,
            ab_pages=request.ab_pages,
            ort_pages=request.ort_pages,
            is_club_period=request.is_club_period,
            selected_sections=request.selected_sections,
            exercises=None,
            teacher_instructions=request.teacher_instructions,
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


class CSUnitInfo(BaseModel):
    unit_number: int
    unit_title: str

class CSUnitsResponse(BaseModel):
    grade: str
    units: List[CSUnitInfo]

class CSLessonInfo(BaseModel):
    lesson_number: int
    lesson_title: str
    sub_topic: str = ""

class CSLessonsResponse(BaseModel):
    grade: str
    unit_number: int
    lessons: List[CSLessonInfo]


@router.get("/cs-units/{grade}", response_model=CSUnitsResponse)
async def get_cs_units_for_grade(grade: str):
    """Get available Computer Studies units from SOW for a given grade."""
    units = ctx_router.get_cs_units_for_grade(grade)
    return CSUnitsResponse(
        grade=grade,
        units=[CSUnitInfo(unit_number=u["unit_number"], unit_title=u["unit_title"]) for u in units]
    )


@router.get("/cs-lessons/{grade}/{unit_number}", response_model=CSLessonsResponse)
async def get_cs_lessons_for_unit(grade: str, unit_number: int):
    """Get available Computer Studies lessons for a unit."""
    lessons = ctx_router.get_cs_lessons_for_unit(grade, unit_number)
    return CSLessonsResponse(
        grade=grade,
        unit_number=unit_number,
        lessons=[
            CSLessonInfo(
                lesson_number=l["lesson_number"],
                lesson_title=l["lesson_title"],
                sub_topic=l.get("sub_topic", "")
            )
            for l in lessons
        ]
    )


@router.get("/cs-lesson-sections")
async def get_cs_lesson_sections_endpoint(
    grade: str,
    unit_number: int,
    lesson_number: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Return available sections for a CS lesson (strategies, warm-up, classwork etc.)"""
    sections = ctx_router.get_cs_sections_for_lesson(grade, unit_number, lesson_number)
    if sections is None:
        return {"success": False, "sections": None, "message": "CS lesson not found"}
    return {"success": True, "sections": sections}


@router.get("/lesson-sections")
async def get_lesson_sections(
    grade: str,
    lesson_number: int,
    subject: str = "English",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Return the available sections (recall, vocabulary, warm-up, exercises, etc.)
    for a given lesson in the new-format SOW. Used by the frontend to populate checkboxes.
    """
    from src.models import Subject as SubjectEnum
    try:
        subject_enum = SubjectEnum(subject)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid subject: {subject}")

    sections = ctx_router.get_sections_for_lesson(grade, subject_enum, lesson_number)
    if sections is None:
        return {"success": False, "sections": None, "message": "No new-format SOW found for this lesson"}

    return {"success": True, "sections": sections}


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
