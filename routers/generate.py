"""
Generation Router - API endpoints for lesson plan generation
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
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
async def generate_lesson_plan(request: GenerateRequest):
    """
    Generate a lesson plan based on the provided parameters.
    
    - Automatically selects appropriate textbooks based on lesson type
    - Retrieves relevant SOW strategies
    - Generates comprehensive lesson plan using LLM
    """
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
