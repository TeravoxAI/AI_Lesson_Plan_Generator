"""
Router - Context retrieval logic for lesson generation
Uses SOW matcher for lesson-based page retrieval from book references
"""
from typing import Dict, Any, List, Optional
from src.models import Subject, LessonType
from src.db.client import db
from src.generation.sow_matcher import (
    get_lesson_context_by_number,
    get_lesson_sections_summary,
    format_lesson_context_for_prompt,
    map_book_type_to_db,
    # Math functions
    get_math_units,
    get_math_unit_by_number,
    format_math_unit_for_prompt,
    parse_page_range
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
        lesson_type: Optional[LessonType] = None,
        page_start: int = 1,
        page_end: Optional[int] = None,
        topic: Optional[str] = None,
        book_type: Optional[str] = None,
        lb_pages: Optional[str] = None,
        ab_pages: Optional[str] = None,
        ort_pages: Optional[str] = None,
        selected_sections: Optional[Dict] = None,  # NEW: structured section selection
        exercises: Optional[str] = None             # LEGACY
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
            "lesson_type": lesson_type.value if lesson_type else None,
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

        # Debug: Print full SOW entry structure
        print(f"\n   📄 [DEBUG] Full SOW entry ID: {sow_data.get('id')}")
        print(f"   📄 [DEBUG] SOW subject: '{sow_data.get('subject')}'")
        print(f"   📄 [DEBUG] SOW grade_level: '{sow_data.get('grade_level')}'")
        print(f"   📄 [DEBUG] SOW file_name: {sow_data.get('file_name')}")

        import json
        extraction_preview = json.dumps(extraction, indent=2)[:1000]  # First 1000 chars
        print(f"   📄 [DEBUG] Extraction preview:\n{extraction_preview}...")
        print()

        # Debug: Print SOW structure
        print(f"   🔍 SOW extraction keys: {list(extraction.keys())}")
        if "curriculum" in extraction:
            curriculum = extraction["curriculum"]
            print(f"   🔍 Curriculum has {len(curriculum.get('units', []))} units")
            if curriculum.get("units"):
                first_unit = curriculum["units"][0]
                print(f"   🔍 First unit: {first_unit.get('unit_number')} '{first_unit.get('unit_title')}'")
                print(f"   🔍 First unit has {len(first_unit.get('lessons', []))} lessons")
                if first_unit.get("lessons"):
                    first_lesson = first_unit["lessons"][0]
                    lb_ab = first_lesson.get("lb_ab", {})
                    ort = first_lesson.get("ort", {})
                    print(f"   🔍 First lesson: Lesson {first_lesson.get('lesson_number')} '{first_lesson.get('lesson_title')}'")
                    print(f"   🔍 lb_ab teaching_sequence steps: {len(lb_ab.get('teaching_sequence', []))}")
                    print(f"   🔍 ort pages: {ort.get('pages', [])}")

        # Step 2: Parse user-supplied page strings
        lb_page_list = parse_page_range(lb_pages) if lb_pages else []
        ab_page_list = parse_page_range(ab_pages) if ab_pages else []
        ort_page_list = parse_page_range(ort_pages) if ort_pages else []

        has_lb_ab = bool(lb_pages or ab_pages)
        has_ort = bool(ort_pages)

        lt_value = lesson_type.value if lesson_type else None
        print(f"   🔍 Looking for lesson_type: '{lt_value}'")
        print(f"   📄 User pages — LB: {lb_pages}, AB: {ab_pages}, ORT: {ort_pages}")
        if selected_sections:
            ex_ids = selected_sections.get("exercise_ids", [])
            print(f"   📝 Selected sections — exercises: {ex_ids}, recall: {selected_sections.get('recall')}, vocab: {selected_sections.get('vocabulary')}, warmup: {selected_sections.get('warmup')}")
        elif exercises:
            print(f"   📝 Exercises (legacy): '{exercises}'")

        # Debug: get lesson without filter to see available types
        lesson_debug = get_lesson_context_by_number(
            sow_data=extraction,
            lesson_number=lesson_number,
            lesson_type=None
        )
        if lesson_debug.get("found"):
            section = lesson_debug.get("section_name", "N/A")
            seq_count = len(lesson_debug.get("teaching_sequence", []))
            print(f"   📋 Found lesson — section: {section}, teaching steps: {seq_count}")

        # Embed has_ort into selected_sections so the formatter can filter CW/HW accordingly
        effective_sections = dict(selected_sections) if selected_sections else {}
        effective_sections['_has_ort'] = has_ort

        # Select SOW section and apply page filter based on which books the user selected
        if has_ort and not has_lb_ab:
            sow_context = get_lesson_context_by_number(
                extraction, lesson_number, "reading",
                filter_pages=ort_page_list,
                selected_sections=effective_sections,
                exercises_text=exercises
            )
            strategy_str = format_lesson_context_for_prompt(sow_context)

        elif has_lb_ab and not has_ort:
            combined_pages = lb_page_list + ab_page_list
            sow_context = get_lesson_context_by_number(
                extraction, lesson_number, lt_value,
                filter_pages=combined_pages,
                selected_sections=effective_sections,
                exercises_text=exercises
            )
            strategy_str = format_lesson_context_for_prompt(sow_context)

        elif has_lb_ab and has_ort:
            lb_ab_ctx = get_lesson_context_by_number(
                extraction, lesson_number, lt_value,
                filter_pages=lb_page_list + ab_page_list,
                selected_sections=effective_sections,
                exercises_text=exercises
            )
            ort_ctx = get_lesson_context_by_number(
                extraction, lesson_number, "reading",
                filter_pages=ort_page_list,
                selected_sections=effective_sections,
                exercises_text=exercises
            )
            sow_context = lb_ab_ctx
            strategy_str = (
                format_lesson_context_for_prompt(lb_ab_ctx)
                + "\n\n--- ORT SECTION ---\n\n"
                + format_lesson_context_for_prompt(ort_ctx)
            )

        else:
            sow_context = get_lesson_context_by_number(
                extraction, lesson_number, lt_value,
                selected_sections=effective_sections,
                exercises_text=exercises
            )
            strategy_str = format_lesson_context_for_prompt(sow_context)

        if sow_context.get("found"):
            print(f"   ✓ Using section: {sow_context.get('section_name')} with {len(sow_context.get('teaching_sequence', []))} strategy steps")
            print(f"   📋 pages_found_in_sow: {sow_context.get('pages_found_in_sow', 'N/A')}")

        context["sow_context"] = sow_context

        if sow_context.get("found"):
            print(f"\n   📘 [DEBUG] Lesson context extracted:")
            print(f"      - Unit: {sow_context.get('unit')}")
            print(f"      - Lesson title: {sow_context.get('lesson_title')}")
            print(f"      - Section: {sow_context.get('section_name')}")
            print(f"      - SLOs: {len(sow_context.get('student_learning_outcomes', []))}")
            print(f"      - Teaching steps: {len(sow_context.get('teaching_sequence', []))}")
            if sow_context.get("ort_pages"):
                print(f"      - ORT pages: {sow_context.get('ort_pages')}")
            print()

        if not sow_context.get("found"):
            print(f"   ⚠ No lesson {lesson_number} found in SOW")
            context["sow_strategy"] = "No SOW lesson found. Generate based on general guidelines."
            return context

        print(f"   ✓ Found: {sow_context.get('unit')} - {sow_context.get('lesson_title')}")

        # Step 3-4: Fetch textbook pages from user-supplied page strings (per book)
        all_content = []

        for book_code, page_str in [("LB", lb_pages), ("AB", ab_pages), ("ORT", ort_pages)]:
            if not page_str:
                continue
            pages = parse_page_range(page_str)
            if not pages:
                print(f"       ⚠ Could not parse page range '{page_str}' for {book_code} — check for typos (e.g. '110-11' instead of '110-111')")
            if not pages:
                continue

            print(f"\n   📖 Fetching {book_code} pages {pages}...")

            # Try by book_tag first, then by mapped book_type
            book = db.get_textbook_by_tag(db_grade_textbooks, subject.value, book_code)
            if not book:
                db_book_type = map_book_type_to_db(book_code)
                book = db.get_textbook(db_grade_textbooks, subject.value, db_book_type)

            if not book:
                print(f"       ⚠ Book not found for {book_code}")
                continue

            fetched_pages = db.get_pages_by_numbers(book["id"], pages)
            print(f"       📖 Found book ID: {book['id']}, title: '{book.get('title', '')}'")
            print(f"       📖 Fetched {len(fetched_pages)} pages from {len(pages)} requested")

            if fetched_pages:
                context["metadata"]["textbook_ids"].append(book["id"])
                context["metadata"]["books_fetched"].append({
                    "book_type": book_code,
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
                        "book_type_short": book_code,
                        "title": book.get("title", ""),
                        "page_no": page_no,
                        "content": content_text,
                        "book_id": book["id"]
                    })
                    content_preview = content_text[:150].replace('\n', ' ') if content_text else '[No content]'
                    print(f"         Page {page_no}: {content_preview}...")
                print(f"       ✓ Fetched {len(fetched_pages)} pages from '{book.get('title', 'Unknown')}'")
            else:
                print(f"       ⚠ No pages found for {book_code} pages {pages}")

        context["book_content"] = all_content
        context["sow_strategy"] = strategy_str

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

    def get_sections_for_lesson(self, grade: str, subject: Subject, lesson_number: int) -> Optional[Dict[str, Any]]:
        """Return available section checkboxes for a lesson (new-format SOW only)."""
        sow_entries = self.db.get_sow_by_subject(subject.value, grade)
        if not sow_entries:
            return None
        extraction = sow_entries[0].get("extraction", {})
        if not extraction:
            return None
        return get_lesson_sections_summary(extraction, lesson_number)

    def retrieve_math_context(
        self,
        grade: str,
        unit_number: int,
        course_book_pages: Optional[str] = None,
        workbook_pages: Optional[str] = None,
        book_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all context needed for Math lesson generation.

        Flow:
        1. Find unit in Math SOW by unit_number
        2. Parse page numbers from course_book_pages and workbook_pages
        3. Fetch textbook pages based on those page numbers, filtered by book_types
        4. Format for LLM

        Args:
            grade: Grade level (e.g., "Grade 2")
            unit_number: The chapter/unit number from Math SOW
            course_book_pages: Course book pages (e.g., "145" or "145-150")
            workbook_pages: Optional workbook pages (e.g., "80" or "80-85")
            book_types: List of book type codes to fetch. "CB" = Course Book, "AB" = Activity Book.
                        Defaults to ["CB", "AB"] if not provided.

        Returns:
            Dict with context for lesson generation
        """
        # Default to both books if not specified
        if book_types is None:
            book_types = ["CB", "AB"]
        subject = "Mathematics"
        db_grade = normalize_grade(grade)

        print(f"\n📚 [MATH CONTEXT] Retrieving content for {subject} {grade}, Unit {unit_number}")
        print(f"   Course Book Pages: {course_book_pages}")
        if workbook_pages:
            print(f"   Workbook Pages: {workbook_pages}")

        context = {
            "grade": grade,
            "subject": subject,
            "unit_number": unit_number,
            "book_content": [],
            "sow_strategy": None,
            "sow_context": None,
            "metadata": {
                "textbook_ids": [],
                "sow_entry_id": None,
                "books_fetched": []
            }
        }

        # Step 1: Fetch Math SOW and find the unit
        print(f"\n📋 [SOW] Finding unit {unit_number} in Math SOW...")
        sow_entries = db.get_sow_by_subject(subject, grade)

        if not sow_entries:
            print(f"   ⚠ No SOW entries found for {subject} {grade}")
            return context

        sow_data = sow_entries[0]
        context["metadata"]["sow_entry_id"] = sow_data.get("id")

        extraction = sow_data.get("extraction", {})
        if not extraction:
            print(f"   ⚠ SOW entry has no extraction data")
            return context

        # Step 2: Get unit content
        unit = get_math_unit_by_number(extraction, unit_number)
        context["sow_context"] = unit

        if not unit:
            print(f"   ⚠ No unit {unit_number} found in Math SOW")
            context["sow_strategy"] = "No Math SOW unit found. Generate based on textbook content only."
        else:
            print(f"   ✓ Found: Chapter {unit['unit_number']}: {unit['unit_title']}")
            context["sow_strategy"] = format_math_unit_for_prompt(unit)

        # Step 3: Parse page numbers
        cb_pages = parse_page_range(course_book_pages) if course_book_pages else []
        wb_pages = parse_page_range(workbook_pages) if workbook_pages else []

        print(f"   📖 Selected book types: {book_types}")
        if cb_pages:
            print(f"   📖 Course Book pages to fetch: {cb_pages}")
        if wb_pages:
            print(f"   📖 Activity Book pages to fetch: {wb_pages}")

        # Step 4: Fetch textbook pages based on selected book_types
        all_content = []

        # Fetch Course Book pages (only if "CB" is in book_types)
        if "CB" in book_types:
            if cb_pages:
                print(f"\n   📘 Fetching Course Book pages...")
                # Try to find by book_tag first
                book = db.get_textbook_by_tag(db_grade, subject, "CB")
                if not book:
                    book = db.get_textbook(db_grade, subject, "course_book")

                if book:
                    fetched_pages = db.get_pages_by_numbers(book["id"], cb_pages)
                    if fetched_pages:
                        context["metadata"]["textbook_ids"].append(book["id"])
                        context["metadata"]["books_fetched"].append({
                            "book_type": "CB",
                            "book_id": book["id"],
                            "title": book.get("title", ""),
                            "pages_requested": cb_pages,
                            "pages_found": len(fetched_pages)
                        })

                        for page in fetched_pages:
                            page_no = page.get("page_no") or page.get("book_page_no")
                            content_text = page.get("book_text") or page.get("content", "")

                            all_content.append({
                                "book_type": "course_book",
                                "book_type_short": "CB",
                                "title": book.get("title", ""),
                                "page_no": page_no,
                                "content": content_text,
                                "book_id": book["id"]
                            })

                        print(f"      ✓ Fetched {len(fetched_pages)} Course Book pages")
                    else:
                        print(f"      ⚠ No pages found for Course Book pages {cb_pages}")
                else:
                    print(f"      ⚠ Course Book not found in database")
            else:
                print(f"\n   📘 Course Book selected but no pages provided - skipping.")
        else:
            print(f"\n   📘 Course Book (CB) not selected in book_types - skipping.")

        # Fetch Activity Book pages (only if "AB" is in book_types)
        if "AB" in book_types:
            if wb_pages:
                print(f"\n   📗 Fetching Activity Book pages...")
                # Try to find by book_tag "AB" first, then "WB" (legacy), then by book_type
                book = db.get_textbook_by_tag(db_grade, subject, "AB")
                if not book:
                    book = db.get_textbook_by_tag(db_grade, subject, "WB")
                if not book:
                    book = db.get_textbook(db_grade, subject, "workbook")

                if book:
                    fetched_pages = db.get_pages_by_numbers(book["id"], wb_pages)
                    if fetched_pages:
                        context["metadata"]["textbook_ids"].append(book["id"])
                        context["metadata"]["books_fetched"].append({
                            "book_type": "AB",
                            "book_id": book["id"],
                            "title": book.get("title", ""),
                            "pages_requested": wb_pages,
                            "pages_found": len(fetched_pages)
                        })

                        for page in fetched_pages:
                            page_no = page.get("page_no") or page.get("book_page_no")
                            content_text = page.get("book_text") or page.get("content", "")

                            all_content.append({
                                "book_type": "workbook",
                                "book_type_short": "AB",
                                "title": book.get("title", ""),
                                "page_no": page_no,
                                "content": content_text,
                                "book_id": book["id"]
                            })

                        print(f"      ✓ Fetched {len(fetched_pages)} Activity Book pages")
                    else:
                        print(f"      ⚠ No pages found for Activity Book pages {wb_pages}")
                else:
                    print(f"      ⚠ Activity Book not found in database")
            else:
                print(f"\n   📗 Activity Book selected but no pages provided - skipping.")
        else:
            print(f"\n   📗 Activity Book (AB) not selected in book_types - skipping.")

        context["book_content"] = all_content

        # Summary
        print(f"\n   📝 Context Summary:")
        if unit:
            print(f"      - Unit: Chapter {unit['unit_number']}: {unit['unit_title']}")
        print(f"      - Book pages loaded: {len(all_content)}")
        if all_content:
            books_used = {}
            for item in all_content:
                book_key = item.get('book_type_short', 'Unknown')
                if book_key not in books_used:
                    books_used[book_key] = []
                books_used[book_key].append(item.get('page_no', '?'))
            print(f"      - Books used: {', '.join([f'{k} (pages {books_used[k]})' for k in books_used])}")

        # Print complete SOW extraction being used
        print("\n" + "="*80)
        print("📋 COMPLETE MATH SOW EXTRACTION USED IN PROMPT:")
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
