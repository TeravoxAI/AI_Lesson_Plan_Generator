"""
Router - Context retrieval logic for lesson generation
Uses SOW matcher for intelligent page-to-lesson mapping
"""
import json
from typing import Dict, Any, List, Optional
from src.models import Subject, LessonType, BookType
from src.db.client import db
from src.generation.book_selector import get_required_books
from src.generation.sow_matcher import (
    get_lesson_context_for_llm,
    format_sow_context_for_prompt,
    map_book_type_to_db,
    map_db_to_book_type
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
        page_start: int,
        page_end: Optional[int] = None,
        topic: Optional[str] = None,
        book_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all context needed for lesson generation.
        
        Matches textbook pages with SOW lessons using book type awareness.
        """
        if page_end is None:
            page_end = page_start
        
        context = {
            "grade": grade,
            "subject": subject.value,
            "lesson_type": lesson_type.value,
            "page_range": f"{page_start}-{page_end}",
            "book_content": [],
            "sow_strategy": None,
            "sow_context": None,
            "metadata": {
                "textbook_id": None,
                "sow_entry_id": None
            }
        }
        
        # Get required books for this lesson type
        required_books = get_required_books(subject, lesson_type)
        print(f"\n📚 [CONTEXT] Retrieving content for {subject.value} {grade}, pages {page_start}-{page_end}")
        print(f"   Required books: {[b.value for b in required_books]}")
        
        # Fetch content from each required book
        all_content = []
        textbook_id = None
        primary_book_type = book_type or "LB"  # Default to Learner's Book
        
        for bt in required_books:
            book = db.get_textbook(grade, subject.value, bt.value)
            if book:
                textbook_id = book["id"]
                
                # Get pages in the requested range
                pages = db.get_textbook_pages(book["id"], page_start, page_end)
                
                for page in pages:
                    all_content.append({
                        "book_type": bt.value,
                        "book_type_short": map_db_to_book_type(bt.value),
                        "title": book.get("title", ""),
                        "page_no": page.get("page_no") or page.get("book_page_no"),
                        "content": page.get("book_text") or page.get("content", ""),
                        "book_id": book["id"]
                    })
                
                # Use first book type found as primary
                if not book_type and all_content:
                    primary_book_type = map_db_to_book_type(bt.value)
        
        context["book_content"] = all_content
        context["metadata"]["textbook_id"] = textbook_id
        print(f"   ✓ Book content extracted: {len(all_content)} pages found")
        if all_content:
            page_nums = [p.get('page_no') for p in all_content]
            print(f"   Page numbers: {page_nums}")
        
        # Fetch SOW and match by page/book type
        print(f"\n📋 [SOW] Matching SOW entries for {subject.value} {grade}...")
        sow_entries = db.get_sow_by_subject(subject.value, grade)
        
        if sow_entries:
            # Use the first SOW entry (or could combine multiple)
            sow_data = sow_entries[0]
            context["metadata"]["sow_entry_id"] = sow_data.get("id")
            
            # Get extraction data
            extraction = sow_data.get("extraction", {})
            
            if extraction:
                # Use the new matcher to find relevant lessons
                sow_context = get_lesson_context_for_llm(
                    sow_data={"extraction": extraction},
                    grade=grade,
                    subject=subject.value,
                    book_type=primary_book_type,
                    page_start=page_start,
                    page_end=page_end
                )
                
                context["sow_context"] = sow_context
                context["sow_strategy"] = format_sow_context_for_prompt(sow_context)
                
                if sow_context.get("found"):
                    matched_lessons = sow_context.get("matching_lessons", [])
                    print(f"   ✓ SOW matched: {len(matched_lessons)} lesson(s) found")
                    for ml in matched_lessons:
                        print(f"     - Lesson {ml.get('lesson_number')}: {ml.get('lesson_title')[:50]}...")
                else:
                    print(f"   ⚠ No matching SOW lessons found for pages {page_start}-{page_end}")
        
        context["metadata"]["books_used"] = [b.value for b in required_books]
        context["metadata"]["pages_found"] = len(all_content)
        context["metadata"]["sow_found"] = context["sow_context"].get("found") if context["sow_context"] else False
        
        return context
    
    def format_book_content(self, book_content: List[Dict[str, Any]]) -> str:
        """Format book content into a readable string for the prompt"""
        if not book_content:
            return "No textbook content found. Please upload the required textbook first."
        
        formatted_parts = []
        
        for page in book_content:
            book_type = page.get('book_type_short') or page.get('book_type', '').upper()
            page_no = page.get('page_no', '?')
            title = page.get('title', '')
            
            header = f"**{book_type}** - Page {page_no}"
            if title:
                header += f" ({title})"
            
            content = page.get('content', '')
            if content:
                parts = [header, content]
            else:
                parts = [header, "*No content on this page.*"]
            
            formatted_parts.append("\n".join(parts))
        
        return "\n\n---\n\n".join(formatted_parts)


# Singleton instance
router = ContextRouter()

