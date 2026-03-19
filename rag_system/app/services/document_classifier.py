"""
Document Classifier
Intelligently detects document type and recommends best processing strategy.
"""
import pdfplumber
import re
from pathlib import Path
from typing import Literal, Dict, Any


DocumentType = Literal["structured", "narrative", "mixed", "technical"]


class DocumentClassifier:
    """
    AI-powered document type detection for intelligent routing.
    
    Document Types:
    - structured: Procedures, manuals, forms (→ JSON processing)
    - narrative: Essays, reports, policies (→ Text chunking)
    - mixed: Has both tables and substantial text (→ Hybrid processing)
    - technical: Code, diagrams, technical specs (→ Specialized processing)
    """
    
    def __init__(self):
        # Patterns that indicate structured content
        self.procedure_patterns = [
            r'\b\d+\.\d+\.\d+\b',  # 9.6.1 format
            r'\bprocedure\s+\d+',
            r'\bstep\s+\d+',
            r'\bsection\s+\d+\.\d+',
            r'\bcontrol\s+owner',
            r'\bresponsible\s+(?:officer|party)',
            r'\bperformed\s+by:',
            r'\braci\s+matrix',
        ]
        
        # Patterns for technical content
        self.technical_patterns = [
            r'```[\w]*\n',  # Code blocks
            r'function\s+\w+\s*\(',
            r'class\s+\w+\s*[:\{]',
            r'import\s+\w+',
            r'def\s+\w+\s*\(',
        ]
    
    def classify(
        self, 
        file_path: str,
        content_sample: str = None
    ) -> tuple[DocumentType, Dict[str, Any]]:
        """
        Classify document type and provide analysis.
        
        Args:
            file_path: Path to document
            content_sample: Optional text sample for analysis
            
        Returns:
            Tuple of (document_type, analysis_details)
        """
        file_ext = Path(file_path).suffix.lower()
        
        # JSON/CSV are always structured
        if file_ext in ['.json', '.csv']:
            return "structured", {
                "confidence": 1.0,
                "reason": "File format is inherently structured",
                "recommended_processor": "structured_json"
            }
        
        # For PDFs and text files, analyze content
        if file_ext == '.pdf':
            return self._classify_pdf(file_path)
        elif file_ext in ['.txt', '.text', '.md']:
            return self._classify_text(file_path, content_sample)
        
        # Default to narrative for unknown types
        return "narrative", {
            "confidence": 0.5,
            "reason": "Unknown file type, defaulting to narrative processing",
            "recommended_processor": "advanced_chunking"
        }
    
    def _classify_pdf(self, pdf_path: str) -> tuple[DocumentType, Dict[str, Any]]:
        """Analyze PDF content to determine type."""
        analysis = {
            "total_pages": 0,
            "total_text": 0,
            "total_tables": 0,
            "table_density": 0.0,
            "has_procedures": False,
            "has_code": False,
            "text_sample": ""
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                analysis["total_pages"] = len(pdf.pages)
                
                # Analyze first 5 pages for performance
                sample_pages = min(5, len(pdf.pages))
                
                for page in pdf.pages[:sample_pages]:
                    # Extract text
                    text = page.extract_text() or ""
                    analysis["total_text"] += len(text)
                    
                    # Store sample for pattern matching
                    if len(analysis["text_sample"]) < 2000:
                        analysis["text_sample"] += text[:1000]
                    
                    # Count tables
                    tables = page.extract_tables()
                    analysis["total_tables"] += len(tables) if tables else 0
                    
                    # Calculate table cell count
                    table_cells = 0
                    if tables:
                        for table in tables:
                            table_cells += sum(len(row) for row in table)
                
                # Calculate table density
                if analysis["total_text"] > 0:
                    # Estimate: each table cell ≈ 50 chars
                    estimated_table_text = table_cells * 50
                    total_content = analysis["total_text"] + estimated_table_text
                    analysis["table_density"] = estimated_table_text / total_content if total_content > 0 else 0
                
                # Check for procedure patterns
                text_sample = analysis["text_sample"]
                analysis["has_procedures"] = any(
                    re.search(pattern, text_sample, re.IGNORECASE)
                    for pattern in self.procedure_patterns
                )
                
                # Check for technical content
                analysis["has_code"] = any(
                    re.search(pattern, text_sample)
                    for pattern in self.technical_patterns
                )
        
        except Exception as e:
            print(f"Warning: Error analyzing PDF: {e}")
            return "narrative", {
                "confidence": 0.3,
                "reason": f"Error analyzing document: {str(e)}",
                "recommended_processor": "advanced_chunking"
            }
        
        # Decision logic
        return self._make_classification_decision(analysis)
    
    def _classify_text(
        self, 
        file_path: str, 
        content_sample: str = None
    ) -> tuple[DocumentType, Dict[str, Any]]:
        """Analyze text file content."""
        # Load text content
        if content_sample is None:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content_sample = f.read(5000)  # First 5000 chars
        
        analysis = {
            "total_text": len(content_sample),
            "text_sample": content_sample[:2000],
            "has_procedures": False,
            "has_code": False,
            "table_density": 0.0
        }
        
        # Check patterns
        analysis["has_procedures"] = any(
            re.search(pattern, content_sample, re.IGNORECASE)
            for pattern in self.procedure_patterns
        )
        
        analysis["has_code"] = any(
            re.search(pattern, content_sample)
            for pattern in self.technical_patterns
        )
        
        # Simple table detection (pipe-separated or tab-separated)
        lines = content_sample.split('\n')
        table_lines = sum(1 for line in lines if '|' in line or '\t' in line)
        analysis["table_density"] = table_lines / len(lines) if lines else 0
        
        return self._make_classification_decision(analysis)
    
    def _make_classification_decision(
        self, 
        analysis: Dict[str, Any]
    ) -> tuple[DocumentType, Dict[str, Any]]:
        """Make final classification decision based on analysis."""
        
        table_density = analysis.get("table_density", 0)
        has_procedures = analysis.get("has_procedures", False)
        has_code = analysis.get("has_code", False)
        
        # Technical content
        if has_code:
            return "technical", {
                "confidence": 0.8,
                "reason": "Document contains code or technical syntax",
                "recommended_processor": "advanced_chunking",
                "analysis": analysis
            }
        
        # Highly structured (procedures + tables)
        if table_density > 0.6 or (has_procedures and table_density > 0.3):
            return "structured", {
                "confidence": 0.9,
                "reason": f"High table density ({table_density:.1%}) and/or procedure patterns detected",
                "recommended_processor": "structured_json",
                "analysis": analysis
            }
        
        # Mixed content (some tables, some narrative)
        if 0.2 < table_density <= 0.6:
            return "mixed", {
                "confidence": 0.7,
                "reason": f"Moderate table density ({table_density:.1%}), requires hybrid approach",
                "recommended_processor": "hybrid",
                "analysis": analysis
            }
        
        # Mostly narrative
        return "narrative", {
            "confidence": 0.8,
            "reason": "Primarily narrative text with minimal structured content",
            "recommended_processor": "advanced_chunking",
            "analysis": analysis
        }
    
    def get_processing_recommendation(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Get detailed processing recommendation for a document.
        
        Returns:
            Dictionary with classification, confidence, and processor recommendation
        """
        doc_type, details = self.classify(file_path)
        
        return {
            "document_type": doc_type,
            "confidence": details.get("confidence", 0.5),
            "recommended_processor": details.get("recommended_processor"),
            "reason": details.get("reason"),
            "can_use_structured": doc_type in ["structured", "mixed"],
            "should_extract_tables": doc_type in ["structured", "mixed"],
            "analysis": details.get("analysis", {})
        }


# Global instance
document_classifier = DocumentClassifier()
