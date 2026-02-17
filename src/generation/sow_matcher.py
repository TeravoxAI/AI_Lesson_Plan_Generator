"""
SOW Matcher - Match textbook pages to SOW lessons
Updated for new English SOW format with lb_ab/ort structure and teaching_sequence with AFL linking.
"""
import re
from typing import Dict, List, Any, Optional, Tuple, Set


def get_lesson_page_coverage(lesson: Dict[str, Any]) -> Dict[str, List[int]]:
    """
    Extract known page references from a lesson's ORT section.
    LB/AB pages come from user input at generation time.

    Returns: dict like {"ORT": [109, 110, 111, 112]}
    """
    coverage: Dict[str, Set[int]] = {}

    ort = lesson.get("ort", {})
    ort_pages = ort.get("pages", [])
    if ort_pages:
        coverage["ORT"] = set(ort_pages)

    return {k: sorted(list(v)) for k, v in coverage.items()}



# ============ LESSON NUMBER MATCHING ============

ORT_LESSON_TYPES = {"reading", "reading_comprehension", "reading_decoding_fluency"}


def filter_teaching_sequence_by_pages(steps: list, pages: list) -> list:
    """
    Return only steps whose content explicitly mentions at least one of the given page numbers.
    Page mentions detected as: "pg. 110", "pg 110", "page 110", "p. 110", or bare number
    preceded by "pg"/"page"/"p." within 10 chars.
    Returns empty list if no steps match (caller should fall back to full sequence).
    """
    if not pages:
        return []
    matched = []
    for step in steps:
        content = step.get("content", "")
        for page in pages:
            if re.search(rf'\b(?:pg\.?\s*|page\s*|p\.\s*){page}\b', content, re.IGNORECASE):
                matched.append(step)
                break  # Don't add same step twice
    return matched


def is_ort_lesson_type(lesson_type: Optional[str]) -> bool:
    """Return True if the requested lesson type is ORT-related."""
    if not lesson_type:
        return False
    lt = lesson_type.lower()
    return any(k in lt for k in ("ort", "reading"))


def find_lesson_by_number(
    sow_data: Dict[str, Any],
    lesson_number: int
) -> Optional[Dict[str, Any]]:
    """
    Find a specific lesson by its lesson_number.

    Returns the lesson dict augmented with its unit's number and title, or None.
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
                    "lb_ab": lesson.get("lb_ab", {}),
                    "ort": lesson.get("ort", {}),
                    "classwork_homework": lesson.get("classwork_homework", [])
                }

    return None


def get_lesson_context_by_number(
    sow_data: Dict[str, Any],
    lesson_number: int,
    lesson_type: Optional[str] = None,
    filter_pages: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Get complete lesson context by lesson number.

    Args:
        sow_data: The full SOW JSON (new lb_ab/ort format)
        lesson_number: The lesson number to find
        lesson_type: Requested lesson type — determines whether lb_ab or ort section is primary
        filter_pages: If provided, filter teaching_sequence to steps mentioning these pages.
                      Falls back to full sequence if no steps match.

    Returns:
        Dict with lesson info, section content, SLOs, skills, teaching sequence, etc.
        Includes pages_found_in_sow: bool indicating whether page filtering found matches.
    """
    lesson = find_lesson_by_number(sow_data, lesson_number)

    if not lesson:
        return {
            "found": False,
            "message": f"No lesson found with number {lesson_number}",
            "lesson": None,
            "book_references": [],
        }

    use_ort = is_ort_lesson_type(lesson_type)

    if use_ort:
        section = lesson.get("ort", {})
        section_name = "ORT"
    else:
        section = lesson.get("lb_ab", {})
        section_name = "LB/AB"

    slos = section.get("slos", [])
    skills = section.get("skills", [])
    teaching_sequence = section.get("teaching_sequence", [])

    # Apply page filtering if requested
    pages_found_in_sow = True
    if filter_pages:
        filtered = filter_teaching_sequence_by_pages(teaching_sequence, filter_pages)
        if filtered:
            teaching_sequence = filtered
        else:
            # No matches found — use full sequence and flag it
            pages_found_in_sow = False

    # Extract audio tracks and YouTube URLs from teaching sequence for resource display
    external_resources = []
    seen_refs: Set = set()
    for step in teaching_sequence:
        content = step.get("content", "")
        # Audio tracks: "Audio Track 70", "audio track 70"
        for m in re.finditer(r'[Aa]udio [Tt]rack\s+(\d+)', content):
            ref = f"Track {m.group(1)}"
            if ref not in seen_refs:
                seen_refs.add(ref)
                external_resources.append({
                    "title": f"Audio Track {m.group(1)}",
                    "type": "audio",
                    "reference": ref
                })
        # YouTube URLs
        for m in re.finditer(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+', content):
            url = m.group(0).rstrip('.,;)')
            if url not in seen_refs:
                seen_refs.add(url)
                external_resources.append({
                    "title": "Video Resource",
                    "type": "video",
                    "reference": url
                })

    # For ORT: also expose vocabulary and book info
    ort_meta = {}
    if use_ort:
        ort_meta = {
            "book_title": section.get("book_title", ""),
            "story_title": section.get("story_title", ""),
            "ort_pages": section.get("pages", []),
            "vocabulary": section.get("vocabulary", []),
        }

    return {
        "found": True,
        "unit": f"Unit {lesson['unit_number']}: {lesson['unit_title']}",
        "lesson_number": lesson["lesson_number"],
        "lesson_title": lesson["lesson_title"],
        "section_name": section_name,
        "student_learning_outcomes": slos,
        "skills": skills,
        "teaching_sequence": teaching_sequence,
        "classwork_homework": lesson.get("classwork_homework", []),
        "pages_found_in_sow": pages_found_in_sow,
        "external_resources": external_resources,
        # ORT-specific fields (empty if not ORT lesson)
        **ort_meta,
        # Backward-compat key still expected by router.py
        "book_references": [],
    }


def format_lesson_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format lesson context (new lb_ab/ort format) into a readable string for the LLM prompt.
    Teaching strategies are listed in sequence with their AFL strategies inline.
    Includes audio/video resource sections and a warning if pages were not found in SOW.
    """
    if not context.get("found"):
        return "No SOW lesson found. Generate based on textbook content only."

    parts = []

    # Add warning if the page filter found no matches
    if context.get("pages_found_in_sow") is False:
        parts.append("⚠️ No explicit page references found in SOW for these pages. Full lesson context provided — extract relevant content for this LP type.")
        parts.append("")

    parts.append(f"**{context.get('unit', '')}**")
    parts.append(f"Lesson {context.get('lesson_number')}: {context.get('lesson_title')}")
    parts.append(f"Section: {context.get('section_name', '')}")

    # ORT book info
    if context.get("book_title"):
        parts.append(f"\n**ORT Book:** {context['book_title']}")
    if context.get("story_title"):
        parts.append(f"**Story:** {context['story_title']}")
    if context.get("ort_pages"):
        parts.append(f"**Pages:** {context['ort_pages']}")
    if context.get("vocabulary"):
        parts.append(f"**Vocabulary:** {', '.join(context['vocabulary'])}")

    if context.get("student_learning_outcomes"):
        parts.append(f"\n**Student Learning Outcomes:**")
        for slo in context["student_learning_outcomes"]:
            parts.append(f"  • {slo}")

    if context.get("skills"):
        parts.append(f"\n**Skills:** {', '.join(context['skills'])}")

    if context.get("teaching_sequence"):
        parts.append(f"\n**Teaching Strategies (in sequence):**")
        for i, step in enumerate(context["teaching_sequence"], 1):
            strategy = step.get("strategy", "")
            content = step.get("content", "")
            afl = step.get("afl", [])

            parts.append(f"\n  {i}. **{strategy}**")
            if content:
                # Indent multiline content
                indented = "\n".join(f"     {line}" for line in content.split("\n") if line.strip())
                parts.append(indented)
            if afl:
                parts.append(f"     ▶ AFL Strategy: {', '.join(afl)}")

    # Surface audio and video resources found in teaching sequence
    external_resources = context.get("external_resources", [])
    audio_resources = [r for r in external_resources if r.get("type") == "audio"]
    video_resources = [r for r in external_resources if r.get("type") == "video"]

    if audio_resources:
        parts.append(f"\n**Audio Resources:**")
        for res in audio_resources:
            parts.append(f"  • {res['title']} (reference: {res['reference']})")

    if video_resources:
        parts.append(f"\n**Video Resources:**")
        for res in video_resources:
            parts.append(f"  • {res['title']}: {res['reference']}")

    if context.get("classwork_homework"):
        parts.append(f"\n**Classwork/Homework:**")
        for item in context["classwork_homework"]:
            parts.append(f"  • {item}")

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


# ============ MATH SOW FUNCTIONS (Simplified Unit-Based Structure) ============

def get_math_units(sow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get all units from a Math SOW document.

    Args:
        sow_data: The full Math SOW JSON (with 'curriculum' key)

    Returns:
        List of units with unit_number and unit_title
    """
    curriculum = sow_data.get("curriculum", sow_data)
    units = curriculum.get("units", [])

    return [
        {
            "unit_number": unit.get("unit_number", 0),
            "unit_title": unit.get("unit_title", "")
        }
        for unit in units
    ]


def get_math_unit_by_number(
    sow_data: Dict[str, Any],
    unit_number: int
) -> Optional[Dict[str, Any]]:
    """
    Get a specific Math unit by its unit_number.

    Args:
        sow_data: The full Math SOW JSON (with 'curriculum' key)
        unit_number: The unit number to find

    Returns:
        The matching unit dict with unit_number, unit_title, content, or None
    """
    curriculum = sow_data.get("curriculum", sow_data)
    units = curriculum.get("units", [])

    for unit in units:
        if unit.get("unit_number") == unit_number:
            return {
                "unit_number": unit.get("unit_number", 0),
                "unit_title": unit.get("unit_title", ""),
                "content": unit.get("content", "")
            }

    return None


def format_math_unit_for_prompt(unit: Dict[str, Any]) -> str:
    """
    Format Math unit content into a readable string for the LLM prompt.

    Args:
        unit: The unit dict from get_math_unit_by_number

    Returns:
        Formatted string for prompt
    """
    if not unit:
        return "No Math SOW unit found. Generate based on textbook content only."

    parts = []
    parts.append(f"**Chapter {unit.get('unit_number', '')}: {unit.get('unit_title', '')}**")
    parts.append("")

    content = unit.get("content", "")
    if content:
        parts.append(content)

    return "\n".join(parts)


def parse_page_range(page_str: str) -> List[int]:
    """
    Parse a page string into a list of page numbers.
    Supports single pages ("145") and ranges ("145-150").

    Args:
        page_str: String like "145" or "145-150"

    Returns:
        List of page numbers
    """
    if not page_str:
        return []

    page_str = page_str.strip()

    # Handle range (145-150 or 145 - 150)
    if "-" in page_str:
        parts = page_str.split("-")
        if len(parts) == 2:
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                return list(range(start, end + 1))
            except ValueError:
                return []

    # Handle single page
    try:
        return [int(page_str)]
    except ValueError:
        return []


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
