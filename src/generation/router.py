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

        print(f"\n📚 [CONTEXT] Retrieving content for {subject.value} {grade}, Lesson {lesson_number}")

        # Step 1: Fetch SOW and find the lesson
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

        # Step 2: Get lesson context by lesson number
        sow_context = get_lesson_context_by_number(
            sow_data=extraction,
            lesson_number=lesson_number,
            lesson_type=lesson_type.value
        )

        context["sow_context"] = sow_context

        if not sow_context.get("found"):
            print(f"   ⚠ No lesson {lesson_number} found in SOW")
            context["sow_strategy"] = "No SOW lesson found. Generate based on general guidelines."
            return context

        print(f"   ✓ Found: {sow_context.get('unit')} - {sow_context.get('lesson_title')}")

        # Step 3: Get book references from the lesson
        book_refs = sow_context.get("book_references", [])
        print(f"   📖 Book references found: {len(book_refs)}")

        # Step 4: Fetch textbook pages for each book reference
        all_content = []

        for ref in book_refs:
            book_type_code = ref.get("book_type", "").upper()
            pages = ref.get("pages", [])
            book_name = ref.get("book_name", "")

            if not book_type_code or not pages:
                continue

            print(f"     - {book_type_code}: pages {pages}")

            # Try to find the book by book_tag first, then by book_type
            book = db.get_textbook_by_tag(grade, subject.value, book_type_code)

            if not book:
                # Fallback: map short code to db book_type
                db_book_type = map_book_type_to_db(book_type_code)
                book = db.get_textbook(grade, subject.value, db_book_type)

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
                    all_content.append({
                        "book_type": book.get("book_type", ""),
                        "book_type_short": book_type_code,
                        "title": book.get("title", ""),
                        "page_no": page.get("page_no") or page.get("book_page_no"),
                        "content": page.get("book_text") or page.get("content", ""),
                        "book_id": book["id"]
                    })

                print(f"       ✓ Fetched {len(fetched_pages)} pages from '{book.get('title', 'Unknown')}'")
            else:
                print(f"       ⚠ No pages found for {book_type_code} pages {pages}")

        context["book_content"] = all_content
        context["sow_strategy"] = format_lesson_context_for_prompt(sow_context)

        # Summary
        print(f"\n   📝 Context Summary:")
        print(f"      - Lesson: {sow_context.get('lesson_title')}")
        print(f"      - Book pages loaded: {len(all_content)}")
        print(f"      - SLOs: {len(sow_context.get('student_learning_outcomes', []))}")
        print(f"      - Skills: {sow_context.get('skills', [])}")

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
