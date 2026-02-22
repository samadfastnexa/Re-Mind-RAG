"""
Document processing service for PDFs and text files.
Handles text extraction and advanced chunking for RAG system.
"""
import os
import uuid
from pathlib import Path
from typing import List, Tuple
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from app.config import settings


class DocumentProcessor:
    """Process documents (PDF, TXT) and split into chunks with advanced strategies."""
    
    def __init__(self):
        # Standard recursive splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Semantic splitter (initialized when needed)
        self._semantic_splitter = None
    
    def get_semantic_splitter(self):
        """Lazy load semantic splitter with embeddings."""
        if self._semantic_splitter is None and settings.use_semantic_chunking:
            try:
                if settings.llm_provider == "openai":
                    from langchain_openai import OpenAIEmbeddings
                    embeddings = OpenAIEmbeddings(
                        openai_api_key=settings.openai_api_key,
                        model=settings.openai_embedding_model
                    )
                else:
                    from langchain_community.embeddings import HuggingFaceEmbeddings
                    embeddings = HuggingFaceEmbeddings(
                        model_name="all-MiniLM-L6-v2",
                        model_kwargs={'device': 'cpu'},
                        encode_kwargs={'normalize_embeddings': True}
                    )
                
                self._semantic_splitter = SemanticChunker(
                    embeddings,
                    breakpoint_threshold_type="percentile"
                )
            except Exception as e:
                print(f"Warning: Could not initialize semantic chunker: {e}")
                print("Falling back to recursive chunking")
        
        return self._semantic_splitter
    
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
        Process document and split into chunks with advanced strategies.
        
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
        
        # Choose chunking strategy
        chunks = self._split_text_intelligently(text)
        
        # Add metadata to each chunk
        chunks_with_metadata = []
        for i, chunk in enumerate(chunks):
            # Calculate position percentage
            position_percent = (i / len(chunks)) * 100 if chunks else 0
            
            chunks_with_metadata.append({
                "text": chunk,
                "metadata": {
                    "document_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "pages": num_pages,
                    "position_percent": round(position_percent, 2),
                    "chunk_length": len(chunk)
                }
            })
        
        return chunks_with_metadata, doc_id, num_pages
    
    def _split_text_intelligently(self, text: str) -> List[str]:
        """
        Split text using the best available strategy.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Try semantic chunking first if enabled
        if settings.use_semantic_chunking:
            semantic_splitter = self.get_semantic_splitter()
            if semantic_splitter:
                try:
                    chunks = semantic_splitter.split_text(text)
                    # If chunks are too large, re-split them
                    final_chunks = []
                    for chunk in chunks:
                        if len(chunk) > settings.chunk_size * 1.5:
                            # Re-split large chunks
                            sub_chunks = self.text_splitter.split_text(chunk)
                            final_chunks.extend(sub_chunks)
                        else:
                            final_chunks.append(chunk)
                    return final_chunks
                except Exception as e:
                    print(f"Semantic chunking failed: {e}, using recursive splitter")
        
        # Fall back to recursive character text splitter
        chunks = self.text_splitter.split_text(text)
        
        # Add sliding window context if enabled
        if settings.enable_sliding_window and len(chunks) > 1:
            chunks = self._add_sliding_window_context(chunks)
        
        return chunks
    
    def _add_sliding_window_context(self, chunks: List[str]) -> List[str]:
        """
        Add context from adjacent chunks using sliding windows.
        
        Args:
            chunks: Original chunks
            
        Returns:
            Chunks with added context
        """
        if len(chunks) <= 1:
            return chunks
        
        enhanced_chunks = []
        overlap_size = settings.chunk_overlap
        
        for i, chunk in enumerate(chunks):
            # Add context from previous chunk
            prefix = ""
            if i > 0:
                prev_chunk = chunks[i-1]
                # Take last N characters from previous chunk
                prefix = f"[...previous context: {prev_chunk[-overlap_size:]}]\n\n"
            
            # Add context from next chunk
            suffix = ""
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                # Take first N characters from next chunk
                suffix = f"\n\n[...continued: {next_chunk[:overlap_size]}]"
            
            enhanced_chunk = f"{prefix}{chunk}{suffix}"
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
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
