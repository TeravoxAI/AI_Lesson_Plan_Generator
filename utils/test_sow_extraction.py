"""
test_sow_extraction.py

Proof-of-concept: Mistral OCR 3 + LLM → Generalized SOW JSON

Usage:
    python utils/test_sow_extraction.py

Tests on pages 1-6 of Comp_SOW-Grade2-1-4-57.pdf and outputs
Demo_docs/test_cs_generalized.json for comparison against sow_comp.json.
"""

import os
import io
import base64
import json
import sys
from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv()

PDF_PATH    = "SOWs/Comp_SOW-Grade2-1-4-57.pdf"
OUTPUT_PATH = "Demo_docs/test_cs_generalized.json"
PAGE_RANGE  = (0, 6)   # pages index 0-5 → physical pages 1-6

# ─────────────────────────────────────────────────────────────────────────────
# Generalized SOW schema description (injected into the extraction prompt)
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_DESCRIPTION = """
The output must be a JSON object matching this exact schema (GeneralizedSOW):

{
  "metadata": {
    "subject": "<string>",     // e.g. "computer_studies"
    "grade": "<string>",       // e.g. "2"
    "term": "<string|null>",
    "language": "<string>",    // "english"
    "sow_version": "2.0"
  },
  "curriculum": {
    "units": [
      {
        "unit_number": <int>,
        "unit_title": "<string>",
        "unit_topic": "<string|null>",
        "lessons": [
          {
            "lesson_number": <int>,
            "lesson_title": "<string>",
            "sub_topic": "<string|null — omit key if absent>",
            "num_periods": <int|null>,

            // Core — always present, empty arrays if nothing in SOW
            "slos": ["<string>"],
            "skills": ["<string>"],
            "resources": ["<string>"],       // omit if not stated
            "methodology": ["<string>"],     // omit if not stated

            // Pre-teaching — omit entire key if section not present
            "introduction": "<string>",
            "warm_up": {
              "activities": [
                {
                  "title": "<string>",
                  "description": "<string>",
                  "afl_strategies": ["<AFL name>"]
                }
              ],
              "afl_strategies": ["<union of all AFL names from warm_up activities>"]
            },

            // Main teaching — for CS use teaching_strategies
            "teaching_strategies": [
              {
                "type": "<one of: introduction|warm_up|brainstorming|explanation|discussion|demonstration|guided_practice|collaborative_learning|whole_class_activity|peer_activity|pair_work|hands_on|real_life_context|multimedia_presentation|think_pair_share|methodology|other>",
                "title": "<exact heading from SOW>",
                "description": "<verbatim text>",
                "afl_strategies": ["<AFL name>"],
                "digital_resources": ["<URL>"]
              }
            ],

            // Assignments — classwork always present, others omit if absent
            "classwork": ["<string>"],
            "homework": ["<string>"],            // omit if absent
            "online_assignment": "<string>",     // omit if absent

            // Digital resources — omit if no dedicated Digital Resource section
            "digital_resources": {
              "objective": "<string>",
              "description": "<string>",
              "urls": ["<URL>"]
            },

            // Textbook pages — omit if not referenced in SOW
            "textbook_pages": { "<BOOK_CODE>": "<page_range>" },

            // Assessment
            "afl_strategies": [
              {
                "name": "<exact AFL name>",
                "objective": "<string — omit if absent>",
                "description": "<string>"
              }
            ],

            // Post-teaching — omit if absent
            "differentiated_instruction": {
              "struggling": "<string>",
              "advanced": "<string>"
            },
            "extension_activity": "<string>"
          }
        ]
      }
    ]
  }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Computer Studies extraction guidance
# ─────────────────────────────────────────────────────────────────────────────

CS_EXTRACTION_GUIDE = """
SUBJECT-SPECIFIC GUIDANCE FOR COMPUTER STUDIES SOW:

1. The SOW is a 3-column table:
   - Column 1: Content, SLOs & Skills
   - Column 2: Teaching Strategies, Suggested Learning Activities, Digital Resources
   - Column 3: Assessment for Learning Strategies

2. There is NO ORT or LB/AB split. Each lesson is a flat structure.

3. Map bold headings in Column 2 to teaching_strategies types:
   warm_up              → "Warm-up Activity:", "Warm-Up Activity:"
   brainstorming        → "Brainstorming Activity:", "Brainstorm Race:"
   explanation          → "Explanation:", "Explanation and Examples:"
   discussion           → "Discussion:", "Interactive Discussion:"
   demonstration        → "Demonstration:", "Interactive Demonstration:"
   guided_practice      → "Guided Practice:"
   collaborative_learning → "Collaborative Learning:"
   whole_class_activity → "Whole Class Activity:", "Whole-Class Activity:"
   pair_work            → "Pair Work:", "Pair Work – Peer Review:"
   hands_on             → "Hands-on Activity:", "Hands-On Activity:"
   think_pair_share     → "Think-Pair-Share Activity:", "Think-Pair-Share:"
   other                → any unrecognised bold heading

4. "Classwork:" or "C.W:" → classwork array
   "Online Assignment:" → online_assignment string
   "Digital Resource(s):" → digital_resources object

5. Column 3 AFL entries are vertically aligned with Column 2 strategies.
   Link each AFL name to the strategy it sits next to.
   The lesson-level afl_strategies array contains ALL AFL entries as full objects.

6. A new lesson begins with "Lesson N:" in Column 1.
   A new unit begins with "Unit N:" in Column 1.
   Content spanning multiple pages for the same lesson MUST be merged.

7. metadata.subject = "computer_studies", metadata.language = "english"
"""

EXTRACTION_SYSTEM_PROMPT = f"""
⚠️ CRITICAL: EXTRACT ONLY — DO NOT INFER, ADD, OR HALLUCINATE ⚠️

You are a precise data extraction agent. The user will provide OCR output (markdown)
from a Scheme of Work (SOW) PDF. Your task is to extract the content into the
GeneralizedSOW JSON schema defined below.

GOLDEN RULE: If it is not written in the SOW → it does not appear in the output.

{SCHEMA_DESCRIPTION}

{CS_EXTRACTION_GUIDE}

FORBIDDEN:
❌ Do NOT add content not in the SOW
❌ Do NOT rephrase or paraphrase
❌ Do NOT create ort or lb_ab keys
❌ Do NOT add markdown fences or commentary to output
❌ Output MUST be valid JSON only
"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Slice PDF to pages 1-6 and encode as base64
# ─────────────────────────────────────────────────────────────────────────────

def slice_pdf_to_base64(pdf_path: str, start: int, end: int) -> str:
    """Extract pages [start, end) from PDF and return as base64 string."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total = len(reader.pages)
    end = min(end, total)

    print(f"📄 Slicing pages {start+1}–{end} of {total} from {pdf_path}")
    for i in range(start, end):
        writer.add_page(reader.pages[i])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    print(f"✅ PDF slice encoded ({len(encoded)//1024} KB base64)")
    return encoded


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Run Mistral OCR on the PDF slice
# ─────────────────────────────────────────────────────────────────────────────

def run_mistral_ocr(pdf_base64: str) -> str:
    """Send PDF to Mistral OCR and return concatenated markdown."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set in environment")

    client = Mistral(api_key=api_key)
    print("🔍 Running Mistral OCR (mistral-ocr-latest)...")

    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_base64}"
        }
    )

    pages_markdown = []
    for i, page in enumerate(response.pages):
        pages_markdown.append(f"<!-- PAGE {i+1} -->\n{page.markdown}")

    combined = "\n\n".join(pages_markdown)
    print(f"✅ OCR complete — {len(response.pages)} page(s), {len(combined)} chars")
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Extract GeneralizedSOW JSON from OCR markdown via LLM
# ─────────────────────────────────────────────────────────────────────────────

def extract_generalized_sow(ocr_markdown: str, subject: str, grade: str) -> dict:
    """Call Mistral LLM to extract GeneralizedSOW JSON from OCR markdown."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set in environment")

    client = Mistral(api_key=api_key)
    model = "mistral-large-latest"
    print(f"🤖 Extracting with {model}...")

    user_content = (
        f"Subject: {subject}\nGrade: {grade}\n\n"
        "Extract the GeneralizedSOW JSON from this OCR output:\n\n"
        f"{ocr_markdown}"
    )

    response = client.chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        temperature=0,
        max_tokens=16000,
        response_format={"type": "json_object"},
    )

    msg = response.choices[0].message.content
    finish = response.choices[0].finish_reason
    usage = response.usage

    if usage:
        print(f"✅ Tokens — in: {usage.prompt_tokens} | out: {usage.completion_tokens} | finish: {finish}")
    if finish == "length":
        print("⚠️  WARNING: output was truncated (hit max_tokens)")

    if not msg:
        raise ValueError("Empty LLM response")

    # Strip markdown fences if present
    stripped = msg.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.endswith("```"):
            stripped = stripped.rsplit("```", 1)[0].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Validate the output
# ─────────────────────────────────────────────────────────────────────────────

def validate(data: dict) -> None:
    """Basic structural validation of GeneralizedSOW."""
    assert "metadata" in data, "Missing 'metadata'"
    assert "curriculum" in data, "Missing 'curriculum'"
    assert "units" in data["curriculum"], "Missing curriculum.units"

    meta = data["metadata"]
    assert "subject" in meta, "metadata missing 'subject'"
    assert "grade" in meta, "metadata missing 'grade'"

    units = data["curriculum"]["units"]
    assert len(units) > 0, "No units extracted"

    total_lessons = 0
    for unit in units:
        assert "unit_number" in unit, "Unit missing 'unit_number'"
        assert "unit_title" in unit, "Unit missing 'unit_title'"
        assert "lessons" in unit, "Unit missing 'lessons'"

        for lesson in unit["lessons"]:
            total_lessons += 1
            ln = lesson.get("lesson_number", "?")
            un = unit.get("unit_number", "?")
            prefix = f"Unit {un} Lesson {ln}"

            assert "lesson_number" in lesson, f"{prefix}: missing lesson_number"
            assert "lesson_title" in lesson, f"{prefix}: missing lesson_title"
            assert isinstance(lesson.get("slos", []), list), f"{prefix}: slos must be list"
            assert isinstance(lesson.get("skills", []), list), f"{prefix}: skills must be list"
            assert "teaching_strategies" in lesson, f"{prefix}: missing teaching_strategies"
            assert isinstance(lesson["teaching_strategies"], list), f"{prefix}: teaching_strategies must be list"
            assert "classwork" in lesson, f"{prefix}: missing classwork"
            assert "afl_strategies" in lesson, f"{prefix}: missing afl_strategies"

            # Confirm no legacy keys
            assert "ort" not in lesson, f"{prefix}: unexpected 'ort' key"
            assert "lb_ab" not in lesson, f"{prefix}: unexpected 'lb_ab' key"

    print(f"📊 Validated: {len(units)} unit(s), {total_lessons} lesson(s)")


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Compare against existing extraction (sow_comp.json)
# ─────────────────────────────────────────────────────────────────────────────

def compare_with_existing(new_data: dict, existing_path: str) -> None:
    """Print side-by-side lesson count and first lesson comparison."""
    if not os.path.exists(existing_path):
        print(f"⚠️  Existing file not found: {existing_path} — skipping comparison")
        return

    with open(existing_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_units = existing.get("curriculum", {}).get("units", [])
    new_units = new_data.get("curriculum", {}).get("units", [])

    # Count lessons across both (only the pages we tested)
    def count_lessons(units):
        return sum(len(u.get("lessons", [])) for u in units)

    # Only compare units/lessons present in the new (sliced) extraction
    new_lesson_count = count_lessons(new_units)
    print(f"\n{'='*60}")
    print(f"COMPARISON (pages {PAGE_RANGE[0]+1}–{PAGE_RANGE[1]})")
    print(f"{'='*60}")
    print(f"New extraction:  {len(new_units)} unit(s), {new_lesson_count} lesson(s)")

    # Show first lesson from each
    if new_units and new_units[0].get("lessons"):
        new_l = new_units[0]["lessons"][0]
        print(f"\nNEW — Unit 1 Lesson 1:")
        print(f"  title:    {new_l.get('lesson_title')}")
        print(f"  slos:     {len(new_l.get('slos', []))} item(s)")
        print(f"  skills:   {len(new_l.get('skills', []))} item(s)")
        print(f"  strategies: {len(new_l.get('teaching_strategies', []))} item(s)")
        print(f"  afl:      {len(new_l.get('afl_strategies', []))} item(s)")
        print(f"  classwork: {len(new_l.get('classwork', []))} item(s)")

    if existing_units and existing_units[0].get("lessons"):
        ex_l = existing_units[0]["lessons"][0]
        print(f"\nEXISTING — Unit 1 Lesson 1:")
        print(f"  title:    {ex_l.get('lesson_title')}")
        print(f"  slos:     {len(ex_l.get('slos', []))} item(s)")
        print(f"  skills:   {len(ex_l.get('skills', []))} item(s)")
        print(f"  strategies: {len(ex_l.get('teaching_strategies', []))} item(s)")
        print(f"  afl:      {len(ex_l.get('afl_strategies', []))} item(s)")
        print(f"  classwork: {len(ex_l.get('classwork', []))} item(s)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Resolve paths relative to repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path    = os.path.join(repo_root, PDF_PATH)
    output_path = os.path.join(repo_root, OUTPUT_PATH)
    existing_path = os.path.join(repo_root, "Demo_docs/sow_comp.json")

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    # 1. Slice PDF
    pdf_b64 = slice_pdf_to_base64(pdf_path, PAGE_RANGE[0], PAGE_RANGE[1])

    # 2. Mistral OCR
    ocr_markdown = run_mistral_ocr(pdf_b64)

    # Save raw OCR for inspection
    ocr_out = os.path.join(repo_root, "Demo_docs/test_cs_ocr_raw.md")
    with open(ocr_out, "w", encoding="utf-8") as f:
        f.write(ocr_markdown)
    print(f"💾 Raw OCR saved to: {ocr_out}")

    # 3. Extract generalized SOW JSON
    result = extract_generalized_sow(ocr_markdown, subject="computer_studies", grade="2")

    # 4. Validate
    print("\n🔍 Validating...")
    validate(result)
    print("✅ Validation passed")

    # 5. Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved to: {output_path}")

    # 6. Compare
    compare_with_existing(result, existing_path)

    print("\n✅ Test complete. Check Demo_docs/test_cs_generalized.json")


if __name__ == "__main__":
    main()
