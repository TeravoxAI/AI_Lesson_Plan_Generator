"""extract_nazra.py — Extract Nazra SOW to GeneralizedSOW JSON."""
import io, base64, json, os, sys
from pypdf import PdfReader, PdfWriter
from mistralai.client import Mistral
from dotenv import load_dotenv
load_dotenv()

PDF_PATH    = "SOWs/Class_II_Nazra_2nd Term_Cold _ Warm Region (1).pdf"
OCR_PATH    = "Demo_docs/nazra_all_ocr.md"
OUTPUT_PATH = "Demo_docs/test_nazra_generalized.json"

SYSTEM_PROMPT = """You are a precise data extraction agent. Extract the Nazra (Quran Recitation) SOW into a GeneralizedSOW JSON structure.

GOLDEN RULE: Extract ONLY what is written. Do NOT infer, add, or hallucinate.

OUTPUT SCHEMA:
{
  "metadata": {"subject": "nazra", "grade": "2", "term": "second", "language": "urdu", "sow_version": "2.0"},
  "curriculum": {
    "units": [
      {
        "unit_number": <int>,
        "unit_title": "<section title>",
        "lessons": [
          {
            "lesson_number": <int>,
            "lesson_title": "<topic>",
            "slos": ["<each objective bullet verbatim>"],
            "skills": [],
            "teaching_strategies": [],
            "afl_strategies": [],
            "classwork": [],
            "recitation": {
              "surah_name": "<Surah name — OMIT KEY if not recitation lesson>",
              "verse_range": "<verse range — OMIT KEY if not recitation lesson>",
              "tajweed_rules": ["<each Tajweed rule name mentioned>"]
            }
          }
        ]
      }
    ]
  }
}

SOW STRUCTURE: 3-column table: week | topic | objectives
Skip page 1 (cover) and page 5 (progress chart).

UNITS:
  Unit 1: "حفظ و ترجمہ و احادیث" — weeks 1-7 (memorization, hadith, duas)
  Unit 2: "ناظرہ قرآن مجید" — weeks 8-17 (Surah Al-Baqarah recitation)

LESSONS: each weekly entry = one lesson, numbered sequentially within unit.
For ناظرہ lessons: populate recitation.surah_name, verse_range, tajweed_rules.
For حفظ/احادیث lessons: OMIT recitation key entirely.

Output valid JSON only."""

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ocr_path    = os.path.join(repo_root, OCR_PATH)
    output_path = os.path.join(repo_root, OUTPUT_PATH)

    if os.path.exists(ocr_path):
        print(f"📄 Loading cached OCR from {ocr_path}")
        with open(ocr_path, encoding='utf-8') as f:
            ocr_text = f.read()
    else:
        pdf_path = os.path.join(repo_root, PDF_PATH)
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for i in range(len(reader.pages)):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        pdf_b64 = base64.b64encode(buf.read()).decode()
        client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
        resp = client.ocr.process(
            model='mistral-ocr-latest',
            document={'type': 'document_url', 'document_url': f'data:application/pdf;base64,{pdf_b64}'}
        )
        ocr_text = '\n\n'.join(f'=== PAGE {i+1} ===\n{p.markdown}' for i, p in enumerate(resp.pages))
        with open(ocr_path, 'w', encoding='utf-8') as f:
            f.write(ocr_text)
        print(f"✅ OCR done: {len(ocr_text)} chars")

    client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
    print(f"🤖 Extracting with mistral-large-latest ({len(ocr_text)} chars)...")
    resp = client.chat.complete(
        model='mistral-large-latest',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'Extract GeneralizedSOW from this Nazra SOW OCR (Grade 2, Second Term):\n\n{ocr_text}'}
        ],
        temperature=0,
        max_tokens=8000,
        response_format={'type': 'json_object'}
    )
    msg = resp.choices[0].message.content
    print(f"✅ Tokens — in: {resp.usage.prompt_tokens} | out: {resp.usage.completion_tokens} | finish: {resp.choices[0].finish_reason}")

    stripped = msg.strip()
    if stripped.startswith('```'):
        stripped = stripped.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    data = json.loads(stripped)

    units = data['curriculum']['units']
    total_lessons = sum(len(u.get('lessons', [])) for u in units)
    print(f"\n📊 Extracted: {len(units)} unit(s), {total_lessons} lesson(s)")
    for u in units:
        print(f"  Unit {u['unit_number']}: {u['unit_title']} — {len(u.get('lessons', []))} lessons")
        for l in u.get('lessons', []):
            has_rec = 'recitation' in l
            tajweed = len(l.get('recitation', {}).get('tajweed_rules', []))
            print(f"    L{l['lesson_number']}: {l['lesson_title'][:55]} | rec={has_rec} tajweed={tajweed}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to: {output_path}")

if __name__ == '__main__':
    main()
