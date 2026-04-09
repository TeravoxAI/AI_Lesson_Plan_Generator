"""
universal_sow_extractor.py — Universal Scheme of Work extractor.

Converts any subject's SOW PDF to the GeneralizedSOW JSON format using:
  1. Mistral OCR (mistral-ocr-latest) for PDF → markdown
  2. mistral-large-latest LLM for markdown → structured JSON

Usage:
    python utils/universal_sow_extractor.py \\
        --pdf  SOWs/Comp_SOW-Grade2-1-4-57.pdf \\
        --subject computer_studies \\
        --grade 2 \\
        --output Demo_docs/sow_cs_grade2.json \\
        [--skip-pages 0]          # number of frontmatter pages to skip (default: auto)
        [--max-pages 54]          # max pages to process (default: all)
        [--ocr-cache ocr_raw.md]  # cache OCR output to avoid re-running

Supported subjects:
    english, mathematics, computer_studies, islamiat, nazra, urdu

Output format: GeneralizedSOW JSON (see src/models.py for schema)
"""

import argparse
import base64
import io
import json
import os
import sys
import time
from pypdf import PdfReader, PdfWriter
from mistralai.client import Mistral
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# Shared schema description (injected into all extraction prompts)
# ─────────────────────────────────────────────────────────────────────────────

SHARED_SCHEMA = """
OUTPUT JSON SCHEMA (GeneralizedSOW):

{
  "metadata": {
    "subject": "<subject string>",
    "grade": "<grade string e.g. '2'>",
    "term": "<'first'|'second'|'third'|null>",
    "language": "<'english'|'urdu'|'arabic'>",
    "sow_version": "2.0"
  },
  "curriculum": {
    "units": [
      {
        "unit_number": <int>,
        "unit_title": "<string>",
        "unit_topic": "<string|null — omit key if absent>",
        "content": "<string|null — Math only: raw unit content>",
        "lessons": [
          {
            "lesson_number": <int>,
            "lesson_title": "<string>",
            "sub_topic": "<string|null — omit key if absent>",
            "num_periods": <int|null — omit key if absent>,

            // Always present, empty array if nothing in SOW
            "slos": ["<string>"],
            "skills": ["<string>"],

            // Omit entire key if not stated in SOW
            "resources": ["<string>"],
            "methodology": ["<string>"],
            "introduction": "<string>",

            // Warm-up section — omit if no warm-up in SOW
            "warm_up": {
              "activities": [
                {"title": "<string>", "description": "<string>", "afl_strategies": ["<AFL name>"]}
              ],
              "afl_strategies": ["<union of warm_up AFL names>"]
            },

            // Main teaching strategies — always present, [] if none
            "teaching_strategies": [
              {
                "type": "<one of: introduction|warm_up|brainstorming|explanation|discussion|demonstration|guided_practice|collaborative_learning|whole_class_activity|peer_activity|pair_work|hands_on|real_life_context|multimedia_presentation|think_pair_share|reading|recitation_practice|vocabulary_activity|other>",
                "title": "<exact heading from SOW>",
                "description": "<verbatim text>",
                "afl_strategies": ["<AFL name>"],
                "digital_resources": ["<URL>"]
              }
            ],

            // Assignments
            "classwork": ["<string>"],           // always present, [] if none
            "homework": ["<string>"],             // omit if absent
            "online_assignment": "<string>",      // omit if absent
            "classwork_homework": ["<string>"],   // use only if CW and HW are not split

            // Digital resources — omit if no dedicated digital resource section
            "digital_resources": {
              "objective": "<string>",
              "description": "<string>",
              "urls": ["<URL>"]
            },

            // Textbook page references — omit if not mentioned in SOW
            "textbook_pages": {"<BOOK_CODE>": "<page_range>"},

            // Assessment — always present
            "afl_strategies": [
              {"name": "<string>", "objective": "<string — omit if absent>", "description": "<string>"}
            ],

            // Post-teaching — omit if absent
            "differentiated_instruction": {"struggling": "<string>", "advanced": "<string>"},
            "extension_activity": "<string>",

            // Nazra/recitation only — omit for all other subjects
            "recitation": {
              "surah_name": "<string>",
              "verse_range": "<string>",
              "tajweed_rules": ["<string>"]
            }
          }
        ]
      }
    ]
  }
}
"""

GOLDEN_RULES = """
GOLDEN RULES (NO EXCEPTIONS):
1. Extract ONLY what is written in the SOW — never infer, add, or hallucinate
2. Output MUST be valid JSON only — no markdown, no backticks, no commentary
3. Verbatim text: copy SLOs, skills, strategy descriptions, AFL names exactly as written
4. Never create ort or lb_ab keys
5. Never omit a field that has content; never include a field with no content (unless required)
"""


# ─────────────────────────────────────────────────────────────────────────────
# Subject-specific extraction guidance
# ─────────────────────────────────────────────────────────────────────────────

SUBJECT_GUIDES = {

"computer_studies": """
SUBJECT: Computer Studies (English SOW)

TABLE FORMAT: 3-column table (left to right):
  Column 1: Content, SLOs & Skills
  Column 2: Teaching Strategies, Suggested Learning Activities, Digital Resources
  Column 3: Assessment for Learning Strategies

UNIT/LESSON BOUNDARIES:
  New unit → "Unit N:" heading in Column 1
  New lesson → "Lesson N:" heading in Column 1

TEACHING STRATEGY TYPE MAPPING (from Column 2 bold headings):
  warm_up             → "Warm-up Activity:", "Warm-Up Activity:"
  brainstorming       → "Brainstorming Activity:", "Brainstorm Race:"
  explanation         → "Explanation:", "Explanation and Examples:"
  discussion          → "Discussion:", "Interactive Discussion:"
  demonstration       → "Demonstration:", "Interactive Demonstration:"
  guided_practice     → "Guided Practice:"
  collaborative_learning → "Collaborative Learning:"
  whole_class_activity→ "Whole Class Activity:", "Whole-Class Activity:"
  pair_work           → "Pair Work:", "Pair Work – Peer Review:"
  hands_on            → "Hands-on Activity:", "Hands-On Activity:"
  think_pair_share    → "Think-Pair-Share Activity:", "Think-Pair-Share:"
  other               → any unrecognised bold heading

"Classwork:" or "C.W:" → classwork[]
"Online Assignment:"   → online_assignment
"Digital Resource(s):" → digital_resources{}

AFL strategies (Column 3) align vertically with Column 2 strategies.
Link each AFL name to the strategy it sits next to.

metadata.language = "english"
""",

"islamiat": """
SUBJECT: Islamiat (Islamic Studies, Urdu SOW)

TABLE FORMAT: 3-column RTL table. In OCR output the columns appear as:
  Column 1 (AFL): نسلانی جاچ / نسلو می — Assessment strategy names
  Column 2 (Teaching): طریقہ تدریس / مجوزہ تدریس / سرگرمیاں — Teaching activities
  Column 3 (Content): متوالت / حاصلات تعلم / مہارتیں — Chapter, SLOs, Skills

UNIT BOUNDARIES: Column 3 shows "باب اول:", "باب دوم:", etc.
  باب اول=1, باب دوم=2, باب سوم=3, باب چهارم=4, باب پنجم=5
  unit_title = Urdu chapter name

LESSON BOUNDARIES: New topic title + new "طلبہ اس قابل ہوں گے کہ:" block.
  Content spanning multiple pages → merge into one lesson.

TEACHING STRATEGY TYPES (Column 2 activity headings):
  think_pair_share     → سرگرمی (سوچیں، تبادلہ خیال کریں اور بتائیں) / جوڑیوں میں
  vocabulary_activity  → سرگرمی (فلیش کارڈ) / فلیش کارڈز
  whole_class_activity → سرگرمی (باتوں کے اشارے) / کوئی مقابلہ
  collaborative_learning → سرگرمی (گروہی) / گروہوں میں
  hands_on             → سرگرمی (رول پلے) / خاکہ / اطلاقی کارڈ
  discussion           → سرگرمی (تبادلہ خیال) / گفت و شنید
  reading              → بلند خوانی / طلبہ سبق پڑھیں
  explanation          → سبق کی وضاحت / وضاحت کریں
  other                → اکثریت کلک / Exit cards / سبق کا اعادہ

DO NOT add Differentiated Instruction or Extension Activity to teaching_strategies.
  Differentiated Instruction → differentiated_instruction.struggling
  Extension Activity → extension_activity

AFL names (Column 1):
  جانچ بذریعہ سوالات, جانچ بذریعہ باتوں کے اشارے, جانچ بذریعہ فلیش کارڈز,
  جانچ بذریعہ اظہار خیال, جانچ بذریعہ اکثریت کلک (Exit Cards)

جماعت / گھر کا کام → split into classwork[] and homework[] if clearly marked.

YouTube URLs in Column 2 → digital_resources.urls[]

metadata.language = "urdu"
""",

"nazra": """
SUBJECT: Nazra (Quran Recitation, Urdu/Arabic SOW)

TABLE FORMAT: 3-column weekly schedule (NOT a teaching strategy table):
  Column 1 (مطابق/مقام): Week number
  Column 2 (طبق/سق): Topic (Surah + verse range, or memorization topic)
  Column 3 (حق/ہے): Objectives (what to recite/memorize + Tajweed focus)

UNITS — group all weekly entries into 2 units:
  Unit 1 (unit_number=1): "حفظ و ترجمہ و احادیث"
    → weeks covering: درود شریف, Islamic phrases, احادیث, دعائیں, اسمائے حسنی
  Unit 2 (unit_number=2): "ناظرہ قرآن مجید"
    → weeks covering: Surah Al-Baqarah recitation

LESSONS — each weekly row = one lesson, numbered sequentially within unit.
  lesson_title = column 2 topic text
  slos = each bullet from column 3 objectives (verbatim)
  teaching_strategies = []  (SOW does not specify teaching methods)
  afl_strategies = []
  classwork = []

For ناظرہ lessons (Unit 2): populate recitation{} block:
  surah_name = Surah name from lesson title
  verse_range = verse range numbers (e.g. "۱۳۲ تا ۱۵۳")
  tajweed_rules = ONLY the specific Tajweed rule NAMES mentioned in objectives
    e.g. "وقف کی علامات", "حروف مدہ", "غنہ", "قلقلہ", "عُثر", "جزم"

For حفظ/احادیث/دعا lessons (Unit 1): OMIT recitation key entirely.

metadata.language = "urdu"
""",

"urdu": """
SUBJECT: Urdu (Language, Urdu SOW)

TABLE FORMAT: Similar to Islamiat — 3-column RTL table:
  Column 1 (AFL): Assessment strategy names
  Column 2 (Teaching): Teaching activities (سرگرمیاں)
  Column 3 (Content): Unit/lesson title, SLOs, Skills

UNIT BOUNDARIES: وحدت/یونٹ or numbered unit headings.
LESSON BOUNDARIES: New سبق/درس/موضوع with SLO block.

Teaching strategies follow same type mapping as Islamiat.
  reading         → سبق کی بلند خوانی / خواندگی
  vocabulary_activity → الفاظ سازی / فلیش کارڈ / نئے الفاظ
  discussion      → تبادلہ خیال / سرگرمی
  think_pair_share → سوچیں، بتائیں / جوڑیوں میں

جماعت کاکام → classwork[]
گھر کاکام → homework[]
Flash card activities → vocabulary_activity strategy type

metadata.language = "urdu"
""",

"english": """
SUBJECT: English (English SOW — new structured format)

TABLE FORMAT: 3-column table:
  Column 1: Content, SLOs & Skills (units, lessons, SLOs, book references)
  Column 2: Teaching Strategies & Activities (lb_ab section, ORT section)
  Column 3: Assessment for Learning

UNIT/LESSON STRUCTURE:
  Each unit has lessons; each lesson has lb_ab section and optionally ORT section.

NEW FORMAT fields to extract per lesson (lb_ab):
  recall: {title, description, afl_strategies[]}
  vocabulary: {words[], activities[], afl_strategies[]}
  warm_up: {activities[], afl_strategies[]}
  exercises: [{exercise_id, title, sub_activities[], afl_strategies[]}]
  differentiated_instruction: {struggling, advanced}
  extension_activity: string

For exercises, each bold exercise heading becomes an exercise entry with sub_activities.

Audio tracks: if "Track N" or "audio track N" mentioned → note in sub_activity description.
YouTube URLs → digital_resources.urls[]

classwork_homework = items from "C.W/H.W:" section (list of "Ex N LB/AB pg N" references)

textbook_pages: extract page refs like {"LB": "88-89", "AB": "90"} from classwork_homework items.

metadata.language = "english"
""",

"mathematics": """
SUBJECT: Mathematics (English SOW)

TABLE FORMAT: Table with unit-level content.
  Mathematics SOW typically has unit-level content strings, not individual lessons.

UNITS: Each chapter/unit = one GeneralizedSOWUnit.
  unit_number: chapter number
  unit_title: chapter title
  content: full raw text of the unit's content (all strategies, activities, SLOs combined)
  lessons: [] (empty — Math uses unit-level content)

Extract EACH unit as a separate entry with its full content.

metadata.language = "english"
""",
}


# ─────────────────────────────────────────────────────────────────────────────
# Page skip defaults per subject (number of frontmatter pages to skip)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SKIP_PAGES = {
    "computer_studies": 0,
    "english":          0,
    "mathematics":      0,
    "islamiat":         9,   # pages 1-9 are cover + curriculum overview
    "nazra":            0,   # all 5 pages contain useful content
    "urdu":             0,
}


# ─────────────────────────────────────────────────────────────────────────────
# OCR
# ─────────────────────────────────────────────────────────────────────────────

def run_ocr(pdf_path: str, skip_pages: int, max_pages: int | None, ocr_cache: str | None) -> str:
    """Run Mistral OCR on PDF (with optional frontmatter skip and cache)."""
    if ocr_cache and os.path.exists(ocr_cache):
        print(f"📄 Loading cached OCR: {ocr_cache}")
        with open(ocr_cache, encoding="utf-8") as f:
            return f.read()

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    end = min(skip_pages + max_pages, total) if max_pages else total
    pages_to_process = list(range(skip_pages, end))

    print(f"📄 PDF: {total} pages total. Processing pages {skip_pages+1}–{end}...")

    writer = PdfWriter()
    for i in pages_to_process:
        writer.add_page(reader.pages[i])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    pdf_b64 = base64.b64encode(buf.read()).decode()

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set in .env")

    client = Mistral(api_key=api_key)
    print("🔍 Running Mistral OCR (mistral-ocr-latest)...")
    resp = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": f"data:application/pdf;base64,{pdf_b64}"},
    )

    combined = "\n\n".join(
        f"=== PDF PAGE {skip_pages + i + 1} ===\n{p.markdown}"
        for i, p in enumerate(resp.pages)
    )
    print(f"✅ OCR done: {len(resp.pages)} pages, {len(combined)} chars")

    if ocr_cache:
        os.makedirs(os.path.dirname(os.path.abspath(ocr_cache)), exist_ok=True)
        with open(ocr_cache, "w", encoding="utf-8") as f:
            f.write(combined)
        print(f"💾 OCR cached: {ocr_cache}")

    return combined


# ─────────────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────────────

def build_system_prompt(subject: str, grade: str) -> str:
    guide = SUBJECT_GUIDES.get(subject, "")
    return (
        "You are a precise SOW data extraction agent.\n\n"
        + GOLDEN_RULES + "\n\n"
        + SHARED_SCHEMA + "\n\n"
        + guide
    )


def extract_sow(ocr_text: str, subject: str, grade: str, term: str | None = None) -> dict:
    api_key = os.getenv("MISTRAL_API_KEY")
    client = Mistral(api_key=api_key)
    model = "mistral-large-latest"

    system_prompt = build_system_prompt(subject, grade)
    user_content = (
        f"Subject: {subject}, Grade: {grade}"
        + (f", Term: {term}" if term else "")
        + f"\n\nExtract the GeneralizedSOW JSON from this SOW OCR output:\n\n{ocr_text}"
    )

    print(f"🤖 Extracting with {model} ({len(ocr_text)} chars OCR)...")
    resp = None
    for attempt in range(1, 4):
        try:
            resp = client.chat.complete(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            break
        except Exception as e:
            if attempt < 3:
                wait = 15 * attempt
                print(f"⚠️  Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    msg = resp.choices[0].message.content
    finish = resp.choices[0].finish_reason
    print(f"✅ Tokens — in: {resp.usage.prompt_tokens} | out: {resp.usage.completion_tokens} | finish: {finish}")
    if finish == "length":
        print("⚠️  WARNING: output truncated (hit max_tokens). Consider splitting the PDF into smaller chunks.")

    stripped = msg.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate(data: dict) -> None:
    assert "metadata" in data, "Missing 'metadata'"
    assert "curriculum" in data, "Missing 'curriculum'"
    units = data["curriculum"].get("units", [])
    assert units, "No units extracted"

    meta = data["metadata"]
    assert meta.get("subject"), "metadata.subject is empty"
    assert meta.get("grade"), "metadata.grade is empty"

    total_lessons = 0
    for unit in units:
        assert "unit_number" in unit, "Unit missing unit_number"
        assert "unit_title" in unit, "Unit missing unit_title"
        for lesson in unit.get("lessons", []):
            total_lessons += 1
            un = unit["unit_number"]
            ln = lesson.get("lesson_number", "?")
            prefix = f"Unit {un} Lesson {ln}"
            assert "lesson_number" in lesson, f"{prefix}: missing lesson_number"
            assert "lesson_title" in lesson, f"{prefix}: missing lesson_title"
            assert isinstance(lesson.get("slos", []), list), f"{prefix}: slos must be list"
            assert isinstance(lesson.get("teaching_strategies", []), list), f"{prefix}: teaching_strategies must be list"
            assert isinstance(lesson.get("afl_strategies", []), list), f"{prefix}: afl_strategies must be list"
            assert isinstance(lesson.get("classwork", []), list), f"{prefix}: classwork must be list"
            assert "ort" not in lesson, f"{prefix}: unexpected 'ort' key"
            assert "lb_ab" not in lesson, f"{prefix}: unexpected 'lb_ab' key"

    print(f"📊 Validated: {len(units)} unit(s), {total_lessons} lesson(s)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Universal SOW extractor — PDF → GeneralizedSOW JSON")
    parser.add_argument("--pdf",        required=True,  help="Path to SOW PDF file")
    parser.add_argument("--subject",    required=True,  choices=list(SUBJECT_GUIDES.keys()), help="Subject name")
    parser.add_argument("--grade",      required=True,  help="Grade number e.g. '2'")
    parser.add_argument("--output",     required=True,  help="Output JSON file path")
    parser.add_argument("--term",       default=None,   help="Term: first|second|third")
    parser.add_argument("--skip-pages", type=int,       default=None, help="Pages to skip (frontmatter). Default: auto per subject.")
    parser.add_argument("--max-pages",  type=int,       default=None, help="Max pages to process (for large PDFs, process in chunks)")
    parser.add_argument("--ocr-cache",  default=None,   help="Path to cache/load OCR markdown output")
    args = parser.parse_args()

    # Resolve paths
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path    = os.path.join(repo_root, args.pdf)    if not os.path.isabs(args.pdf)    else args.pdf
    output_path = os.path.join(repo_root, args.output) if not os.path.isabs(args.output) else args.output
    ocr_cache   = (os.path.join(repo_root, args.ocr_cache) if args.ocr_cache and not os.path.isabs(args.ocr_cache) else args.ocr_cache)

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    skip_pages = args.skip_pages if args.skip_pages is not None else DEFAULT_SKIP_PAGES.get(args.subject, 0)
    print(f"📋 Subject: {args.subject} | Grade: {args.grade} | Skip: {skip_pages} page(s)")

    # Step 1: OCR
    ocr_text = run_ocr(pdf_path, skip_pages, args.max_pages, ocr_cache)

    # Step 2: Extract
    data = extract_sow(ocr_text, args.subject, args.grade, args.term)

    # Step 3: Validate
    print("\n🔍 Validating...")
    validate(data)
    print("✅ Validation passed")

    # Step 4: Summary
    units = data["curriculum"]["units"]
    for u in units:
        lessons = u.get("lessons", [])
        print(f"  Unit {u['unit_number']}: {u['unit_title']} — {len(lessons)} lesson(s)")
        for l in lessons[:3]:
            print(f"    L{l['lesson_number']}: {l['lesson_title'][:60]}")
        if len(lessons) > 3:
            print(f"    ... and {len(lessons)-3} more")

    # Step 5: Save
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved: {output_path}")


if __name__ == "__main__":
    main()
