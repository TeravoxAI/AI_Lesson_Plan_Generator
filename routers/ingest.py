"""
Ingestion Router - API endpoints for uploading and processing documents
Uses LandingAI ADE ONLY for document extraction (no fallback)
"""
import os
import tempfile
import shutil
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from src.models import Subject, BookType, IngestResponse
from src.db.client import db


router = APIRouter(tags=["Ingestion"])


@router.post("/textbook", response_model=IngestResponse)
async def ingest_textbook(
    file: UploadFile = File(...),
    grade: str = Form(default="Grade 2"),
    subject: Subject = Form(...),
    book_type: BookType = Form(...),
    title: str = Form(...)
):
    """
    Upload and process a textbook PDF using LandingAI ADE.
    
    - Uses LandingAI ADE for OCR
    - Stores pages as JSONB array: [{"book_text": "...", "page_no": 1}, ...]
    - Images are converted to inline: [object: description]
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Check if book already exists
    existing = db.get_textbook(grade, subject.value, book_type.value)
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Book already exists: {existing['title']}. Delete it first to re-upload."
        )
    
    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Use ADE processor only
        from src.ingestion.ade_processor import get_ade_processor
        processor = get_ade_processor()
        
        # Process PDF - returns [{"book_text": "...", "page_no": 1}, ...]
        pages_data = processor.process_pdf(temp_path)
        
        # Create textbook record with pages
        book_id = db.insert_textbook(
            grade_level=grade,
            subject=subject.value,
            book_type=book_type.value,
            title=title,
            pages=pages_data
        )
        
        if not book_id:
            raise HTTPException(status_code=500, detail="Failed to create textbook record")
        
        return IngestResponse(
            success=True,
            message=f"Successfully processed {title} using ADE",
            book_id=book_id,
            pages_processed=len(pages_data)
        )
        
    except Exception as e:
        return IngestResponse(
            success=False,
            message="Failed to process textbook",
            error=str(e)
        )
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/sow", response_model=IngestResponse)
async def ingest_sow(
    file: UploadFile = File(...),
    grade: str = Form(default="Grade 2"),
    subject: Subject = Form(...),
    term: str = Form(default="Term 1")
):
    """
    Upload and process a Scheme of Work (SOW) document using LandingAI ADE.
    
    - Uses LandingAI ADE for structured extraction
    - Extracts topics, page mappings, strategies, and activities
    """
    filename = file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith(('.png', '.jpg', '.jpeg'))):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF and image files (PNG, JPG) are accepted"
        )
    
    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Use ADE processor to extract SOW
        from src.ingestion.ade_processor import get_ade_processor
        processor = get_ade_processor()
        extraction = processor.extract_sow(temp_path)
        
        # Store the complete extraction as a single record
        sow_id = db.insert_sow_entry(
            grade_level=grade,
            subject=subject.value,
            term=term,
            title=file.filename,
            extraction=extraction
        )
        
        if sow_id:
            return IngestResponse(
                success=True,
                message=f"Successfully extracted SOW for {subject.value}",
                entries_extracted=1,
                sow_id=sow_id
            )
        else:
            return IngestResponse(
                success=False,
                message="Failed to save SOW extraction to database",
                error="Database insert failed"
            )
        
    except Exception as e:
        return IngestResponse(
            success=False,
            message="Failed to process SOW",
            error=str(e)
        )
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


GENERALIZED_SOW_SUBJECTS = {"islamiat", "nazra", "urdu"}


@router.post("/generalized-sow", response_model=IngestResponse)
async def ingest_generalized_sow(
    file: UploadFile = File(...),
    grade: str = Form(default="Grade 2"),
    subject: str = Form(...),
    term: str = Form(default=None),
    skip_pages: int = Form(default=-1),   # -1 = use subject default
):
    """
    Upload and process a GeneralizedSOW PDF (Islamiat, Nazra, Urdu, etc.)
    using Mistral OCR + mistral-large-latest extraction.
    """
    subject_lower = subject.lower().replace(" ", "_")
    if subject_lower not in GENERALIZED_SOW_SUBJECTS and subject_lower not in {"computer_studies", "english", "mathematics"}:
        raise HTTPException(status_code=400, detail=f"Unsupported subject for generalized ingestion: {subject}")

    filename = file.filename.lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted for GeneralizedSOW ingestion")

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Import universal extractor functions
        import sys as _sys
        _repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _repo_root not in _sys.path:
            _sys.path.insert(0, _repo_root)
        from utils.universal_sow_extractor import run_ocr, extract_sow, DEFAULT_SKIP_PAGES

        # Resolve skip_pages
        resolved_skip = skip_pages if skip_pages >= 0 else DEFAULT_SKIP_PAGES.get(subject_lower, 0)

        # Step 1: OCR
        ocr_text = run_ocr(
            pdf_path=temp_path,
            skip_pages=resolved_skip,
            max_pages=None,
            ocr_cache=None,  # no cache for API ingestion
        )

        # Step 2: Extract GeneralizedSOW JSON
        extraction = extract_sow(ocr_text, subject=subject_lower, grade=grade, term=term or None)

        # Step 3: Save to database
        sow_id = db.insert_sow_entry(
            grade_level=grade,
            subject=subject,
            term=term or "Term 1",
            title=file.filename,
            extraction=extraction
        )

        if sow_id:
            units = extraction.get("curriculum", {}).get("units", [])
            total_lessons = sum(len(u.get("lessons", [])) for u in units)
            return IngestResponse(
                success=True,
                message=f"Successfully extracted {subject} SOW: {len(units)} units, {total_lessons} lessons",
                entries_extracted=total_lessons,
                sow_id=sow_id
            )
        else:
            return IngestResponse(success=False, message="Failed to save SOW to database", error="Database insert failed")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return IngestResponse(success=False, message="Failed to process GeneralizedSOW", error=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/books")
async def list_books():
    """List all ingested textbooks"""
    books = db.list_textbooks()
    
    # Add page count, don't send full content in list
    for book in books:
        content = book.get("content_text", [])
        if isinstance(content, str):
            import json
            content = json.loads(content) if content else []
        book["page_count"] = len(content)
        book["has_content"] = len(content) > 0
        # Remove content from list response (too large)
        if "content_text" in book:
            del book["content_text"]
    
    return {"books": books}


@router.get("/books/{book_id}/pages")
async def get_book_pages(
    book_id: int,
    page_start: int = 1,
    page_end: Optional[int] = None
):
    """Get specific pages from a textbook"""
    book = db.get_textbook_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if page_end is None:
        page_end = page_start
    
    pages = db.get_textbook_pages(book_id, page_start, page_end)
    
    return {
        "book_id": book_id,
        "title": book.get("title"),
        "page_range": f"{page_start}-{page_end}",
        "pages": pages
    }


@router.delete("/books/{book_id}")
async def delete_book(book_id: int):
    """Delete a textbook"""
    success = db.delete_textbook(book_id)
    if success:
        return {"success": True, "message": f"Deleted book {book_id}"}
    raise HTTPException(status_code=404, detail="Book not found")


@router.get("/sow")
async def list_sow(
    subject: Optional[Subject] = None,
    grade: Optional[str] = None
):
    """List SOW entries with optional filtering"""
    entries = db.list_sow_entries(
        subject=subject.value if subject else None,
        grade_level=grade
    )
    return {"entries": entries, "count": len(entries)}
