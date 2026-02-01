import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
# from template import SYSTEM_PROMPT

load_dotenv()


SYSTEM_PROMPT = """
ROLE:
You are an expert curriculum parser and instructional designer for English Curriculum.

Your task is to read and parse the provided Scheme of Work (SoW) and generate a fully populated JSON output that strictly follows the schema and rules below.

1. INPUT MATERIAL
You will be given a Scheme of Work.
The Scheme of Work contains unit titles and numbers, lesson numbers and titles, teaching activities, strategies, audio or video references, and Learner’s Book (LB), Activity Book (AB), Oxford Reading Tree (ORT), and Teacher Resource (TR) page references.
You must extract information only from the Scheme of Work. Do not hallucinate lesson content, page numbers, or activities.

2. OUTPUT FORMAT (STRICT)
Your output must be valid JSON and conform exactly to the following structure:

{
  "curriculum": {
    "units": [
      {
        "unit_number": 8,
        "unit_title": "Unit Title",
        "lessons": [
          {
            "lesson_number": 1,
            "lesson_title": "Lesson Title",
            "lesson_plan_types": [
              {
                "type": "recall_review",
                "content": "Extracted SoW content relevant to this LP type",
                "learning_strategies": ["Strategy from SoW"],
                "student_learning_outcomes": ["Grade-appropriate SLO derived from SoW"],
                "skills": ["Listening", "Speaking", "Reading", "Writing", "Thinking"],
                "book_references": [
                  {
                    "book_type": "LB | AB | TR | ORT",
                    "book_name": "Full book name",
                    "pages": [110, 111]
                  }
                ],
                "external_resources": [
                  {
                    "title": "Audio / Video / Online Resource",
                    "type": "audio | video | document | interactive",
                    "reference": "Track number or URL if mentioned"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}

3. APPROVED LESSON PLAN TYPES (DO NOT ADD OR REMOVE)
You may ONLY use the following lesson plan types:
- recall_review
- vocabulary_word_meaning
- listening_audio_video
- reading_decoding_fluency
- reading_comprehension
- grammar_phonics
- speaking_oral_language
- writing_guided_creative

Each lesson plan type must represent a complete 45-minute lesson.

4. LP TYPE MAPPING RULES
For each lesson:
- Identify which lesson plan types are naturally present based on the Scheme of Work
- Do not force all lesson plan types into every lesson
- Typical lessons will contain 3 to 6 lesson plan types


5. CONTENT EXTRACTION RULES
Content:
- Retrieve only the relevant Scheme of Work activities for that lesson plan type, preserving the original content

Learning strategies:
- Extract named strategies from the Scheme of Work where it fits the lesson plan type (e.g., Think-Pair-Share, Paired Reading)

Student learning outcomes:
- Choose the relevant Student Learning Outcomes (SLOs) from Scheme of Work related to the lesson plan type and its content.
- Begin outcomes with verbs such as identify, describe, read, listen, speak, or write
- Outcomes must align with the lesson plan type

Skills:
Choose the relevant skills from Scheme of Work related to the lesson plan type and its content. Skills can include but not limited to:
- Listening
- Speaking
- Reading
- Writing
- Phonics
- Vocabulary
- Critical thinking
- Collaboration

6. BOOK REFERENCES
- Extract exact page numbers from the Scheme of Work
- Use correct book types: LB, AB, TR, ORT
- If no page number is mentioned for a lesson plan type, omit the reference

7. EXTERNAL RESOURCES
- Include only if explicitly mentioned in the Scheme of Work
- Use track numbers when URLs are not provided
- Do not invent links or resources

8. QUALITY AND VALIDATION RULES
- Output must be machine-readable JSON only
- Do not include markdown, explanations, or commentary
- Do not include trailing commas
- Do not duplicate lesson plan types within a lesson
- Lesson numbers and titles must exactly match the Scheme of Work
- Preserve the original unit and lesson structure
- Do not add any additional information or comments
- Preserve the original content of the Scheme of Work
"""

class BookDigitizationAgent:
    def __init__(self, model="openai/gpt-5.1"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = model

    def _convert_pdf_to_images(self, pdf_path):
        from pdf2image import convert_from_path
        import io

        images = convert_from_path(pdf_path)
        base64_images = []

        for image in images:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_images.append(img_str)

        return base64_images

    def parse_book_pages(self, pdf_path, system_prompt):
        base64_images = self._convert_pdf_to_images(pdf_path)

        content_list = [
            {"type": "text", "text": "Parse the attached Scheme of Work PDF"}
        ]

        for base64_img in base64_images:
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_img}"
                }
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": content_list
            }
        ],
            response_format={"type": "json_object"},
            temperature=0
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("Empty response from model")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError("Model returned invalid JSON") from e


# ==========================
# Usage
# ==========================
if __name__ == "__main__":
    agent = BookDigitizationAgent()

    try:
        pages_data = agent.parse_book_pages("unit 8.pdf", SYSTEM_PROMPT)
        with open("sow1.json", "w", encoding="utf-8") as f:
            json.dump(pages_data, f, indent=4, ensure_ascii=False)

        print("✅ Result saved to sow1.json")

    except Exception as e:
        print(f"❌ Error: {e}")
