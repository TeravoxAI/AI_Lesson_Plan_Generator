"""
SOW Parser - Extract structured data from Scheme of Work documents
"""
import os
import json
import base64
import re
from typing import List, Dict, Any
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
import httpx

from src.prompts.templates import SOW_PARSER_PROMPT


class SOWParser:
    """Parse Scheme of Work documents using Vision LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "openai/gpt-4.1"
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    def _expand_page_range(self, page_str: str) -> List[int]:
        """
        Expand page references to list of integers
        Examples:
            "44-46" -> [44, 45, 46]
            "12, 15, 18" -> [12, 15, 18]
            "pg 23-25, 30" -> [23, 24, 25, 30]
        """
        pages = []
        
        # Remove common prefixes
        cleaned = re.sub(r'(pg|page|p\.|pp\.)\s*', '', page_str, flags=re.IGNORECASE)
        
        # Split by comma
        parts = cleaned.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Handle range
                try:
                    start, end = part.split('-')
                    start = int(re.sub(r'\D', '', start))
                    end = int(re.sub(r'\D', '', end))
                    pages.extend(range(start, end + 1))
                except ValueError:
                    pass
            else:
                # Single page
                try:
                    page = int(re.sub(r'\D', '', part))
                    if page > 0:
                        pages.append(page)
                except ValueError:
                    pass
        
        return sorted(list(set(pages)))
    
    def _call_vision_llm(self, image_base64: str) -> Dict[str, Any]:
        """Call OpenRouter Vision LLM for SOW parsing"""
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
                            "text": SOW_PARSER_PROMPT
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
            "max_tokens": 8000
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                return json.loads(content.strip())
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            return {"entries": []}
        except Exception as e:
            print(f"Vision LLM call failed: {e}")
            return {"entries": []}
    
    def parse_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parse SOW from PDF document
        
        Args:
            pdf_path: Path to the SOW PDF file
        
        Returns:
            List of parsed SOW entries
        """
        all_entries = []
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Convert PDF to images
        print(f"Converting SOW PDF to images: {pdf_path.name}")
        images = convert_from_path(str(pdf_path), dpi=200)
        
        total_pages = len(images)
        print(f"Processing {total_pages} SOW pages...")
        
        for page_num, image in enumerate(images, start=1):
            print(f"  Parsing SOW page {page_num}/{total_pages}...")
            
            image_base64 = self._image_to_base64(image)
            result = self._call_vision_llm(image_base64)
            
            entries = result.get("entries", [])
            
            # Post-process entries
            for entry in entries:
                # Ensure page numbers are properly parsed
                if isinstance(entry.get("mapped_page_numbers"), str):
                    entry["mapped_page_numbers"] = self._expand_page_range(
                        entry["mapped_page_numbers"]
                    )
                elif not entry.get("mapped_page_numbers"):
                    entry["mapped_page_numbers"] = []
                
                all_entries.append(entry)
        
        print(f"Extracted {len(all_entries)} SOW entries")
        return all_entries
    
    def parse_image(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Parse SOW from a single image
        
        Args:
            image_path: Path to the SOW image file
        
        Returns:
            List of parsed SOW entries
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        print(f"Parsing SOW image: {image_path.name}")
        
        image = Image.open(image_path)
        image_base64 = self._image_to_base64(image)
        result = self._call_vision_llm(image_base64)
        
        entries = result.get("entries", [])
        
        # Post-process entries
        for entry in entries:
            if isinstance(entry.get("mapped_page_numbers"), str):
                entry["mapped_page_numbers"] = self._expand_page_range(
                    entry["mapped_page_numbers"]
                )
            elif not entry.get("mapped_page_numbers"):
                entry["mapped_page_numbers"] = []
        
        print(f"Extracted {len(entries)} SOW entries")
        return entries


# Singleton instance
sow_parser = SOWParser()
