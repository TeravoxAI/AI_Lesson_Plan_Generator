"""
Lesson Generator - Generate lesson plans using LLM
"""
import os
import json
from typing import Dict, Any, Optional
import httpx

from src.models import LessonType, GenerateResponse, LessonPlan
from src.prompts.templates import LESSON_ARCHITECT_PROMPT, LESSON_TYPE_PROMPTS
from src.generation.router import router


class LessonGenerator:
    """Generate lesson plans using retrieved context and LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "openai/gpt-5.1"
    
    def _build_prompt(
        self,
        grade: str,
        subject: str,
        lesson_type: str,
        book_content: str,
        sow_strategy: str
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
                    "content": "You are an expert curriculum designer and academic coordinator. Generate comprehensive, practical lesson plans that teachers can use directly in classrooms."
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
    
    def generate(
        self,
        grade: str,
        subject: str,
        lesson_type: LessonType,
        page_start: int,
        page_end: Optional[int] = None,
        topic: Optional[str] = None
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
        
        Returns:
            GenerateResponse with the lesson plan
        """
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
                sow_strategy=sow_strategy_str
            )
            
            # Generate lesson plan
            raw_content = self._call_llm(prompt)
            
            # Parse the response (attempt to structure it)
            lesson_plan = self._parse_lesson_plan(raw_content)
            
            return GenerateResponse(
                success=True,
                lesson_plan=lesson_plan,
                raw_content=raw_content
            )
            
        except Exception as e:
            return GenerateResponse(
                success=False,
                error=str(e)
            )
    
    def _parse_lesson_plan(self, content: str) -> Optional[LessonPlan]:
        """
        Attempt to parse the raw content into a structured LessonPlan.
        Returns None if parsing fails (raw_content is still available).
        """
        try:
            # Extract sections using markdown headers
            sections = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('## ') or line.startswith('# '):
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = line.lstrip('#').strip().lower()
                    current_content = []
                else:
                    current_content.append(line)
            
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Map to LessonPlan fields
            def find_section(keywords):
                for key in sections:
                    for kw in keywords:
                        if kw in key:
                            return sections[key]
                return ""
            
            # Extract SLOs (usually a bulleted list)
            slos_text = find_section(['objective', 'slo', 'learning'])
            slos = [line.strip().lstrip('- •*').strip() 
                   for line in slos_text.split('\n') 
                   if line.strip().startswith(('-', '•', '*', '1', '2', '3'))]
            
            # Extract resources
            resources_text = find_section(['resource'])
            resources = [line.strip().lstrip('- •*').strip() 
                        for line in resources_text.split('\n') 
                        if line.strip().startswith(('-', '•', '*'))]
            
            return LessonPlan(
                slos=slos or ["Objective derived from content"],
                methodology=find_section(['methodology', 'method']),
                brainstorming_activity=find_section(['brainstorm', 'warm']),
                main_teaching_activity=find_section(['main', 'teaching activity']),
                hands_on_activity=find_section(['hands', 'hands-on', 'activity']),
                afl=find_section(['afl', 'assessment']),
                resources=resources or ["Textbook pages as specified"]
            )
            
        except Exception:
            return None


# Singleton instance
generator = LessonGenerator()
