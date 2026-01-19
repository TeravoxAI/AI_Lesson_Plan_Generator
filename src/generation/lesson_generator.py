"""
Lesson Generator - Generate lesson plans using LLM and save to database
"""
import os
import json
from typing import Dict, Any, Optional
import httpx

from src.models import LessonType, GenerateResponse, LessonPlan
from src.prompts.templates import LESSON_ARCHITECT_PROMPT, LESSON_TYPE_PROMPTS
from src.generation.router import router
from src.db.client import db


class LessonGenerator:
    """Generate lesson plans using retrieved context and LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "openai/gpt-4.1"
    
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
        
        # Add instruction to return JSON
        prompt += """

IMPORTANT: Return your response as a valid JSON object with this exact structure:
{
    "slos": ["SLO 1", "SLO 2", "SLO 3"],
    "methodology": "Step-by-step methodology text...",
    "brainstorming_activity": "Warm-up activity description...",
    "main_teaching_activity": "Main teaching activity description...",
    "hands_on_activity": "Hands-on activity description...",
    "afl": "Assessment for learning description...",
    "resources": ["Resource 1", "Resource 2"]
}

Return ONLY the JSON object, no markdown code blocks or additional text."""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call OpenRouter LLM for generation"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert curriculum designer and academic coordinator. Generate comprehensive, practical lesson plans that teachers can use directly in classrooms. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
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
            GenerateResponse with the lesson plan
        """
        if page_end is None:
            page_end = page_start
            
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
            
            # Generate lesson plan
            raw_content = self._call_llm(prompt)
            
            # Parse the JSON response
            lesson_plan_dict = self._parse_json_response(raw_content)
            
            # Create LessonPlan object
            lesson_plan = LessonPlan(
                slos=lesson_plan_dict.get("slos", []),
                methodology=lesson_plan_dict.get("methodology", ""),
                brainstorming_activity=lesson_plan_dict.get("brainstorming_activity", ""),
                main_teaching_activity=lesson_plan_dict.get("main_teaching_activity", ""),
                hands_on_activity=lesson_plan_dict.get("hands_on_activity", ""),
                afl=lesson_plan_dict.get("afl", ""),
                resources=lesson_plan_dict.get("resources", [])
            )
            
            # Save to database if enabled
            plan_id = None
            if save_to_db:
                plan_id = db.insert_lesson_plan(
                    grade_level=grade,
                    subject=subject,
                    lesson_type=lesson_type.value,
                    page_start=page_start,
                    page_end=page_end,
                    topic=topic,
                    lesson_plan=lesson_plan_dict,
                    textbook_id=context["metadata"].get("textbook_id"),
                    sow_entry_id=context["metadata"].get("sow_entry_id")
                )
            
            return GenerateResponse(
                success=True,
                lesson_plan=lesson_plan,
                raw_content=raw_content,
                plan_id=plan_id
            )
            
        except Exception as e:
            return GenerateResponse(
                success=False,
                error=str(e)
            )


# Singleton instance
generator = LessonGenerator()
