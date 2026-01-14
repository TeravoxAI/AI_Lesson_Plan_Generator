"""
PDF Processor - Extract text from textbook pages using Vision LLM
"""
import os
import json
import base64
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path

import pdfplumber
from pdf2image import convert_from_path
from PIL import Image
import httpx

from src.prompts.templates import PDF_OCR_PROMPT


class PDFProcessor:
    """Process textbook PDFs and extract content using Vision LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "openai/gpt-4.1"  # Vision-capable model
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    def _extract_text_pdfplumber(self, pdf_path: str, page_num: int) -> str:
        """Fallback: Extract text using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num <= len(pdf.pages):
                    page = pdf.pages[page_num - 1]  # 0-indexed
                    return page.extract_text() or ""
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
        return ""
    
    def _call_vision_llm(self, image_base64: str) -> Dict[str, Any]:
        """Call OpenRouter Vision LLM for OCR"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PDF_OCR_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                # Handle potential markdown code blocks
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                return json.loads(content.strip())
                
        except Exception as e:
            print(f"Vision LLM call failed: {e}")
            return {
                "page_text": "",
                "image_descriptions": [],
                "has_exercises": False,
                "exercise_count": 0
            }
    
    def process_pdf(
        self, 
        pdf_path: str,
        use_vision: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process entire PDF and extract content from each page
        
        Args:
            pdf_path: Path to the PDF file
            use_vision: Whether to use Vision LLM (True) or pdfplumber (False)
        
        Returns:
            List of page data dictionaries
        """
        pages_data = []
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Convert PDF to images
        print(f"Converting PDF to images: {pdf_path.name}")
        images = convert_from_path(str(pdf_path), dpi=150)
        
        total_pages = len(images)
        print(f"Processing {total_pages} pages...")
        
        for page_num, image in enumerate(images, start=1):
            print(f"  Processing page {page_num}/{total_pages}...")
            
            if use_vision:
                # Use Vision LLM for OCR
                image_base64 = self._image_to_base64(image)
                ocr_result = self._call_vision_llm(image_base64)
                
                pages_data.append({
                    "page_number": page_num,
                    "content_text": ocr_result.get("page_text", ""),
                    "image_summary": "; ".join(ocr_result.get("image_descriptions", [])),
                    "has_exercises": ocr_result.get("has_exercises", False),
                    "exercise_count": ocr_result.get("exercise_count", 0)
                })
            else:
                # Fallback to pdfplumber
                text = self._extract_text_pdfplumber(str(pdf_path), page_num)
                pages_data.append({
                    "page_number": page_num,
                    "content_text": text,
                    "image_summary": "",
                    "has_exercises": False,
                    "exercise_count": 0
                })
        
        print(f"Completed processing {total_pages} pages")
        return pages_data
    
    def process_page_range(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int,
        use_vision: bool = True
    ) -> List[Dict[str, Any]]:
        """Process a specific range of pages"""
        pages_data = []
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Convert specific pages to images
        images = convert_from_path(
            str(pdf_path),
            dpi=150,
            first_page=start_page,
            last_page=end_page
        )
        
        for idx, image in enumerate(images):
            page_num = start_page + idx
            print(f"Processing page {page_num}...")
            
            if use_vision:
                image_base64 = self._image_to_base64(image)
                ocr_result = self._call_vision_llm(image_base64)
                
                pages_data.append({
                    "page_number": page_num,
                    "content_text": ocr_result.get("page_text", ""),
                    "image_summary": "; ".join(ocr_result.get("image_descriptions", [])),
                    "has_exercises": ocr_result.get("has_exercises", False),
                    "exercise_count": ocr_result.get("exercise_count", 0)
                })
            else:
                text = self._extract_text_pdfplumber(str(pdf_path), page_num)
                pages_data.append({
                    "page_number": page_num,
                    "content_text": text,
                    "image_summary": "",
                    "has_exercises": False,
                    "exercise_count": 0
                })
        
        return pages_data


# Singleton instance
pdf_processor = PDFProcessor()
