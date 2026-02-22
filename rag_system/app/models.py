"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    success: bool
    message: str
    document_id: str
    filename: str
    pages: Optional[int] = None
    chunks: int


class QueryRequest(BaseModel):
    """Request model for querying documents."""
    question: str = Field(..., min_length=1, description="Question to ask about the documents")
    top_k: int = Field(default=6, ge=1, le=10, description="Number of relevant chunks to retrieve (more = better context)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the main topic of the document?",
                "top_k": 6
            }
        }


class QueryResponse(BaseModel):
    """Response model for query results."""
    question: str
    answer: str
    sources: List[dict]
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the main topic?",
                "answer": "The document discusses...",
                "sources": [
                    {
                        "document": "example.pdf",
                        "page": 1,
                        "content": "Relevant excerpt..."
                    }
                ]
            }
        }


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
