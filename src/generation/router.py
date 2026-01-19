"""
Router - Context retrieval logic for lesson generation
Updated for JSONB pages storage
"""
import json
from typing import Dict, Any, List, Optional
from src.models import Subject, LessonType, BookType
from src.db.client import db
from src.generation.book_selector import get_required_books


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
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all context needed for lesson generation.
        
        Fetches pages from JSONB storage format.
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
            "metadata": {
                "textbook_id": None,
                "sow_entry_id": None
            }
        }
        
        # Get required books for this lesson type
        required_books = get_required_books(subject, lesson_type)
        
        # Fetch content from each required book
        all_content = []
        textbook_id = None
        
        for book_type in required_books:
            book = db.get_textbook(grade, subject.value, book_type.value)
            if book:
                textbook_id = book["id"]
                
                # Get pages in the requested range
                pages = db.get_textbook_pages(book["id"], page_start, page_end)
                
                for page in pages:
                    all_content.append({
                        "book_type": book_type.value,
                        "title": book.get("title", ""),
                        "page_no": page.get("page_no"),
                        "content": page.get("book_text", ""),
                        "book_id": book["id"]
                    })
        
        context["book_content"] = all_content
        context["metadata"]["textbook_id"] = textbook_id
        
        # Fetch SOW based on subject strategy
        sow_entries = []
        if subject == Subject.MATHEMATICS:
            # Maths: Page-First approach
            sow_entries = db.get_sow_by_pages(subject.value, grade, page_start)
        else:
            # English: Topic-First or Page-based
            if topic:
                sow_entries = db.get_sow_by_topic(subject.value, grade, topic)
            else:
                sow_entries = db.get_sow_by_pages(subject.value, grade, page_start)
        
        if sow_entries:
            context["sow_strategy"] = self._format_sow(sow_entries)
            context["metadata"]["sow_entry_id"] = sow_entries[0].get("id")
        
        context["metadata"]["books_used"] = [b.value for b in required_books]
        context["metadata"]["pages_found"] = len(all_content)
        context["metadata"]["sow_entries_found"] = len(sow_entries) if sow_entries else 0
        
        return context
    
    def _format_sow(self, sow_entries: List[Dict[str, Any]]) -> str:
        """Format SOW entries into a readable string"""
        formatted_parts = []
        
        for entry in sow_entries:
            parts = [f"**Topic:** {entry.get('topic_name', 'N/A')}"]
            
            if entry.get('teaching_strategy'):
                parts.append(f"**Teaching Strategy:** {entry['teaching_strategy']}")
            
            if entry.get('activities'):
                parts.append(f"**Activities:** {entry['activities']}")
            
            if entry.get('afl_strategy'):
                parts.append(f"**AFL:** {entry['afl_strategy']}")
            
            if entry.get('resources_text'):
                parts.append(f"**Resources:** {entry['resources_text']}")
            
            formatted_parts.append("\n".join(parts))
        
        return "\n\n---\n\n".join(formatted_parts)
    
    def format_book_content(self, book_content: List[Dict[str, Any]]) -> str:
        """Format book content into a readable string for the prompt"""
        if not book_content:
            return "No textbook content found. Please upload the required textbook first."
        
        formatted_parts = []
        
        for page in book_content:
            parts = [f"**{page['book_type'].upper()}** - Page {page.get('page_no', '?')}"]
            if page.get('title'):
                parts[0] += f" ({page['title']})"
            
            content = page.get('content', '')
            if content:
                parts.append(content)
            else:
                parts.append("*No content on this page.*")
            
            formatted_parts.append("\n".join(parts))
        
        return "\n\n---\n\n".join(formatted_parts)


# Singleton instance
router = ContextRouter()
