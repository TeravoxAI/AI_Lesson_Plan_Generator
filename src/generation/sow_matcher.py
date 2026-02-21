"""
SOW Matcher - Match textbook pages to SOW lessons
Supports both legacy teaching_sequence format and new structured format
(recall / vocabulary / warm_up / exercises / differentiated_instruction / extension_activity).
"""
import re
from typing import Dict, List, Any, Optional, Tuple, Set


# ============ UTILITIES ============

def get_lesson_page_coverage(lesson: Dict[str, Any]) -> Dict[str, List[int]]:
    ort = lesson.get("ort", {})
    ort_pages = ort.get("pages", [])
    coverage: Dict[str, Set[int]] = {}
    if ort_pages:
        coverage["ORT"] = set(ort_pages)
    return {k: sorted(list(v)) for k, v in coverage.items()}


ORT_LESSON_TYPES = {"reading", "reading_comprehension", "reading_decoding_fluency"}


def is_ort_lesson_type(lesson_type: Optional[str]) -> bool:
    if not lesson_type:
        return False
    lt = lesson_type.lower()
    return any(k in lt for k in ("ort", "reading"))


def parse_page_range(page_str: str) -> List[int]:
    if not page_str:
        return []
    page_str = page_str.strip()
    if "-" in page_str:
        parts = page_str.split("-")
        if len(parts) == 2:
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start > end:
                    print(f"   ⚠ [parse_page_range] Invalid range '{page_str}': start ({start}) > end ({end}) — likely a typo, returning empty.")
                    return []
                return list(range(start, end + 1))
            except ValueError:
                return []
    try:
        return [int(page_str)]
    except ValueError:
        return []


def find_lesson_by_number(sow_data: Dict[str, Any], lesson_number: int) -> Optional[Dict[str, Any]]:
    curriculum = sow_data.get("curriculum", sow_data)
    for unit in curriculum.get("units", []):
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


def _is_new_format(lb_ab: Dict[str, Any]) -> bool:
    """New format has 'exercises' list; old format has 'teaching_sequence' list."""
    return "exercises" in lb_ab and "teaching_sequence" not in lb_ab


# ============ NEW FORMAT — SECTIONS SUMMARY (for frontend) ============

def _extract_page_hints(classwork_homework: List[str]) -> Dict[str, str]:
    """
    Parse CW/HW items to extract page hints per book code.
    e.g. "Ex 1, 2 & 3 AB pgs. 88 – 89"  →  {"AB": "88-89"}
         "Ex 2& 5LB pgs. 110 – 111"      →  {"LB": "110-111"}
    """
    hints: Dict[str, str] = {}
    # Match patterns like "LB pgs. 110 – 111", "AB pg. 88-89", "ORT ... Pg 109 to 112"
    pattern = re.compile(
        r'\b(LB|AB|ORT)\b.*?'               # book code
        r'[Pp]gs?\.?\s*'                    # pg / pgs / Pg
        r'(\d+)\s*(?:–|-|to)\s*(\d+)',      # range: 110 – 111
        re.IGNORECASE
    )
    single_pattern = re.compile(
        r'\b(LB|AB|ORT)\b.*?'
        r'[Pp]g\.?\s*'
        r'(\d+)(?!\s*(?:–|-|to)\s*\d)',
        re.IGNORECASE
    )
    for item in classwork_homework:
        for m in pattern.finditer(item):
            code = m.group(1).upper()
            if code not in hints:
                hints[code] = f"{m.group(2)}-{m.group(3)}"
        for m in single_pattern.finditer(item):
            code = m.group(1).upper()
            if code not in hints:
                hints[code] = m.group(2)
    return hints


def get_lesson_sections_summary(sow_data: Dict[str, Any], lesson_number: int) -> Optional[Dict[str, Any]]:
    """
    Return available sections for a lesson for the frontend to display as checkboxes.
    Also includes page_hints (e.g. {"LB": "110-111", "AB": "88-89"}) parsed from CW/HW.
    Returns None if lesson not found or not new-format SOW.
    """
    lesson = find_lesson_by_number(sow_data, lesson_number)
    if not lesson:
        return None

    lb_ab = lesson.get("lb_ab", {})
    if not _is_new_format(lb_ab):
        return None

    recall = lb_ab.get("recall")
    vocabulary = lb_ab.get("vocabulary")
    warm_up = lb_ab.get("warm_up")
    exercises_list = lb_ab.get("exercises", [])
    diff = lb_ab.get("differentiated_instruction")
    ext = lb_ab.get("extension_activity")

    exercises = [
        {
            "exercise_id": str(ex.get("exercise_id", "")),
            "title": ex.get("title", f"Exercise {ex.get('exercise_id', '')}")
        }
        for ex in exercises_list
    ]

    # Parse page hints from classwork/homework
    cw_hw = lesson.get("classwork_homework", [])
    page_hints = _extract_page_hints(cw_hw)

    return {
        "lesson_number": lesson_number,
        "lesson_title": lesson.get("lesson_title", ""),
        "recall": {
            "available": recall is not None,
            "title": recall.get("title", "Unit Review") if recall else None
        },
        "vocabulary": {
            "available": vocabulary is not None,
            "words": vocabulary.get("words", []) if vocabulary else []
        },
        "warmup": {"available": warm_up is not None},
        "exercises": exercises,
        "differentiated": {"available": diff is not None},
        "extension": {"available": ext is not None},
        "page_hints": page_hints   # e.g. {"LB": "110-111", "AB": "88-89", "ORT": "109-112"}
    }


# ============ NEW FORMAT — RESOURCE EXTRACTION ============

def _extract_resources_new_format(lb_ab: Dict[str, Any], selected_sections: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Extract audio/video resources from new-format SOW based on selected sections."""
    resources = []
    seen: Set = set()
    ss = selected_sections or {}
    selected_ex_ids = [str(i) for i in ss.get("exercise_ids", [])]

    def _add_audio(track_num):
        ref = f"Track {track_num}"
        if ref not in seen:
            seen.add(ref)
            resources.append({"title": f"Audio Track {track_num}", "type": "audio", "reference": ref})

    def _add_video(url_str):
        for u in url_str.split():
            u = u.rstrip(".,;)")
            if ("youtube" in u or "youtu.be" in u) and u not in seen:
                seen.add(u)
                resources.append({"title": "Video Resource", "type": "video", "reference": u})

    # Warm-up resources
    if ss.get("warmup", False):
        for act in lb_ab.get("warm_up", {}).get("activities", []):
            dr = act.get("digital_resource", "")
            if dr:
                _add_video(dr)

    # Exercise resources
    for ex in lb_ab.get("exercises", []):
        if selected_ex_ids and str(ex.get("exercise_id")) not in selected_ex_ids:
            continue
        for sub in ex.get("sub_activities", []):
            t = sub.get("audio_track")
            if t:
                _add_audio(t)
            dr = sub.get("digital_resource", "")
            if dr:
                _add_video(dr)

    return resources


# ============ NEW FORMAT — CONTEXT FORMATTER ============

def _format_new_structure_for_prompt(lesson: Dict[str, Any], lb_ab: Dict[str, Any],
                                     selected_sections: Optional[Dict]) -> str:
    """
    Format new-format SOW content into a string for the LLM prompt.
    Shows selected vs not-selected sections clearly.
    """
    ss = selected_sections or {}
    selected_ex_ids = [str(i) for i in ss.get("exercise_ids", [])]

    recall = lb_ab.get("recall")
    vocabulary = lb_ab.get("vocabulary")
    warm_up = lb_ab.get("warm_up")
    exercises_list = lb_ab.get("exercises", [])
    diff = lb_ab.get("differentiated_instruction")
    ext = lb_ab.get("extension_activity")

    parts = []

    # Header
    parts.append(f"**{lesson['unit_number']}. {lesson['unit_title']}**")
    parts.append(f"Lesson {lesson['lesson_number']}: {lesson['lesson_title']}")
    parts.append("")

    # Selections summary
    ex_titles = []
    for ex in exercises_list:
        if str(ex.get("exercise_id")) in selected_ex_ids:
            ex_titles.append(ex.get("title", ""))
    sel_parts = []
    sel_parts.append("✓ Recall" if ss.get("recall") else "✗ Recall")
    sel_parts.append("✓ Vocabulary" if ss.get("vocabulary") else "✗ Vocabulary")
    sel_parts.append("✓ Warm-up" if ss.get("warmup") else "✗ Warm-up")
    if ex_titles:
        sel_parts.append(f"Exercises: {', '.join(ex_titles)}")
    else:
        sel_parts.append("Exercises: none selected")
    sel_parts.append("✓ Differentiated" if ss.get("differentiated") else "✗ Differentiated (LLM will create)")
    sel_parts.append("✓ Extension" if ss.get("extension") else "✗ Extension (LLM will create)")
    parts.append("TEACHER SELECTIONS: " + " | ".join(sel_parts))
    parts.append("")

    # Available SLOs and Skills (LLM picks relevant ones)
    slos = lb_ab.get("slos", [])
    skills = lb_ab.get("skills", [])
    if slos:
        parts.append("AVAILABLE SLOs (pick 2-4 relevant to selected sections):")
        for s in slos:
            parts.append(f"  • {s}")
        parts.append("")
    if skills:
        parts.append("AVAILABLE SKILLS (pick 2-4 most actively exercised):")
        parts.append(f"  {', '.join(skills)}")
        parts.append("")

    # RECALL
    if ss.get("recall") and recall:
        parts.append("## RECALL / RECAP")
        parts.append(f"Title: {recall.get('title', '')}")
        parts.append(recall.get("description", ""))
        if recall.get("afl_strategies"):
            parts.append(f"AFL: {', '.join(recall['afl_strategies'])}")
        parts.append("")

    # VOCABULARY
    if ss.get("vocabulary") and vocabulary:
        parts.append("## VOCABULARY")
        words = vocabulary.get("words", [])
        if words:
            parts.append(f"Words: {', '.join(words)}")
        for act in vocabulary.get("activities", []):
            if not act.get("optional", False):
                parts.append(f"Activity — {act.get('title', '')}: {act.get('description', '')}")
        parts.append("")

    # WARM-UP
    if ss.get("warmup") and warm_up:
        parts.append("## WARM-UP")
        for act in warm_up.get("activities", []):
            parts.append(f"• {act.get('title', '')}: {act.get('description', '')}")
            dr = act.get("digital_resource", "")
            if dr:
                parts.append(f"  [Digital resource: {dr}]")
            if act.get("afl_strategies"):
                parts.append(f"  AFL: {', '.join(act['afl_strategies'])}")
        if warm_up.get("afl_strategies"):
            parts.append(f"Overall AFL: {', '.join(warm_up['afl_strategies'])}")
        parts.append("")

    # EXERCISES (selected ones, in order)
    if selected_ex_ids:
        parts.append("## EXERCISES TO COVER")
        parts.append("(Each exercise below MUST become its own <h2> section in the LP, using the exact exercise title)")
        parts.append("")
        for ex in exercises_list:
            if str(ex.get("exercise_id")) not in selected_ex_ids:
                continue
            parts.append(f"--- EXERCISE: \"{ex.get('title', '')}\" ---")
            for sub in ex.get("sub_activities", []):
                parts.append(f"  Sub-activity: {sub.get('title', '')}")
                parts.append(f"  {sub.get('description', '')}")
                t = sub.get("audio_track")
                if t:
                    parts.append(f"  [Audio Track {t}]")
                dr = sub.get("digital_resource", "")
                if dr:
                    parts.append(f"  [Resource: {dr}]")
                if sub.get("afl_strategies"):
                    parts.append(f"  AFL: {', '.join(sub['afl_strategies'])}")
                parts.append("")
            if ex.get("afl_strategies"):
                parts.append(f"  Exercise AFL: {', '.join(ex['afl_strategies'])}")
            parts.append("")

    # DIFFERENTIATED INSTRUCTION
    parts.append("## DIFFERENTIATED INSTRUCTION")
    if ss.get("differentiated") and diff and diff.get("description"):
        parts.append("(From SOW — use this content:)")
        parts.append(diff.get("description", ""))
    else:
        parts.append("(Not selected or not in SOW — create appropriate 3-level activity based on lesson content:)")
        parts.append("  Struggling: scaffold with sentence frames / word banks / picture support")
        parts.append("  On-level: standard lesson activity")
        parts.append("  Advanced: challenge extension or higher-order task")
    parts.append("")

    # EXTENSION ACTIVITY
    parts.append("## EXTENSION ACTIVITY")
    if ss.get("extension") and ext and ext.get("description"):
        parts.append("(From SOW — use this content:)")
        parts.append(ext.get("description", ""))
    else:
        parts.append("(Not selected or not in SOW — create an appropriate extension based on lesson content)")
    parts.append("")

    # CLASSWORK / HOMEWORK — filter ORT items when ORT not selected
    include_ort_cwhw = ss.get("_has_ort", True)
    cw_hw = lesson.get("classwork_homework", [])
    if cw_hw:
        filtered_cw_hw = []
        for item in cw_hw:
            item_lower = item.lower()
            is_ort_item = "ort" in item_lower or "oxford reading" in item_lower
            if is_ort_item and not include_ort_cwhw:
                continue
            filtered_cw_hw.append(item)
        if filtered_cw_hw:
            parts.append("## CLASSWORK / HOMEWORK (from SOW)")
            for item in filtered_cw_hw:
                parts.append(f"  {item}")
            parts.append("")

    return "\n".join(parts)


# ============ MAIN CONTEXT FUNCTION ============

def get_lesson_context_by_number(
    sow_data: Dict[str, Any],
    lesson_number: int,
    lesson_type: Optional[str] = None,
    filter_pages: Optional[List[int]] = None,
    exercises_text: Optional[str] = None,       # LEGACY
    selected_sections: Optional[Dict] = None    # NEW
) -> Dict[str, Any]:
    """
    Get complete lesson context. Supports both old (teaching_sequence) and
    new (recall/vocabulary/warm_up/exercises/...) SOW formats.
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
        # ORT section — use old structure (reading_stages) or fallback
        section = lesson.get("ort", {})
        section_name = "ORT"
        slos = section.get("slos", [])
        skills = section.get("skills", [])
        vocabulary = section.get("vocabulary", {})
        ort_pages = section.get("pages", [])

        # Build external resources from old-style content scan
        external_resources = []
        seen_refs: Set = set()
        reading_stages = section.get("reading_stages", {})
        for stage_name, stage in reading_stages.items():
            for act in stage.get("activities", []):
                desc = act.get("description", "")
                for m in re.finditer(r'[Aa]udio [Tt]rack\s+(\d+)', desc):
                    ref = f"Track {m.group(1)}"
                    if ref not in seen_refs:
                        seen_refs.add(ref)
                        external_resources.append({"title": f"Audio Track {m.group(1)}", "type": "audio", "reference": ref})
                for m in re.finditer(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+', desc):
                    url = m.group(0).rstrip(".,;)")
                    if url not in seen_refs:
                        seen_refs.add(url)
                        external_resources.append({"title": "Video Resource", "type": "video", "reference": url})

        return {
            "found": True,
            "unit": f"Unit {lesson['unit_number']}: {lesson['unit_title']}",
            "lesson_number": lesson["lesson_number"],
            "lesson_title": lesson["lesson_title"],
            "section_name": section_name,
            "student_learning_outcomes": slos,
            "skills": skills,
            "teaching_sequence": [],  # ORT uses reading_stages instead
            "classwork_homework": lesson.get("classwork_homework", []),
            "pages_found_in_sow": True,
            "external_resources": external_resources,
            "exercise_step_indices": [],
            "book_title": section.get("book_title", ""),
            "story_title": section.get("story_title", ""),
            "ort_pages": ort_pages,
            "vocabulary": vocabulary.get("words", []) if vocabulary else [],
            "reading_stages": reading_stages,
            "book_references": [],
            "sow_format": "ort"
        }

    # LB/AB section
    section = lesson.get("lb_ab", {})
    section_name = "LB/AB"
    slos = section.get("slos", [])
    skills = section.get("skills", [])

    if _is_new_format(section):
        # ─── NEW FORMAT ───
        external_resources = _extract_resources_new_format(section, selected_sections)
        return {
            "found": True,
            "unit": f"Unit {lesson['unit_number']}: {lesson['unit_title']}",
            "lesson_number": lesson["lesson_number"],
            "lesson_title": lesson["lesson_title"],
            "section_name": section_name,
            "student_learning_outcomes": slos,
            "skills": skills,
            "teaching_sequence": [],          # not used in new format
            "classwork_homework": lesson.get("classwork_homework", []),
            "pages_found_in_sow": True,
            "external_resources": external_resources,
            "exercise_step_indices": [],
            "selected_sections": selected_sections,
            "lb_ab_raw": section,             # raw section for formatter
            "lesson_raw": lesson,             # raw lesson for formatter
            "book_references": [],
            "sow_format": "new"
        }
    else:
        # ─── LEGACY FORMAT (teaching_sequence) ───
        full_teaching_sequence = section.get("teaching_sequence", [])
        external_resources = []
        seen_refs: Set = set()
        for step in full_teaching_sequence:
            content = step.get("content", "")
            for m in re.finditer(r'[Aa]udio [Tt]rack\s+(\d+)', content):
                ref = f"Track {m.group(1)}"
                if ref not in seen_refs:
                    seen_refs.add(ref)
                    external_resources.append({"title": f"Audio Track {m.group(1)}", "type": "audio", "reference": ref})
            for m in re.finditer(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+', content):
                url = m.group(0).rstrip(".,;)")
                if url not in seen_refs:
                    seen_refs.add(url)
                    external_resources.append({"title": "Video Resource", "type": "video", "reference": url})

        teaching_sequence = full_teaching_sequence
        pages_found_in_sow = True
        if filter_pages:
            filtered = filter_teaching_sequence_by_pages(full_teaching_sequence, filter_pages)
            if len(filtered) >= 3:
                teaching_sequence = filtered
            elif len(filtered) == 0:
                pages_found_in_sow = False

        exercise_step_indices = set()
        if exercises_text:
            names = [e.strip().lower() for e in exercises_text.split(',') if e.strip()]
            for i, step in enumerate(teaching_sequence):
                s = step.get("strategy", "").lower()
                c = step.get("content", "").lower()
                if any(n in s or n in c for n in names):
                    exercise_step_indices.add(i)

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
            "exercise_step_indices": sorted(list(exercise_step_indices)),
            "book_references": [],
            "sow_format": "legacy"
        }


# ============ FORMAT FOR PROMPT ============

def format_lesson_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format lesson context into a string for the LLM prompt."""
    if not context.get("found"):
        return "No SOW lesson found. Generate based on textbook content only."

    sow_format = context.get("sow_format", "legacy")

    if sow_format == "new":
        lb_ab = context.get("lb_ab_raw", {})
        lesson = context.get("lesson_raw", {})
        selected_sections = context.get("selected_sections")
        return _format_new_structure_for_prompt(lesson, lb_ab, selected_sections)

    if sow_format == "ort":
        return _format_ort_context_for_prompt(context)

    # LEGACY format
    return _format_legacy_context_for_prompt(context)


def _format_legacy_context_for_prompt(context: Dict[str, Any]) -> str:
    parts = []
    if context.get("pages_found_in_sow") is False:
        parts.append("⚠️ No explicit page references found in SOW. Full lesson context provided.")
        parts.append("")
    parts.append(f"**{context.get('unit', '')}**")
    parts.append(f"Lesson {context.get('lesson_number')}: {context.get('lesson_title')}")
    parts.append(f"Section: {context.get('section_name', '')}")
    if context.get("student_learning_outcomes"):
        parts.append(f"\n**Student Learning Outcomes:**")
        for s in context["student_learning_outcomes"]:
            parts.append(f"  • {s}")
    if context.get("skills"):
        parts.append(f"\n**Skills:** {', '.join(context['skills'])}")
    if context.get("teaching_sequence"):
        parts.append(f"\n**Teaching Strategies (in sequence):**")
        exercise_indices = set(context.get("exercise_step_indices", []))
        for i, step in enumerate(context["teaching_sequence"]):
            strategy = step.get("strategy", "")
            content = step.get("content", "")
            afl = step.get("afl", [])
            focus = " ★ TEACHER'S FOCUS" if i in exercise_indices else ""
            parts.append(f"\n  {i+1}. **{strategy}**{focus}")
            if content:
                indented = "\n".join(f"     {line}" for line in content.split("\n") if line.strip())
                parts.append(indented)
            if afl:
                parts.append(f"     ▶ AFL Strategy: {', '.join(afl)}")
    ext = [r for r in context.get("external_resources", []) if r.get("type") == "audio"]
    vid = [r for r in context.get("external_resources", []) if r.get("type") == "video"]
    if ext:
        parts.append(f"\n**Audio Resources:**")
        for r in ext:
            parts.append(f"  • {r['title']} (reference: {r['reference']})")
    if vid:
        parts.append(f"\n**Video Resources:**")
        for r in vid:
            parts.append(f"  • {r['title']}: {r['reference']}")
    if context.get("classwork_homework"):
        parts.append(f"\n**Classwork/Homework:**")
        for item in context["classwork_homework"]:
            parts.append(f"  • {item}")
    return "\n".join(parts)


def _format_ort_context_for_prompt(context: Dict[str, Any]) -> str:
    parts = []
    parts.append(f"**{context.get('unit', '')}**")
    parts.append(f"Lesson {context.get('lesson_number')}: {context.get('lesson_title')}")
    parts.append(f"ORT Book: {context.get('book_title', '')} — {context.get('story_title', '')}")
    if context.get("ort_pages"):
        parts.append(f"Pages: {context['ort_pages']}")
    if context.get("vocabulary"):
        parts.append(f"Vocabulary: {', '.join(context['vocabulary'])}")
    if context.get("student_learning_outcomes"):
        parts.append("\n**SLOs:**")
        for s in context["student_learning_outcomes"]:
            parts.append(f"  • {s}")
    stages = context.get("reading_stages", {})
    if stages:
        parts.append("\n**Reading Stages:**")
        for stage_name, stage in stages.items():
            parts.append(f"\n  [{stage_name.upper().replace('_', ' ')}]")
            for act in stage.get("activities", []):
                parts.append(f"  • {act.get('title', '')}: {act.get('description', '')}")
    ext = [r for r in context.get("external_resources", []) if r.get("type") == "audio"]
    vid = [r for r in context.get("external_resources", []) if r.get("type") == "video"]
    if ext:
        parts.append("\n**Audio Resources:**")
        for r in ext:
            parts.append(f"  • {r['title']} (reference: {r['reference']})")
    if vid:
        parts.append("\n**Video Resources:**")
        for r in vid:
            parts.append(f"  • {r['title']}: {r['reference']}")
    return "\n".join(parts)


# ============ BOOK TYPE MAPPING ============

def map_book_type_to_db(book_type: str) -> str:
    mapping = {
        "LB": "learners", "AB": "activity", "TR": "teachers_resource",
        "ORT": "reading", "CB": "course_book", "WB": "workbook"
    }
    return mapping.get(book_type.upper(), book_type.lower())


def map_db_to_book_type(db_type: str) -> str:
    mapping = {
        "learners": "LB", "activity": "AB", "teachers_resource": "TR",
        "reading": "ORT", "course_book": "CB", "workbook": "WB"
    }
    return mapping.get(db_type, db_type.upper())


def get_available_book_types(sow_data: Dict[str, Any]) -> List[str]:
    book_types = set()
    curriculum = sow_data.get("curriculum", sow_data)
    for unit in curriculum.get("units", []):
        for lesson in unit.get("lessons", []):
            coverage = get_lesson_page_coverage(lesson)
            book_types.update(coverage.keys())
    return sorted(list(book_types))


# ============ MATH SOW FUNCTIONS ============

def get_math_units(sow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    curriculum = sow_data.get("curriculum", sow_data)
    return [
        {"unit_number": u.get("unit_number", 0), "unit_title": u.get("unit_title", "")}
        for u in curriculum.get("units", [])
    ]


def get_math_unit_by_number(sow_data: Dict[str, Any], unit_number: int) -> Optional[Dict[str, Any]]:
    curriculum = sow_data.get("curriculum", sow_data)
    for unit in curriculum.get("units", []):
        if unit.get("unit_number") == unit_number:
            return {
                "unit_number": unit.get("unit_number", 0),
                "unit_title": unit.get("unit_title", ""),
                "content": unit.get("content", "")
            }
    return None


def format_math_unit_for_prompt(unit: Dict[str, Any]) -> str:
    if not unit:
        return "No Math SOW unit found. Generate based on textbook content only."
    parts = [f"**Chapter {unit.get('unit_number', '')}: {unit.get('unit_title', '')}**", ""]
    content = unit.get("content", "")
    if content:
        parts.append(content)
    return "\n".join(parts)


# ============ LEGACY SUPPORT ============

def filter_teaching_sequence_by_pages(steps: list, pages: list) -> list:
    if not pages:
        return []
    matched = []
    for step in steps:
        content = step.get("content", "")
        for page in pages:
            if re.search(rf'\b(?:pg\.?\s*|page\s*|p\.\s*){page}\b', content, re.IGNORECASE):
                matched.append(step)
                break
    return matched


def extract_pages_with_book_type(text: str) -> List[Tuple[str, int]]:
    if not text:
        return []
    results = []
    range_with_book = r'(LB|AB|TR|ORT)\s*(?:pgs?\.?\s*#?\s*)?(\d+)\s*(?:to|–|-)\s*(\d+)'
    for match in re.finditer(range_with_book, text, re.IGNORECASE):
        book_type = match.group(1).upper()
        start, end = int(match.group(2)), int(match.group(3))
        for page in range(start, end + 1):
            results.append((book_type, page))
    single_with_book = r'(LB|AB|TR|ORT)\s*(?:pgs?\.?\s*#?\s*)?(\d+)(?!\s*(?:to|–|-))'
    for match in re.finditer(single_with_book, text, re.IGNORECASE):
        book_type = match.group(1).upper()
        page = int(match.group(2))
        if (book_type, page) not in results:
            results.append((book_type, page))
    return results
