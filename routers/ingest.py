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


@router.get("/books")
async def list_books():
    """List all ingested textbooks"""
    books = db.list_textbooks()
    
    # Add page count, don't send full pages in list
    for book in books:
        pages = book.get("pages", [])
        if isinstance(pages, str):
            import json
            pages = json.loads(pages) if pages else []
        book["page_count"] = len(pages)
        book["has_content"] = len(pages) > 0
        # Remove pages from list response (too large)
        if "pages" in book:
            del book["pages"]
    
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
