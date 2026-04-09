"""
ingest_book.py — OCR a textbook PDF using Mistral OCR and save to Supabase DB.

Usage:
    python utils/ingest_book.py \
        --pdf "books/Computer Book 2.pdf" \
        --subject "Computer Studies" \
        --grade "Grade 2" \
        --book-type "textbook" \
        --title "Tech Explorers Computer Book 2" \
        --page-offset 2 \
        --skip-pdf-pages 1,2 \
        [--ocr-cache Demo_docs/cs_book_ocr.json] \
        [--dry-run]

page-offset:     book_page = pdf_page - offset
skip-pdf-pages:  comma-separated 1-indexed PDF pages to exclude (cover, copyright, etc.)
dry-run:         print results without saving to DB
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time

from pypdf import PdfReader, PdfWriter
from dotenv import load_dotenv

load_dotenv()

# ── path setup so we can import src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_mistral_ocr(pdf_path: str, pdf_pages_to_ocr: list[int], ocr_cache: str | None) -> dict[int, str]:
    """
    Run Mistral OCR on the given 1-indexed PDF pages.
    Returns {pdf_page_no: markdown_text}.
    """
    if ocr_cache and os.path.exists(ocr_cache):
        print(f"📄 Loading cached OCR: {ocr_cache}")
        with open(ocr_cache, encoding="utf-8") as f:
            cached = json.load(f)
        return {int(k): v for k, v in cached.items()}

    from mistralai.client import Mistral
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set in .env")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for pg in pdf_pages_to_ocr:
        writer.add_page(reader.pages[pg - 1])  # 0-indexed

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    pdf_b64 = base64.b64encode(buf.read()).decode()

    print(f"🔍 Running Mistral OCR on {len(pdf_pages_to_ocr)} pages...")
    client = Mistral(api_key=api_key)
    resp = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": f"data:application/pdf;base64,{pdf_b64}"},
    )
    print(f"✅ OCR done: {len(resp.pages)} pages returned")

    results = {}
    for i, page in enumerate(resp.pages):
        pdf_pg = pdf_pages_to_ocr[i]
        results[pdf_pg] = page.markdown

    if ocr_cache:
        os.makedirs(os.path.dirname(os.path.abspath(ocr_cache)), exist_ok=True)
        with open(ocr_cache, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in results.items()}, f, ensure_ascii=False, indent=2)
        print(f"💾 OCR cached: {ocr_cache}")

    return results


def clean_content(text: str) -> str:
    """
    Clean Mistral OCR output for DB storage:
    - Replace image markdown refs with inline [image] placeholders
    - Remove excessive blank lines
    """
    # Replace ![description](filename) with [image: description or 'diagram/screenshot']
    def replace_img(m):
        alt = m.group(1).strip()
        if alt and not alt.startswith("img-"):
            return f"[image: {alt}]"
        return "[image: diagram/screenshot]"

    text = re.sub(r'!\[([^\]]*)\]\([^\)]*\)', replace_img, text)
    # Collapse 3+ blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def is_annotation_noise(text: str) -> bool:
    """
    Heuristic: pages with heavy pencil annotation produce very short
    or mostly non-alphanumeric OCR output.
    """
    clean = re.sub(r'\s+', '', text)
    if len(clean) < 60:
        return True
    alphanum = sum(1 for c in clean if c.isalnum())
    if alphanum / max(len(clean), 1) < 0.25:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Ingest a textbook PDF to Supabase DB via Mistral OCR")
    parser.add_argument("--pdf",            required=True,  help="Path to PDF file")
    parser.add_argument("--subject",        required=True,  help="Subject name (e.g. 'Computer Studies')")
    parser.add_argument("--grade",          required=True,  help="Grade level (e.g. 'Grade 2')")
    parser.add_argument("--book-type",      required=True,  help="Book type (e.g. 'textbook', 'learners', 'activity')")
    parser.add_argument("--title",          required=True,  help="Book title")
    parser.add_argument("--page-offset",    type=int, default=0, help="book_page = pdf_page - offset (default 0)")
    parser.add_argument("--skip-pdf-pages", default="",     help="Comma-separated 1-indexed PDF pages to skip (e.g. '1,2')")
    parser.add_argument("--ocr-cache",      default=None,   help="JSON file path to cache/load OCR results")
    parser.add_argument("--dry-run",        action="store_true", help="Print pages without saving to DB")
    args = parser.parse_args()

    reader = PdfReader(args.pdf)
    total_pdf_pages = len(reader.pages)
    print(f"📖 PDF: {args.pdf} ({total_pdf_pages} pages)")

    # Build skip set
    skip_set = set()
    if args.skip_pdf_pages.strip():
        for s in args.skip_pdf_pages.split(","):
            s = s.strip()
            if s:
                skip_set.add(int(s))

    pages_to_ocr = [pg for pg in range(1, total_pdf_pages + 1) if pg not in skip_set]
    print(f"📄 Pages to process: {len(pages_to_ocr)} (skipping {sorted(skip_set)})")
    print(f"📐 Page offset: {args.page_offset}  (book_page = pdf_page - {args.page_offset})")

    # OCR
    ocr_results = run_mistral_ocr(args.pdf, pages_to_ocr, args.ocr_cache)

    # Build page records
    pages = []
    skipped_noise = []
    skipped_empty = []

    for pdf_pg in sorted(ocr_results.keys()):
        raw = ocr_results[pdf_pg]
        book_pg = pdf_pg - args.page_offset
        content = clean_content(raw)

        if not content:
            skipped_empty.append(pdf_pg)
            continue

        if is_annotation_noise(raw):
            print(f"  ⚠ PDF page {pdf_pg} (book {book_pg}): flagged as noise/annotation ({len(raw)} chars) — skipping")
            skipped_noise.append(pdf_pg)
            continue

        pages.append({
            "content":      content,
            "pdf_page_no":  pdf_pg,
            "book_page_no": book_pg,
        })

    print(f"\n📊 Summary:")
    print(f"   Pages with content:  {len(pages)}")
    print(f"   Skipped (empty):     {len(skipped_empty)} {skipped_empty}")
    print(f"   Skipped (noise):     {len(skipped_noise)} {skipped_noise}")

    # Preview first 3 pages
    print("\n── First 3 pages preview ──")
    for p in pages[:3]:
        print(f"  pdf={p['pdf_page_no']} book={p['book_page_no']} chars={len(p['content'])}")
        print(f"  {p['content'][:200]}")
        print()

    if args.dry_run:
        print("🔍 Dry-run mode — not saving to DB")
        return

    # Save to DB
    from src.db.client import db
    print(f"\n💾 Saving to DB: subject={args.subject}, grade={args.grade}, type={args.book_type}")
    book_id = db.insert_textbook(
        grade_level=args.grade,
        subject=args.subject,
        book_type=args.book_type,
        title=args.title,
        pages=pages,
    )
    if book_id:
        print(f"✅ Saved! book_id={book_id}, {len(pages)} pages")
    else:
        print("❌ DB insert failed")


if __name__ == "__main__":
    main()
