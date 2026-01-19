"""
ADE Processor - Extract text from documents using LandingAI Agentic Document Extraction
Uses official SDK patterns from LandingAI documentation
"""
import os
import json
import re
from io import BytesIO
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from landingai_ade import LandingAIADE
from landingai_ade.lib import pydantic_to_json_schema
from pdf2image import convert_from_path


# ============ Pydantic Models for Extraction ============

class PageContent(BaseModel):
    """A single page of text content from a textbook."""
    page_no: int = Field(..., description="The page number")
    book_text: str = Field(..., description="Full text content of the page. Images should be described inline as [object: description of image]")


class TextbookExtraction(BaseModel):
    """Extracted content from a textbook PDF."""
    pages: List[PageContent] = Field(
        ...,
        description="List of pages with their text content. Each page includes page number and full text. Images are described inline as [object: description]"
    )


class SOWEntry(BaseModel):
    """A single entry from a Scheme of Work document."""
    topic_name: str = Field(..., description="The lesson/unit title")
    page_references: str = Field(default="", description="All page numbers mentioned (e.g., 'pg 44-46', 'AB pg. 85')")
    teaching_strategy: str = Field(default="", description="Teaching methodology and activities")
    activities: str = Field(default="", description="Specific games, videos, or named activities")
    afl_strategy: str = Field(default="", description="Assessment methods (e.g., Quiz, RSQC2)")
    resources: str = Field(default="", description="URLs, digital resources, or materials listed")


class SOWExtraction(BaseModel):
    """Extracted content from a Scheme of Work document."""
    entries: List[SOWEntry] = Field(
        ...,
        description="List of lesson entries from the Scheme of Work table. Each row in the SOW table should be one entry."
    )


class SimpleTextExtraction(BaseModel):
    """Simple text extraction from a document."""
    book_text: str = Field(..., description="Full text content including [object: description] for any images")


# ============ ADE Processor Class ============

class ADEProcessor:
    """
    Process documents using LandingAI Agentic Document Extraction.
    
    Output format for books:
    [
        {"book_text": "Page content with [object: image description]...", "page_no": 1},
        {"book_text": "More content...", "page_no": 2}
    ]
    """
    
    def __init__(self):
        self.api_key = os.getenv("ADE_API_KEY")
        if not self.api_key:
            raise ValueError("ADE_API_KEY not found in environment variables")
        
        self.client = LandingAIADE(apikey=self.api_key)
        
        # Pre-compute JSON schemas
        self.textbook_schema = pydantic_to_json_schema(TextbookExtraction)
        self.sow_schema = pydantic_to_json_schema(SOWExtraction)
        self.simple_schema = pydantic_to_json_schema(SimpleTextExtraction)
    
    def _clean_markdown_to_text(self, markdown_text: str) -> str:
        """Clean markdown formatting while preserving content structure."""
        text = markdown_text
        
        # Convert markdown images to inline format
        image_pattern = r'!\[([^\]]*)\]\([^)]+\)'
        text = re.sub(image_pattern, lambda m: f"[object: {m.group(1)}]" if m.group(1) else "[object: image]", text)
        
        # Remove markdown headers but keep the text
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Remove bold/italic but keep text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process a PDF file: parse to markdown, then extract structured data.
        
        Flow: PDF → parse() → markdown → extract(schema, BytesIO(markdown)) → JSON
        
        Returns:
            List of dicts: [{"book_text": "...", "page_no": 1}, ...]
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Processing PDF with LandingAI ADE: {pdf_path.name}")
        
        # Step 1: Parse PDF to Markdown
        print("  Step 1: Parsing PDF to markdown...")
        parse_result = self.client.parse(document=pdf_path)
        
        if not hasattr(parse_result, 'markdown') or not parse_result.markdown:
            print("  WARNING: No markdown from parse!")
            return []
        
        markdown_content = parse_result.markdown
        print(f"  Got {len(markdown_content)} chars of markdown")
        
        # Step 2: Extract structured data from markdown
        print("  Step 2: Extracting structured pages from markdown...")
        
        try:
            extract_result = self.client.extract(
                schema=self.textbook_schema,
                markdown=BytesIO(markdown_content.encode('utf-8'))
            )
            
            print(f"  Extract result: {type(extract_result)}")
            
            if hasattr(extract_result, 'extraction') and extract_result.extraction:
                pages = extract_result.extraction.get('pages', [])
                print(f"  Extracted {len(pages)} pages")
                if pages:
                    return pages
            
        except Exception as e:
            print(f"  Extract failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Fallback: Return cleaned markdown as single page
        print("  Fallback: Returning cleaned markdown as single page")
        cleaned = self._clean_markdown_to_text(markdown_content)
        return [{"book_text": cleaned, "page_no": 1}]
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image file: parse to markdown, then extract.
        
        Returns:
            Dict: {"book_text": "...", "page_no": 1}
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        print(f"Processing image with LandingAI ADE: {image_path.name}")
        
        # Step 1: Parse image to markdown
        parse_result = self.client.parse(document=image_path)
        
        if not hasattr(parse_result, 'markdown') or not parse_result.markdown:
            return {"book_text": "", "page_no": 1}
        
        # Step 2: Extract structured data
        try:
            extract_result = self.client.extract(
                schema=self.simple_schema,
                markdown=BytesIO(parse_result.markdown.encode('utf-8'))
            )
            
            if hasattr(extract_result, 'extraction') and extract_result.extraction:
                return {
                    "book_text": extract_result.extraction.get('book_text', ''),
                    "page_no": 1
                }
        except:
            pass
        
        # Fallback to cleaned markdown
        return {"book_text": self._clean_markdown_to_text(parse_result.markdown), "page_no": 1}
    
    def extract_sow(self, file_path: str) -> Dict[str, Any]:
        """
        Extract Scheme of Work from a document.
        
        Flow: PDF/Image → parse() → markdown → extract(SOW schema) → complete JSON
        
        Returns:
            Complete extraction dict with entries, metadata, etc.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        print(f"Extracting SOW with LandingAI ADE: {file_path.name}")
        
        # Step 1: Parse to markdown
        print("  Step 1: Parsing SOW to markdown...")
        parse_result = self.client.parse(document=file_path)
        
        if not hasattr(parse_result, 'markdown') or not parse_result.markdown:
            print("  ERROR: No markdown from parse!")
            return {"error": "No markdown from parse", "entries": []}
        
        markdown_content = parse_result.markdown
        print(f"  Got {len(markdown_content)} chars of markdown")
        
        # Step 2: Extract structured data
        print("  Step 2: Extracting structured entries from markdown...")
        
        try:
            extract_result = self.client.extract(
                schema=self.sow_schema,
                markdown=BytesIO(markdown_content.encode('utf-8'))
            )
            
            print(f"  Extract result type: {type(extract_result)}")
            
            if hasattr(extract_result, 'extraction') and extract_result.extraction:
                extraction = extract_result.extraction
                print(f"  Extraction: {extraction}")
                
                # Return complete extraction dict
                return extraction
        
        except Exception as e:
            print(f"  ERROR in extract: {e}")
            import traceback
            traceback.print_exc()
        
        # Fallback: Return empty structure
        print("  Returning empty extraction")
        return {"entries": [], "error": "Extraction failed"}
    
    def _parse_page_references(self, page_str: str) -> List[int]:
        """
        Parse page reference strings into list of integers.
        
        Examples:
            "pg 44-46" -> [44, 45, 46]
            "CB p.12, WB p.5" -> [12, 5]
            "pages 10, 12, 15" -> [10, 12, 15]
        """
        if not page_str:
            return []
        
        pages = []
        
        # Remove common prefixes
        cleaned = re.sub(r'(pg|page|p\.|pp\.|CB|WB|LB|AB|TR)\s*', '', page_str, flags=re.IGNORECASE)
        
        # Split by comma or 'and'
        parts = re.split(r'[,\s]+(?:and\s+)?', cleaned)
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Handle range
                try:
                    match = re.match(r'(\d+)\s*-\s*(\d+)', part)
                    if match:
                        start, end = int(match.group(1)), int(match.group(2))
                        pages.extend(range(start, end + 1))
                except ValueError:
                    pass
            else:
                # Single page
                match = re.search(r'\d+', part)
                if match:
                    pages.append(int(match.group()))
        
        return sorted(list(set(pages)))


# Lazy singleton - only initialize when needed
_ade_processor: Optional[ADEProcessor] = None

def get_ade_processor() -> ADEProcessor:
    global _ade_processor
    if _ade_processor is None:
        _ade_processor = ADEProcessor()
    return _ade_processor
