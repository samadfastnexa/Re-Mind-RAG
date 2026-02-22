"""
FastAPI application for RAG system.
Provides REST API with Swagger documentation.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from datetime import datetime, timedelta
from app.config import settings

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
from app.models import (
    DocumentUploadResponse,
    QueryRequest,
    QueryResponse,
    DocumentInfo,
    HealthResponse
)
from app.auth_models import UserCreate, UserLogin, UserResponse, Token, UserRole
from app.auth_utils import (
    get_current_user,
    get_current_admin_user,
    verify_password,
    create_access_token
)
from app.services.user_service import (
    init_user_database,
    get_user_by_username,
    create_user,
    get_all_users
)
from app.services.document_processor import document_processor
from app.services.vector_store import vector_store
from app.services.rag_chain import rag_chain

# Initialize user database on startup
init_user_database()


# Initialize FastAPI app
app = FastAPI(
    title="RAG System API",
    description="Retrieval-Augmented Generation system for PDF and text documents using ChromaDB, OpenAI, and LangChain",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware - configured via .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint."""
    try:
        stats = vector_store.get_collection_stats()
        chromadb_status = "healthy"
    except Exception as e:
        chromadb_status = f"error: {str(e)}"
    
    # Check LLM configuration based on provider
    if settings.llm_provider == "openai":
        llm_configured = bool(settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here")
    else:  # ollama
        llm_configured = True  # Ollama runs locally, always available
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        chromadb_status=chromadb_status,
        openai_configured=llm_configured
    )


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register_user(
    user_data: UserCreate,
    current_user = Depends(get_current_admin_user)
):
    """
    Register a new user (Admin only).
    
    - **username**: Username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (min 6 characters)
    - **role**: User role (user or admin)
    
    Only admins can create new users.
    Default users can only query. Admins can upload documents.
    """
    # Check if username exists
    existing_user = get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create user
    new_user = create_user(user_data)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@app.post("/api/auth/login", response_model=Token, tags=["Authentication"])
@limiter.limit("10/minute")  # Max 10 login attempts per minute
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login to get access token.
    
    - **username**: Your username
    - **password**: Your password
    
    Returns a JWT token to use for authenticated requests.
    Use the token in the Authorization header: 'Bearer <token>'
    
    **Default admin credentials:**
    - Username: `admin`
    - Password: `admin123`
    
    ⚠️ Change the admin password after first login!
    """
    # Authenticate user
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current user information.
    
    Requires authentication.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@app.get("/api/auth/users", response_model=list[UserResponse], tags=["Authentication"])
async def list_all_users(current_user = Depends(get_current_admin_user)):
    """
    List all users (Admin only).
    
    Returns a list of all registered users.
    """
    users = get_all_users()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at
        )
        for u in users
    ]


@app.post("/upload", response_model=DocumentUploadResponse, tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin_user)
):
    """
    Upload a PDF or text document for processing.
    
    **🔒 Requires ADMIN role - Only admins can upload documents.**
    
    - **file**: PDF or TXT file to upload (max 50MB)
    
    Returns document ID and processing information.
    
    ⚠️ Normal users cannot upload documents. Contact an admin to get uploader permissions.
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.pdf', '.txt', '.text']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Only PDF and TXT files are supported."
            )
        
        # Read file content
        file_content = await file.read()
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.2f}MB. Maximum size is {settings.max_file_size_mb}MB."
            )
        
        # Save file
        file_path = document_processor.save_uploaded_file(file_content, file.filename)
        
        # Process document
        chunks_with_metadata, doc_id, num_pages = document_processor.process_document(
            file_path, file.filename
        )
        
        # Add to vector store
        num_chunks = vector_store.add_documents(chunks_with_metadata, doc_id)
        
        return DocumentUploadResponse(
            success=True,
            message="Document uploaded and processed successfully",
            document_id=doc_id,
            filename=file.filename,
            pages=num_pages,
            chunks=num_chunks
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["Query"])
@limiter.limit("30/minute")  # Max 30 queries per minute per user
async def query_documents(
    request_data: QueryRequest,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Ask a question about the uploaded documents.
    
    **🔓 Requires authentication - All authenticated users can query.**
    
    - **question**: Your question about the documents
    - **top_k**: Number of relevant chunks to retrieve (1-10, default: 6 for better context)
    
    Returns a detailed answer based on the document content with source citations.
    Uses enhanced prompting for higher quality, more comprehensive responses.
    """
    try:
        result = rag_chain.query(request_data.question, top_k=request_data.top_k)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/documents", response_model=list[DocumentInfo], tags=["Documents"])
async def list_documents(current_user = Depends(get_current_user)):
    """
    List all uploaded documents.
    
    **🔓 Requires authentication - All authenticated users can view documents.**
    
    Returns a list of all documents in the system with their metadata.
    """
    try:
        documents = vector_store.list_documents()
        
        # Add upload_date (placeholder since we don't store it yet)
        for doc in documents:
            doc['upload_date'] = datetime.now().isoformat()
        
        return [DocumentInfo(**doc) for doc in documents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


@app.delete("/documents/{document_id}", tags=["Documents"])
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Delete a document and all its chunks.
    
    **🔒 Requires ADMIN role - Only admins can delete documents.**
    
    - **document_id**: ID of the document to delete
    
    Returns the number of chunks deleted.
    
    ⚠️ Normal users cannot delete documents. Contact an admin for document management.
    """
    try:
        num_deleted = vector_store.delete_document(document_id)
        
        if num_deleted == 0:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        
        return {
            "success": True,
            "message": f"Document deleted successfully",
            "document_id": document_id,
            "chunks_deleted": num_deleted
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


@app.get("/stats", tags=["General"])
async def get_stats():
    """Get statistics about the RAG system."""
    try:
        stats = vector_store.get_collection_stats()
        documents = vector_store.list_documents()
        
        return {
            "total_documents": len(documents),
            "total_chunks": stats["total_chunks"],
            "collection_name": stats["collection_name"],
            "model": settings.openai_model,
            "embedding_model": settings.embedding_model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
