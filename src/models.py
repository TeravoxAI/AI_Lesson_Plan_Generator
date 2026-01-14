"""
Pydantic Models for API Request/Response
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class LessonType(str, Enum):
    """Available lesson plan types"""
    # English types
    READING = "reading"
    COMPREHENSION = "comprehension"
    GRAMMAR = "grammar"
    CREATIVE_WRITING = "creative_writing"
    # Maths types
    CONCEPT = "concept"
    PRACTICE = "practice"


class BookType(str, Enum):
    """Book types available in the system"""
    # English books
    LEARNERS = "learners"
    ACTIVITY = "activity"
    READING = "reading"
    # Maths books
    COURSE_BOOK = "course_book"
    WORKBOOK = "workbook"


class Subject(str, Enum):
    """Available subjects"""
    ENGLISH = "English"
    MATHEMATICS = "Mathematics"


# ============= Request Models =============

class GenerateRequest(BaseModel):
    """Request model for lesson plan generation"""
    grade: str = "Grade 2"
    subject: Subject
    lesson_type: LessonType
    page_start: int
    page_end: Optional[int] = None
    topic: Optional[str] = None


class TextbookUpload(BaseModel):
    """Metadata for textbook upload"""
    grade: str = "Grade 2"
    subject: Subject
    book_type: BookType
    title: str


class SOWUpload(BaseModel):
    """Metadata for SOW upload"""
    grade: str = "Grade 2"
    subject: Subject
    term: str = "Term 1"


# ============= Response Models =============

class LessonPlan(BaseModel):
    """Generated lesson plan structure"""
    slos: List[str]
    methodology: str
    brainstorming_activity: str
    main_teaching_activity: str
    hands_on_activity: str
    afl: str
    resources: List[str]


class GenerateResponse(BaseModel):
    """Response model for lesson plan generation"""
    success: bool
    lesson_plan: Optional[LessonPlan] = None
    raw_content: Optional[str] = None
    error: Optional[str] = None


class IngestResponse(BaseModel):
    """Response model for ingestion operations"""
    success: bool
    message: str
    job_id: Optional[str] = None
    pages_processed: Optional[int] = None
    entries_extracted: Optional[int] = None
    error: Optional[str] = None


class BookInfo(BaseModel):
    """Book information response"""
    id: int
    grade_level: str
    subject: str
    book_type: str
    title: str
    page_count: Optional[int] = None
