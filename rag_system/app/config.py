"""
Configuration management for RAG system using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider Configuration
    llm_provider: str = "ollama"  # "openai" or "ollama"
    
    # OpenAI Configuration (optional - only needed if llm_provider=openai)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Ollama Configuration (all values from .env - no hardcoded defaults)
    ollama_base_url: str = ""  # Set via OLLAMA_BASE_URL in .env
    ollama_model: str = ""  # Set via OLLAMA_MODEL in .env
    ollama_embedding_base_url: Optional[str] = None  # Set via OLLAMA_EMBEDDING_BASE_URL in .env (defaults to ollama_base_url)
    ollama_embedding_model: str = ""  # Set via OLLAMA_EMBEDDING_MODEL in .env
    
    # ChromaDB Configuration
    chroma_db_path: str = "./data/chroma_db"
    collection_name: str = "documents"
    
    # Upload Configuration
    upload_dir: str = "./data/documents"
    max_file_size_mb: int = 50
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,exp://,*"
    
    # Chunking Configuration
    chunk_size: int = 1200  # Balanced size — enough context for SOP procedures
    chunk_overlap: int = 200  # Overlap to preserve cross-chunk context
    
    # RAG Quality Settings
    retrieval_top_k: int = 8  # More context for better answers
    llm_temperature: float = 0.3  # Lower for more focused responses
    
    # Advanced Processing Settings
    use_advanced_processing: bool = True  # Enable table/image extraction
    use_sop_processing: bool = True  # Auto-detect and use procedure-based chunking for SOPs
    
    # Hybrid Search Configuration
    enable_hybrid_search: bool = True  # Combine vector + BM25 keyword search
    bm25_weight: float = 0.4  # 40% BM25, 60% vector - more keyword matching
    hybrid_top_k: int = 50  # Retrieve more candidates before reranking

    # Reranking Configuration
    enable_reranking: bool = True  # Use reranker model to refine results
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Fast & accurate
    reranker_top_k: int = 15  # Final number after reranking (enough context for the LLM)
    
    # Enhanced Chunking Configuration
    use_semantic_chunking: bool = True  # Split by semantic meaning
    enable_sliding_window: bool = True  # Add overlapping context
    
    # Advanced Document Processing
    use_advanced_processing: bool = True  # Use advanced processor with table/image extraction
    extract_tables: bool = True  # Extract and preserve tables
    extract_images: bool = True  # Extract images from documents
    save_extracted_images: bool = True  # Save images to disk
    table_format: str = "structured"  # "markdown" or "structured" - structured is cleaner for complex tables
    
    # Conversation History
    enable_conversation_history: bool = True
    max_history_messages: int = 10  # Keep last 10 messages per session
    
    # JWT Authentication Settings
    jwt_secret_key: str = "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    
    @property
    def cors_origins_list(self) -> list:
        """Convert CORS origins string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Ensure directories exist
Path(settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
