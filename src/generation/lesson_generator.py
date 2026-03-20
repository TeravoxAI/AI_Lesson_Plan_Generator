"""
Lesson Generator - Generate lesson plans using LLM and save to database
"""
import os
import json
import time
from typing import Dict, Any, Optional, Tuple
import httpx

from src.models import LessonType, GenerateResponse, LessonPlan, TeacherResource
from src.prompts.templates import (
    LESSON_ARCHITECT_PROMPT,
    LESSON_TYPE_PROMPTS,
    ENG_SYSTEM_PROMPT,
    MATHS_SYSTEM_PROMPT,
    ART_SYSTEM_PROMPT
)
from src.generation.router import router
from src.db.client import db
from src.config import LLM_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL


class LessonGenerator:
    """Generate lesson plans using retrieved context and LLM"""
    
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        self.model = LLM_MODEL
    
    def _build_exercises_html(
        self,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Build deterministic HTML for exercise sections from SOW data (new format only).
        Returns None if not applicable (legacy/ORT/no exercises selected).
        """
        sow_format = context.get("sow_format", "legacy")
        if sow_format != "new":
            return None

        lb_ab = context.get("lb_ab_raw", {})
        selected_sections = context.get("selected_sections") or {}
        selected_ex_ids = [str(i) for i in selected_sections.get("exercise_ids", [])]

        if not selected_ex_ids:
            return None

        exercises_list = lb_ab.get("exercises", [])
        html_parts = []

        for ex in exercises_list:
            if str(ex.get("exercise_id")) not in selected_ex_ids:
                continue

            title = ex.get("title", f"Exercise {ex.get('exercise_id', '')}")
            html_parts.append(f"  <h2>{title}</h2>")
            html_parts.append("  <ul>")

            for sub in ex.get("sub_activities", []):
                sub_title = sub.get("title", "")
                desc = sub.get("description", "")
                audio = sub.get("audio_track")
                resource = sub.get("digital_resource", "")

                # Build bullet: title + description (truncate long descriptions)
                bullet = f"{sub_title}: {desc}".strip(": ") if sub_title else desc
                if bullet:
                    html_parts.append(f"    <li>{bullet}</li>")
                if audio:
                    html_parts.append(f"    <li>Play Audio Track {audio} for students.</li>")
                if resource:
                    # Only include YouTube/video links
                    if "youtube" in resource or "youtu.be" in resource:
                        html_parts.append(f"    <li>Show video resource: {resource}</li>")

            html_parts.append("  </ul>")

        return "\n".join(html_parts) if html_parts else None

    def _inject_exercises(self, html_content: str, exercises_html: Optional[str]) -> str:
        """Replace the EXERCISES_PLACEHOLDER comment with pre-built exercise HTML."""
        placeholder = "<!-- EXERCISES_PLACEHOLDER -->"
        if exercises_html and placeholder in html_content:
            return html_content.replace(placeholder, exercises_html)
        # If no placeholder found but we have exercises, insert before Differentiated or Success Criteria
        if exercises_html and placeholder not in html_content:
            for marker in ["<h2>Differentiated", "<h2>Success Criteria"]:
                if marker in html_content:
                    return html_content.replace(marker, exercises_html + "\n\n  " + marker, 1)
        return html_content

    def _build_prompt(
        self,
        grade: str,
        subject: str,
        lesson_type: str,
        book_content: str,
        sow_strategy: str,
        page_start: int,
        page_end: int,
        period_time: str = "35 minutes",
        club_period_note: str = "",
        exercises: Optional[str] = None,
        selected_sections: Optional[Dict[str, Any]] = None,
        teacher_instructions: Optional[str] = None
    ) -> str:
        """Build the complete prompt for lesson generation"""
        # Derive a label for display in the prompt
        if selected_sections:
            ex_ids = selected_sections.get("exercise_ids", [])
            exercises_label = f"Structured sections (exercises: {ex_ids})"
        elif exercises:
            exercises_label = exercises
        else:
            exercises_label = lesson_type or "General"

        prompt = LESSON_ARCHITECT_PROMPT.format(
            grade=grade,
            subject=subject,
            exercises_label=exercises_label,
            book_content=book_content,
            sow_strategy=sow_strategy or "No SOW strategy found. Generate based on textbook content.",
            period_time=period_time,
            club_period_note=club_period_note
        )

        # Lesson-type-specific additions only for Math / legacy
        if not selected_sections and not exercises:
            type_addition = LESSON_TYPE_PROMPTS.get(lesson_type, "")
            if type_addition:
                prompt += f"\n\n{type_addition}"

        # Append teacher instructions if provided
        if teacher_instructions and teacher_instructions.strip():
            import re as _re
            clean = _re.sub(r'<[^>]+>', '', teacher_instructions).strip()[:300]
            prompt += f"\n\nTEACHER'S ADDITIONAL INSTRUCTIONS (follow these):\n{clean}"

        return prompt
    
    def _get_system_prompt(self, subject: str) -> str:
        """Get the appropriate system prompt based on subject"""
        if subject.lower() == "mathematics":
            return MATHS_SYSTEM_PROMPT
        elif subject.lower() == "art":
            return ART_SYSTEM_PROMPT
        else:
            return ENG_SYSTEM_PROMPT  # Default to English
    
    def _call_llm(self, prompt: str, subject: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call OpenRouter LLM for generation.

        Returns:
            Tuple of (content, usage_data) where usage_data contains:
                - input_tokens: int
                - output_tokens: int
                - total_tokens: int
                - cost: float (from OpenRouter)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://www.ai-lp-generator.teravox.ai/",
            "X-Title": "LP Generator"
        }

        # Select subject-specific system prompt
        system_prompt = self._get_system_prompt(subject)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 8000,
            "temperature": 0.7
        }

        try:
            print(f"\n🤖 [LLM] Calling {self.model}...")
            # 180 second timeout for slow models (Gemini can be slow)
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                print(f"Response from LLM:\n{content}\n")

                # Extract usage data from OpenRouter response
                usage = result.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

                # Get cost from OpenRouter (they provide it!)
                # OpenRouter returns cost in the usage object
                cost = usage.get("cost", 0.0)

                usage_data = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost
                }

                print(f"   ✓ LLM response received ({len(content)} chars)")
                print(f"   📊 Tokens: {input_tokens} in / {output_tokens} out = {total_tokens} total")
                print(f"   💰 Cost: ${cost:.6f}" if cost > 0 else "   💰 Cost: Not reported")

                return content, usage_data

        except Exception as e:
            raise Exception(f"LLM call failed: {e}")
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response to JSON, handling potential markdown wrapping"""
        # Clean up potential markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json) and last line (```)
            content = "\n".join(lines[1:-1])
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a structured response from the text
            return {
                "slos": ["Unable to parse - see raw content"],
                "methodology": content,
                "brainstorming_activity": "",
                "main_teaching_activity": "",
                "hands_on_activity": "",
                "afl": "",
                "resources": []
            }
    
    def generate_math(
        self,
        grade: str,
        unit_number: int,
        course_book_pages: Optional[str] = None,
        workbook_pages: Optional[str] = None,
        book_types: Optional[list] = None,
        teacher_instructions: Optional[str] = None,
        created_by_id: Optional[str] = None,
        save_to_db: bool = True
    ) -> GenerateResponse:
        """
        Generate a Math lesson plan using unit-based context.

        Args:
            grade: Grade level (e.g., "Grade 2")
            unit_number: Unit/chapter number from Math SOW
            course_book_pages: Course book pages (e.g., "145" or "145-150")
            workbook_pages: Optional workbook pages (e.g., "80" or "80-85")
            book_types: List of book type codes to include, e.g. ["CB", "AB"]. Defaults to both.
            created_by_id: User ID of the teacher creating this lesson plan
            save_to_db: Whether to save the generated plan to database

        Returns:
            GenerateResponse with the lesson plan, cost, and time taken
        """
        subject = "Mathematics"
        start_time = time.time()

        try:
            # Resolve book_types: default to both if not specified
            resolved_book_types = book_types if book_types else ["CB", "AB"]

            # Retrieve Math context using unit and page numbers
            context = router.retrieve_math_context(
                grade=grade,
                unit_number=unit_number,
                course_book_pages=course_book_pages,
                workbook_pages=workbook_pages,
                book_types=resolved_book_types
            )

            print(f"\n📝 [GENERATE] Building prompt for Math lesson plan...")

            # Extract teacher resources from SOW context if available
            teacher_resources = []
            sow_context = context.get("sow_context")
            if sow_context:
                # For Math SOW, resources might be embedded in content
                # Extract URLs from content if present
                content = sow_context.get("content", "")
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, content)
                for url in urls:
                    if "youtube" in url or "youtu.be" in url:
                        teacher_resources.append({
                            "title": "Video Resource",
                            "type": "video",
                            "reference": url
                        })

            # Format content for prompt
            book_content_str = router.format_book_content(context["book_content"])
            sow_strategy_str = context.get("sow_strategy", "")

            # Build prompt for Math (use "concept" as default lesson type for prompt building)
            prompt = self._build_prompt(
                grade=grade,
                subject=subject,
                lesson_type="concept",
                book_content=book_content_str,
                sow_strategy=sow_strategy_str,
                page_start=0,
                page_end=0,
                teacher_instructions=teacher_instructions
            )

            # Append book availability constraint so LLM only references provided books
            if "CB" in resolved_book_types and "AB" not in resolved_book_types:
                prompt += "\n\nIMPORTANT: Only Course Book (CB) content has been provided. Reference ONLY CB pages in Resources and Classwork. Do NOT reference WB, AB, or any workbook pages."
            elif "AB" in resolved_book_types and "CB" not in resolved_book_types:
                prompt += "\n\nIMPORTANT: Only Activity Book (AB) content has been provided. Reference ONLY AB pages in Resources and Classwork. Do NOT reference CB or course book pages."

            # Generate lesson plan (HTML)
            html_content, usage_data = self._call_llm(prompt, subject)

            # Clean up HTML if wrapped in code blocks
            html_content = html_content.strip()
            if html_content.startswith("```"):
                lines = html_content.split("\n")
                html_content = "\n".join(lines[1:-1])

            # Calculate time taken
            end_time = time.time()
            generation_time = round(end_time - start_time, 2)

            print(f"   ✓ Math lesson plan generated successfully!")
            print(f"Lesson Plan:\n{html_content}")
            print(f"   HTML length: {len(html_content)} chars")
            print(f"   ⏱️  Time: {generation_time}s")

            # Save to database if enabled
            plan_id = None
            unit_title = sow_context.get("unit_title", "") if sow_context else ""
            math_topic = f"Chapter {unit_number}: {unit_title}" if unit_title else f"Chapter {unit_number}: {course_book_pages}"
            if save_to_db:
                textbook_ids = context["metadata"].get("textbook_ids", [])
                textbook_id = textbook_ids[0] if textbook_ids else None

                plan_id = db.insert_lesson_plan(
                    grade_level=grade,
                    subject=subject,
                    lesson_type=f"unit_{unit_number}",  # Store unit number as lesson type
                    page_start=0,
                    page_end=0,
                    topic=math_topic,
                    lesson_plan={"html_content": html_content},
                    textbook_id=textbook_id,
                    sow_entry_id=context["metadata"].get("sow_entry_id"),
                    created_by_id=created_by_id,
                    generation_time=generation_time,
                    cost=usage_data["cost"],
                    input_tokens=usage_data["input_tokens"],
                    output_tokens=usage_data["output_tokens"],
                    total_tokens=usage_data["total_tokens"]
                )

            return GenerateResponse(
                success=True,
                html_content=html_content,
                plan_id=plan_id,
                topic=math_topic,
                teacher_resources=teacher_resources,
                generation_time=generation_time,
                cost=usage_data["cost"],
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                total_tokens=usage_data["total_tokens"]
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return GenerateResponse(
                success=False,
                error=str(e)
            )

    def generate_art(
        self,
        grade: str,
        week_number: int,
        selected_topics: list[str],
        tb_pages: Optional[str] = None,
        teacher_instructions: Optional[str] = None,
        created_by_id: Optional[str] = None,
        save_to_db: bool = True
    ) -> GenerateResponse:
        """
        Generate an Art lesson plan using week/topic-based SOW context.

        Args:
            grade: Grade level (e.g., "Grade 2")
            week_number: Week number from Art SOW
            selected_topics: List of topic names selected by the teacher
            tb_pages: Optional Art textbook pages (e.g., "21-22")
            teacher_instructions: Optional freeform teacher notes
            created_by_id: User ID of the teacher
            save_to_db: Whether to save the generated plan to database

        Returns:
            GenerateResponse with the lesson plan, cost, and time taken
        """
        subject = "Art"
        start_time = time.time()

        try:
            # Retrieve Art context
            context = router.retrieve_art_context(
                grade=grade,
                week_number=week_number,
                selected_topics=selected_topics,
                tb_pages=tb_pages
            )

            print(f"\n📝 [GENERATE] Building prompt for Art lesson plan...")

            # Extract video resources from SOW topics
            teacher_resources = []
            topics = context.get("sow_context", [])
            seen_urls = set()
            for topic in topics:
                strategy = topic.get("teaching_strategy", {})
                for url in strategy.get("digital_resources", []):
                    if url and ("youtube" in url or "youtu.be" in url) and url not in seen_urls:
                        seen_urls.add(url)
                        teacher_resources.append({
                            "title": "Video Resource",
                            "type": "video",
                            "reference": url
                        })

            if teacher_resources:
                print(f"\n📹 [RESOURCES] Found {len(teacher_resources)} video(s)")
                for res in teacher_resources:
                    print(f"   📹 {res['title']}: {res['reference'][:60]}...")

            # Format content for prompt
            book_content_str = router.format_book_content(context["book_content"])
            sow_strategy_str = context.get("sow_strategy", "")

            # Build prompt using LESSON_ARCHITECT_PROMPT template
            prompt = self._build_prompt(
                grade=grade,
                subject=subject,
                lesson_type="general",
                book_content=book_content_str,
                sow_strategy=sow_strategy_str,
                page_start=0,
                page_end=0,
                period_time="35 minutes",
                club_period_note="",
                teacher_instructions=teacher_instructions
            )

            # Generate lesson plan (HTML) using Art system prompt
            html_content, usage_data = self._call_llm(prompt, subject)

            # Clean up HTML if wrapped in code blocks
            html_content = html_content.strip()
            if html_content.startswith("```"):
                lines = html_content.split("\n")
                html_content = "\n".join(lines[1:-1])

            # Calculate time taken
            end_time = time.time()
            generation_time = round(end_time - start_time, 2)

            print(f"   ✓ Art lesson plan generated successfully!")
            print(f"   HTML length: {len(html_content)} chars")
            print(f"   ⏱️  Time: {generation_time}s")

            # Build topic string
            topic_names = [t.get("topic", "") for t in topics]
            art_topic = f"Week {week_number}: {', '.join(topic_names)}" if topic_names else f"Week {week_number}"

            # Save to database if enabled
            plan_id = None
            if save_to_db:
                textbook_ids = context["metadata"].get("textbook_ids", [])
                textbook_id = textbook_ids[0] if textbook_ids else None

                plan_id = db.insert_lesson_plan(
                    grade_level=grade,
                    subject=subject,
                    lesson_type=f"week_{week_number}",
                    page_start=0,
                    page_end=0,
                    topic=art_topic,
                    lesson_plan={"html_content": html_content},
                    textbook_id=textbook_id,
                    sow_entry_id=context["metadata"].get("sow_entry_id"),
                    created_by_id=created_by_id,
                    generation_time=generation_time,
                    cost=usage_data["cost"],
                    input_tokens=usage_data["input_tokens"],
                    output_tokens=usage_data["output_tokens"],
                    total_tokens=usage_data["total_tokens"]
                )

            return GenerateResponse(
                success=True,
                html_content=html_content,
                plan_id=plan_id,
                topic=art_topic,
                teacher_resources=[
                    TeacherResource(title=r["title"], type=r["type"], reference=r["reference"])
                    for r in teacher_resources
                ],
                generation_time=generation_time,
                cost=usage_data["cost"],
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                total_tokens=usage_data["total_tokens"]
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return GenerateResponse(
                success=False,
                error=str(e)
            )

    def generate(
        self,
        grade: str,
        subject: str,
        lesson_type: Optional[LessonType],
        page_start: int,
        page_end: Optional[int] = None,
        topic: Optional[str] = None,
        lb_pages: Optional[str] = None,
        ab_pages: Optional[str] = None,
        ort_pages: Optional[str] = None,
        is_club_period: bool = False,
        selected_sections: Optional[Dict[str, Any]] = None,
        exercises: Optional[str] = None,  # LEGACY
        teacher_instructions: Optional[str] = None,
        created_by_id: Optional[str] = None,
        save_to_db: bool = True
    ) -> GenerateResponse:
        """
        Generate a complete lesson plan.

        Args:
            grade: Grade level (e.g., "Grade 2")
            subject: Subject name
            lesson_type: Type of lesson
            page_start: Starting page number
            page_end: Ending page number
            topic: Optional topic for English
            save_to_db: Whether to save the generated plan to database

        Returns:
            GenerateResponse with the lesson plan, cost, and time taken
        """
        if page_end is None:
            page_end = page_start

        # Start timing
        start_time = time.time()

        try:
            # Import Subject enum for router
            from src.models import Subject as SubjectEnum
            subject_enum = SubjectEnum(subject)

            # Retrieve context using router
            context = router.retrieve_context(
                grade=grade,
                subject=subject_enum,
                lesson_type=lesson_type,
                page_start=page_start,
                page_end=page_end,
                topic=topic,
                lb_pages=lb_pages,
                ab_pages=ab_pages,
                ort_pages=ort_pages,
                selected_sections=selected_sections,
                exercises=exercises
            )

            print(f"\n📝 [GENERATE] Building prompt for {subject} lesson plan...")

            # Extract teacher resources (videos and audio) from SOW context.
            # Only include resources when the pages were actually found in the SOW.
            # If pages_found_in_sow=False the full-lesson fallback is used, meaning
            # audio tracks / YouTube links may come from a completely different topic.
            teacher_resources = []
            sow_context = context.get("sow_context")
            # Build full topic string: "Unit 8: Lesson 1: What kind of homes do people and animals build?"
            if sow_context and sow_context.get("found"):
                unit_str   = sow_context.get("unit", "")            # "Unit 8: Home, sweet home"
                unit_part  = unit_str.split(":")[0].strip()          # "Unit 8"
                lesson_num = sow_context.get("lesson_number", page_start)
                lesson_title = sow_context.get("lesson_title", "")
                if unit_part and lesson_title:
                    resolved_topic = f"{unit_part}: Lesson {lesson_num}: {lesson_title}"
                else:
                    resolved_topic = topic or lesson_title or None
            else:
                resolved_topic = topic or None
            if sow_context and sow_context.get("found"):
                pages_found_in_sow = sow_context.get("pages_found_in_sow", True)
                if not pages_found_in_sow:
                    print(f"   ⚠ pages_found_in_sow=False — skipping external resources to avoid unrelated content")
                external_resources = sow_context.get("external_resources", []) if pages_found_in_sow else []

                for res in external_resources:
                    res_type = res.get("type")
                    if res_type not in ["video", "audio"] or not res.get("reference"):
                        continue

                    reference = res.get("reference", "")
                    title = res.get("title", f"{res_type.title()} Resource")

                    # For audio tracks, construct API endpoint URL
                    if res_type == "audio":
                        # Extract track number from reference (e.g., "Track 70" -> 70)
                        import re
                        track_match = re.search(r'Track\s+(\d+)', reference, re.IGNORECASE)
                        if track_match:
                            track_num = track_match.group(1)
                            # Normalize grade for URL (e.g., "Grade 2" -> "2")
                            grade_num = grade.replace("Grade ", "").replace("grade ", "").strip()
                            # Construct API endpoint: /audio/2/English/70
                            reference = f"/audio/{grade_num}/{subject}/{track_num}"

                    teacher_resources.append({
                        "title": title,
                        "type": res_type,
                        "reference": reference
                    })

                if teacher_resources:
                    video_count = sum(1 for r in teacher_resources if r["type"] == "video")
                    audio_count = sum(1 for r in teacher_resources if r["type"] == "audio")
                    print(f"\n📹 [RESOURCES] Found {video_count} video(s) and {audio_count} audio track(s)")
                    for res in teacher_resources:
                        icon = "📹" if res["type"] == "video" else "🔊"
                        ref_preview = res['reference'][:60] if len(res['reference']) > 60 else res['reference']
                        print(f"   {icon} {res['title']}: {ref_preview}...")

            # Format content for prompt
            book_content_str = router.format_book_content(context["book_content"])
            sow_strategy_str = context.get("sow_strategy", "")

            # Compute period duration for the prompt
            if is_club_period:
                period_time = "70 minutes (Club Period — 2 consecutive periods)"
                club_period_note = (
                    "NOTE: This is a CLUB PERIOD (2 consecutive lessons). Structure the plan in two phases:\n"
                    "  Phase 1 (~35 min): Introduction, teaching, guided practice\n"
                    "  Phase 2 (~35 min): Independent practice, extension activity, assessment"
                )
            else:
                period_time = "35 minutes"
                club_period_note = ""

            # Build prompt
            prompt = self._build_prompt(
                grade=grade,
                subject=subject,
                lesson_type=lesson_type.value if lesson_type else "general",
                book_content=book_content_str,
                sow_strategy=sow_strategy_str,
                page_start=page_start,
                page_end=page_end,
                period_time=period_time,
                club_period_note=club_period_note,
                exercises=exercises,
                selected_sections=selected_sections,
                teacher_instructions=teacher_instructions
            )

            # Pre-build deterministic exercise HTML (new format only)
            exercises_html = self._build_exercises_html(context.get("sow_context") or context)

            # Generate lesson plan (HTML) - use subject-specific system prompt
            html_content, usage_data = self._call_llm(prompt, subject)

            # Clean up HTML if wrapped in code blocks
            html_content = html_content.strip()
            if html_content.startswith("```"):
                lines = html_content.split("\n")
                html_content = "\n".join(lines[1:-1])

            # Inject deterministic exercise sections
            html_content = self._inject_exercises(html_content, exercises_html)

            # Calculate time taken
            end_time = time.time()
            generation_time = round(end_time - start_time, 2)

            print(f"   ✓ Lesson plan generated successfully!")
            print(f"   HTML length: {len(html_content)} chars")
            print(f"   ⏱️  Time: {generation_time}s")

            # Save to database if enabled
            plan_id = None
            if save_to_db:
                # Get first textbook_id from list (for backwards compatibility)
                textbook_ids = context["metadata"].get("textbook_ids", [])
                textbook_id = textbook_ids[0] if textbook_ids else None

                if selected_sections:
                    ex_ids = selected_sections.get("exercise_ids", [])
                    db_lesson_type = ("ex:" + ",".join(str(i) for i in ex_ids))[:50]
                elif exercises:
                    db_lesson_type = exercises[:50]
                else:
                    db_lesson_type = lesson_type.value if lesson_type else "exercises"
                plan_id = db.insert_lesson_plan(
                    grade_level=grade,
                    subject=subject,
                    lesson_type=db_lesson_type,
                    page_start=page_start,
                    page_end=page_end,
                    topic=resolved_topic,
                    lesson_plan={"html_content": html_content},
                    textbook_id=textbook_id,
                    sow_entry_id=context["metadata"].get("sow_entry_id"),
                    created_by_id=created_by_id,
                    generation_time=generation_time,
                    cost=usage_data["cost"],
                    input_tokens=usage_data["input_tokens"],
                    output_tokens=usage_data["output_tokens"],
                    total_tokens=usage_data["total_tokens"]
                )

            return GenerateResponse(
                success=True,
                html_content=html_content,
                plan_id=plan_id,
                topic=resolved_topic,
                teacher_resources=teacher_resources,
                generation_time=generation_time,
                cost=usage_data["cost"],
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                total_tokens=usage_data["total_tokens"]
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return GenerateResponse(
                success=False,
                error=str(e)
            )


# Singleton instance
generator = LessonGenerator()
