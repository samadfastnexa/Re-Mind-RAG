"""
Document processing service for PDFs and text files.
Handles text extraction and chunking for RAG system.
"""
import os
import uuid
from pathlib import Path
from typing import List, Tuple
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class DocumentProcessor:
    """Process documents (PDF, TXT) and split into chunks."""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, number_of_pages)
        """
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            
            text = ""
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n\n--- Page {page_num} ---\n\n{page_text}"
            
            return text, num_pages
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Extracted text
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error reading text file: {str(e)}")
    
    def process_document(self, file_path: str, filename: str) -> Tuple[List[dict], str, int]:
        """
        Process document and split into chunks.
        
        Args:
            file_path: Path to document file
            filename: Original filename
            
        Returns:
            Tuple of (chunks_with_metadata, document_id, num_pages)
        """
        # Generate unique document ID
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        # Extract text based on file type
        file_ext = Path(filename).suffix.lower()
        num_pages = None
        
        if file_ext == '.pdf':
            text, num_pages = self.extract_text_from_pdf(file_path)
        elif file_ext in ['.txt', '.text']:
            text = self.extract_text_from_txt(file_path)
            # Estimate pages for text files (assuming ~500 words per page)
            num_pages = max(1, len(text.split()) // 500)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        if not text.strip():
            raise ValueError("No text could be extracted from the document")
        
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Add metadata to each chunk
        chunks_with_metadata = []
        for i, chunk in enumerate(chunks):
            chunks_with_metadata.append({
                "text": chunk,
                "metadata": {
                    "document_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "pages": num_pages
                }
            })
        
        return chunks_with_metadata, doc_id, num_pages
    
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
document_processor = DocumentProcessor()
