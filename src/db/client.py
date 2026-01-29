"""
Database Client - Supabase Operations (Updated for simplified schema)
"""
import os
import json
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
        title: str,
        pages: List[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Insert a new textbook with its OCR pages.

        Args:
            pages: List of dicts with format [{"book_text": "...", "page_no": 1}, ...]
        """
        if not self.client:
            return None

        result = self.client.table("textbooks").insert({
            "grade_level": grade_level,
            "subject": subject,
            "book_type": book_type,
            "title": title,
            "content_text": json.dumps(pages or [])
        }).execute()

        if result.data:
            return result.data[0]["id"]
        return None

    def update_textbook_pages(self, book_id: int, pages: List[Dict[str, Any]]) -> bool:
        """
        Update the pages of a textbook.

        Args:
            pages: List of dicts with format [{"book_text": "...", "page_no": 1}, ...]
        """
        if not self.client:
            return False

        result = self.client.table("textbooks").update({
            "content_text": json.dumps(pages)
        }).eq("id", book_id).execute()

        return bool(result.data)

    def get_textbook_pages(self, book_id: int, page_start: int, page_end: int) -> List[Dict[str, Any]]:
        """
        Get specific pages from a textbook.

        Returns pages within the specified range.
        """
        book = self.get_textbook_by_id(book_id)
        if not book or not book.get("content_text"):
            return []

        pages = book["content_text"]
        if isinstance(pages, str):
            pages = json.loads(pages)

        return [
            p for p in pages
            if page_start <= p.get("page_no", 0) <= page_end or page_start <= p.get("book_page_no", 0) <= page_end
        ]

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

    def get_textbook_by_tag(
        self,
        grade_level: str,
        subject: str,
        book_tag: str
    ) -> Optional[Dict[str, Any]]:
        """Get textbook by book_tag (short code like LB, AB, ORT)"""
        if not self.client:
            return None

        result = self.client.table("textbooks").select("*").eq(
            "grade_level", grade_level
        ).eq(
            "subject", subject
        ).eq(
            "book_tag", book_tag
        ).execute()

        if result.data:
            return result.data[0]
        return None

    def get_pages_by_numbers(
        self,
        book_id: int,
        page_numbers: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Get specific pages by their page numbers.

        Args:
            book_id: The textbook ID
            page_numbers: List of specific page numbers to fetch

        Returns:
            List of page dicts with book_text and page_no
        """
        book = self.get_textbook_by_id(book_id)
        if not book or not book.get("content_text"):
            return []

        pages = book["content_text"]
        if isinstance(pages, str):
            import json
            pages = json.loads(pages)

        page_set = set(page_numbers)
        return [
            p for p in pages
            if p.get("page_no") in page_set or p.get("book_page_no") in page_set
        ]

    def get_textbook_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get textbook by ID"""
        if not self.client:
            return None

        result = self.client.table("textbooks").select("*").eq("id", book_id).execute()

        if result.data:
            return result.data[0]
        return None

    def list_textbooks(self) -> List[Dict[str, Any]]:
        """List all textbooks"""
        if not self.client:
            return []

        result = self.client.table("textbooks").select("*").execute()
        return result.data or []

    def delete_textbook(self, book_id: int) -> bool:
        """Delete a textbook"""
        if not self.client:
            return False

        result = self.client.table("textbooks").delete().eq("id", book_id).execute()
        return bool(result.data)

    # ============= SOW Operations =============

    def insert_sow_entry(
        self,
        grade_level: str,
        subject: str,
        term: str,
        title: str,
        extraction: Dict[str, Any]
    ) -> Optional[int]:
        """Insert a SOW entry with complete extraction JSON and return its ID"""
        if not self.client:
            return None

        result = self.client.table("sow_entries").insert({
            "grade_level": grade_level,
            "subject": subject,
            "term": term,
            "title": title,
            "extraction": extraction
        }).execute()

        if result.data:
            return result.data[0]["id"]
        return None

    def get_sow_by_subject(
        self,
        subject: str,
        grade_level: str
    ) -> List[Dict[str, Any]]:
        """Get all SOW entries for a subject/grade"""
        if not self.client:
            return []

        result = self.client.table("sow_entries").select("*").eq(
            "subject", subject
        ).eq(
            "grade_level", grade_level
        ).execute()

        return result.data or []

    def get_sow_by_id(self, sow_id: int) -> Optional[Dict[str, Any]]:
        """Get a SOW entry by ID"""
        if not self.client:
            return None

        result = self.client.table("sow_entries").select("*").eq("id", sow_id).execute()

        if result.data:
            return result.data[0]
        return None

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

    # ============= Lesson Plan Operations =============

    def insert_lesson_plan(
        self,
        grade_level: str,
        subject: str,
        lesson_type: str,
        page_start: int,
        page_end: int,
        topic: Optional[str],
        lesson_plan: Dict[str, Any],
        textbook_id: Optional[int] = None,
        sow_entry_id: Optional[int] = None,
        generation_time: Optional[float] = None,
        cost: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None
    ) -> Optional[int]:
        """Insert a generated lesson plan with usage metrics stored in metadata and return its ID"""
        if not self.client:
            return None

        # Build metadata object with usage metrics
        metadata = {}
        if generation_time is not None:
            metadata["generation_time"] = generation_time
        if cost is not None:
            metadata["cost"] = cost
        if input_tokens is not None:
            metadata["input_tokens"] = input_tokens
        if output_tokens is not None:
            metadata["output_tokens"] = output_tokens
        if total_tokens is not None:
            metadata["total_tokens"] = total_tokens

        data = {
            "grade_level": grade_level,
            "subject": subject,
            "lesson_type": lesson_type,
            "page_start": page_start,
            "page_end": page_end,
            "topic": topic,
            "lesson_plan": json.dumps(lesson_plan) if isinstance(lesson_plan, dict) else lesson_plan,
            "textbook_id": textbook_id,
            "sow_entry_id": sow_entry_id,
            "metadata": json.dumps(metadata) if metadata else json.dumps({})
        }

        result = self.client.table("lesson_plans").insert(data).execute()

        if result.data:
            return result.data[0]["id"]
        return None

    def get_lesson_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get a lesson plan by ID"""
        if not self.client:
            return None

        result = self.client.table("lesson_plans").select("*").eq("id", plan_id).execute()

        if result.data:
            return result.data[0]
        return None

    # ============= User Profile Operations =============

    def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Create a user profile linked to the auth user.
        """
        if not self.client:
            return False

        # Add ID to data
        data = profile_data.copy()
        data["id"] = user_id

        try:
            result = self.client.table("users").insert(data).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error creating user profile: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user profile by ID.
        """
        if not self.client:
            return None

        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            return None

    def update_lesson_plan(self, plan_id: int, html_content: str) -> bool:
        """Update the HTML content of a lesson plan"""
        if not self.client:
            return False

        try:
            from datetime import datetime, timezone

            # Update the lesson_plan JSON field with new HTML content
            data = {
                "lesson_plan": json.dumps({"html_content": html_content}),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.client.table("lesson_plans").update(data).eq("id", plan_id).execute()

            return result.data is not None and len(result.data) > 0
        except Exception as e:
            print(f"Error updating lesson plan: {e}")
            return False

    def list_lesson_plans(
        self,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        lesson_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List lesson plans with optional filtering"""
        if not self.client:
            return []

        try:
            query = self.client.table("lesson_plans").select("*")

            if subject:
                query = query.eq("subject", subject)
            if grade_level:
                query = query.eq("grade_level", grade_level)
            if lesson_type:
                query = query.eq("lesson_type", lesson_type)

            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            # Table may not exist yet
            print(f"Error listing lesson plans: {e}")
            return []


# Singleton instance
db = DatabaseClient()
