"""
Pydantic Models for API Request/Response
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LessonType(str, Enum):
    """Available lesson plan types"""
    # English types (in order as per design)
    RECALL = "recall"
    VOCABULARY = "vocabulary"
    LISTENING = "listening"
    READING = "reading"
    READING_COMPREHENSION = "reading_comprehension"
    GRAMMAR = "grammar"
    ORAL_SPEAKING = "oral_speaking"
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
    # English flow: lesson_type + lesson_number (page_start)
    lesson_type: Optional[LessonType] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    topic: Optional[str] = None
    # Math flow: unit_number + page numbers
    unit_number: Optional[int] = None
    course_book_pages: Optional[str] = None  # e.g., "145" or "145-150"
    workbook_pages: Optional[str] = None  # Optional, e.g., "80" or "80-85"
    book_types: Optional[List[str]] = None  # e.g., ["CB", "AB"] - which books to include
    # English per-book page inputs
    lb_pages: Optional[str] = None       # e.g. "110-111" or "110"
    ab_pages: Optional[str] = None       # e.g. "88-89"
    ort_pages: Optional[str] = None      # e.g. "109-112"
    is_club_period: bool = False          # True = 70 min, False = 35 min
    # English section selections (new structured approach)
    selected_sections: Optional[Dict[str, Any]] = None
    teacher_instructions: Optional[str] = None  # freeform teacher notes appended to prompt
    # selected_sections structure:
    # {
    #   "recall": bool,
    #   "vocabulary": bool,
    #   "warmup": bool,
    #   "exercise_ids": List[str],   # e.g. ["1", "3", "4"]
    #   "differentiated": bool,
    #   "extension": bool
    # }


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


class UserCredentials(BaseModel):
    """User credentials for signup/login"""
    email: str
    password: str


class UserRegistration(BaseModel):
    """User registration data"""
    first_name: str
    last_name: str
    grade: Optional[str] = None
    subject: Optional[str] = None
    school_branch: str
    email: str
    password: str
    role : str


class AuthResponse(BaseModel):
    """Response model for authentication"""
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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


class TeacherResource(BaseModel):
    """External resource for teachers (videos, audio, documents)"""
    title: str
    type: str  # "video", "audio", "document", "interactive"
    reference: str  # URL or reference identifier


class GenerateResponse(BaseModel):
    """Response model for lesson plan generation"""
    success: bool
    html_content: Optional[str] = None  # HTML formatted lesson plan
    lesson_plan: Optional[LessonPlan] = None  # Legacy JSON format
    raw_content: Optional[str] = None
    plan_id: Optional[int] = None  # ID of saved lesson plan in database
    error: Optional[str] = None
    teacher_resources: Optional[List[TeacherResource]] = None  # External resources from SOW
    # Usage metrics
    generation_time: Optional[float] = None  # Time in seconds
    cost: Optional[float] = None  # Cost in USD
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class IngestResponse(BaseModel):
    """Response model for ingestion operations"""
    success: bool
    message: str
    book_id: Optional[int] = None
    sow_id: Optional[int] = None
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
    has_content: bool = False  # Whether content_text is populated


# ============= SOW Models (English Format) =============

class SOWTeachingStep(BaseModel):
    """A single teaching strategy entry in the teaching sequence"""
    strategy: str = Field(..., description="Exact bold heading/section name from Column 2 of SoW")
    content: str = Field(default="", description="Full verbatim text of the strategy's description from Column 2")
    afl: List[str] = Field(default_factory=list, description="AFL strategy names from Column 3 aligned with this strategy")


class SOWLbAbSection(BaseModel):
    """LB + AB (Learner's Book / Activity Book) section of a lesson"""
    slos: List[str] = Field(default_factory=list, description="Exact SLO bullet texts from 'Students will be able to:'")
    skills: List[str] = Field(default_factory=list, description="Exact skill names listed in Content column")
    teaching_sequence: List[SOWTeachingStep] = Field(default_factory=list, description="Ordered teaching strategies from Column 2")


class SOWOrtSection(BaseModel):
    """Oxford Reading Tree section of a lesson (separate from LB/AB)"""
    book_title: str = Field(default="", description="Full ORT book title e.g. 'Oxford Reading Tree Reader Level 8'")
    story_title: str = Field(default="", description="Story title e.g. 'Victorian Adventure'")
    pages: List[int] = Field(default_factory=list, description="Page numbers covered e.g. [109,110,111,112]")
    slos: List[str] = Field(default_factory=list, description="Exact SLO bullet texts from ORT section")
    skills: List[str] = Field(default_factory=list, description="Exact skill names from ORT section")
    vocabulary: List[str] = Field(default_factory=list, description="Vocabulary words from ORT vocabulary table")
    teaching_sequence: List[SOWTeachingStep] = Field(default_factory=list, description="ORT teaching strategies from Column 2")


class SOWLesson(BaseModel):
    """A lesson within a unit"""
    lesson_number: int = Field(..., description="Lesson number")
    lesson_title: str = Field(..., description="Lesson title")
    lb_ab: SOWLbAbSection = Field(default_factory=SOWLbAbSection, description="LB/AB main lesson section")
    ort: SOWOrtSection = Field(default_factory=SOWOrtSection, description="Oxford Reading Tree section")
    classwork_homework: List[str] = Field(default_factory=list, description="Each classwork/homework bullet verbatim")


class SOWUnit(BaseModel):
    """A unit within the curriculum"""
    unit_number: int = Field(..., description="Unit number")
    unit_title: str = Field(..., description="Unit title")
    lessons: List[SOWLesson] = Field(default_factory=list, description="Lessons in the unit")


class SOWCurriculum(BaseModel):
    """Root curriculum structure"""
    units: List[SOWUnit] = Field(default_factory=list, description="Units in the curriculum")


class SOWDocument(BaseModel):
    """Complete SOW document structure"""
    curriculum: SOWCurriculum = Field(..., description="The curriculum data")


# ============= Math SOW Models (Simplified Format) =============

class MathSOWUnit(BaseModel):
    """A Math unit with content (simplified structure without lessons)"""
    unit_number: int = Field(..., description="Unit/Chapter number")
    unit_title: str = Field(..., description="Unit/Chapter title")
    content: str = Field(default="", description="Complete unit content including SLOs, skills, activities, etc.")


class MathSOWCurriculum(BaseModel):
    """Math curriculum structure"""
    units: List[MathSOWUnit] = Field(default_factory=list, description="Units in the Math curriculum")


class MathSOWDocument(BaseModel):
    """Complete Math SOW document structure"""
    curriculum: MathSOWCurriculum = Field(..., description="The Math curriculum data")

