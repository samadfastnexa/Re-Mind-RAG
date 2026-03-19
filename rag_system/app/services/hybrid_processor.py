"""
Hybrid Document Processor
Intelligently routes documents to the best processing strategy.
"""
import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from app.services.structured_processor import structured_processor
from app.services.advanced_document_processor import AdvancedDocumentProcessor
from app.services.document_classifier import document_classifier
from app.services.smart_text_parser import smart_text_parser
from app.services.sop_processor import sop_processor
from app.config import settings


class HybridDocumentProcessor:
    """
    Smart processor that routes documents to optimal processing strategy.
    
    Supports:
    - Auto-detection of document type
    - Structured processing for tables/procedures
    - Advanced text chunking for narrative content
    - Hybrid processing for mixed documents
    """
    
    def __init__(self):
        self.structured_processor = structured_processor
        self.text_processor = AdvancedDocumentProcessor()
        self.sop_processor = sop_processor
        self.classifier = document_classifier
    
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
        
        # Ensure upload directory exists
        os.makedirs(settings.upload_dir, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path
    
    async def process_document(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None,
        processing_mode: str = "auto",  # Changed from ProcessingMode to str
        save_images: bool = True
    ) -> Tuple[List[Dict[str, Any]], str, int, Optional[List[str]]]:
        """
        Process document with intelligent routing.
        
        Args:
            file_path: Path to document
            filename: Original filename
            document_id: Optional document ID
            processing_mode: "auto", "structured", "text", or "hybrid"
            save_images: Whether to save extracted images
            
        Returns:
            Tuple of (chunks, document_id, num_pages/items, image_paths)
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Validate processing_mode
        valid_modes = ["auto", "structured", "text", "hybrid"]
        if processing_mode not in valid_modes:
            print(f"Warning: Invalid processing_mode '{processing_mode}', defaulting to 'auto'")
            processing_mode = "auto"
        
        # Determine processing mode
        if processing_mode == "auto":
            doc_type, analysis = self.classifier.classify(file_path)
            processing_mode = self._map_doc_type_to_mode(doc_type)
            print(f"Auto-detected document type: {doc_type} → using {processing_mode} processing")
        
        # Route to appropriate processor
        if processing_mode == "structured":
            return await self._process_structured(file_path, filename, document_id, file_ext)
        
        elif processing_mode == "text":
            return await self._process_text(file_path, filename, document_id, save_images)
        
        elif processing_mode == "hybrid":
            return await self._process_hybrid(file_path, filename, document_id, save_images)
        
        else:
            # Default to text processing
            return await self._process_text(file_path, filename, document_id, save_images)
    
    async def _process_structured(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str],
        file_ext: str
    ) -> Tuple[List[Dict[str, Any]], str, int, Optional[List[str]]]:
        """Process as structured JSON data."""
        
        if file_ext == '.json':
            chunks, doc_id, num_items = self.structured_processor.process_json_file(
                file_path, filename, document_id
            )
        elif file_ext == '.csv':
            chunks, doc_id, num_items = self.structured_processor.process_csv_file(
                file_path, filename, document_id
            )
        elif file_ext in ('.docx', '.doc'):
            # Word documents — extract tables as structured chunks
            chunks, doc_id, num_items = self.structured_processor.extract_tables_from_docx(
                file_path, filename, document_id
            )
        elif file_ext == '.pdf':
            # Extract tables from PDF as structured data
            chunks, doc_id, num_items = self.structured_processor.extract_tables_from_pdf(
                file_path, filename, document_id
            )
        else:
            # Fallback to text processing
            return await self._process_text(file_path, filename, document_id, False)
        
        # Structured processing doesn't have traditional pages
        return chunks, doc_id, num_items, None
    
    async def _process_text(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str],
        save_images: bool
    ) -> Tuple[List[Dict[str, Any]], str, int, Optional[List[str]]]:
        """Process as narrative text with advanced chunking."""
        
        file_ext = Path(file_path).suffix.lower()
        
        # Check if this is an SOP/procedure document (only for PDFs)
        if file_ext == '.pdf':
            try:
                # Quick check: Extract first few pages to detect SOP patterns
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    sample_text = ""
                    for page in pdf.pages[:min(5, len(pdf.pages))]:  # Check first 5 pages
                        sample_text += page.extract_text() or ""
                    
                    if self.sop_processor.detect_is_sop_document(sample_text):
                        print(f"🔍 Detected SOP/Procedure document: {filename}")
                        print(f"   Using procedure-based chunking instead of fixed-size chunks")
                        chunks, doc_id, num_pages = self.sop_processor.process_pdf(
                            file_path, filename, document_id
                        )
                        return chunks, doc_id, num_pages, None
            except Exception as e:
                print(f"Warning: SOP detection failed, using standard processing: {e}")
        
        if file_ext == '.pdf' and settings.use_advanced_processing:
            # Advanced processing with tables and images
            chunks, doc_id, num_pages, image_paths = self.text_processor.process_document(
                file_path, filename, document_id, save_images
            )
            
            # Enhance with smart parsing to extract structure
            try:
                chunks = smart_text_parser.enhance_chunks_with_structure(chunks)
                print(f"Smart parser: Enhanced {len(chunks)} chunks with structure extraction")
            except Exception as e:
                print(f"Warning: Smart parsing enhancement failed: {e}")
            
            return chunks, doc_id, num_pages, image_paths
        
        elif file_ext in ['.txt', '.text']:
            # Text file processing
            if hasattr(self.text_processor, 'process_text_file'):
                chunks, doc_id, num_pages = self.text_processor.process_text_file(
                    file_path, filename, document_id
                )
            else:
                # Fallback to standard processing (returns 4 values)
                chunks, doc_id, num_pages, _ = self.text_processor.process_document(
                    file_path, filename, document_id, False  # Don't save images for text files
                )
            
            # Enhance with smart parsing
            try:
                chunks = smart_text_parser.enhance_chunks_with_structure(chunks)
                print(f"Smart parser: Enhanced {len(chunks)} text chunks")
            except Exception as e:
                print(f"Warning: Smart parsing enhancement failed: {e}")
            
            return chunks, doc_id, num_pages, None
        
        else:
            # Standard text processing
            chunks, doc_id, num_pages, image_paths = self.text_processor.process_document(
                file_path, filename, document_id
            )
            
            # Enhance with smart parsing
            try:
                chunks = smart_text_parser.enhance_chunks_with_structure(chunks)
                print(f"Smart parser: Enhanced {len(chunks)} chunks")
            except Exception as e:
                print(f"Warning: Smart parsing enhancement failed: {e}")
            
            return chunks, doc_id, num_pages, image_paths
    
    async def _process_hybrid(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str],
        save_images: bool
    ) -> Tuple[List[Dict[str, Any]], str, int, Optional[List[str]]]:
        """
        Process document with hybrid approach.
        Extracts structured tables AND processes narrative text.
        For SOP documents, uses procedure-based chunking.
        """
        import uuid
        import traceback
        
        try:
            # Generate document ID if not provided
            doc_id = document_id if document_id else f"doc_{uuid.uuid4().hex[:12]}"
            
            file_ext = Path(file_path).suffix.lower()
            
            # Check if this is an SOP/procedure document (only for PDFs)
            if file_ext == '.pdf':
                try:
                    # Quick check: Extract first few pages to detect SOP patterns
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        sample_text = ""
                        for page in pdf.pages[:min(5, len(pdf.pages))]:  # Check first 5 pages
                            sample_text += page.extract_text() or ""
                        
                        if self.sop_processor.detect_is_sop_document(sample_text):
                            print(f"🔍 Detected SOP/Procedure document in hybrid mode: {filename}")
                            print(f"   Using specialized SOP processor with procedure-based chunking")
                            chunks, doc_id, num_pages = self.sop_processor.process_pdf(
                                file_path, filename, doc_id
                            )
                            return chunks, doc_id, num_pages, None
                except Exception as e:
                    print(f"Warning: SOP detection failed, using standard hybrid processing: {e}")
            
            if file_ext in ('.docx', '.doc'):
                # Word documents — extract tables as structured chunks
                try:
                    docx_chunks, _, num_items = self.structured_processor.extract_tables_from_docx(
                        file_path, filename, doc_id
                    )
                    for idx, chunk in enumerate(docx_chunks):
                        chunk['metadata']['chunk_index'] = idx
                        chunk['metadata']['total_chunks'] = len(docx_chunks)
                    return docx_chunks, doc_id, num_items, None
                except Exception as e:
                    print(f"Warning: DOCX structured extraction failed, falling back to text: {e}")
                    return await self._process_text(file_path, filename, doc_id, save_images)

            if file_ext != '.pdf':
                # Only PDFs support hybrid processing
                return await self._process_text(file_path, filename, doc_id, save_images)
            
            all_chunks = []
            image_paths = []
            num_pages = 0
            
            # 1. Extract structured data from tables
            try:
                print(f"Extracting tables from PDF: {filename}")
                table_chunks, _, num_table_rows = self.structured_processor.extract_tables_from_pdf(
                    file_path, filename, doc_id
                )
                all_chunks.extend(table_chunks)
                print(f"Extracted {len(table_chunks)} structured table rows")
            except Exception as e:
                print(f"Warning: Could not extract structured tables: {e}")
                traceback.print_exc()
            
            # 2. Process narrative text (excluding tables)
            try:
                print(f"Processing narrative text with save_images={save_images}")
                text_chunks, _, num_pages, imgs = self.text_processor.process_document(
                    file_path, filename, doc_id, save_images
                )
                print(f"Got {len(text_chunks)} text chunks, {num_pages} pages")
                
                # Filter out chunks that are mostly tables (already processed as structured)
                narrative_chunks = [
                    chunk for chunk in text_chunks
                    if not chunk.get('metadata', {}).get('has_table', False) or
                       chunk.get('metadata', {}).get('chunk_type') != 'table'
                ]
                
                # 3. Enhance narrative chunks with smart parsing
                # Extract structure from text (sections, procedures, metadata)
                try:
                    narrative_chunks = smart_text_parser.enhance_chunks_with_structure(narrative_chunks)
                    print(f"Enhanced {len(narrative_chunks)} chunks with intelligent structure extraction")
                except Exception as e:
                    print(f"Warning: Could not enhance chunks with smart parsing: {e}")
                
                all_chunks.extend(narrative_chunks)
                image_paths = imgs or []
                print(f"Extracted {len(narrative_chunks)} narrative chunks")
            except Exception as e:
                print(f"Error: Could not process narrative text: {e}")
                traceback.print_exc()
                raise
            
            # Re-index all chunks
            for idx, chunk in enumerate(all_chunks):
                chunk['metadata']['chunk_index'] = idx
                chunk['metadata']['total_chunks'] = len(all_chunks)
            
            print(f"Hybrid processing complete: {len(all_chunks)} total chunks, {num_pages} pages")
            return all_chunks, doc_id, num_pages, image_paths
            
        except Exception as e:
            print(f"CRITICAL ERROR in _process_hybrid: {e}")
            traceback.print_exc()
            raise
    
    def _map_doc_type_to_mode(self, doc_type: str) -> str:  # Changed return type from ProcessingMode to str
        """Map document classification to processing mode."""
        mapping = {
            "structured": "structured",
            "narrative": "text",
            "mixed": "hybrid",
            "technical": "text"
        }
        return mapping.get(doc_type, "text")
    
    def get_processing_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about how a document would be processed.
        
        Useful for UI to show users what processing will be applied.
        """
        recommendation = self.classifier.get_processing_recommendation(file_path)
        
        return {
            **recommendation,
            "supported_modes": self._get_supported_modes(file_path),
            "default_mode": "auto"
        }
    
    def _get_supported_modes(self, file_path: str) -> List[str]:
        """Get list of processing modes supported for this file type."""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.json', '.csv']:
            return ["structured"]
        elif file_ext == '.pdf':
            return ["auto", "structured", "text", "hybrid"]
        elif file_ext in ['.txt', '.text', '.md']:
            return ["auto", "text"]
        else:
            return ["text"]


# Global instance
hybrid_processor = HybridDocumentProcessor()
