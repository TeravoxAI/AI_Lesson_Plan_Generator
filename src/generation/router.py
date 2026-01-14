"""
Router - Context retrieval logic for lesson generation
"""
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
        
        This implements the "Router" algorithm:
        - Maths (Page-First): Uses page range to query both books and SOW
        - English (Topic-First): Can use topic OR pages
        
        Args:
            grade: Grade level (e.g., "Grade 2")
            subject: Subject enum
            lesson_type: Type of lesson to generate
            page_start: Starting page number
            page_end: Ending page number (defaults to page_start)
            topic: Optional topic string for English
        
        Returns:
            Dict with book_content, sow_strategy, and metadata
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
            "metadata": {}
        }
        
        # Get required books for this lesson type
        required_books = get_required_books(subject, lesson_type)
        
        # Fetch content from each required book
        all_content = []
        for book_type in required_books:
            book_content = self._fetch_book_content(
                grade, subject.value, book_type.value, page_start, page_end
            )
            if book_content:
                all_content.extend(book_content)
        
        context["book_content"] = all_content
        
        # Fetch SOW based on subject strategy
        if subject == Subject.MATHEMATICS:
            # Maths: Page-First approach
            sow_entries = db.get_sow_by_pages(subject.value, grade, page_start)
        else:
            # English: Topic-First or Page-based
            if topic:
                sow_entries = db.get_sow_by_topic(subject.value, grade, topic)
            else:
                # Fallback to page-based
                sow_entries = db.get_sow_by_pages(subject.value, grade, page_start)
        
        if sow_entries:
            # Use the first matching entry (or combine if multiple)
            context["sow_strategy"] = self._format_sow(sow_entries)
        
        # Add metadata
        context["metadata"] = {
            "books_used": [b.value for b in required_books],
            "pages_found": len(all_content),
            "sow_entries_found": len(sow_entries) if sow_entries else 0
        }
        
        return context
    
    def _fetch_book_content(
        self,
        grade: str,
        subject: str,
        book_type: str,
        page_start: int,
        page_end: int
    ) -> List[Dict[str, Any]]:
        """Fetch content from a specific book"""
        # First, get the book ID
        book = db.get_textbook(grade, subject, book_type)
        if not book:
            return []
        
        # Then fetch pages
        pages = db.get_pages_by_range(book["id"], page_start, page_end)
        
        return [
            {
                "book_type": book_type,
                "page_number": p["page_number"],
                "content": p["content_text"],
                "images": p.get("image_summary", "")
            }
            for p in pages
        ]
    
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
            return "No textbook content found for the specified pages."
        
        formatted_parts = []
        
        for page in book_content:
            parts = [f"**{page['book_type'].upper()} - Page {page['page_number']}**"]
            parts.append(page['content'])
            
            if page.get('images'):
                parts.append(f"\n*Visual elements:* {page['images']}")
            
            formatted_parts.append("\n".join(parts))
        
        return "\n\n---\n\n".join(formatted_parts)


# Singleton instance
router = ContextRouter()
