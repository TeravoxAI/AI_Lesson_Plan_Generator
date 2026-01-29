"""
Lesson Generator - Generate lesson plans using LLM and save to database
"""
import os
import json
import time
from typing import Dict, Any, Optional, Tuple
import httpx

from src.models import LessonType, GenerateResponse, LessonPlan
from src.prompts.templates import (
    LESSON_ARCHITECT_PROMPT,
    LESSON_TYPE_PROMPTS,
    ENG_SYSTEM_PROMPT,
    MATHS_SYSTEM_PROMPT
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
    
    def _build_prompt(
        self,
        grade: str,
        subject: str,
        lesson_type: str,
        book_content: str,
        sow_strategy: str,
        page_start: int,
        page_end: int
    ) -> str:
        """Build the complete prompt for lesson generation"""
        # Start with the main prompt
        prompt = LESSON_ARCHITECT_PROMPT.format(
            grade=grade,
            subject=subject,
            lesson_type=lesson_type,
            book_content=book_content,
            sow_strategy=sow_strategy or "No SOW strategy found. Generate based on textbook content."
        )
        
        # Add lesson-type-specific additions
        type_addition = LESSON_TYPE_PROMPTS.get(lesson_type, "")
        if type_addition:
            prompt += f"\n\n{type_addition}"
        
        return prompt
    
    def _get_system_prompt(self, subject: str) -> str:
        """Get the appropriate system prompt based on subject"""
        if subject.lower() == "mathematics":
            return MATHS_SYSTEM_PROMPT
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
            "Content-Type": "application/json"
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
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

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
    
    def generate(
        self,
        grade: str,
        subject: str,
        lesson_type: LessonType,
        page_start: int,
        page_end: Optional[int] = None,
        topic: Optional[str] = None,
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
                topic=topic
            )

            print(f"\n📝 [GENERATE] Building prompt for {subject} lesson plan...")

            # Extract teacher resources (videos and audio) from SOW context
            teacher_resources = []
            sow_context = context.get("sow_context")
            if sow_context and sow_context.get("found"):
                external_resources = sow_context.get("external_resources", [])

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

            # Build prompt
            prompt = self._build_prompt(
                grade=grade,
                subject=subject,
                lesson_type=lesson_type.value,
                book_content=book_content_str,
                sow_strategy=sow_strategy_str,
                page_start=page_start,
                page_end=page_end
            )

            # Generate lesson plan (HTML) - use subject-specific system prompt
            html_content, usage_data = self._call_llm(prompt, subject)
            
            # Clean up HTML if wrapped in code blocks
            html_content = html_content.strip()
            if html_content.startswith("```"):
                lines = html_content.split("\n")
                html_content = "\n".join(lines[1:-1])

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

                plan_id = db.insert_lesson_plan(
                    grade_level=grade,
                    subject=subject,
                    lesson_type=lesson_type.value,
                    page_start=page_start,
                    page_end=page_end,
                    topic=topic,
                    lesson_plan={"html_content": html_content},
                    textbook_id=textbook_id,
                    sow_entry_id=context["metadata"].get("sow_entry_id"),
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
