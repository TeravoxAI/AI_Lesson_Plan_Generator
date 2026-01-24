"""
Book Selector - Smart book selection based on lesson type
"""
from typing import List
from src.models import LessonType, Subject, BookType


# Book mapping: lesson_type -> list of book_types to use
# English books: Course, Activity, Reading
# Maths books: Course, Activity
BOOK_MAPPING = {
    Subject.ENGLISH: {
        LessonType.READING: [BookType.READING],
        LessonType.COMPREHENSION: [BookType.ACTIVITY],
        LessonType.GRAMMAR: [BookType.COURSE_BOOK],
        LessonType.CREATIVE_WRITING: [BookType.COURSE_BOOK, BookType.ACTIVITY],
    },
    Subject.MATHEMATICS: {
        LessonType.CONCEPT: [BookType.COURSE_BOOK],
        LessonType.PRACTICE: [BookType.COURSE_BOOK, BookType.ACTIVITY],
    }
}


def get_required_books(subject: Subject, lesson_type: LessonType) -> List[BookType]:
    """
    Get the list of book types required for a given subject and lesson type.
    
    Args:
        subject: The subject (English or Mathematics)
        lesson_type: The type of lesson to generate
    
    Returns:
        List of BookType values that should be used
    """
    subject_mapping = BOOK_MAPPING.get(subject, {})
    return subject_mapping.get(lesson_type, [])


def is_valid_lesson_type(subject: Subject, lesson_type: LessonType) -> bool:
    """
    Check if a lesson type is valid for the given subject.
    
    Args:
        subject: The subject
        lesson_type: The lesson type to validate
    
    Returns:
        True if the lesson type is valid for the subject
    """
    subject_mapping = BOOK_MAPPING.get(subject, {})
    return lesson_type in subject_mapping


def get_available_lesson_types(subject: Subject) -> List[LessonType]:
    """
    Get all available lesson types for a subject.
    
    Args:
        subject: The subject
    
    Returns:
        List of available LessonType values
    """
    subject_mapping = BOOK_MAPPING.get(subject, {})
    return list(subject_mapping.keys())


# Lesson type descriptions for UI
LESSON_TYPE_DESCRIPTIONS = {
    LessonType.READING: "Reading lesson using the Reading Book",
    LessonType.COMPREHENSION: "Comprehension lesson using the Activity Book",
    LessonType.GRAMMAR: "Grammar lesson using the Course Book",
    LessonType.CREATIVE_WRITING: "Creative writing using Course and Activity Books",
    LessonType.CONCEPT: "Mathematical concept lesson using the Course Book",
    LessonType.PRACTICE: "Practice lesson using Course Book and Activity Book",
}
