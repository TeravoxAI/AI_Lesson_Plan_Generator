"""
extract_islamiat.py — Extract Islamiat SOW to GeneralizedSOW JSON format.

Uses Mistral OCR (mistral-ocr-latest) for PDF → markdown,
then mistral-large-latest to extract the structured JSON.

Processes lesson pages only (skips frontmatter pages 1-9).
"""

import io
import base64
import json
import os
import sys
from pypdf import PdfReader, PdfWriter
from mistralai.client import Mistral
from dotenv import load_dotenv

load_dotenv()

PDF_PATH    = "SOWs/Class_II_Islamiyat_2nd Term_Cold _ Warm Region.pdf"
OCR_PATH    = "Demo_docs/islamiat_all_lessons_ocr.md"
OUTPUT_PATH = "Demo_docs/test_islamiat_generalized.json"

ISLAMIAT_EXTRACTION_PROMPT = """You are a precise data extraction agent. Extract the Islamiat (Islamic Studies) Scheme of Work into a GeneralizedSOW JSON structure.

GOLDEN RULE: Extract ONLY what is written. Do NOT infer, add, or hallucinate.

═══════════════════════════════════════════
OUTPUT JSON SCHEMA
═══════════════════════════════════════════

{
  "metadata": {
    "subject": "islamiat",
    "grade": "2",
    "term": "second",
    "language": "urdu",
    "sow_version": "2.0"
  },
  "curriculum": {
    "units": [
      {
        "unit_number": <int>,
        "unit_title": "<Urdu chapter title>",
        "lessons": [
          {
            "lesson_number": <int>,
            "lesson_title": "<Urdu topic title>",
            "slos": ["<each bullet under طلبہ اس قابل ہوں گے کہ:>"],
            "skills": ["<each item under مہارتیں>"],
            "teaching_strategies": [
              {
                "type": "<mapped type — see mapping below>",
                "title": "<exact heading from SOW>",
                "description": "<verbatim text>",
                "afl_strategies": ["<AFL name if aligned>"],
                "digital_resources": ["<URL if present>"]
              }
            ],
            "differentiated_instruction": {
              "struggling": "<verbatim Differentiated Instruction text>"
            },
            "extension_activity": "<verbatim Extension Activity text>",
            "afl_strategies": [
              {"name": "<AFL name>", "description": "<description if given>"}
            ],
            "classwork": ["<each جماعت کا کام item>"],
            "homework": ["<each گھر کا کام item>"],
            "digital_resources": {"urls": ["<YouTube or other URL>"]}
          }
        ]
      }
    ]
  }
}

═══════════════════════════════════════════
DOCUMENT STRUCTURE
═══════════════════════════════════════════

The SOW is a 3-column table in Urdu (RTL). Columns left to right in the OCR:

  COLUMN 1 (نسلانی جاچ / نسلو می):
    - AFL strategy names (assessment methods)
    - e.g. "جانچ بذریعہ سوالات", "جانچ بذریعہ باتوں کے اشارے"

  COLUMN 2 (طریقہ تدریس / مجوزہ تدریس / سرگرمیاں):
    - Main teaching content: activities, explanations, discussion prompts
    - Contains: سرگرمی entries, بلند خوانی instructions
    - Contains: Differentiated Instruction section (in English)
    - Contains: Extension Activity section (in English)
    - Contains: YouTube URLs
    - Contains: جماعت / گھر کا کام (classwork/homework) at end of lesson

  COLUMN 3 (متوالت / حاصلات تعلم / مہارتیں):
    - Chapter heading: "باب اول:", "باب دوم:", etc.
    - Topic/lesson title
    - SLOs: طلبہ اس قابل ہوں گے کہ: [bullet list]
    - Skills: مہارتیں [bullet list]

═══════════════════════════════════════════
UNIT AND LESSON BOUNDARIES
═══════════════════════════════════════════

NEW UNIT: Column 3 shows a chapter heading:
  باب اول = unit 1
  باب دوم = unit 2
  باب سوم = unit 3
  باب چهارم = unit 4
  باب پنجم = unit 5

  The unit_title is the Urdu name that follows "باب X:" or "باب X" on the same line or next line.

NEW LESSON: Column 3 shows a new topic title followed by SLOs.
  Number lessons sequentially within each unit (1, 2, 3...).

CONTENT SPANNING PAGES: If a lesson continues across multiple pages, merge all content into one lesson entry. The lesson boundary is a new topic title + new SLO block.

═══════════════════════════════════════════
TEACHING STRATEGY TYPE MAPPING
═══════════════════════════════════════════

Map each named activity heading to a type:

  think_pair_share      → سرگرمی containing سوچیں، تبادلہ خیال کریں اور بتائیں
                          OR سرگرمی containing جوڑیوں میں / ساتھی سے
  vocabulary_activity   → سرگرمی (فلیش کارڈ) / فلیش کارڈز
  whole_class_activity  → سرگرمی (باتوں کے اشارے) / ہاتھ اٹھانا / کوئی مقابلہ
  collaborative_learning→ سرگرمی (گروہی) / گروہوں میں
  hands_on              → سرگرمی (رول پلے) / خاک / ڈرائنگ / اطلاقی کارڈ
  discussion            → سرگرمی (تبادلہ خیال) / گفت و شنید
  reading               → بلند خوانی / طلبہ سبق پڑھیں
  explanation           → سبق کی وضاحت / وضاحت کریں
  other                 → اکثریت کلک / Exit cards / سبق کا اعادہ / ڈیجیٹل مواد

SKIP — do NOT add to teaching_strategies:
  Differentiated Instruction → extract to differentiated_instruction.struggling
  Extension Activity → extract to extension_activity string

═══════════════════════════════════════════
AFL STRATEGIES
═══════════════════════════════════════════

From Column 1. Each bullet = one AFL strategy.
The lesson-level afl_strategies array contains ALL AFL names from Column 1 for that lesson.
Each teaching_strategy.afl_strategies contains ONLY the AFL names that align with that activity.

Common AFL names found in this SOW:
  جانچ بذریعہ سوالات
  جانچ بذریعہ باتوں کے اشارے
  جانچ بذریعہ فلیش کارڈز
  جانچ بذریعہ اطہار خیال / اظہار خیال
  جانچ بذریعہ اکثریت کلک (Exit Cards)

═══════════════════════════════════════════
CLASSWORK / HOMEWORK
═══════════════════════════════════════════

Appears as "جماعت / گھر کا کام:" at end of lesson.
Each bullet → one classwork item.
If split into جماعت (classwork) and گھر (homework), separate them.
If not clearly split, put all in classwork[].

═══════════════════════════════════════════
DIGITAL RESOURCES
═══════════════════════════════════════════

YouTube URLs appearing in Column 2 → digital_resources.urls[].
Also note the context text near each URL in the teaching_strategy description.

═══════════════════════════════════════════
FORBIDDEN
═══════════════════════════════════════════

❌ Do NOT add content not in the SOW
❌ Do NOT skip any unit or lesson
❌ Do NOT create ort or lb_ab keys
❌ Output MUST be valid JSON only — no markdown, no backticks
"""


def ocr_lesson_pages(pdf_path: str, ocr_path: str = OCR_PATH) -> str:
    """OCR lesson pages (skipping frontmatter pages 1-9)."""
    if os.path.exists(ocr_path):
        print(f"📄 Loading cached OCR from {ocr_path}")
        with open(ocr_path, encoding="utf-8") as f:
            return f.read()

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    print(f"📄 PDF: {total} pages total. Processing lesson pages (10–{total})...")

    writer = PdfWriter()
    for i in range(9, total):   # skip frontmatter (pages 1-9)
        writer.add_page(reader.pages[i])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    pdf_b64 = base64.b64encode(buf.read()).decode()

    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    print("🔍 Running Mistral OCR...")
    resp = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": f"data:application/pdf;base64,{pdf_b64}"}
    )

    combined = "\n\n".join(
        f"=== PDF PAGE {i+10} (SOW page {i+9} of 21) ===\n{p.markdown}"
        for i, p in enumerate(resp.pages)
    )

    os.makedirs(os.path.dirname(ocr_path), exist_ok=True)
    with open(ocr_path, "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"✅ OCR done: {len(resp.pages)} pages, {len(combined)} chars saved to {ocr_path}")
    return combined


def extract_sow(ocr_text: str) -> dict:
    """Extract GeneralizedSOW JSON from OCR markdown."""
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    model = "mistral-large-latest"
    print(f"🤖 Extracting with {model} ({len(ocr_text)} chars OCR input)...")

    resp = client.chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": ISLAMIAT_EXTRACTION_PROMPT},
            {"role": "user",   "content": f"Extract the GeneralizedSOW from this Islamiat SOW OCR (Grade 2, Second Term):\n\n{ocr_text}"},
        ],
        temperature=0,
        max_tokens=16000,
        response_format={"type": "json_object"},
    )

    msg = resp.choices[0].message.content
    finish = resp.choices[0].finish_reason
    print(f"✅ Tokens — in: {resp.usage.prompt_tokens} | out: {resp.usage.completion_tokens} | finish: {finish}")
    if finish == "length":
        print("⚠️  WARNING: output truncated (hit max_tokens)")

    stripped = msg.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    return json.loads(stripped)


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path    = os.path.join(repo_root, PDF_PATH)
    output_path = os.path.join(repo_root, OUTPUT_PATH)

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    # Step 1: OCR
    ocr_path    = os.path.join(repo_root, OCR_PATH)
    output_path = os.path.join(repo_root, OUTPUT_PATH)

    ocr_text = ocr_lesson_pages(pdf_path, ocr_path)

    # Step 2: Extract
    data = extract_sow(ocr_text)

    # Step 3: Quick validation
    units = data.get("curriculum", {}).get("units", [])
    total_lessons = sum(len(u.get("lessons", [])) for u in units)
    print(f"\n📊 Extracted: {len(units)} unit(s), {total_lessons} lesson(s)")
    for u in units:
        print(f"  Unit {u['unit_number']}: {u['unit_title']} — {len(u.get('lessons', []))} lesson(s)")

    # Step 4: Save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to: {output_path}")


if __name__ == "__main__":
    main()
