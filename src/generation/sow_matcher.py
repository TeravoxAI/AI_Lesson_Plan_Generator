"""
SOW Matcher - Match textbook pages to SOW lessons
Handles page reference extraction with book type awareness
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set


def extract_pages_with_book_type(text: str) -> List[Tuple[str, int]]:
    """
    Extract page numbers along with their book type from text
    Returns: list of tuples [(book_type, page_number), ...]
    """
    if not text:
        return []
    
    results = []
    
    # Pattern for page ranges with book type prefix
    # Matches: "LB pgs. 108 – 109", "AB pg 84", "Ex 1 &3 AB pg. 85"
    range_with_book = r'(LB|AB|TR|ORT)\s*(?:pgs?\.?\s*#?\s*)?(\d+)\s*(?:to|–|-)\s*(\d+)'
    for match in re.finditer(range_with_book, text, re.IGNORECASE):
        book_type = match.group(1).upper()
        start, end = int(match.group(2)), int(match.group(3))
        for page in range(start, end + 1):
            results.append((book_type, page))
    
    # Pattern for single page with book type
    # Matches: "LB pg. 110", "AB pg 85", "TR pg. 94"
    single_with_book = r'(LB|AB|TR|ORT)\s*(?:pgs?\.?\s*#?\s*)?(\d+)(?!\s*(?:to|–|-))'
    for match in re.finditer(single_with_book, text, re.IGNORECASE):
        book_type = match.group(1).upper()
        page = int(match.group(2))
        if (book_type, page) not in results:
            results.append((book_type, page))
    
    # Pattern for ORT specific format
    # Matches: "ORT Reading and Explanation Pg 109 to 112"
    ort_pattern = r'ORT[^0-9]*(?:pg[s]?\.?\s*#?\s*)?(\d+)(?:\s*(?:to|–|-)\s*(\d+))?'
    for match in re.finditer(ort_pattern, text, re.IGNORECASE):
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        for page in range(start, end + 1):
            if ("ORT", page) not in results:
                results.append(("ORT", page))
    
    # Pattern for literature_pages (usually ORT)
    # Matches: "pg # 104 to 106", "pg 109 to 112"
    lit_pages_pattern = r'^pg[s]?\.?\s*#?\s*(\d+)\s*(?:to|–|-)\s*(\d+)'
    for match in re.finditer(lit_pages_pattern, text, re.IGNORECASE):
        start, end = int(match.group(1)), int(match.group(2))
        for page in range(start, end + 1):
            if ("ORT", page) not in results:
                results.append(("ORT", page))
    
    # Standalone page pattern (no book type - will be marked as UNKNOWN)
    standalone_pattern = r'(?<![A-Z])\s+pg[s]?\.?\s*#?\s*(\d+)(?:\s*(?:to|–|-)\s*(\d+))?'
    for match in re.finditer(standalone_pattern, text, re.IGNORECASE):
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        for page in range(start, end + 1):
            existing_pages = [p for (b, p) in results]
            if page not in existing_pages:
                results.append(("UNKNOWN", page))
    
    return results


def get_lesson_page_coverage(lesson: Dict[str, Any]) -> Dict[str, List[int]]:
    """
    Extract all page references from a lesson and organize by book type
    Returns: dict like {"LB": [108, 109, 110], "AB": [84, 85], "ORT": [109, 110, 111, 112]}
    """
    all_pages = []
    
    # 1. Check book_references
    for ref in lesson.get("book_references", []):
        all_pages.extend(extract_pages_with_book_type(ref))
    
    # 2. Check literature_pages (typically ORT)
    lit_pages = lesson.get("literature_pages")
    if lit_pages:
        extracted = extract_pages_with_book_type(lit_pages)
        for book_type, page in extracted:
            if book_type == "UNKNOWN":
                all_pages.append(("ORT", page))
            else:
                all_pages.append((book_type, page))
    
    # 3. Check main_activities descriptions
    for activity in lesson.get("main_activities", []):
        desc = activity.get("description", "")
        all_pages.extend(extract_pages_with_book_type(desc))
    
    # 4. Check homework_assignments
    for hw in lesson.get("homework_assignments", []):
        all_pages.extend(extract_pages_with_book_type(hw))
    
    # Organize by book type
    coverage: Dict[str, Set[int]] = {}
    for book_type, page in all_pages:
        if book_type not in coverage:
            coverage[book_type] = set()
        coverage[book_type].add(page)
    
    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in coverage.items()}


def search_lessons_by_pages(
    sow_data: Dict[str, Any], 
    book_type: str, 
    target_pages: List[int]
) -> List[Dict[str, Any]]:
    """
    Search SOW for lessons matching given book type and page numbers
    
    Args:
        sow_data: The full SOW JSON (with 'extraction' key)
        book_type: "LB", "AB", "TR", "ORT", or "ANY" for all books
        target_pages: list of ints (e.g., [110, 111, 112])
    
    Returns:
        List of matching lessons with relevant context
    """
    target_set = set(target_pages)
    book_type = book_type.upper()
    matching_lessons = []
    
    extraction = sow_data.get("extraction", sow_data)
    curriculum_units = extraction.get("curriculum_units", [])
    
    for unit in curriculum_units:
        unit_id = unit.get("unit_id", "")
        unit_title = unit.get("unit_title", "")
        
        for lesson in unit.get("lessons", []):
            coverage = get_lesson_page_coverage(lesson)
            
            # Determine which pages to check
            if book_type == "ANY":
                all_pages = set()
                for pages in coverage.values():
                    all_pages.update(pages)
                lesson_pages = all_pages
                matched_book_types = {
                    bt: sorted(list(target_set.intersection(set(pages)))) 
                    for bt, pages in coverage.items() 
                    if target_set.intersection(set(pages))
                }
            else:
                lesson_pages = set(coverage.get(book_type, []))
                matched_book_types = {
                    book_type: sorted(list(target_set.intersection(lesson_pages)))
                } if target_set.intersection(lesson_pages) else {}
            
            overlap = target_set.intersection(lesson_pages)
            
            if overlap:
                matching_lessons.append({
                    "unit_id": unit_id,
                    "unit_title": unit_title,
                    "lesson_number": lesson.get("lesson_number"),
                    "lesson_title": lesson.get("lesson_title"),
                    "matched_pages": sorted(list(overlap)),
                    "matched_by_book": matched_book_types,
                    "full_page_coverage": coverage,
                    "lesson_data": lesson
                })
    
    return matching_lessons


def get_lesson_context_for_llm(
    sow_data: Dict[str, Any], 
    grade: str, 
    subject: str, 
    book_type: str, 
    page_start: int, 
    page_end: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main function to get SOW context for lesson plan generation
    
    Args:
        sow_data: The full SOW JSON
        grade: Grade level (e.g., "Grade 2")
        subject: Subject name (e.g., "English")
        book_type: "LB", "AB", "TR", "ORT", or "ANY"
        page_start: Starting page number
        page_end: Ending page number (optional, for range)
    
    Returns:
        Dict with found status and formatted context for LLM
    """
    # Build page list
    if page_end:
        pages = list(range(page_start, page_end + 1))
    else:
        pages = [page_start]
    
    # Search with book type filter
    matches = search_lessons_by_pages(sow_data, book_type, pages)
    
    if not matches:
        return {
            "found": False,
            "message": f"No lessons found for {book_type} pages {pages}",
            "context": None,
            "matching_lessons": []
        }
    
    # Format for LLM
    context = {
        "found": True,
        "grade": grade,
        "subject": subject,
        "book_type": book_type,
        "requested_pages": pages,
        "matching_lessons": []
    }
    
    for match in matches:
        lesson = match["lesson_data"]
        context["matching_lessons"].append({
            "unit": f"{match['unit_id']}: {match['unit_title']}",
            "lesson_title": match["lesson_title"],
            "lesson_number": match["lesson_number"],
            "matched_pages": match["matched_pages"],
            "matched_by_book": match["matched_by_book"],
            "full_page_coverage": match["full_page_coverage"],
            "slos": lesson.get("slos", []),
            "vocabulary_list": lesson.get("vocabulary_list", []),
            "skills_focus": lesson.get("skills_focus", []),
            "warm_up_strategy": lesson.get("warm_up_strategy"),
            "main_activities": lesson.get("main_activities", []),
            "formative_strategies": lesson.get("formative_strategies", []),
            "homework_assignments": lesson.get("homework_assignments", []),
            "differentiation_notes": lesson.get("differentiation_notes"),
            "extension_activities": lesson.get("extension_activities"),
            "audio_tracks": lesson.get("audio_tracks", []),
            "video_links": lesson.get("video_links", []),
            "pre_reading_task": lesson.get("pre_reading_task"),
            "guided_reading_task": lesson.get("guided_reading_task"),
            "post_reading_task": lesson.get("post_reading_task")
        })
    
    return context


def format_sow_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format the SOW context into a readable string for the LLM prompt
    """
    if not context.get("found"):
        return "No SOW strategy found. Generate based on textbook content only."
    
    parts = []
    
    for lesson in context.get("matching_lessons", []):
        lesson_parts = []
        
        lesson_parts.append(f"**{lesson.get('unit', '')}**")
        lesson_parts.append(f"Lesson {lesson.get('lesson_number')}: {lesson.get('lesson_title')}")
        lesson_parts.append(f"Matched Pages: {lesson.get('matched_pages')}")
        
        if lesson.get("slos"):
            lesson_parts.append(f"\n**SLOs:**")
            for slo in lesson["slos"]:
                lesson_parts.append(f"  • {slo}")
        
        if lesson.get("vocabulary_list"):
            lesson_parts.append(f"\n**Vocabulary:** {', '.join(lesson['vocabulary_list'])}")
        
        if lesson.get("skills_focus"):
            lesson_parts.append(f"\n**Skills Focus:** {', '.join(lesson['skills_focus'])}")
        
        if lesson.get("warm_up_strategy"):
            lesson_parts.append(f"\n**Warm-up:** {lesson['warm_up_strategy']}")
        
        if lesson.get("main_activities"):
            lesson_parts.append(f"\n**Main Activities:**")
            for act in lesson["main_activities"]:
                name = act.get("activity_name", "Activity")
                desc = act.get("description", "")
                grouping = f" ({act['grouping']})" if act.get("grouping") else ""
                lesson_parts.append(f"  • {name}{grouping}: {desc[:200]}...")
        
        if lesson.get("formative_strategies"):
            lesson_parts.append(f"\n**Assessment Strategies:** {', '.join(lesson['formative_strategies'])}")
        
        if lesson.get("homework_assignments"):
            lesson_parts.append(f"\n**Homework:**")
            for hw in lesson["homework_assignments"]:
                lesson_parts.append(f"  • {hw}")
        
        if lesson.get("audio_tracks"):
            lesson_parts.append(f"\n**Audio Tracks:** {', '.join(lesson['audio_tracks'])}")
        
        if lesson.get("video_links"):
            lesson_parts.append(f"\n**Video Links:** {', '.join(lesson['video_links'])}")
        
        parts.append("\n".join(lesson_parts))
    
    return "\n\n---\n\n".join(parts)


# ============ UTILITY FUNCTIONS ============

def get_available_book_types(sow_data: Dict[str, Any]) -> List[str]:
    """Get all book types found in the SOW"""
    book_types = set()
    
    extraction = sow_data.get("extraction", sow_data)
    for unit in extraction.get("curriculum_units", []):
        for lesson in unit.get("lessons", []):
            coverage = get_lesson_page_coverage(lesson)
            book_types.update(coverage.keys())
    
    return sorted(list(book_types))


def map_book_type_to_db(book_type: str) -> str:
    """Map short book type codes to database book_type values"""
    mapping = {
        "LB": "learners",
        "AB": "activity",
        "TR": "teachers_resource",
        "ORT": "reading",
        "CB": "course_book",
        "WB": "workbook"
    }
    return mapping.get(book_type.upper(), book_type.lower())


def map_db_to_book_type(db_type: str) -> str:
    """Map database book_type to short codes"""
    mapping = {
        "learners": "LB",
        "activity": "AB",
        "teachers_resource": "TR",
        "reading": "ORT",
        "course_book": "CB",
        "workbook": "WB"
    }
    return mapping.get(db_type, db_type.upper())
