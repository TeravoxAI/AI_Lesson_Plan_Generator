"""
Ingestion Router - API endpoints for uploading and processing documents
"""
import os
import tempfile
import shutil
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from src.models import Subject, BookType, IngestResponse
from src.db.client import db
from src.ingestion.pdf_processor import pdf_processor
from src.ingestion.sow_parser import sow_parser


router = APIRouter(tags=["Ingestion"])


@router.post("/textbook", response_model=IngestResponse)
async def ingest_textbook(
    file: UploadFile = File(...),
    grade: str = Form(default="Grade 2"),
    subject: Subject = Form(...),
    book_type: BookType = Form(...),
    title: str = Form(...),
    use_vision: bool = Form(default=True)
):
    """
    Upload and process a textbook PDF.
    
    - Extracts text from each page using Vision LLM (or pdfplumber fallback)
    - Stores metadata and content in database
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Check if book already exists
    existing = db.get_textbook(grade, subject.value, book_type.value)
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Book already exists: {title}. Delete it first to re-upload."
        )
    
    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Create textbook record
        book_id = db.insert_textbook(
            grade_level=grade,
            subject=subject.value,
            book_type=book_type.value,
            title=title
        )
        
        if not book_id:
            raise HTTPException(status_code=500, detail="Failed to create textbook record")
        
        # Process PDF pages
        pages_data = pdf_processor.process_pdf(temp_path, use_vision=use_vision)
        
        # Insert pages into database
        for page in pages_data:
            db.insert_page(
                book_id=book_id,
                page_number=page["page_number"],
                content_text=page["content_text"],
                image_summary=page.get("image_summary", ""),
                has_exercises=page.get("has_exercises", False),
                exercise_count=page.get("exercise_count", 0)
            )
        
        return IngestResponse(
            success=True,
            message=f"Successfully processed {title}",
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
    Upload and process a Scheme of Work (SOW) document.
    
    - Parses SOW tables using Vision LLM
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
        
        # Parse SOW based on file type
        if filename.endswith('.pdf'):
            entries = sow_parser.parse_pdf(temp_path)
        else:
            entries = sow_parser.parse_image(temp_path)
        
        # Insert entries into database
        inserted_count = 0
        for entry in entries:
            entry_id = db.insert_sow_entry(
                grade_level=grade,
                subject=subject.value,
                term=term,
                topic_name=entry.get("topic_name", ""),
                mapped_page_numbers=entry.get("mapped_page_numbers", []),
                teaching_strategy=entry.get("teaching_strategy", ""),
                resources_text=entry.get("resources", ""),
                afl_strategy=entry.get("afl_strategy", ""),
                activities=entry.get("activities", "")
            )
            if entry_id:
                inserted_count += 1
        
        return IngestResponse(
            success=True,
            message=f"Successfully parsed SOW for {subject.value}",
            entries_extracted=inserted_count
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
    
    # Enrich with page count
    for book in books:
        pages = db.get_pages_by_book(book["id"])
        book["page_count"] = len(pages)
    
    return {"books": books}


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
