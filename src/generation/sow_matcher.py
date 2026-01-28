"""
SOW Matcher - Match textbook pages to SOW lessons
Updated for new SOW format with lesson_plan_types and structured book_references
"""
import re
from typing import Dict, List, Any, Optional, Tuple, Set


def get_lesson_plan_type_page_coverage(lesson_plan_type: Dict[str, Any]) -> Dict[str, List[int]]:
    """
    Extract all page references from a lesson plan type and organize by book type

    New format has book_references as array of objects:
    {
        "book_type": "LB",
        "book_name": "...",
        "pages": [110, 111]
    }

    Returns: dict like {"LB": [108, 109, 110], "AB": [84, 85], "ORT": [109, 110, 111, 112]}
    """
    coverage: Dict[str, Set[int]] = {}

    for ref in lesson_plan_type.get("book_references", []):
        book_type = ref.get("book_type", "").upper()
        pages = ref.get("pages", [])

        if book_type and pages:
            if book_type not in coverage:
                coverage[book_type] = set()
            coverage[book_type].update(pages)

    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in coverage.items()}


def get_lesson_page_coverage(lesson: Dict[str, Any]) -> Dict[str, List[int]]:
    """
    Extract all page references from all lesson_plan_types in a lesson
    Returns: dict like {"LB": [108, 109, 110], "AB": [84, 85], "ORT": [109, 110, 111, 112]}
    """
    coverage: Dict[str, Set[int]] = {}

    for lpt in lesson.get("lesson_plan_types", []):
        lpt_coverage = get_lesson_plan_type_page_coverage(lpt)
        for book_type, pages in lpt_coverage.items():
            if book_type not in coverage:
                coverage[book_type] = set()
            coverage[book_type].update(pages)

    return {k: sorted(list(v)) for k, v in coverage.items()}


def search_lessons_by_pages(
    sow_data: Dict[str, Any],
    book_type: str,
    target_pages: List[int]
) -> List[Dict[str, Any]]:
    """
    Search SOW for lessons matching given book type and page numbers

    Args:
        sow_data: The full SOW JSON (with 'curriculum' key)
        book_type: "LB", "AB", "TR", "ORT", or "ANY" for all books
        target_pages: list of ints (e.g., [110, 111, 112])

    Returns:
        List of matching lessons with relevant context
    """
    target_set = set(target_pages)
    book_type = book_type.upper()
    matching_lessons = []

    # Navigate new format: curriculum.units[]
    curriculum = sow_data.get("curriculum", sow_data)
    units = curriculum.get("units", [])

    for unit in units:
        unit_number = unit.get("unit_number", 0)
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
                # Find matching lesson_plan_types
                matching_lpts = []
                for lpt in lesson.get("lesson_plan_types", []):
                    lpt_coverage = get_lesson_plan_type_page_coverage(lpt)
                    lpt_pages = set()
                    for pages in lpt_coverage.values():
                        lpt_pages.update(pages)

                    if book_type != "ANY":
                        lpt_pages = set(lpt_coverage.get(book_type, []))

                    if target_set.intersection(lpt_pages):
                        matching_lpts.append(lpt)

                matching_lessons.append({
                    "unit_number": unit_number,
                    "unit_title": unit_title,
                    "lesson_number": lesson.get("lesson_number"),
                    "lesson_title": lesson.get("lesson_title"),
                    "matched_pages": sorted(list(overlap)),
                    "matched_by_book": matched_book_types,
                    "full_page_coverage": coverage,
                    "lesson_data": lesson,
                    "matching_lesson_plan_types": matching_lpts
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
        matching_lpts = match.get("matching_lesson_plan_types", [])

        # Collect all SLOs, strategies, skills from matching lesson plan types
        all_slos = []
        all_strategies = []
        all_skills = set()
        all_external_resources = []

        formatted_lpts = []
        for lpt in matching_lpts:
            all_slos.extend(lpt.get("student_learning_outcomes", []))
            all_strategies.extend(lpt.get("learning_strategies", []))
            all_skills.update(lpt.get("skills", []))
            all_external_resources.extend(lpt.get("external_resources", []))

            formatted_lpts.append({
                "type": lpt.get("type", ""),
                "content": lpt.get("content", ""),
                "learning_strategies": lpt.get("learning_strategies", []),
                "student_learning_outcomes": lpt.get("student_learning_outcomes", []),
                "skills": lpt.get("skills", []),
                "book_references": lpt.get("book_references", []),
                "external_resources": lpt.get("external_resources", [])
            })

        context["matching_lessons"].append({
            "unit": f"Unit {match['unit_number']}: {match['unit_title']}",
            "lesson_title": match["lesson_title"],
            "lesson_number": match["lesson_number"],
            "matched_pages": match["matched_pages"],
            "matched_by_book": match["matched_by_book"],
            "full_page_coverage": match["full_page_coverage"],
            "student_learning_outcomes": list(set(all_slos)),
            "learning_strategies": list(set(all_strategies)),
            "skills": sorted(list(all_skills)),
            "external_resources": all_external_resources,
            "lesson_plan_types": formatted_lpts
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

        if lesson.get("student_learning_outcomes"):
            lesson_parts.append(f"\n**Student Learning Outcomes:**")
            for slo in lesson["student_learning_outcomes"]:
                lesson_parts.append(f"  • {slo}")

        if lesson.get("skills"):
            lesson_parts.append(f"\n**Skills Focus:** {', '.join(lesson['skills'])}")

        if lesson.get("learning_strategies"):
            lesson_parts.append(f"\n**Learning Strategies:**")
            for strategy in lesson["learning_strategies"]:
                lesson_parts.append(f"  • {strategy}")

        # Format lesson plan types
        for lpt in lesson.get("lesson_plan_types", []):
            lpt_type = lpt.get("type", "Unknown")
            lesson_parts.append(f"\n**Lesson Plan Type: {lpt_type.replace('_', ' ').title()}**")

            if lpt.get("content"):
                lesson_parts.append(f"  Content: {lpt['content'][:300]}...")

            if lpt.get("book_references"):
                lesson_parts.append(f"  Book References:")
                for ref in lpt["book_references"]:
                    book_type = ref.get("book_type", "")
                    book_name = ref.get("book_name", "")
                    pages = ref.get("pages", [])
                    ref_str = f"    - {book_type}"
                    if book_name:
                        ref_str += f" ({book_name})"
                    if pages:
                        ref_str += f": pages {pages}"
                    lesson_parts.append(ref_str)

        if lesson.get("external_resources"):
            lesson_parts.append(f"\n**External Resources:**")
            for res in lesson["external_resources"]:
                res_title = res.get("title", "Resource")
                res_type = res.get("type", "")
                res_ref = res.get("reference", "")
                res_str = f"  • {res_title} ({res_type})"
                if res_ref:
                    res_str += f": {res_ref}"
                lesson_parts.append(res_str)

        parts.append("\n".join(lesson_parts))

    return "\n\n---\n\n".join(parts)


# ============ LESSON NUMBER MATCHING ============

def find_lesson_by_number(
    sow_data: Dict[str, Any],
    lesson_number: int
) -> Optional[Dict[str, Any]]:
    """
    Find a specific lesson by its lesson_number.

    Args:
        sow_data: The full SOW JSON (with 'curriculum' key)
        lesson_number: The lesson number to find

    Returns:
        The matching lesson dict or None
    """
    curriculum = sow_data.get("curriculum", sow_data)
    units = curriculum.get("units", [])

    for unit in units:
        for lesson in unit.get("lessons", []):
            if lesson.get("lesson_number") == lesson_number:
                return {
                    "unit_number": unit.get("unit_number", 0),
                    "unit_title": unit.get("unit_title", ""),
                    "lesson_number": lesson.get("lesson_number"),
                    "lesson_title": lesson.get("lesson_title", ""),
                    "lesson_plan_types": lesson.get("lesson_plan_types", [])
                }

    return None


def get_book_references_from_lesson(
    lesson: Dict[str, Any],
    lesson_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extract all book references from a lesson's lesson_plan_types.

    Args:
        lesson: The lesson dict (output from find_lesson_by_number)
        lesson_type: Optional filter for specific lesson plan type (uses partial matching)

    Returns:
        List of book references with book_type, book_name, pages
    """
    all_refs = []
    seen = set()  # Avoid duplicates

    for lpt in lesson.get("lesson_plan_types", []):
        # Use flexible matching instead of exact comparison
        if lesson_type and not matches_lesson_type(lpt.get("type", ""), lesson_type):
            continue

        for ref in lpt.get("book_references", []):
            book_type = ref.get("book_type", "")
            pages = tuple(ref.get("pages", []))
            key = (book_type, pages)

            if key not in seen and book_type and pages:
                seen.add(key)
                all_refs.append({
                    "book_type": book_type,
                    "book_name": ref.get("book_name", ""),
                    "pages": list(pages)
                })

    return all_refs


def matches_lesson_type(sow_type: str, requested_type: Optional[str]) -> bool:
    """
    Check if a SOW lesson_plan_type matches the requested lesson type.
    Uses partial matching to handle variations in naming.

    Examples:
        - "recall_review" matches "recall"
        - "vocabulary_word_meaning" matches "vocabulary"
        - "listening_audio_video" matches "listening"
        - "speaking_oral_language" matches "oral_speaking" (also checks reverse)
    """
    if not requested_type:
        return True

    sow_lower = sow_type.lower()
    req_lower = requested_type.lower()

    # Direct substring match (most common case)
    if req_lower in sow_lower or sow_lower in req_lower:
        return True

    # Handle special cases where naming differs
    # "oral_speaking" <-> "speaking_oral_language"
    if "oral" in req_lower and "speaking" in req_lower:
        return "oral" in sow_lower and "speaking" in sow_lower

    # "creative_writing" <-> "writing_guided_creative"
    if "creative" in req_lower and "writing" in req_lower:
        return "creative" in sow_lower and "writing" in sow_lower

    return False


def get_lesson_context_by_number(
    sow_data: Dict[str, Any],
    lesson_number: int,
    lesson_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get complete lesson context by lesson number.

    Args:
        sow_data: The full SOW JSON
        lesson_number: The lesson number to find
        lesson_type: Optional filter for specific lesson plan type (uses partial matching)

    Returns:
        Dict with lesson info, book references, SLOs, strategies, etc.
    """
    lesson = find_lesson_by_number(sow_data, lesson_number)

    if not lesson:
        return {
            "found": False,
            "message": f"No lesson found with number {lesson_number}",
            "lesson": None,
            "book_references": [],
            "lesson_plan_types": []
        }

    # Get book references with flexible matching
    book_refs = []
    seen = set()

    # Collect SLOs, strategies, skills from relevant lesson plan types
    all_slos = []
    all_strategies = []
    all_skills = set()
    all_external_resources = []
    filtered_lpts = []

    for lpt in lesson.get("lesson_plan_types", []):
        # Use flexible matching instead of exact comparison
        if lesson_type and not matches_lesson_type(lpt.get("type", ""), lesson_type):
            continue

        # Extract book references from this lesson plan type
        for ref in lpt.get("book_references", []):
            book_type = ref.get("book_type", "")
            pages = tuple(ref.get("pages", []))
            key = (book_type, pages)

            if key not in seen and book_type and pages:
                seen.add(key)
                book_refs.append({
                    "book_type": book_type,
                    "book_name": ref.get("book_name", ""),
                    "pages": list(pages)
                })

        all_slos.extend(lpt.get("student_learning_outcomes", []))
        all_strategies.extend(lpt.get("learning_strategies", []))
        all_skills.update(lpt.get("skills", []))
        all_external_resources.extend(lpt.get("external_resources", []))
        filtered_lpts.append(lpt)

    return {
        "found": True,
        "unit": f"Unit {lesson['unit_number']}: {lesson['unit_title']}",
        "lesson_number": lesson["lesson_number"],
        "lesson_title": lesson["lesson_title"],
        "book_references": book_refs,
        "lesson_plan_types": filtered_lpts,
        "student_learning_outcomes": list(set(all_slos)),
        "learning_strategies": list(set(all_strategies)),
        "skills": sorted(list(all_skills)),
        "external_resources": all_external_resources
    }


def format_lesson_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format lesson context into a readable string for the LLM prompt.
    """
    if not context.get("found"):
        return "No SOW lesson found. Generate based on textbook content only."

    parts = []

    parts.append(f"**{context.get('unit', '')}**")
    parts.append(f"Lesson {context.get('lesson_number')}: {context.get('lesson_title')}")

    if context.get("student_learning_outcomes"):
        parts.append(f"\n**Student Learning Outcomes:**")
        for slo in context["student_learning_outcomes"]:
            parts.append(f"  • {slo}")

    if context.get("skills"):
        parts.append(f"\n**Skills Focus:** {', '.join(context['skills'])}")

    if context.get("learning_strategies"):
        parts.append(f"\n**Learning Strategies:**")
        for strategy in context["learning_strategies"]:
            parts.append(f"  • {strategy}")

    # Format lesson plan types
    for lpt in context.get("lesson_plan_types", []):
        lpt_type = lpt.get("type", "Unknown")
        parts.append(f"\n**Lesson Plan Type: {lpt_type.replace('_', ' ').title()}**")

        if lpt.get("content"):
            content = lpt["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            parts.append(f"  Content: {content}")

        if lpt.get("book_references"):
            parts.append(f"  Book References:")
            for ref in lpt["book_references"]:
                book_type = ref.get("book_type", "")
                book_name = ref.get("book_name", "")
                pages = ref.get("pages", [])
                ref_str = f"    - {book_type}"
                if book_name:
                    ref_str += f" ({book_name})"
                if pages:
                    ref_str += f": pages {pages}"
                parts.append(ref_str)

    if context.get("external_resources"):
        parts.append(f"\n**External Resources:**")
        for res in context["external_resources"]:
            res_title = res.get("title", "Resource")
            res_type = res.get("type", "")
            res_ref = res.get("reference", "")
            res_str = f"  • {res_title} ({res_type})"
            if res_ref:
                res_str += f": {res_ref}"
            parts.append(res_str)

    return "\n".join(parts)


# ============ UTILITY FUNCTIONS ============

def get_available_book_types(sow_data: Dict[str, Any]) -> List[str]:
    """Get all book types found in the SOW"""
    book_types = set()

    curriculum = sow_data.get("curriculum", sow_data)
    for unit in curriculum.get("units", []):
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


# ============ LEGACY SUPPORT ============

def extract_pages_with_book_type(text: str) -> List[Tuple[str, int]]:
    """
    Legacy function: Extract page numbers along with their book type from text
    Used for parsing old-format SOW data or free-form text
    Returns: list of tuples [(book_type, page_number), ...]
    """
    if not text:
        return []

    results = []

    # Pattern for page ranges with book type prefix
    range_with_book = r'(LB|AB|TR|ORT)\s*(?:pgs?\.?\s*#?\s*)?(\d+)\s*(?:to|–|-)\s*(\d+)'
    for match in re.finditer(range_with_book, text, re.IGNORECASE):
        book_type = match.group(1).upper()
        start, end = int(match.group(2)), int(match.group(3))
        for page in range(start, end + 1):
            results.append((book_type, page))

    # Pattern for single page with book type
    single_with_book = r'(LB|AB|TR|ORT)\s*(?:pgs?\.?\s*#?\s*)?(\d+)(?!\s*(?:to|–|-))'
    for match in re.finditer(single_with_book, text, re.IGNORECASE):
        book_type = match.group(1).upper()
        page = int(match.group(2))
        if (book_type, page) not in results:
            results.append((book_type, page))

    return results
