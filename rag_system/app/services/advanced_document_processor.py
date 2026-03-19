"""
Advanced Document Processing Service with intelligent chunking.
Handles tables, images, page numbers, and document structure.
"""
import os
import re
import uuid
import base64
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from io import BytesIO

import pdfplumber
from PIL import Image
import pandas as pd

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class TableElement:
    """Represents a table extracted from document."""
    def __init__(self, data: List[List[str]], page_number: int, bbox: Optional[tuple] = None):
        self.data = data
        self.page_number = page_number
        self.bbox = bbox  # Bounding box (x0, y0, x1, y1)
        
    def to_markdown(self) -> str:
        """Convert table to markdown format with cleaned data."""
        if not self.data or not self.data[0]:
            return ""
        
        # Clean and optimize table data
        cleaned_data = self._clean_table_data()
        if not cleaned_data or len(cleaned_data) < 2:
            return ""
        
        # Use pandas for better table formatting
        df = pd.DataFrame(cleaned_data[1:], columns=cleaned_data[0])
        markdown = df.to_markdown(index=False)
        return f"\n\n**Table (Page {self.page_number})**\n{markdown}\n\n"
    
    def to_structured_text(self) -> str:
        """Convert table to structured text format (better for complex tables)."""
        if not self.data or not self.data[0]:
            return ""
        
        # Clean table data
        cleaned_data = self._clean_table_data()
        if not cleaned_data or len(cleaned_data) < 2:
            return ""
        
        # Convert to structured text
        result = [f"\n**Table (Page {self.page_number})**\n"]
        headers = cleaned_data[0]
        
        for row_idx, row in enumerate(cleaned_data[1:], 1):
            # Try to use a meaningful row label from the first column
            row_label = row[0].strip() if row and row[0] and row[0].strip() else f"Row {row_idx}"
            result.append(f"\n--- {row_label} ---")
            for header, value in zip(headers, row):
                if value and value.strip():
                    # Use header as label (clean up column_N patterns)
                    label = header if header and not header.startswith('column_') else f"Field {headers.index(header)+1}"
                    result.append(f"{label}: {value}")
        
        return "\n".join(result) + "\n\n"
    
    def _clean_table_data(self) -> List[List[str]]:
        """Clean table data by removing empty columns, merging fragmented cells, and improving headers."""
        if not self.data:
            return []
        
        # Step 1: Identify non-empty columns
        num_cols = max(len(row) for row in self.data) if self.data else 0
        col_has_content = [False] * num_cols
        
        for row in self.data:
            for col_idx, cell in enumerate(row):
                if col_idx < num_cols and cell and str(cell).strip():
                    col_has_content[col_idx] = True
        
        # Step 2: Remove completely empty columns
        cleaned_data = []
        for row in self.data:
            # Extend row to match num_cols
            extended_row = row + [''] * (num_cols - len(row))
            cleaned_row = [extended_row[i] for i in range(num_cols) if col_has_content[i]]
            cleaned_data.append(cleaned_row)
        
        # Step 3: Remove columns that are >80% empty (except headers and first col)
        if len(cleaned_data) > 2:
            num_cols = len(cleaned_data[0]) if cleaned_data else 0
            col_content_ratio = [0] * num_cols
            
            for row in cleaned_data[1:]:  # Skip header
                for col_idx, cell in enumerate(row):
                    if col_idx < num_cols and cell and str(cell).strip():
                        col_content_ratio[col_idx] += 1
            
            # Calculate ratio
            total_rows = len(cleaned_data) - 1
            if total_rows > 0:
                keep_cols = [
                    (col_content_ratio[i] / total_rows) > 0.15 or i == 0  # Keep first col always
                    for i in range(num_cols)
                ]
            else:
                keep_cols = [True] * num_cols
            
            cleaned_data = [
                [row[i] for i in range(min(len(row), num_cols)) if i < len(keep_cols) and keep_cols[i]]
                for row in cleaned_data
            ]
        
        # Step 4: Clean cell values and normalize whitespace
        final_data = []
        for row in cleaned_data:
            cleaned_row = [
                ' '.join(str(cell).split()) if cell else ''
                for cell in row
            ]
            # Only keep non-empty rows
            if any(cell.strip() for cell in cleaned_row):
                final_data.append(cleaned_row)
        
        # Step 5: Improve header names - replace empty headers with inferred names
        if final_data:
            import re as _re
            headers = final_data[0]
            for i, h in enumerate(headers):
                if not h or h.strip() == '':
                    # Try to infer from data in this column
                    for data_row in final_data[1:3]:  # Check first 2 data rows
                        if i < len(data_row) and data_row[i]:
                            val = data_row[i].strip()
                            if _re.match(r'^\d+\.\d+', val):
                                headers[i] = 'No.'
                            elif len(val) > 80:
                                headers[i] = 'Description'
                            break
                    if not headers[i]:
                        headers[i] = f'Field {i+1}'
        
        return final_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert table to dictionary."""
        return {
            "type": "table",
            "page": self.page_number,
            "data": self.data,
            "markdown": self.to_markdown(),
            "bbox": self.bbox
        }


class ImageElement:
    """Represents an image extracted from document."""
    def __init__(self, image: Image.Image, page_number: int, image_index: int, bbox: Optional[tuple] = None):
        self.image = image
        self.page_number = page_number
        self.image_index = image_index
        self.bbox = bbox
        self.base64_data = None
        
    def to_base64(self) -> str:
        """Convert image to base64 string."""
        if self.base64_data is None:
            buffered = BytesIO()
            self.image.save(buffered, format="PNG")
            self.base64_data = base64.b64encode(buffered.getvalue()).decode()
        return self.base64_data
    
    def save(self, output_dir: str, document_id: str) -> str:
        """Save image to disk and return path."""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{document_id}_page{self.page_number}_img{self.image_index}.png"
        filepath = os.path.join(output_dir, filename)
        self.image.save(filepath, format="PNG")
        return filepath
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert image to dictionary."""
        return {
            "type": "image",
            "page": self.page_number,
            "index": self.image_index,
            "base64": self.to_base64(),
            "bbox": self.bbox
        }


class DocumentSection:
    """Represents a section of document with its content and metadata."""
    def __init__(self, text: str, page_number: int, section_type: str = "paragraph"):
        self.text = text
        self.page_number = page_number
        self.section_type = section_type  # heading, paragraph, list, etc.
        
    def __str__(self):
        return self.text


class AdvancedDocumentProcessor:
    """
    Advanced document processor with intelligent chunking.
    Handles tables, images, page numbers, and document structure.
    """
    
    def __init__(self):
        # Initialize text splitter for large sections
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def extract_document_elements(self, pdf_path: str) -> Tuple[List[DocumentSection], List[TableElement], List[ImageElement]]:
        """
        Extract all elements from PDF: text sections, tables, and images.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (sections, tables, images)
        """
        sections = []
        tables = []
        images = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract tables with better settings
                page_tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "edge_min_length": 3,
                    "min_words_vertical": 1,
                    "min_words_horizontal": 1,
                    "intersection_tolerance": 3,
                })
                
                for table_data in page_tables:
                    if table_data and len(table_data) > 1:  # At least header + one row
                        # Clean table data
                        cleaned_table = []
                        for row in table_data:
                            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                            if any(cleaned_row):  # Skip empty rows
                                cleaned_table.append(cleaned_row)
                        
                        if cleaned_table and len(cleaned_table) > 1:
                            tables.append(TableElement(cleaned_table, page_num))
                
                # Extract images
                if hasattr(page, 'images'):
                    for img_idx, img_info in enumerate(page.images):
                        try:
                            # Get image from page
                            bbox = (img_info.get('x0'), img_info.get('top'), 
                                   img_info.get('x1'), img_info.get('bottom'))
                            
                            # Extract image using page coordinates
                            img = page.within_bbox(bbox).to_image(resolution=150)
                            pil_image = img.original
                            
                            images.append(ImageElement(pil_image, page_num, img_idx, bbox))
                        except Exception as e:
                            print(f"Warning: Could not extract image {img_idx} from page {page_num}: {e}")
                
                # Extract text (excluding table areas to avoid duplication)
                text = page.extract_text()
                if text:
                    # Clean up text
                    text = self._clean_text(text)
                    
                    # Split into paragraphs and detect structure
                    paragraphs = self._split_into_paragraphs(text, page_num)
                    sections.extend(paragraphs)
        
        return sections, tables, images
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove common PDF artifacts
        text = re.sub(r'\x00', '', text)
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text.strip()
    
    @staticmethod
    def _is_toc_section(text: str) -> bool:
        """
        Detect whether a block of text is a Table of Contents entry.
        TOC lines look like:  'SECTION TITLE .......  42'
        If ≥50% of non-blank lines match the pattern → it is a TOC block.
        """
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return False
        toc_pattern = re.compile(r'\.{3,}\s*\d+\s*$')
        toc_hits = sum(1 for l in lines if toc_pattern.search(l))
        return toc_hits / len(lines) >= 0.5

    @staticmethod
    def _extract_section_id(text: str) -> Optional[str]:
        """
        Pull the leading section number from a paragraph text.
        e.g. '10.3.1 All new systems...'  →  '10.3.1'
        Returns None when no section number is found.
        """
        m = re.match(r'^(\d+(?:\.\d+)+)', text.strip())
        return m.group(1) if m else None

    def _split_into_paragraphs(self, text: str, page_number: int) -> List[DocumentSection]:
        """Split text into structured paragraphs with type detection, skipping TOC pages."""
        sections = []

        # Skip the entire page if it looks like a Table of Contents
        if self._is_toc_section(text):
            return sections

        # Split by double line breaks or numbered list starters
        parts = re.split(r'\n\n+|\n(?=\d+\.|\•|\-\s)', text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Also skip individual TOC lines that slipped through
            if self._is_toc_section(part):
                continue

            # Detect section type
            if re.match(r'^[A-Z\s]{5,}$', part):   # ALL CAPS = heading
                section_type = "heading"
            elif re.match(r'^\d+\.', part):          # Numbered section / list
                section_type = "list_item"
            elif re.match(r'^[•\-]\s', part):        # Bullet list
                section_type = "list_item"
            else:
                section_type = "paragraph"

            sections.append(DocumentSection(part, page_number, section_type))

        return sections
    
    def create_intelligent_chunks(
        self, 
        sections: List[DocumentSection], 
        tables: List[TableElement], 
        images: List[ImageElement],
        document_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Create intelligent chunks that preserve document structure.
        
        Strategy:
        1. Keep tables intact with their own chunks
        2. Group related sections together (headings with following paragraphs)
        3. Add page numbers and context to each chunk
        4. Reference images in nearby text chunks
        
        Args:
            sections: List of document sections
            tables: List of extracted tables
            images: List of extracted images
            document_id: Document identifier
            filename: Original filename
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        chunk_index = 0
        
        # First, add table chunks (tables are kept intact)
        for table in tables:
            # Choose format based on settings
            if settings.table_format == "structured":
                table_text = table.to_structured_text()
            else:
                table_text = table.to_markdown()
            
            chunks.append({
                "text": table_text,
                "metadata": {
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "chunk_type": "table",
                    "page": table.page_number,
                    "has_table": True,
                    "table_data": json.dumps(table.to_dict())
                }
            })
            chunk_index += 1
        
        # Group sections intelligently
        current_chunk_text = []
        current_chunk_pages = set()
        current_section_start = None
        
        for i, section in enumerate(sections):
            # Start new chunk on headings (but include heading in chunk)
            if section.section_type == "heading" and current_chunk_text:
                # Save previous chunk
                chunk_text = " ".join(current_chunk_text)
                if chunk_text.strip():
                    chunks.extend(self._create_text_chunks(
                        chunk_text, 
                        list(current_chunk_pages),
                        document_id,
                        filename,
                        chunk_index,
                        images
                    ))
                    chunk_index += len(chunks) - chunk_index
                
                # Start new chunk
                current_chunk_text = [section.text]
                current_chunk_pages = {section.page_number}
            else:
                current_chunk_text.append(section.text)
                current_chunk_pages.add(section.page_number)
            
            # If chunk is getting too large, split it
            combined_text = " ".join(current_chunk_text)
            if len(combined_text) > settings.chunk_size * 2:
                chunks.extend(self._create_text_chunks(
                    combined_text,
                    list(current_chunk_pages),
                    document_id,
                    filename,
                    chunk_index,
                    images
                ))
                chunk_index += len(chunks) - chunk_index
                current_chunk_text = []
                current_chunk_pages = set()
        
        # Add remaining text
        if current_chunk_text:
            chunk_text = " ".join(current_chunk_text)
            if chunk_text.strip():
                chunks.extend(self._create_text_chunks(
                    chunk_text,
                    list(current_chunk_pages),
                    document_id,
                    filename,
                    chunk_index,
                    images
                ))
        
        # Update total chunks in all metadata
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = total_chunks
        
        return chunks
    
    def _create_text_chunks(
        self,
        text: str,
        pages: List[int],
        document_id: str,
        filename: str,
        start_index: int,
        images: List[ImageElement]
    ) -> List[Dict[str, Any]]:
        """Create chunks from text with metadata."""
        # Split if text is too large
        if len(text) > settings.chunk_size * 1.5:
            text_chunks = self.text_splitter.split_text(text)
        else:
            text_chunks = [text]
        
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            # Find relevant images for this page range
            related_images = [
                img.to_dict() for img in images 
                if img.page_number in pages
            ]

            # Pull section ID from very first non-whitespace token of the chunk
            section_id = self._extract_section_id(chunk_text)

            chunk_metadata = {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": start_index + i,
                "chunk_type": "text",
                "page": pages[0] if len(pages) == 1 else None,
                "page_range": f"{min(pages)}-{max(pages)}" if len(pages) > 1 else str(pages[0]),
                "pages": json.dumps(sorted(pages)),
                "chunk_length": len(chunk_text),
                "has_table": False,
            }
            if section_id:
                chunk_metadata["section_id"] = section_id
            
            # Add image references if present
            if related_images:
                chunk_metadata["related_images"] = json.dumps(related_images)
                chunk_metadata["has_images"] = True
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
        
        return chunks
    
    def process_document(
        self, 
        file_path: str, 
        filename: str, 
        document_id: Optional[str] = None,
        save_images: bool = True
    ) -> Tuple[List[Dict[str, Any]], str, int, List[str]]:
        """
        Process document with advanced chunking, table and image extraction.
        
        Args:
            file_path: Path to PDF file
            filename: Original filename
            document_id: Optional document ID (generates new if not provided)
            save_images: Whether to save extracted images to disk
            
        Returns:
            Tuple of (chunks, document_id, num_pages, image_paths)
        """
        # Generate document ID if not provided
        doc_id = document_id if document_id else f"doc_{uuid.uuid4().hex[:12]}"
        
        # Extract all elements
        sections, tables, images = self.extract_document_elements(file_path)
        
        # Save images if requested
        image_paths = []
        if save_images and images:
            image_dir = os.path.join(settings.upload_dir, "images")
            for image in images:
                try:
                    image_path = image.save(image_dir, doc_id)
                    image_paths.append(image_path)
                except Exception as e:
                    print(f"Warning: Could not save image: {e}")
        
        # Get page count
        with pdfplumber.open(file_path) as pdf:
            num_pages = len(pdf.pages)
        
        # Create intelligent chunks
        chunks = self.create_intelligent_chunks(
            sections, tables, images, doc_id, filename
        )
        
        if not chunks:
            raise ValueError("No content could be extracted from the document")
        
        return chunks, doc_id, num_pages, image_paths
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def process_text_file(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """Process plain text file."""
        doc_id = document_id if document_id else f"doc_{uuid.uuid4().hex[:12]}"
        
        text = self.extract_text_from_txt(file_path)
        if not text.strip():
            raise ValueError("No text could be extracted from the file")
        
        # Estimate pages
        num_pages = max(1, len(text.split()) // 500)
        
        # Create simple chunks for text files
        text_chunks = self.text_splitter.split_text(text)
        
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "document_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "chunk_type": "text",
                    "pages": num_pages,
                    "chunk_length": len(chunk_text)
                }
            })
        
        return chunks, doc_id, num_pages


    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """
        Save uploaded file to disk.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Path to saved file
        """
        # Create unique filename to avoid conflicts
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(settings.upload_dir, unique_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path


# Global instance
advanced_document_processor = AdvancedDocumentProcessor()
