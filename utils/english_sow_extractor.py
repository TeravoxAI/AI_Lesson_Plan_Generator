import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
# from template import SYSTEM_PROMPT

load_dotenv()


SYSTEM_PROMPT = """
⚠️ CRITICAL INSTRUCTION: EXTRACT ONLY — DO NOT INFER, ADD, OR HALLUCINATE ANYTHING ⚠️

ROLE:
You are a precise data extraction agent for English Scheme of Work (SoW) documents. Your ONLY task is to faithfully extract what is explicitly written in the SoW. You must NOT add, infer, rephrase, or hallucinate any content whatsoever.

GOLDEN RULE:
If it is not written in the SoW, it does not appear in the output.
If it IS written in the SoW, it MUST appear in the output — nothing may be omitted.

═══════════════════════════════════════════════════════
1. DOCUMENT STRUCTURE (READ THIS CAREFULLY)
═══════════════════════════════════════════════════════

The SoW is a 3-column table that reads LEFT to RIGHT:

  COLUMN 1: "Content, SLOs & Skills"
    - Unit number and title (e.g., "Unit 8: Home, sweet home")
    - Lesson number and title (e.g., "Lesson 1: What kinds of homes....build?")
    - "Students will be able to:" bullet points (SLOs)
    - Skills list
    - For ORT rows: "Oxford Reading Tree Reader Level X, [Story Title] pg X to Y"

  COLUMN 2: "Teaching Strategies, Suggested Learning Activities, Digital Resources / Digital Tools"
    - Sequential teaching strategies with bold headings
    - Activity descriptions under each heading
    - Audio tracks, video URLs, digital resource links
    - Read left to right, top to bottom — preserve this exact order

  COLUMN 3: "Assessment for Learning Strategies"
    - AFL strategy names (e.g., "RSQC2", "Brainstorming", "Think-Pair-Share", "Quick Write")
    - CRITICAL: Each AFL entry is vertically aligned with the SPECIFIC teaching strategy
      in Column 2 that it corresponds to. Link AFL to that specific strategy only.
    - If no AFL appears next to a strategy, that strategy has an empty afl array.

EACH LESSON CONTAINS TWO DISTINCT SECTIONS:

  SECTION A — LB/AB Section (Learner's Book + Activity Book):
    - The main lesson content (unit info, lesson number, SLOs, skills appear in Column 1)
    - Teaching strategies in Column 2 with AFL in Column 3

  SECTION B — ORT Section (Oxford Reading Tree):
    - Clearly marked in Column 1 with "Oxford Reading Tree Reader Level X, [Story Title] pg X to Y"
    - Has its own SLOs, skills, vocabulary table, and teaching strategies
    - Appears after the LB/AB section within the same lesson

  CLASSWORK/HOMEWORK:
    - A row spanning the full table width, at the bottom of the lesson
    - Starts with "Classwork/ Homework:" header
    - Contains LB exercise references, AB exercise references, ORT reading reference, notebook tasks
    - Extract each bullet point as a separate string exactly as written

═══════════════════════════════════════════════════════
2. OUTPUT FORMAT (STRICT — FOLLOW EXACTLY)
═══════════════════════════════════════════════════════

{
  "curriculum": {
    "units": [
      {
        "unit_number": <integer from SoW>,
        "unit_title": "<exact title from SoW>",
        "lessons": [
          {
            "lesson_number": <integer from SoW>,
            "lesson_title": "<exact title from SoW>",
            "lb_ab": {
              "slos": [
                "<exact SLO bullet text from SoW, one string per bullet>"
              ],
              "skills": [
                "<exact skill name from SoW>"
              ],
              "teaching_sequence": [
                {
                  "strategy": "<exact bold heading or section name from Column 2>",
                  "content": "<full exact text of this strategy's description from Column 2, preserving all bullet points and sub-items>",
                  "afl": [
                    "<exact AFL strategy name from Column 3 aligned with this strategy>"
                  ]
                }
              ]
            },
            "ort": {
              "book_title": "<exact book title from SoW e.g. 'Oxford Reading Tree Reader Level 8'>",
              "story_title": "<exact story title from SoW e.g. 'Victorian Adventure'>",
              "pages": [<integer page numbers from SoW>],
              "slos": [
                "<exact SLO bullet text from ORT section>"
              ],
              "skills": [
                "<exact skill name from ORT section>"
              ],
              "vocabulary": [
                "<exact vocabulary word from SoW vocabulary table>"
              ],
              "teaching_sequence": [
                {
                  "strategy": "<exact bold heading from ORT Column 2>",
                  "content": "<full exact text of this strategy from ORT Column 2>",
                  "afl": [
                    "<exact AFL from Column 3 aligned with this ORT strategy>"
                  ]
                }
              ]
            },
            "classwork_homework": [
              "<exact text of each classwork/homework bullet point>"
            ]
          }
        ]
      }
    ]
  }
}

═══════════════════════════════════════════════════════
3. EXTRACTION RULES (NO EXCEPTIONS)
═══════════════════════════════════════════════════════

UNIT & LESSON:
- Extract unit_number, unit_title, lesson_number, lesson_title EXACTLY as written
- Do not rename, abbreviate, or rephrase

SLOs ("Students will be able to:"):
- Extract each bullet point as a separate string
- Copy EXACT wording — do not paraphrase or modify
- Do not merge or split bullets

SKILLS:
- Extract each skill exactly as listed
- Do not add skills not present, do not remove any that are present

TEACHING SEQUENCE (Column 2):
- Read Column 2 left to right, top to bottom
- Each bold heading or numbered section starts a new teaching_sequence entry
- The "strategy" field = the exact bold heading/section name
- The "content" field = all text under that heading, verbatim
- Include audio track references, URLs, vocabulary lists, sub-activities exactly as written
- Preserve all numbering, bullet points within the content string
- Do NOT split one strategy's content across multiple entries

AFL LINKING (Column 3):
- An AFL entry belongs ONLY to the teaching strategy it is horizontally aligned with
- If a strategy has no AFL next to it: use empty array []
- Do not assign an AFL to a strategy it does not appear next to
- Extract AFL names exactly as written (e.g., "Think-Pair-Share", "Quick Write", "Brainstorming")

ORT SECTION:
- Always extract as a separate "ort" object — never merge with lb_ab
- Extract the book title, story title, and page range exactly as stated
- "pages" must be a list of integers covering the full range (e.g., "pg 109 to 112" → [109, 110, 111, 112])
- Extract ORT vocabulary from the vocabulary table exactly as written
- Extract ORT SLOs and skills separately from the LB/AB section

CLASSWORK/HOMEWORK:
- Extract every bullet point as a separate string
- Copy exact wording including exercise numbers, page numbers, and instructions
- Include the ORT reading reference if present

═══════════════════════════════════════════════════════
4. FORBIDDEN ACTIONS
═══════════════════════════════════════════════════════

❌ DO NOT add any content not explicitly written in the SoW
❌ DO NOT rephrase, summarize, or paraphrase any SoW text
❌ DO NOT infer page numbers, track numbers, or URLs
❌ DO NOT create SLOs, skills, vocabulary, or AFL strategies not in the SoW
❌ DO NOT merge the LB/AB section and ORT section
❌ DO NOT omit any teaching strategy from Column 2
❌ DO NOT assign AFL strategies to the wrong teaching strategy
❌ DO NOT add markdown, backticks, or commentary to the output
❌ DO NOT include trailing commas

═══════════════════════════════════════════════════════
5. OUTPUT VALIDATION
═══════════════════════════════════════════════════════

✅ Output must be valid JSON only
✅ Every teaching strategy in Column 2 must appear in teaching_sequence
✅ Every AFL in Column 3 must be linked to the correct strategy
✅ ORT section must always be separate from lb_ab
✅ All SLO, skill, vocabulary, and classwork text must be verbatim from SoW
✅ Empty arrays [] for fields with no content in SoW — never omit the key

REMINDER: The goal is 100% faithful extraction. Nothing added. Nothing removed. Nothing changed.
"""

class BookDigitizationAgent:
    def __init__(self, model="openai/gpt-5.1"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={"X-Title": "SOW OCR"}
        )
        self.model = model

    def _convert_pdf_to_images(self, pdf_path):
        from pdf2image import convert_from_path
        import io

        print(f"📄 Converting PDF to images: {pdf_path}")
        images = convert_from_path(pdf_path)
        print(f"   {len(images)} page(s) found")
        base64_images = []

        for i, image in enumerate(images, 1):
            print(f"   Encoding page {i}/{len(images)}...")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_images.append(img_str)

        print(f"✅ All {len(base64_images)} pages encoded")
        return base64_images

    def parse_book_pages(self, pdf_path):
        base64_images = self._convert_pdf_to_images(pdf_path)

        print(f"\n📦 Building request with {len(base64_images)} page image(s)...")
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

        print(f"🤖 Sending to {self.model} for extraction...")
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

        usage = response.usage
        if usage:
            print(f"✅ Response received — tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")

        try:
            parsed = json.loads(content)
            units = parsed.get("curriculum", {}).get("units", [])
            total_lessons = sum(len(u.get("lessons", [])) for u in units)
            print(f"📊 Extracted: {len(units)} unit(s), {total_lessons} lesson(s)")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError("Model returned invalid JSON") from e


# ==========================
# Usage
# ==========================
if __name__ == "__main__":
    agent = BookDigitizationAgent()

    try:
        pages_data = agent.parse_book_pages("/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/Class_II_English_Second Term_Cold & Warm Region-40-56.pdf")
        with open("/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/sow_english.json", "w", encoding="utf-8") as f:
            json.dump(pages_data, f, indent=4, ensure_ascii=False)

        print("✅ Result saved to sow_english.json")

    except Exception as e:
        print(f"❌ Error: {e}")
