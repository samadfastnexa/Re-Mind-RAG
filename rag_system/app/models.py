"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
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


class QueryRequest(BaseModel):
    """Request model for querying documents with advanced features."""
    question: str = Field(..., min_length=1, description="Question to ask about the documents")
    top_k: int = Field(default=6, ge=1, le=20, description="Number of relevant chunks to retrieve")
    answer_type: AnswerType = Field(default=AnswerType.default, description="Type of answer to generate")
    filters: Optional[Dict[str, str]] = Field(default=None, description="Metadata filters (e.g., {'document_id': 'doc_123'})")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID for follow-up questions")
    
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


class RetrievalMetadata(BaseModel):
    """Metadata about the retrieval process."""
    total_sources: int
    hybrid_search_used: bool
    reranking_used: bool
    filters_applied: bool


class QueryResponse(BaseModel):
    """Enhanced response model for query results."""
    question: str
    answer: str
    sources: List[SourceInfo]
    answer_type: str = "default"
    retrieval_metadata: Optional[RetrievalMetadata] = None
    
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


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    chromadb_status: str
    openai_configured: bool
