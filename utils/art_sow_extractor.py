import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """
⚠️ CRITICAL INSTRUCTION: EXTRACT ONLY — DO NOT INFER, ADD, OR HALLUCINATE ANYTHING ⚠️

ROLE:
You are a precise data extraction agent for Art Scheme of Work (SoW) documents.
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
    - Lesson title (bold, at top of the row)
    - Optional STREAM marker: if the title contains "(STREAM)", set stream: true
    - "Students will be able to:" bullet points (SLOs)
    - "Skills" sub-heading followed by a skill list

  COLUMN 2: "Teaching Strategies, Suggested Learning Activities, Digital Resources"
    - Sequential teaching strategies with bold/underlined headings
    - All activity descriptions, demonstration steps, discussion prompts
    - Classwork (labelled "CW:" at the bottom of the row)
    - YouTube/digital resource URLs embedded within strategy descriptions
    - Read left to right, top to bottom — preserve exact order

  COLUMN 3: "Assessment for Learning Strategies"
    - AFL strategy entries vertically aligned with the SPECIFIC teaching strategy
      in Column 2 they correspond to
    - Each entry may be a name only, or a name + description
    - Link each AFL only to its aligned strategy
    - If no AFL appears next to a strategy → empty array []

THE ART SOW HAS A FLAT LESSON STRUCTURE — THERE ARE NO FORMAL UNITS.
Do NOT create a "units" array. The top-level key is "lessons".
Each table row = one lesson. Extract all lessons in top-to-bottom order.

═══════════════════════════════════════════════════════
2. SECTION IDENTIFICATION IN COLUMN 2
═══════════════════════════════════════════════════════

Map each bold/underlined heading in Column 2 to a type as follows:

  starter_brainstorming     → "Starter Activity (Brainstorming):", "Starter activity (Brainstorming):"
  starter_think_pair_share  → "Starter Activity (Think, Pair and Share):", "Starter activity (Think, Pair and Share):"
  starter_class_discussion  → "Starter Activity (Class Discussion):", "Starter activity (Class Discussion):"
  pair_discussion           → "Pair Discussion (Think, Pair and Share):", "Pair Discussion:"
  pair_work                 → "Pair Work:"
  group_activity            → "Group Activity:"
  monitor_facilitate        → "Monitor/Observe and facilitate students...", "Observe and facilitate students..."
  kwl_chart                 → "Activity (KWL Chart):"
  group_discussion_muddiest → "Group Discussion (Muddiest Point):"
  sub_activity              → Any bold/underlined heading that names a specific art task or topic
                              (e.g. "Drawing with Shapes", "Jungle Scene", "Origami",
                              "Giraffe (Paper Pasting)", "Boat (Paper Collage)",
                              "3D flower making", "CD Friends", etc.)
  other                     → Any bold heading not matched above

  classwork                 → "CW:" — extract as classwork array (each bullet = one string)

Within a strategy, sub-headings that are NOT primary section headings are captured
inside the description string verbatim — do NOT split them into separate entries.

═══════════════════════════════════════════════════════
3. OUTPUT FORMAT (STRICT — FOLLOW EXACTLY)
═══════════════════════════════════════════════════════

{
  "curriculum": {
    "lessons": [
      {
        "lesson_number": <integer — sequential 1, 2, 3... based on order in SoW>,
        "lesson_title": "<exact title from Column 1>",
        "stream": <true if title or Column 1 contains "(STREAM)", else false>,
        "slos": ["<exact SLO bullet text>"],
        "skills": ["<exact skill name>"],
        "teaching_strategies": [
          {
            "type": "<one of the type values from section 2 mapping>",
            "title": "<exact heading text from SoW>",
            "description": "<full verbatim text of this strategy>",
            "digital_resources": ["<URL strings embedded within this strategy — OMIT KEY if none>"],
            "afl_strategies": ["<AFL names aligned with this strategy in Column 3, or []>"]
          }
        ],
        "classwork": ["<exact text of each CW bullet or line>"],
        "afl_strategies": [
          {
            "name": "<exact AFL strategy name e.g. 'Brainstorming', 'Think, Pair and Share',
                     'Observation', 'Peer Assessment', 'Self-assessment',
                     'Peer/Self-assessment', 'KWL Chart', 'Muddiest Point',
                     'Group Discussion (Muddiest Point)'>",
            "description": "<full verbatim description or procedure text — OMIT KEY if not stated>"
          }
        ]
      }
    ]
  }
}

═══════════════════════════════════════════════════════
4. SECTION PRESENCE RULES
═══════════════════════════════════════════════════════

- stream              → always include; true or false
- slos                → ALWAYS include; use [] if none listed
- skills              → ALWAYS include; use [] if none listed
- teaching_strategies → ALWAYS include; use [] if no strategies present
- classwork           → ALWAYS include; use [] if no CW present
- afl_strategies      → ALWAYS include at lesson level; use [] if none present
- afl_strategies[]    → always include per strategy; use [] if none aligned
- digital_resources   → OMIT key from a teaching_strategy if no URLs are present in that strategy

═══════════════════════════════════════════════════════
5. AFL LINKING RULES
═══════════════════════════════════════════════════════

Column 3 contains AFL entries. Each entry is vertically aligned with a specific
teaching strategy in Column 2.

- An AFL entry belongs ONLY to the teaching strategy it is vertically aligned with
- The lesson-level afl_strategies array contains ALL AFL entries for the lesson,
  extracted as structured objects with name + description (if stated)
- The afl_strategies array inside each teaching_strategy contains ONLY the
  NAME strings of the AFL entries aligned with that specific strategy
- AFL names must be extracted exactly as written:
  e.g. "Brainstorming", "Think, Pair and Share", "Observation",
       "Peer Assessment", "Self-assessment", "Peer/Self-assessment",
       "KWL Chart", "Muddiest Point", "Group Discussion (Muddiest Point)"
- If an AFL entry has a description or procedure text, include it in the
  lesson-level afl_strategies object's description field
- Never assign an AFL to a strategy it does not appear next to

═══════════════════════════════════════════════════════
6. EXTRACTION RULES (NO EXCEPTIONS)
═══════════════════════════════════════════════════════

- lesson_number is a sequential integer starting at 1, derived from the top-to-bottom
  order of rows in the SoW table — assign it yourself based on position
- lesson_title = exact text from Column 1 (strip the STREAM marker from the title
  if it appears there, but set stream: true)
- Each SLO bullet = one separate string, verbatim
- Each skill = one separate string, verbatim
- teaching_strategies entries must follow the exact top-to-bottom order of Column 2
- description fields must contain the complete verbatim text of that section,
  including all numbered lists, bullet points, teacher instructions, safety notes,
  material lists, and embedded "Do you Know?" facts
- digital_resources inside a teaching_strategy = flat list of URL strings found
  within that strategy's text only
- classwork = flat list of strings; each bullet point or line = one string
- Do NOT split one strategy's content across multiple teaching_strategies entries
- Do NOT merge content from different strategies into one entry
- Do NOT create sub-entries within teaching_strategies; embed all content into
  the description string of the relevant strategy
- When a lesson row contains multiple distinct art tasks as separate bold headings
  (e.g. "Jungle Scene" and "Drawing in Notebook" in the same row), each is a
  separate teaching_strategy entry with type "sub_activity"
- Preserve teacher instructions, safety notes, material lists, and all prose
  within description fields verbatim

═══════════════════════════════════════════════════════
7. LESSON BOUNDARY DETECTION
═══════════════════════════════════════════════════════

A new lesson begins when the SoW table starts a new row with a new topic/title
in Column 1. Content that spans multiple physical pages but belongs to the same
lesson row must be merged into that lesson's entry — do NOT create duplicate lesson
entries for the same row.

Some lesson rows contain multiple art activity headings within Column 2 — these
are all part of the same lesson, not separate lessons.

═══════════════════════════════════════════════════════
8. FORBIDDEN ACTIONS
═══════════════════════════════════════════════════════

❌ DO NOT add any content not explicitly written in the SoW
❌ DO NOT rephrase, summarize, or paraphrase any SoW text
❌ DO NOT infer URLs, page numbers, or any other values
❌ DO NOT create SLOs, skills, AFL strategies, or activities not in the SoW
❌ DO NOT create a "units" wrapper — the Art SoW has no units
❌ DO NOT omit any teaching strategy from Column 2
❌ DO NOT assign AFL strategies to the wrong teaching strategy
❌ DO NOT add markdown, backticks, or commentary to the output
❌ DO NOT include trailing commas
❌ DO NOT invent activity titles — derive them only from bold headings in Column 2
❌ DO NOT place CW content inside teaching_strategies

═══════════════════════════════════════════════════════
9. OUTPUT VALIDATION CHECKLIST
═══════════════════════════════════════════════════════

✅ Output is valid JSON only — no markdown, no backticks, no commentary
✅ Top-level structure is {"curriculum": {"lessons": [...]}}
✅ Every teaching strategy in Column 2 appears in teaching_strategies in order
✅ Every AFL in Column 3 is linked to the correct strategy by name string
✅ All lesson-level AFL entries are objects with at least a name field
✅ No "units" key exists anywhere in the output
✅ stream is always a boolean (true/false)
✅ classwork and afl_strategies arrays are always present (use [] if empty)
✅ digital_resources key is omitted from strategies that have no URLs
✅ All SLO, skill, classwork, and AFL text is verbatim from SoW
✅ No key is omitted if it has content — no key is present if it has no content
✅ URLs are copied exactly as written — do not shorten or expand them

REMINDER: The goal is 100% faithful extraction. Nothing added. Nothing removed. Nothing changed.
"""


class SOWExtractionAgent:
    def __init__(self, model: str = "openai/gpt-5.1"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                "HTTP-Referer": "https://ai-lp-generator.teravox.ai",
                "X-Title": "SOW Extractor",
            }
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
            temperature=0,
            max_tokens=100000
        )
        msg = response.choices[0].message.content
        if not msg:
            raise ValueError("Empty response from model")

        finish_reason = response.choices[0].finish_reason
        usage = response.usage
        if usage:
            print(f"✅ Tokens — in: {usage.prompt_tokens} | out: {usage.completion_tokens} | finish: {finish_reason}")
        if finish_reason == "length":
            raise ValueError("Model output was truncated (hit max_tokens). Increase max_tokens or reduce input.")

        return msg

    # ── Validate structure ─────────────────────────────────────────────────
    def _validate(self, data: dict) -> None:
        lessons = data.get("curriculum", {}).get("lessons", [])
        if not lessons:
            raise ValueError("No lessons found in extracted data")

        # Ensure no units wrapper was accidentally created
        if "units" in data.get("curriculum", {}):
            raise ValueError("Unexpected 'units' key — Art SoW has no units structure")

        valid_types = {
            "starter_brainstorming", "starter_think_pair_share", "starter_class_discussion",
            "pair_discussion", "pair_work", "group_activity", "monitor_facilitate",
            "kwl_chart", "group_discussion_muddiest", "sub_activity", "other"
        }

        for lesson in lessons:
            lesson_num = lesson.get("lesson_number", "?")
            prefix = f"Lesson {lesson_num}"

            # Forbidden English/Computer SOW keys
            if "lb_ab" in lesson:
                raise ValueError(f"{prefix}: unexpected 'lb_ab' key — this extractor is for Art SoW")
            if "ort" in lesson:
                raise ValueError(f"{prefix}: unexpected 'ort' key — this extractor is for Art SoW")

            # stream must be a bool
            if "stream" not in lesson:
                raise ValueError(f"{prefix}: missing 'stream' field")
            if not isinstance(lesson["stream"], bool):
                raise ValueError(f"{prefix}: 'stream' must be a boolean")

            # Required list fields
            for field in ("slos", "skills", "teaching_strategies", "classwork", "afl_strategies"):
                if field not in lesson:
                    raise ValueError(f"{prefix}: missing '{field}'")
                if not isinstance(lesson[field], list):
                    raise ValueError(f"{prefix}: '{field}' must be a list")

            # Validate AFL strategy objects
            for afl in lesson["afl_strategies"]:
                if not isinstance(afl, dict):
                    raise ValueError(f"{prefix}: each afl_strategies entry must be an object")
                if "name" not in afl:
                    raise ValueError(f"{prefix}: afl_strategies entry missing 'name'")

            # Validate teaching strategies
            for ts in lesson["teaching_strategies"]:
                if not isinstance(ts, dict):
                    raise ValueError(f"{prefix}: each teaching_strategy must be an object")
                if "type" not in ts:
                    raise ValueError(f"{prefix}: teaching_strategy missing 'type'")
                if ts["type"] not in valid_types:
                    raise ValueError(
                        f"{prefix}: unknown teaching_strategy type '{ts['type']}'"
                    )
                if "title" not in ts:
                    raise ValueError(f"{prefix}: teaching_strategy missing 'title'")
                if "description" not in ts:
                    raise ValueError(f"{prefix}: teaching_strategy missing 'description'")
                if "afl_strategies" not in ts:
                    raise ValueError(f"{prefix}: teaching_strategy '{ts['title']}' missing 'afl_strategies'")
                if not isinstance(ts["afl_strategies"], list):
                    raise ValueError(f"{prefix}: teaching_strategy afl_strategies must be a list")

        print(f"📊 Validated: {len(lessons)} lesson(s)")

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
    PDF_PATH    = "/home/taha/APS/AI_Lesson_Plan_Generator/Class_II_Art_2nd Term_Cold _ Warm Region.pdf"
    OUTPUT_PATH = "/home/taha/APS/AI_Lesson_Plan_Generator/sow_art.json"

    agent = SOWExtractionAgent(model="openai/gpt-5.1")

    try:
        data = agent.extract(PDF_PATH)
        agent.save(data, OUTPUT_PATH)
        print("✅ Extraction complete")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
