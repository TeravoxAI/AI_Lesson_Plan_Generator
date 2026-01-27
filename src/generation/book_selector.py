"""
Book Selector - Lesson type definitions and validation
"""
from typing import List
from src.models import LessonType, Subject, BookType


# Define available lesson types per subject (in order as per design)
LESSON_TYPES_BY_SUBJECT = {
    Subject.ENGLISH: [
        LessonType.RECALL,
        LessonType.VOCABULARY,
        LessonType.LISTENING,
        LessonType.READING,
        LessonType.READING_COMPREHENSION,
        LessonType.GRAMMAR,
        LessonType.ORAL_SPEAKING,
        LessonType.CREATIVE_WRITING,
    ],
    Subject.MATHEMATICS: [
        LessonType.CONCEPT,
        LessonType.PRACTICE,
    ]
}


# Default book mapping (used as fallback when SOW doesn't specify books)
BOOK_MAPPING = {
    Subject.ENGLISH: {
        LessonType.RECALL: [BookType.LEARNERS],
        LessonType.VOCABULARY: [BookType.LEARNERS, BookType.ACTIVITY],
        LessonType.LISTENING: [BookType.LEARNERS],
        LessonType.READING: [BookType.READING],
        LessonType.READING_COMPREHENSION: [BookType.LEARNERS, BookType.ACTIVITY],
        LessonType.GRAMMAR: [BookType.LEARNERS, BookType.ACTIVITY],
        LessonType.ORAL_SPEAKING: [BookType.LEARNERS],
        LessonType.CREATIVE_WRITING: [BookType.LEARNERS, BookType.ACTIVITY],
    },
    Subject.MATHEMATICS: {
        LessonType.CONCEPT: [BookType.COURSE_BOOK],
        LessonType.PRACTICE: [BookType.COURSE_BOOK, BookType.WORKBOOK],
    }
}


def get_required_books(subject: Subject, lesson_type: LessonType) -> List[BookType]:
    """
    Get the list of book types required for a given subject and lesson type.
    This is a fallback when SOW doesn't specify book references.

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
    valid_types = LESSON_TYPES_BY_SUBJECT.get(subject, [])
    return lesson_type in valid_types


def get_available_lesson_types(subject: Subject) -> List[LessonType]:
    """
    Get all available lesson types for a subject (in display order).

    Args:
        subject: The subject

    Returns:
        List of available LessonType values in order
    """
    return LESSON_TYPES_BY_SUBJECT.get(subject, [])


# Lesson type descriptions for UI
LESSON_TYPE_DESCRIPTIONS = {
    LessonType.RECALL: "Recall and review previous learning",
    LessonType.VOCABULARY: "Vocabulary building and word study",
    LessonType.LISTENING: "Listening comprehension activities",
    LessonType.READING: "Reading fluency and expression",
    LessonType.READING_COMPREHENSION: "Reading comprehension and analysis",
    LessonType.GRAMMAR: "Grammar rules and practice",
    LessonType.ORAL_SPEAKING: "Oral communication and speaking practice",
    LessonType.CREATIVE_WRITING: "Creative writing and composition",
    LessonType.CONCEPT: "Mathematical concept introduction",
    LessonType.PRACTICE: "Mathematical practice and problem solving",
}
