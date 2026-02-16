import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
# from template import SYSTEM_PROMPT

load_dotenv()


SYSTEM_PROMPT = """
ROLE:
You are an expert curriculum parser and instructional designer for Mathematics Curriculum.

Your task is to read and parse the provided Mathematics Scheme of Work (SoW) and generate a fully populated JSON output that strictly follows the schema and rules below.

1. INPUT MATERIAL
You will be given a Mathematics Scheme of Work.
The Scheme of Work contains chapter/unit titles and numbers, lesson titles, Content/SLOs/Skills, Teaching Strategies, Suggested Learning Activities, Digital Resources, and Assessment for Learning Strategies.
You must extract information only from the Scheme of Work. Do not hallucinate content, page numbers, or activities.

2. OUTPUT FORMAT (STRICT)
Your output must be valid JSON and conform exactly to the following structure:

{
  "curriculum": {
    "units": [
      {
        "unit_number": 13,
        "unit_title": "Position and Movement",
        "content": "Complete extracted content for this unit including all lessons, SLOs, skills, teaching strategies, activities, digital resources, vocabulary, and assessment strategies"
      }
    ]
  }
}

3. CONTENT EXTRACTION RULES
For each unit/chapter, extract and combine ALL of the following into the "content" field:

Lessons:
- List all lesson titles within the unit (e.g., Lesson 1: Clockwise and Anti-clockwise Movement, Lesson 2: Rotation)

Student Learning Outcomes (SLOs):
- Extract all "Students will be able to:" statements exactly as written
- Preserve bullet points and formatting

Skills:
- Extract all skills listed (e.g., Identifying, Reading Time, Recognizing, Critical Thinking, Analysing, Creativity, Digital Literacy)

Vocabulary:
- Extract all vocabulary words listed for the unit

Teaching Strategies and Activities:
- Extract all Starter Activities, main activities, group activities, games, and extension activities
- Preserve the activity names and descriptions (e.g., "Think, Pair and Share", "Gallery Walk", "Turn and Twist Game")
- Include differentiated instructions for less able and more able students

Digital Resources:
- Extract all URLs and digital resource references exactly as provided
- Do not modify or shorten URLs

Assessment Strategies:
- Extract all assessment for learning strategies mentioned

Book/Page References:
- Extract any Course Book or Practice Workbook page references mentioned
- Include Class/Home Work instructions

4. QUALITY AND VALIDATION RULES
- Output must be machine-readable JSON only
- Do not include markdown, explanations, or commentary
- Do not include trailing commas
- Chapter/Unit numbers and titles must exactly match the Scheme of Work
- Preserve the original content of the Scheme of Work verbatim where possible
- Do not add any additional information or comments
- Do not invent or hallucinate any content not present in the SoW
- Each unit should contain ALL information from that chapter/unit section
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
        pages_data = agent.parse_book_pages("/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/Class_II_Maths_Second Term_Cold _ Warm Region-19-21.pdf", SYSTEM_PROMPT)
        with open("Demo_docs/sow1.json", "w", encoding="utf-8") as f:
            json.dump(pages_data, f, indent=4, ensure_ascii=False)

        print("✅ Result saved to sow1.json")

    except Exception as e:
        print(f"❌ Error: {e}")
