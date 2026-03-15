import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """
⚠️ CRITICAL INSTRUCTION: EXTRACT ONLY — DO NOT INFER, ADD, OR HALLUCINATE ANYTHING ⚠️

ROLE:
You are a precise data extraction agent for Computer Studies Scheme of Work (SoW) documents.
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
    - Sub-topic label (if present, e.g. "Sub-Topic: Introduction to Search Engines")
    - "Students will be able to:" bullet points (SLOs)
    - Skills list

  COLUMN 2: "Teaching Strategies, Suggested Learning Activities, Digital Resources / Digital Tools"
    - Sequential teaching strategies with bold headings
    - All activity descriptions, discussion prompts, demonstration steps
    - Classwork (labelled "Classwork:", "C.W:", or "C.W :")
    - Online assignments (labelled "Online Assignment:")
    - Digital resource sections with URLs
    - Read left to right, top to bottom — preserve exact order

  COLUMN 3: "Assessment for Learning Strategies"
    - AFL strategy entries vertically aligned with the SPECIFIC teaching strategy
      in Column 2 they correspond to
    - Each entry may have a name, objective, and procedure/description
    - Link each AFL only to its aligned strategy
    - If no AFL appears next to a strategy → empty array []

THERE IS NO ORT / LB-AB SPLIT IN THIS SOW.
Each lesson has a single flat structure. Do NOT create ort or lb_ab keys.

═══════════════════════════════════════════════════════
2. SECTION IDENTIFICATION IN COLUMN 2
═══════════════════════════════════════════════════════

Map each bold heading in Column 2 to a section type as follows:

  introduction          → "Introduction:", "Introduction to the Topic:", "Lesson Topic:"
  warm_up               → "Warm-up Activity:", "Warm-Up Activity:", "Warm up Activity:"
  brainstorming         → "Brainstorming Activity:", "Brainstorm Race:", "Brainstorming Race:"
  explanation           → "Explanation and Examples:", "Explanation:"
  discussion            → "Discussion:", "Interactive Discussion:", "Discussion and Explanation:"
  demonstration         → "Demonstration:", "Interactive Demonstration:"
  guided_practice       → "Guided Practice:"
  collaborative_learning→ "Collaborative Learning:"
  whole_class_activity  → "Whole Class Activity:", "Whole-Class Activity:"
  peer_activity         → "Peer Activity:"
  pair_work             → "Pair Work:", "Pair Work – Peer Review:"
  hands_on              → "Hands-on Activity:", "Hands-On Activity:", "Activities & Classwork:"
  real_life_context     → "Real-Life Context:"
  multimedia_presentation → "Multimedia Presentation:"
  think_pair_share      → "Think-Pair-Share Activity:", "Think-Pair-Share:"
  methodology           → "Methodology:"
  other                 → any bold heading not matched above

  classwork             → "Classwork:", "C.W:", "C.W :" — extract as classwork array
  online_assignment     → "Online Assignment:" — extract as online_assignment string
  digital_resources     → "Digital Resource:", "Digital Resources:" — extract as digital_resources object

Within a section, sub-headings (bold but not the primary section heading) are
captured inside the description string verbatim — do NOT split them into separate
teaching_strategies entries.

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
            "sub_topic": "<exact sub-topic label — OMIT KEY if not present>",
            "slos": ["<exact SLO bullet text>"],
            "skills": ["<exact skill name>"],
            "introduction": "<full verbatim introduction text — OMIT KEY if not present>",
            "warm_up": {
              "activities": [
                {
                  "title": "<exact heading label e.g. 'Warm-up Activity', 'Brainstorming Activity'>",
                  "description": "<full verbatim text>",
                  "afl_strategies": ["<AFL name aligned with this activity, or [] if none>"]
                }
              ],
              "afl_strategies": ["<union of all AFL from warm_up activities>"]
            },
            "teaching_strategies": [
              {
                "type": "<one of the type values from section 2 mapping>",
                "title": "<exact heading text from SoW>",
                "description": "<full verbatim text of this strategy>",
                "digital_resources": ["<URL strings embedded within this strategy, omit key if none>"],
                "afl_strategies": ["<AFL names aligned with this strategy in Column 3, or []>"]
              }
            ],
            "digital_resources": {
              "objective": "<verbatim objective text — OMIT KEY if not stated>",
              "description": "<verbatim description of the resource — OMIT KEY if not stated>",
              "urls": ["<full URL strings>"]
            },
            "classwork": ["<exact text of each classwork bullet or step>"],
            "online_assignment": "<full verbatim text of the online assignment — OMIT KEY if not present>",
            "afl_strategies": [
              {
                "name": "<exact AFL strategy name e.g. 'Exit Cards', 'Think-Pair-Share', 'Oral Questions', 'Class Participation', 'Exit Ticket', 'Peer Feedback', 'Pair Work'>",
                "objective": "<verbatim objective text if stated — OMIT KEY if not stated>",
                "description": "<full verbatim procedure or description text>"
              }
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

- sub_topic           → OMIT key entirely if not present in Column 1
- introduction        → OMIT key entirely if not present
- warm_up             → OMIT key entirely if neither warm_up nor brainstorming heading appears
- digital_resources   → OMIT key entirely if no "Digital Resource(s):" section present
- online_assignment   → OMIT key entirely if not present
- teaching_strategies → ALWAYS include; use [] if no strategies present
- classwork           → ALWAYS include; use [] if no classwork present
- slos                → ALWAYS include; use [] if none listed
- skills              → ALWAYS include; use [] if none listed
- afl_strategies      → ALWAYS include at lesson level; use [] if none present
- afl_strategies[]    → always include per activity/strategy; use [] if none aligned

═══════════════════════════════════════════════════════
5. AFL LINKING RULES
═══════════════════════════════════════════════════════

Column 3 contains AFL entries. Each entry is aligned vertically with a specific
teaching strategy in Column 2.

- An AFL entry belongs ONLY to the teaching strategy it is vertically aligned with
- The lesson-level afl_strategies array contains ALL AFL entries for the lesson,
  extracted as structured objects with name + description (+ objective if stated)
- The afl_strategies array inside each teaching_strategy contains ONLY the
  NAME strings of the AFL entries aligned with that specific strategy
- The afl_strategies array inside each warm_up activity also contains only name strings
- AFL names must be extracted exactly as written:
  e.g. "Think-Pair-Share", "Exit Cards", "Exit Ticket", "Oral Questions",
       "Class Participation", "Picture Identification", "Pair Work", "Peer Feedback",
       "Brainstorming Race", "Brainstorm Race"
- If an AFL entry in Column 3 has an "Objective:" and "Procedure:" structure,
  extract both into the lesson-level afl_strategies object
- If an AFL entry is a short descriptive label (e.g. "Brainstorming Race:
  Help students recognize..."), the label before the colon is the name and the
  rest is the description
- Never assign an AFL to a strategy it does not appear next to

═══════════════════════════════════════════════════════
6. EXTRACTION RULES (NO EXCEPTIONS)
═══════════════════════════════════════════════════════

- Extract unit_number, unit_title, lesson_number, lesson_title, sub_topic EXACTLY as written
- Each SLO bullet = one separate string, verbatim
- Each skill = one separate string, verbatim
- teaching_strategies entries must follow the exact top-to-bottom order of Column 2
- description fields must contain the complete verbatim text of that section,
  including all numbered lists, bullet points, sub-headings, and examples
- digital_resources.urls = flat list of all URL strings found in the Digital Resource section
- URLs appearing inline within a teaching strategy (not in a dedicated Digital Resource
  section) go into that strategy's digital_resources array
- classwork = flat list of strings; each bullet point or numbered step = one string
- online_assignment = single verbatim string of the full online assignment text
- Do NOT split one strategy's content across multiple teaching_strategies entries
- Do NOT merge content from different strategies into one entry
- Do NOT create sub-entries within teaching_strategies; embed all sub-heading
  content into the description string of the parent strategy

═══════════════════════════════════════════════════════
7. LESSON BOUNDARY DETECTION
═══════════════════════════════════════════════════════

A new lesson begins when Column 1 shows a new "Lesson N:" heading.
A new unit begins when Column 1 shows a new "Unit N:" heading.
Content that spans multiple physical pages but belongs to the same lesson
must be merged into that lesson's entry — do NOT create duplicate lesson entries.

Some lessons may not have an explicit lesson number — derive it from the sequence
within the unit. Some units may have a "sub_topic" in Column 1 beneath the lesson
title — extract it into the sub_topic field.

═══════════════════════════════════════════════════════
8. FORBIDDEN ACTIONS
═══════════════════════════════════════════════════════

❌ DO NOT add any content not explicitly written in the SoW
❌ DO NOT rephrase, summarize, or paraphrase any SoW text
❌ DO NOT infer URLs, page numbers, track numbers, or any other values
❌ DO NOT create SLOs, skills, AFL strategies, or activities not in the SoW
❌ DO NOT create ort or lb_ab keys — this SoW has no such structure
❌ DO NOT omit any teaching strategy from Column 2
❌ DO NOT assign AFL strategies to the wrong teaching strategy
❌ DO NOT add markdown, backticks, or commentary to the output
❌ DO NOT include trailing commas
❌ DO NOT invent activity titles — derive them only from bold headings in Column 2
❌ DO NOT merge classwork and online_assignment into a single field
❌ DO NOT place Digital Resource section content inside teaching_strategies

═══════════════════════════════════════════════════════
9. OUTPUT VALIDATION CHECKLIST
═══════════════════════════════════════════════════════

✅ Output is valid JSON only — no markdown, no backticks, no commentary
✅ Every teaching strategy in Column 2 appears in teaching_strategies in order
✅ Every AFL in Column 3 is linked to the correct strategy by name string
✅ All lesson-level AFL entries are structured objects with name + description
✅ No ort or lb_ab keys exist anywhere in the output
✅ sub_topic, introduction, warm_up, digital_resources, online_assignment
   are present only when explicitly in the SoW
✅ classwork and afl_strategies arrays are always present (use [] if empty)
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

    # ── Fix model placing digital_resources inside teaching_strategies ──────
    def _fix_misplaced_digital_resources(self, data: dict) -> None:
        for unit in data.get("curriculum", {}).get("units", []):
            for lesson in unit.get("lessons", []):
                strategies = lesson.get("teaching_strategies", [])
                keep = []
                for ts in strategies:
                    if ts.get("type") == "digital_resources":
                        # Merge URLs into lesson-level digital_resources
                        urls = ts.get("digital_resources", [])
                        if urls:
                            dr = lesson.setdefault("digital_resources", {})
                            existing = dr.setdefault("urls", [])
                            for u in urls:
                                if u not in existing:
                                    existing.append(u)
                        # Skip adding to keep — remove from teaching_strategies
                    else:
                        keep.append(ts)
                lesson["teaching_strategies"] = keep

    # ── Validate structure ─────────────────────────────────────────────────
    def _validate(self, data: dict) -> None:
        units = data.get("curriculum", {}).get("units", [])
        if not units:
            raise ValueError("No units found in extracted data")

        total_lessons = 0
        for unit in units:
            unit_num = unit.get("unit_number", "?")
            lessons = unit.get("lessons", [])
            total_lessons += len(lessons)

            for lesson in lessons:
                lesson_num = lesson.get("lesson_number", "?")
                prefix = f"Unit {unit_num} Lesson {lesson_num}"

                # Must not contain ORT or LB/AB keys
                if "ort" in lesson:
                    raise ValueError(f"{prefix}: unexpected 'ort' key — this extractor is for Computer SoW")
                if "lb_ab" in lesson:
                    raise ValueError(f"{prefix}: unexpected 'lb_ab' key — this extractor is for Computer SoW")

                # Required fields
                if "slos" not in lesson:
                    raise ValueError(f"{prefix}: missing 'slos'")
                if not isinstance(lesson["slos"], list):
                    raise ValueError(f"{prefix}: 'slos' must be a list")

                if "teaching_strategies" not in lesson:
                    raise ValueError(f"{prefix}: missing 'teaching_strategies'")
                if not isinstance(lesson["teaching_strategies"], list):
                    raise ValueError(f"{prefix}: 'teaching_strategies' must be a list")

                if "classwork" not in lesson:
                    raise ValueError(f"{prefix}: missing 'classwork'")
                if not isinstance(lesson["classwork"], list):
                    raise ValueError(f"{prefix}: 'classwork' must be a list")

                if "afl_strategies" not in lesson:
                    raise ValueError(f"{prefix}: missing lesson-level 'afl_strategies'")
                if not isinstance(lesson["afl_strategies"], list):
                    raise ValueError(f"{prefix}: lesson-level 'afl_strategies' must be a list")

                # Validate each AFL strategy object
                for afl in lesson["afl_strategies"]:
                    if not isinstance(afl, dict):
                        raise ValueError(f"{prefix}: each afl_strategies entry must be an object")
                    if "name" not in afl:
                        raise ValueError(f"{prefix}: afl_strategies entry missing 'name'")
                    if "description" not in afl:
                        raise ValueError(f"{prefix}: afl_strategies entry missing 'description'")

                # Validate each teaching strategy
                valid_types = {
                    "introduction", "warm_up", "brainstorming", "explanation",
                    "discussion", "demonstration", "guided_practice",
                    "collaborative_learning", "whole_class_activity", "peer_activity",
                    "pair_work", "hands_on", "real_life_context",
                    "multimedia_presentation", "think_pair_share", "methodology", "other"
                }
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

        self._fix_misplaced_digital_resources(parsed)
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
    PDF_PATH    = "/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/Comp_SOW-Grade2-1-4-57.pdf"
    OUTPUT_PATH = "/home/omen-097/Teravox/LessonPlan_Generator/Demo_docs/sow_comp.json"

    agent = SOWExtractionAgent(model="openai/gpt-5.1")

    try:
        data = agent.extract(PDF_PATH)
        agent.save(data, OUTPUT_PATH)
        print("✅ Extraction complete")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise