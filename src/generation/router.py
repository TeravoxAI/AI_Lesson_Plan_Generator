"""
Router - Context retrieval logic for lesson generation
Uses SOW matcher for lesson-based page retrieval from book references
"""
from typing import Dict, Any, List, Optional
from src.models import Subject, LessonType
from src.db.client import db
from src.generation.sow_matcher import (
    get_lesson_context_by_number,
    format_lesson_context_for_prompt,
    map_book_type_to_db
)


def normalize_grade(grade: str) -> str:
    """
    Normalize grade format to match database format.
    Converts "Grade 2" -> "2", "grade 3" -> "3", etc.
    If already a number, returns as-is.
    """
    grade_str = str(grade).strip()

    # If it starts with "Grade" or "grade", extract the number
    if grade_str.lower().startswith("grade"):
        # Remove "Grade" or "grade" and extract number
        import re
        match = re.search(r'\d+', grade_str)
        if match:
            return match.group(0)

    # If it's already just a number, return as-is
    if grade_str.isdigit():
        return grade_str

    # Otherwise return as-is (fallback)
    return grade_str


class ContextRouter:
    """Routes requests to appropriate content and retrieves context"""

    def __init__(self):
        self.db = db

    def retrieve_context(
        self,
        grade: str,
        subject: Subject,
        lesson_type: LessonType,
        page_start: int,  # This is actually lesson_number now
        page_end: Optional[int] = None,
        topic: Optional[str] = None,
        book_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all context needed for lesson generation.

        Flow:
        1. Find lesson in SOW by lesson_number
        2. Get book_references from that lesson
        3. Fetch textbook pages based on those references
        4. Format for LLM
        """
        lesson_number = page_start  # Rename for clarity

        # Normalize grade format for textbook lookups only
        # SOW uses "Grade 2", textbooks use "2"
        db_grade_textbooks = normalize_grade(grade)
        print(f"\n📚 [CONTEXT] Retrieving content for {subject.value} {grade}, Lesson {lesson_number}")

        context = {
            "grade": grade,
            "subject": subject.value,
            "lesson_type": lesson_type.value,
            "lesson_number": lesson_number,
            "book_content": [],
            "sow_strategy": None,
            "sow_context": None,
            "metadata": {
                "textbook_ids": [],
                "sow_entry_id": None,
                "books_fetched": []
            }
        }

        # Step 1: Fetch SOW and find the lesson (SOW uses original grade format "Grade 2")
        print(f"\n📋 [SOW] Finding lesson {lesson_number} in SOW...")
        sow_entries = db.get_sow_by_subject(subject.value, grade)

        if not sow_entries:
            print(f"   ⚠ No SOW entries found for {subject.value} {grade}")
            return context

        # Use the first SOW entry
        sow_data = sow_entries[0]
        context["metadata"]["sow_entry_id"] = sow_data.get("id")

        # Get extraction data
        extraction = sow_data.get("extraction", {})

        if not extraction:
            print(f"   ⚠ SOW entry has no extraction data")
            return context

        # Debug: Print SOW structure
        print(f"   🔍 SOW extraction keys: {list(extraction.keys())}")
        if "curriculum" in extraction:
            curriculum = extraction["curriculum"]
            print(f"   🔍 Curriculum has {len(curriculum.get('units', []))} units")
            if curriculum.get("units"):
                first_unit = curriculum["units"][0]
                print(f"   🔍 First unit has {len(first_unit.get('lessons', []))} lessons")
                if first_unit.get("lessons"):
                    first_lesson = first_unit["lessons"][0]
                    print(f"   🔍 First lesson has {len(first_lesson.get('lesson_plan_types', []))} lesson_plan_types")
                    if first_lesson.get("lesson_plan_types"):
                        types = [lpt.get("type") for lpt in first_lesson["lesson_plan_types"]]
                        print(f"   🔍 First lesson types: {types}")

        # Step 2: Get lesson context by lesson number
        print(f"   🔍 Looking for lesson_type: '{lesson_type.value}'")

        # First, get the lesson without filtering to see what types are available
        lesson_debug = get_lesson_context_by_number(
            sow_data=extraction,
            lesson_number=lesson_number,
            lesson_type=None  # No filter to see all types
        )

        if lesson_debug.get("found"):
            available_types = [lpt.get("type") for lpt in lesson_debug.get("lesson_plan_types", [])]
            print(f"   📋 Available lesson_plan_types in SOW: {available_types}")

        # Now get with the filter (uses partial matching)
        sow_context = get_lesson_context_by_number(
            sow_data=extraction,
            lesson_number=lesson_number,
            lesson_type=lesson_type.value
        )

        # Show what was matched after filtering
        if sow_context.get("found"):
            matched_types = [lpt.get("type") for lpt in sow_context.get("lesson_plan_types", [])]
            print(f"   ✓ Matched lesson_plan_types: {matched_types}")

        context["sow_context"] = sow_context

        if not sow_context.get("found"):
            print(f"   ⚠ No lesson {lesson_number} found in SOW")
            context["sow_strategy"] = "No SOW lesson found. Generate based on general guidelines."
            return context

        print(f"   ✓ Found: {sow_context.get('unit')} - {sow_context.get('lesson_title')}")

        # Step 3: Get book references from the lesson
        book_refs = sow_context.get("book_references", [])
        print(f"   📖 Book references found: {len(book_refs)}")
        if book_refs:
            for ref in book_refs:
                print(f"      - {ref.get('book_type')}: pages {ref.get('pages')}")
        else:
            print(f"      ⚠ No book references extracted (likely lesson_type mismatch)")
            print(f"      💡 Hint: Check if SOW lesson_plan_types match the requested type '{lesson_type.value}'")

        # Step 4: Fetch textbook pages for each book reference
        all_content = []

        for ref in book_refs:
            book_type_code = ref.get("book_type", "").upper()
            pages = ref.get("pages", [])

            if not book_type_code or not pages:
                continue

            print(f"     - {book_type_code}: pages {pages}")
            print(f"       🔍 Searching DB: grade='{db_grade_textbooks}', subject='{subject.value}', book_tag='{book_type_code}'")

            # Try to find the book by book_tag first, then by book_type (use normalized grade for textbooks)
            book = db.get_textbook_by_tag(db_grade_textbooks, subject.value, book_type_code)

            if not book:
                # Fallback: map short code to db book_type
                db_book_type = map_book_type_to_db(book_type_code)
                book = db.get_textbook(db_grade_textbooks, subject.value, db_book_type)

            if not book:
                print(f"       ⚠ Book not found for {book_type_code}")
                continue

            # Fetch specific pages
            fetched_pages = db.get_pages_by_numbers(book["id"], pages)

            if fetched_pages:
                context["metadata"]["textbook_ids"].append(book["id"])
                context["metadata"]["books_fetched"].append({
                    "book_type": book_type_code,
                    "book_id": book["id"],
                    "title": book.get("title", ""),
                    "pages_requested": pages,
                    "pages_found": len(fetched_pages)
                })

                for page in fetched_pages:
                    page_no = page.get("page_no") or page.get("book_page_no")
                    content_text = page.get("book_text") or page.get("content", "")

                    all_content.append({
                        "book_type": book.get("book_type", ""),
                        "book_type_short": book_type_code,
                        "title": book.get("title", ""),
                        "page_no": page_no,
                        "content": content_text,
                        "book_id": book["id"]
                    })

                    # Show preview of fetched content
                    content_preview = content_text[:150].replace('\n', ' ') if content_text else '[No content]'
                    print(f"         Page {page_no}: {content_preview}...")

                print(f"       ✓ Fetched {len(fetched_pages)} pages from '{book.get('title', 'Unknown')}'")
            else:
                print(f"       ⚠ No pages found for {book_type_code} pages {pages}")

        context["book_content"] = all_content
        context["sow_strategy"] = format_lesson_context_for_prompt(sow_context)

        # Summary
        print(f"\n   📝 Context Summary:")
        print(f"      - Lesson: {sow_context.get('lesson_title')}")
        print(f"      - Book pages loaded: {len(all_content)}")
        if all_content:
            # Show which books were used
            books_used = {}
            for item in all_content:
                book_key = item.get('book_type_short', 'Unknown')
                if book_key not in books_used:
                    books_used[book_key] = []
                books_used[book_key].append(item.get('page_no', '?'))
            print(f"      - Books used: {', '.join([f'{k} (pages {books_used[k]})' for k in books_used])}")
        print(f"      - SLOs: {len(sow_context.get('student_learning_outcomes', []))}")
        print(f"      - Skills: {sow_context.get('skills', [])}")

        # Print complete SOW extraction being used
        print("\n" + "="*80)
        print("📋 COMPLETE SOW EXTRACTION USED IN PROMPT:")
        print("="*80)
        print(context["sow_strategy"])
        print("="*80)

        # Print complete book OCR content being used
        print("\n" + "="*80)
        print("📖 COMPLETE BOOK OCR CONTENT USED IN PROMPT:")
        print("="*80)
        formatted_book_content = self.format_book_content(all_content)
        print(formatted_book_content)
        print("="*80 + "\n")

        return context

    def format_book_content(self, book_content: List[Dict[str, Any]]) -> str:
        """Format book content into a readable string for the prompt"""
        if not book_content:
            return "No textbook content found. Please upload the required textbook first."

        formatted_parts = []

        # Group by book type
        by_book = {}
        for page in book_content:
            bt = page.get('book_type_short') or page.get('book_type', '').upper()
            if bt not in by_book:
                by_book[bt] = []
            by_book[bt].append(page)

        for book_type, pages in by_book.items():
            # Sort pages by page number
            pages.sort(key=lambda p: p.get('page_no', 0))

            title = pages[0].get('title', '') if pages else ''
            formatted_parts.append(f"### {book_type} - {title}")

            for page in pages:
                page_no = page.get('page_no', '?')
                content = page.get('content', '')

                if content:
                    formatted_parts.append(f"\n**Page {page_no}:**\n{content}")
                else:
                    formatted_parts.append(f"\n**Page {page_no}:** *No content on this page.*")

        return "\n\n---\n\n".join(formatted_parts)


# Singleton instance
router = ContextRouter()
