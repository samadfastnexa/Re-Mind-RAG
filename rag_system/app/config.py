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
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"  # Main LLM model
    ollama_embedding_model: str = "gemma3:1b"  # For embeddings
    
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
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # RAG Quality Settings
    retrieval_top_k: int = 6  # More context for better answers
    llm_temperature: float = 0.3  # Lower for more focused responses
    
    # Hybrid Search Configuration
    enable_hybrid_search: bool = True  # Combine vector + BM25 keyword search
    bm25_weight: float = 0.3  # 30% BM25, 70% vector similarity
    hybrid_top_k: int = 20  # Retrieve more before reranking
    
    # Reranking Configuration
    enable_reranking: bool = True  # Use reranker model to refine results
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Fast & accurate
    reranker_top_k: int = 6  # Final number after reranking
    
    # Enhanced Chunking Configuration
    use_semantic_chunking: bool = True  # Split by semantic meaning
    enable_sliding_window: bool = True  # Add overlapping context
    
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
