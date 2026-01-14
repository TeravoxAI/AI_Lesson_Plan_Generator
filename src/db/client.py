"""
Database Client - Supabase Operations
"""
import os
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class DatabaseClient:
    """Supabase database operations wrapper"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client"""
        project_url = os.getenv("SUPABASE_PROJECT_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if project_url and anon_key:
            self.client = create_client(project_url, anon_key)
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.client is not None
    
    # ============= Textbook Operations =============
    
    def insert_textbook(
        self, 
        grade_level: str, 
        subject: str, 
        book_type: str, 
        title: str
    ) -> Optional[int]:
        """Insert a new textbook and return its ID"""
        if not self.client:
            return None
        
        result = self.client.table("textbooks").insert({
            "grade_level": grade_level,
            "subject": subject,
            "book_type": book_type,
            "title": title
        }).execute()
        
        if result.data:
            return result.data[0]["id"]
        return None
    
    def get_textbook(
        self, 
        grade_level: str, 
        subject: str, 
        book_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get textbook by criteria"""
        if not self.client:
            return None
        
        result = self.client.table("textbooks").select("*").eq(
            "grade_level", grade_level
        ).eq(
            "subject", subject
        ).eq(
            "book_type", book_type
        ).execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def list_textbooks(self) -> List[Dict[str, Any]]:
        """List all textbooks"""
        if not self.client:
            return []
        
        result = self.client.table("textbooks").select("*").execute()
        return result.data or []
    
    # ============= Page Operations =============
    
    def insert_page(
        self, 
        book_id: int, 
        page_number: int, 
        content_text: str,
        image_summary: str = "",
        has_exercises: bool = False,
        exercise_count: int = 0
    ) -> Optional[int]:
        """Insert a page and return its ID"""
        if not self.client:
            return None
        
        result = self.client.table("textbook_pages").insert({
            "book_id": book_id,
            "page_number": page_number,
            "content_text": content_text,
            "image_summary": image_summary,
            "has_exercises": has_exercises,
            "exercise_count": exercise_count
        }).execute()
        
        if result.data:
            return result.data[0]["id"]
        return None
    
    def get_pages_by_range(
        self, 
        book_id: int, 
        page_start: int, 
        page_end: int
    ) -> List[Dict[str, Any]]:
        """Get pages within a range"""
        if not self.client:
            return []
        
        result = self.client.table("textbook_pages").select("*").eq(
            "book_id", book_id
        ).gte(
            "page_number", page_start
        ).lte(
            "page_number", page_end
        ).order("page_number").execute()
        
        return result.data or []
    
    def get_pages_by_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all pages for a book"""
        if not self.client:
            return []
        
        result = self.client.table("textbook_pages").select("*").eq(
            "book_id", book_id
        ).order("page_number").execute()
        
        return result.data or []
    
    # ============= SOW Operations =============
    
    def insert_sow_entry(
        self,
        grade_level: str,
        subject: str,
        term: str,
        topic_name: str,
        mapped_page_numbers: List[int],
        teaching_strategy: str,
        resources_text: str = "",
        afl_strategy: str = "",
        activities: str = ""
    ) -> Optional[int]:
        """Insert a SOW entry and return its ID"""
        if not self.client:
            return None
        
        result = self.client.table("sow_entries").insert({
            "grade_level": grade_level,
            "subject": subject,
            "term": term,
            "topic_name": topic_name,
            "mapped_page_numbers": mapped_page_numbers,
            "teaching_strategy": teaching_strategy,
            "resources_text": resources_text,
            "afl_strategy": afl_strategy,
            "activities": activities
        }).execute()
        
        if result.data:
            return result.data[0]["id"]
        return None
    
    def get_sow_by_pages(
        self, 
        subject: str, 
        grade_level: str, 
        page_number: int
    ) -> List[Dict[str, Any]]:
        """Get SOW entries that contain the given page number (for Maths)"""
        if not self.client:
            return []
        
        # Use PostgREST 'cs' (contains) filter for array column
        result = self.client.table("sow_entries").select("*").eq(
            "subject", subject
        ).eq(
            "grade_level", grade_level
        ).contains(
            "mapped_page_numbers", [page_number]
        ).execute()
        
        return result.data or []
    
    def get_sow_by_topic(
        self, 
        subject: str, 
        grade_level: str, 
        topic: str
    ) -> List[Dict[str, Any]]:
        """Get SOW entries matching topic name (for English)"""
        if not self.client:
            return []
        
        result = self.client.table("sow_entries").select("*").eq(
            "subject", subject
        ).eq(
            "grade_level", grade_level
        ).ilike(
            "topic_name", f"%{topic}%"
        ).execute()
        
        return result.data or []
    
    def list_sow_entries(
        self, 
        subject: Optional[str] = None, 
        grade_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List SOW entries with optional filtering"""
        if not self.client:
            return []
        
        query = self.client.table("sow_entries").select("*")
        
        if subject:
            query = query.eq("subject", subject)
        if grade_level:
            query = query.eq("grade_level", grade_level)
        
        result = query.execute()
        return result.data or []


# Singleton instance
db = DatabaseClient()
