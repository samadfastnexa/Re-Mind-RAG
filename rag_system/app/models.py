"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AnswerType(str, Enum):
    """Enumeration of available answer types."""
    default = "default"
    summary = "summary"
    detailed = "detailed"
    bullet_points = "bullet_points"
    compare = "compare"
    explain_simple = "explain_simple"


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    success: bool
    message: str
    document_id: str
    filename: str
    pages: Optional[int] = None
    chunks: int


class UploadProgress(BaseModel):
    """Progress information for document upload."""
    status: str = Field(..., description="Status: uploading, processing, vectorizing, completed, failed")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    message: str = Field(..., description="Current progress message")
    document_id: Optional[str] = None
    filename: Optional[str] = None
    pages: Optional[int] = None
    chunks: Optional[int] = None
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for querying documents with advanced features."""
    question: str = Field(..., min_length=1, description="Question to ask about the documents")
    top_k: int = Field(default=6, ge=1, le=20, description="Number of relevant chunks to retrieve")
    answer_type: AnswerType = Field(default=AnswerType.default, description="Type of answer to generate")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Metadata filters for structured data (e.g., {'control_owner': 'CTO', 'section_id': '9.2'})"
    )
    session_id: Optional[str] = Field(default=None, description="Conversation session ID for follow-up questions")
    return_structured: bool = Field(
        default=True, 
        description="Return structured data from JSON chunks if available"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the main topic of the document?",
                "top_k": 6,
                "answer_type": "default",
                "filters": None,
                "session_id": None
            }
        }


class SourceInfo(BaseModel):
    """Enhanced source information."""
    source_id: int = Field(..., description="Sequential source identifier")
    document_id: str = Field(..., description="Unique document identifier")
    document: str = Field(..., description="Document filename")
    chunk: int = Field(..., description="Chunk number")
    total_chunks: int = Field(..., description="Total chunks in document")
    position_percent: float = Field(..., description="Position in document (0-100%)")
    content: str = Field(..., description="Preview of chunk content")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    chunk_length: int = Field(..., description="Length of chunk in characters")
    # Optional location metadata — present when available
    page: Optional[int] = Field(None, description="Single page number")
    page_range: Optional[str] = Field(None, description="Page range, e.g. '52-53'")
    pages: Optional[List[int]] = Field(None, description="List of pages covered by the chunk")
    section_id: Optional[str] = Field(None, description="Section number, e.g. '10.3.1'")
    has_table: Optional[bool] = Field(None, description="Chunk contains a table")


class RetrievalMetadata(BaseModel):
    """Metadata about the retrieval process."""
    total_sources: int
    hybrid_search_used: bool
    reranking_used: bool
    filters_applied: bool


class QueryResponse(BaseModel):
    structured_data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Structured JSON data from matching chunks (if available)"
    )
    """Enhanced response model for query results."""
    question: str
    answer: str
    sources: List[SourceInfo]
    answer_type: str = "default"
    retrieval_metadata: Optional[RetrievalMetadata] = None
    unanswerable: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the main topic?",
                "answer": "The document discusses...",
                "sources": [
                    {
                        "source_id": 1,
                        "document_id": "doc_abc123",
                        "document": "example.pdf",
                        "chunk": 1,
                        "total_chunks": 25,
                        "position_percent": 4.0,
                        "content": "Relevant excerpt...",
                        "relevance_score": 0.92,
                        "chunk_length": 850
                    }
                ],
                "answer_type": "default",
                "retrieval_metadata": {
                    "total_sources": 6,
                    "hybrid_search_used": True,
                    "reranking_used": True,
                    "filters_applied": False
                }
            }
        }


class ConversationSessionCreate(BaseModel):
    """Request to create a conversation session."""
    user_id: Optional[str] = None


class ConversationSessionResponse(BaseModel):
    """Response with conversation session ID."""
    session_id: str
    created_at: str


class ConversationMessage(BaseModel):
    """Individual conversation message."""
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict] = None


class ConversationHistoryResponse(BaseModel):
    """Response with conversation history."""
    session_id: str
    messages: List[ConversationMessage]


class FeedbackRequest(BaseModel):
    """User feedback on a response."""
    session_id: Optional[str] = None
    question: str
    answer: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")
    feedback_text: Optional[str] = None


class DocumentInfo(BaseModel):
    """Information about an uploaded document."""
    document_id: str
    filename: str
    upload_date: str
    chunks: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123456",
                "filename": "example.pdf",
                "upload_date": "2026-02-17T14:30:00",
                "chunks": 25
            }
        }


class DocumentChunk(BaseModel):
    """A single chunk from a document."""
    chunk_id: str
    content: str
    chunk_number: int
    metadata: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "doc_123456_chunk_0",
                "content": "This is the text content of the chunk...",
                "chunk_number": 0,
                "metadata": {
                    "document_id": "doc_123456",
                    "filename": "example.pdf",
                    "chunk": 0,
                    "total_chunks": 25
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    chromadb_status: str
    openai_configured: bool


# Territory Management Models
class TerritoryData(BaseModel):
    """Single territory data entry for bulk import."""
    region: str
    city: str
    zone: str
    territories: List[str]


class TerritoryBulkImportRequest(BaseModel):
    """Bulk import request for territories."""
    data: List[TerritoryData]
    clear_existing: bool = Field(default=False, description="Clear existing data before import")


class TerritoryBulkImportResponse(BaseModel):
    """Response for bulk territory import."""
    success: bool
    message: str
    stats: Dict[str, int]


class RegionResponse(BaseModel):
    """Response model for region data."""
    id: int
    name: str
    created_at: str
    city_count: Optional[int] = None


class CityResponse(BaseModel):
    """Response model for city data."""
    id: int
    name: str
    created_at: str
    zone_count: Optional[int] = None


class ZoneResponse(BaseModel):
    """Response model for zone data."""
    id: int
    name: str
    color: Optional[str]
    created_at: str
    territory_count: Optional[int] = None


class TerritoryResponse(BaseModel):
    """Response model for territory data."""
    id: int
    name: str
    created_at: str


class TerritorySearchResult(BaseModel):
    """Search result for territories."""
    territory_name: str
    zone_name: str
    zone_color: Optional[str]
    city_name: str
    region_name: str
