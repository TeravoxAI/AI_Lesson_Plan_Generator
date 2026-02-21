import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """
⚠️ CRITICAL INSTRUCTION: EXTRACT ONLY — DO NOT INFER, ADD, OR HALLUCINATE ANYTHING ⚠️

ROLE:
You are a precise data extraction agent for English Scheme of Work (SoW) documents.
Your ONLY task is to faithfully extract what is explicitly written in the SoW.
You must NOT add, infer, rephrase, or hallucinate any content whatsoever.

GOLDEN RULE:
If it is not written in the SoW → it does not appear in the output.
If it IS written in the SoW → it MUST appear in the output. Nothing may be omitted.

═══════════════════════════════════════════════════════
1. DOCUMENT STRUCTURE
═══════════════════════════════════════════════════════

The SoW is a 3-column table read LEFT → RIGHT:

  COLUMN 1: "Content, SLOs & Skills"
    - Unit number and title
    - Lesson number and title
    - "Students will be able to:" bullet points (SLOs)
    - Skills list
    - For ORT rows: "Oxford Reading Tree Reader Level X, [Story Title] pg X to Y"

  COLUMN 2: "Teaching Strategies, Suggested Learning Activities, Digital Resources / Digital Tools"
    - Sequential teaching strategies with bold headings
    - All activity descriptions, audio tracks, video URLs, digital resource links
    - Read left to right, top to bottom — preserve exact order

  COLUMN 3: "Assessment for Learning Strategies"
    - AFL strategy names vertically aligned with the SPECIFIC teaching strategy
      in Column 2 they correspond to
    - Link each AFL only to its aligned strategy
    - If no AFL appears next to a strategy → empty array []

EACH LESSON HAS TWO DISTINCT SECTIONS:

  SECTION A — LB/AB (Learner's Book + Activity Book):
    - Main lesson: unit info, lesson number, SLOs, skills in Column 1
    - Teaching strategies in Column 2, AFL in Column 3

  SECTION B — ORT (Oxford Reading Tree):
    - Marked in Column 1: "Oxford Reading Tree Reader Level X, [Story Title] pg X to Y"
    - Has its OWN SLOs, skills, vocabulary, and teaching strategies
    - ALWAYS extract as completely separate from LB/AB

  CLASSWORK/HOMEWORK:
    - A full-width row at the bottom of the lesson
    - Extract each bullet as a separate string, verbatim

═══════════════════════════════════════════════════════
2. SECTION IDENTIFICATION IN COLUMN 2
═══════════════════════════════════════════════════════

When reading Column 2, map each bold heading to a section type:

  UNIT_REVIEW   → headings like "Unit X review strategies:", "Revision:", "Recap:"
  VOCABULARY    → headings like "Vocabulary:", "Vocabulary introduction:"
  WARM_UP       → headings like "Warm-up:", "Warm up:"
  EXERCISE      → numbered headings like "1. Read and listen:", "2. A tree house:",
                   "3. Topic vocabulary:", "4. Talk about it:", etc.
  DIFF_INSTR    → headings like "Differentiated instructions:", "Differentiated Instructions:"
  EXTENSION     → headings like "Extension Activity:", "Extension activity:"
  ADDITIONAL    → headings like "Additional activities:"

Within EXERCISE sections, sub-headings (bold but not numbered) are sub_activities.
Within WARM_UP, multiple paragraphs/bold sub-headings are individual warm-up activities.
Within VOCABULARY, activities describe how vocabulary is introduced.

═══════════════════════════════════════════════════════
3. OUTPUT FORMAT (STRICT — FOLLOW EXACTLY)
═══════════════════════════════════════════════════════

{
  "curriculum": {
    "units": [
      {
        "unit_number": <integer>,
        "unit_title": "<exact title>",
        "lessons": [
          {
            "lesson_number": <integer>,
            "lesson_title": "<exact title>",
            "lb_ab": {
              "slos": ["<exact SLO bullet text>"],
              "skills": ["<exact skill name>"],
              "unit_review": {
                "title": "<exact heading text from SoW>",
                "description": "<full verbatim text of this section>",
                "afl_strategies": ["<exact AFL names aligned with this section>"]
              },
              "vocabulary": {
                "words": ["<exact word from vocabulary list>"],
                "afl_strategies": ["<AFL aligned with vocabulary section>"],
                "activities": [
                  {
                    "title": "<exact sub-heading or description label>",
                    "optional": <true if marked optional, else omit this key>,
                    "description": "<full verbatim text>",
                    "afl_strategies": ["<AFL aligned with this activity>"]
                  }
                ]
              },
              "warm_up": {
                "afl_strategies": ["<all AFL aligned with warm-up section combined>"],
                "activities": [
                  {
                    "title": "<exact sub-heading label>",
                    "description": "<full verbatim text>",
                    "digital_resource": "<URL if present, else omit key>",
                    "afl_strategies": ["<AFL aligned with this specific warm-up activity>"]
                  }
                ]
              },
              "exercises": [
                {
                  "exercise_id": "<number as string e.g. '1', '2'>",
                  "title": "<exact exercise heading text>",
                  "afl_strategies": ["<all AFL aligned with this exercise combined>"],
                  "sub_activities": [
                    {
                      "title": "<exact sub-heading label>",
                      "description": "<full verbatim text>",
                      "audio_track": <integer if mentioned, else omit key>,
                      "digital_resource": "<URL if present, else omit key>",
                      "comprehension_questions": ["<question text if listed, else omit key>"],
                      "afl_strategies": ["<AFL aligned with this sub-activity>"]
                    }
                  ]
                }
              ],
              "differentiated_instruction": {
                "description": "<full verbatim text>",
                "afl_strategies": ["<AFL aligned with this section>"]
              },
              "extension_activity": {
                "description": "<full verbatim text>",
                "afl_strategies": ["<AFL aligned with this section>"]
              },
              "additional_activities": {
                "description": "<full verbatim text>",
                "afl_strategies": ["<AFL aligned with this section>"]
              }
            },
            "ort": {
              "book_title": "<e.g. 'Oxford Reading Tree Reader Level 8'>",
              "story_title": "<e.g. 'Victorian Adventure'>",
              "pages": [<integer list of all page numbers in range>],
              "slos": ["<exact ORT SLO bullet text>"],
              "skills": ["<exact ORT skill name>"],
              "vocabulary": {
                "words": ["<exact word from ORT vocabulary table>"],
                "afl_strategies": ["<AFL aligned with ORT vocabulary section>"],
                "activities": [
                  {
                    "title": "<label>",
                    "description": "<full verbatim text>",
                    "afl_strategies": ["<AFL aligned>"]
                  }
                ]
              },
              "reading_stages": {
                "pre_reading": {
                  "afl_strategies": ["<AFL aligned with pre-reading>"],
                  "activities": [
                    {
                      "title": "<label>",
                      "description": "<full verbatim text>",
                      "afl_strategies": ["<AFL aligned with this activity>"]
                    }
                  ]
                },
                "independent_reading": {
                  "pages": "<page range string e.g. '111-112'>",
                  "afl_strategies": ["<AFL aligned>"],
                  "activities": [
                    {
                      "title": "<label>",
                      "description": "<full verbatim text>",
                      "comprehension_questions": ["<question if listed>"],
                      "afl_strategies": ["<AFL aligned>"]
                    }
                  ]
                },
                "paired_reading": {
                  "pages": "<page range string>",
                  "afl_strategies": ["<AFL aligned>"],
                  "activities": [
                    {
                      "title": "<label>",
                      "description": "<full verbatim text>",
                      "afl_strategies": ["<AFL aligned>"]
                    }
                  ]
                },
                "guided_reading": {
                  "pages": "<page range string>",
                  "afl_strategies": ["<AFL aligned>"],
                  "activities": [
                    {
                      "title": "<label>",
                      "description": "<full verbatim text>",
                      "comprehension_questions": ["<question if listed>"],
                      "afl_strategies": ["<AFL aligned>"]
                    }
                  ]
                },
                "post_reading": {
                  "afl_strategies": ["<AFL aligned>"],
                  "activities": [
                    {
                      "title": "<label>",
                      "description": "<full verbatim text>",
                      "afl_strategies": ["<AFL aligned>"]
                    }
                  ]
                }
              },
              "classwork_homework": [
                "<exact text of each ORT-specific classwork/homework bullet>"
              ]
            },
            "classwork_homework": [
              "<exact text of each combined classwork/homework bullet>"
            ]
          }
        ]
      }
    ]
  }
}

═══════════════════════════════════════════════════════
4. SECTION PRESENCE RULES
═══════════════════════════════════════════════════════

- If unit_review is NOT present in the SoW for this lesson → omit the key entirely
- If vocabulary activities are NOT present → activities array is []
- If warm_up is NOT present → omit the key entirely
- If differentiated_instruction is NOT present → omit the key entirely
- If extension_activity is NOT present → omit the key entirely
- If additional_activities is NOT present → omit the key entirely
- If a reading stage (e.g. paired_reading) is NOT present in ORT → omit that key
- afl_strategies arrays → always include, use [] if none aligned
- exercises array → always include, use [] if no exercises present

═══════════════════════════════════════════════════════
5. AFL LINKING RULES
═══════════════════════════════════════════════════════

- An AFL entry belongs ONLY to the strategy it is vertically aligned with in Column 3
- AFL at the section level (e.g. warm_up.afl_strategies) = union of all AFL
  from activities within that section
- AFL at the activity level = only the AFL directly aligned with that specific activity
- Never assign an AFL to a strategy it does not appear next to
- Extract AFL names exactly as written (e.g. "Think-Pair-Share", "Quick Write")

═══════════════════════════════════════════════════════
6. EXTRACTION RULES (NO EXCEPTIONS)
═══════════════════════════════════════════════════════

- Extract unit_number, unit_title, lesson_number, lesson_title EXACTLY as written
- Each SLO bullet = one separate string, verbatim
- Each skill = one separate string, verbatim
- vocabulary.words = flat list of words only, no definitions
- Exercise sub-activity titles = the bold sub-heading text exactly as written
- audio_track = integer only (e.g. 70, 71), omit key if not mentioned
- digital_resource = full URL string, omit key if not mentioned
- comprehension_questions = list only if explicitly listed as questions in SoW, omit otherwise
- pages in ORT = list of ALL integers in the range
  (e.g. "pg 109 to 112" → [109, 110, 111, 112])
- Preserve all numbered lists and bullet points within description strings
- Do NOT split one strategy's content across multiple entries
- Do NOT merge content from different strategies into one entry

═══════════════════════════════════════════════════════
7. FORBIDDEN ACTIONS
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
❌ DO NOT invent activity titles — derive them only from bold sub-headings in Column 2

═══════════════════════════════════════════════════════
8. OUTPUT VALIDATION CHECKLIST
═══════════════════════════════════════════════════════

✅ Output is valid JSON only — no markdown, no backticks, no commentary
✅ Every teaching strategy in Column 2 appears in the correct section
✅ Every AFL in Column 3 is linked to the correct strategy
✅ ORT section is always separate from lb_ab
✅ All SLO, skill, vocabulary, and classwork text is verbatim from SoW
✅ Section keys are omitted when not present in SoW (not set to null)
✅ afl_strategies at section level = union of its activities' afl_strategies
✅ No key is omitted if it has content — no key is present if it has no content

REMINDER: The goal is 100% faithful extraction. Nothing added. Nothing removed. Nothing changed.
"""


class SOWExtractionAgent:
    def __init__(self, model: str = "openai/gpt-5.1"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={"X-Title": "SOW Extractor"}
        )
        self.model = model

    # ── PDF → base64 images ────────────────────────────────────────────────
    def _pdf_to_base64_images(self, pdf_path: str) -> list[str]:
        from pdf2image import convert_from_path
        import io

        print(f"📄 Converting PDF: {pdf_path}")
        images = convert_from_path(pdf_path)
        print(f"   {len(images)} page(s) found")

        encoded = []
        for i, img in enumerate(images, 1):
            print(f"   Encoding page {i}/{len(images)}...")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            encoded.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

        print(f"✅ All {len(encoded)} pages encoded")
        return encoded

    # ── Build multimodal message content ───────────────────────────────────
    def _build_content(self, base64_images: list[str]) -> list[dict]:
        content = [{"type": "text", "text": "Extract the Scheme of Work from the attached PDF pages."}]
        for img in base64_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"}
            })
        return content

    # ── Call model ─────────────────────────────────────────────────────────
    def _call_model(self, content: list[dict]) -> str:
        print(f"🤖 Sending to {self.model}...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": content}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        msg = response.choices[0].message.content
        if not msg:
            raise ValueError("Empty response from model")

        usage = response.usage
        if usage:
            print(f"✅ Tokens — in: {usage.prompt_tokens} | out: {usage.completion_tokens}")

        return msg

    # ── Validate structure ─────────────────────────────────────────────────
    def _validate(self, data: dict) -> None:
        units = data.get("curriculum", {}).get("units", [])
        if not units:
            raise ValueError("No units found in extracted data")

        total_lessons = 0
        for unit in units:
            lessons = unit.get("lessons", [])
            total_lessons += len(lessons)
            for lesson in lessons:
                if "lb_ab" not in lesson:
                    raise ValueError(
                        f"Missing lb_ab in Unit {unit.get('unit_number')} "
                        f"Lesson {lesson.get('lesson_number')}"
                    )
                if "ort" not in lesson:
                    raise ValueError(
                        f"Missing ort in Unit {unit.get('unit_number')} "
                        f"Lesson {lesson.get('lesson_number')}"
                    )

        print(f"📊 Validated: {len(units)} unit(s), {total_lessons} lesson(s)")

    # ── Main entry point ───────────────────────────────────────────────────
    def extract(self, pdf_path: str) -> dict:
        images   = self._pdf_to_base64_images(pdf_path)
        content  = self._build_content(images)
        raw_json = self._call_model(content)

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise ValueError("Model returned invalid JSON") from e

        self._validate(parsed)
        return parsed

    # ── Save to file ───────────────────────────────────────────────────────
    def save(self, data: dict, output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"💾 Saved to: {output_path}")


# ══════════════════════════════════════════════════════════════════════════════
# Usage
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    PDF_PATH    = "/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/Class_II_English_Second Term_Cold & Warm Region-40-56.pdf"
    OUTPUT_PATH = "/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/sow_english.json"

    agent = SOWExtractionAgent(model="openai/gpt-5.1")

    try:
        data = agent.extract(PDF_PATH)
        agent.save(data, OUTPUT_PATH)
        print("✅ Extraction complete")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise