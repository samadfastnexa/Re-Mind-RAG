"""
FastAPI application for RAG system.
Provides REST API with Swagger documentation.
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import List
import os
import hashlib
from datetime import datetime, timedelta
from app.config import settings

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
from app.models import (
    DocumentUploadResponse,
    UploadProgress,
    QueryRequest,
    QueryResponse,
    DocumentInfo,
    DocumentChunk,
    HealthResponse,
    ConversationSessionCreate,
    ConversationSessionResponse,
    ConversationHistoryResponse,
    FeedbackRequest,
    AnswerType,
    TerritoryData,
    TerritoryBulkImportRequest,
    TerritoryBulkImportResponse,
    RegionResponse,
    CityResponse,
    ZoneResponse,
    TerritoryResponse,
    TerritorySearchResult
)
from app.auth_models import UserCreate, UserUpdate, UserLogin, UserResponse, Token, UserRole
from app.auth_utils import (
    get_current_user,
    get_current_admin_user,
    verify_password,
    needs_password_rehash,
    get_password_hash,
    create_access_token
)
from app.services.user_service import (
    init_user_database,
    get_user_by_username,
    create_user,
    get_all_users,
    update_user_permission,
    update_user,
    delete_user,
    update_user_password_hash
)
from app.services.document_processor import document_processor
from app.services.advanced_document_processor import advanced_document_processor
from app.services.hybrid_processor import hybrid_processor
from app.services.vector_store import vector_store
from app.services.rag_chain import rag_chain
from app.services.conversation_history import conversation_history
from app.services.ticket_service import ticket_service
from app.services.upload_progress import upload_progress_tracker
from app.services.territory_service import TerritoryService


def get_active_processor(use_hybrid: bool = True):
    """Get the active document processor based on configuration."""
    # Prefer hybrid processor for intelligent routing
    if use_hybrid and settings.use_advanced_processing:
        return hybrid_processor
    elif settings.use_advanced_processing:
        return advanced_document_processor
    return document_processor


# Initialize user database on startup
init_user_database()

# Initialize territory service
territory_service = TerritoryService()


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
        can_delete_history=new_user.can_delete_history,
        can_export=new_user.can_export,
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

    # Auto-upgrade hash if it was stored at a higher bcrypt cost (e.g. rounds=12).
    # The check is instant (reads the embedded cost prefix); only the rehash costs
    # a tiny bit more on this one login — every login after will be fast.
    if needs_password_rehash(user.hashed_password):
        try:
            update_user_password_hash(user.username, get_password_hash(form_data.password))
        except Exception:
            pass  # Never block login if rehash fails
    
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
        can_delete_history=current_user.can_delete_history,
        can_export=current_user.can_export,
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
            can_delete_history=u.can_delete_history,
            can_export=u.can_export,
            created_at=u.created_at
        )
        for u in users
    ]


@app.put("/api/auth/users/{user_id}/permissions", tags=["Authentication"])
async def update_user_permissions(
    user_id: int,
    can_delete_history: bool = None,
    can_export: bool = None,
    current_user = Depends(get_current_admin_user)
):
    """
    Update user permissions (Admin only).
    
    **🔒 Requires ADMIN role**
    
    - **user_id**: The ID of the user to update
    - **can_delete_history**: Whether the user can delete conversation history
    - **can_export**: Whether the user can export conversations
    """
    success = update_user_permission(user_id, can_delete_history, can_export)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found or no permissions to update")
    
    return {
        "success": True,
        "message": "User permissions updated successfully",
        "user_id": user_id,
        "can_delete_history": can_delete_history,
        "can_export": can_export
    }


@app.put("/api/auth/users/{user_id}", response_model=UserResponse, tags=["Authentication"])
async def update_user_info(
    user_id: int,
    user_data: UserUpdate,
    current_user = Depends(get_current_admin_user)
):
    """
    Update user information (Admin only).

    **🔒 Requires ADMIN role**

    Updatable fields: username, email, password, role, is_active.
    Only provide the fields you want to change.
    """
    try:
        updated = update_user(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            is_active=user_data.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="User not found or nothing to update")

    return UserResponse(
        id=updated.id,
        username=updated.username,
        email=updated.email,
        role=updated.role,
        is_active=updated.is_active,
        can_delete_history=updated.can_delete_history,
        can_export=updated.can_export,
        created_at=updated.created_at
    )


@app.delete("/api/auth/users/{user_id}", tags=["Authentication"])
async def delete_user_endpoint(
    user_id: int,
    current_user = Depends(get_current_admin_user)
):
    """
    Delete a user (Admin only).

    **🔒 Requires ADMIN role**

    Cannot delete your own account.
    """
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "message": "User deleted successfully",
        "user_id": user_id
    }


async def process_update_background(
    upload_id: str,
    document_id: str,
    file_content: bytes,
    filename: str,
    file_ext: str,
    file_hash: str = None,
    processing_mode: str = "auto"
):
    """Background task to process document update."""
    try:
        import asyncio
        import uuid
        # Small delay to ensure frontend can catch initial state
        await asyncio.sleep(0.1)
        
        # Update progress: Saving file
        upload_progress_tracker.update_progress(
            upload_id,
            status="processing",
            progress=10,
            message="Saving updated file...",
            document_id=document_id
        )
        
        # Get processor (prefer hybrid for intelligent routing)
        processor = get_active_processor(use_hybrid=True)
        
        # Save file
        if hasattr(processor, 'save_uploaded_file'):
            file_path = processor.save_uploaded_file(file_content, filename)
        else:
            # Fallback for processors without save method
            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
            file_path = os.path.join(settings.upload_dir, unique_filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
        
        # Update progress: Processing document
        upload_progress_tracker.update_progress(
            upload_id,
            status="processing",
            progress=20,
            message=f"Analyzing document structure ({processing_mode} mode)...",
            document_id=document_id
        )
        
        # Process document with hybrid processor, using existing document_id
        try:
            # Update for processing start
            upload_progress_tracker.update_progress(
                upload_id,
                status="processing",
                progress=35,
                message="Processing document with intelligent routing...",
                document_id=document_id
            )
            
            # Use hybrid processor with intelligent routing
            chunks_with_metadata, processed_doc_id, num_pages, image_paths = await processor.process_document(
                file_path=file_path,
                filename=filename,
                document_id=document_id,
                processing_mode=processing_mode,
                save_images=settings.save_extracted_images
            )
            
            # Update after processing
            upload_progress_tracker.update_progress(
                upload_id,
                status="processing",
                progress=55,
                message=f"Successfully processed {len(chunks_with_metadata)} chunks...",
                document_id=document_id
            )
            
        except Exception as e:
            print(f"Error processing document: {e}")
            raise
        
        # Update progress: Preparing for vectorization
        upload_progress_tracker.update_progress(
            upload_id,
            status="vectorizing",
            progress=65,
            message=f"Preparing {len(chunks_with_metadata)} chunks for vectorization...",
            document_id=document_id,
            pages=num_pages
        )
        
        # Add file hash to all chunk metadata for duplicate detection
        if file_hash:
            for chunk in chunks_with_metadata:
                chunk["metadata"]["file_hash"] = file_hash
        
        # Update progress: Creating embeddings
        upload_progress_tracker.update_progress(
            upload_id,
            status="vectorizing",
            progress=75,
            message=f"Creating embeddings for {len(chunks_with_metadata)} chunks...",
            document_id=document_id,
            pages=num_pages
        )
        
        # Add to vector store
        num_chunks = vector_store.add_documents(chunks_with_metadata, document_id)
        
        # Update progress: Finalizing
        upload_progress_tracker.update_progress(
            upload_id,
            status="vectorizing",
            progress=95,
            message="Finalizing document update...",
            document_id=document_id,
            pages=num_pages,
            chunks=num_chunks
        )
        
        # Complete
        upload_progress_tracker.complete_upload(upload_id, document_id, num_pages, num_chunks)
        
    except Exception as e:
        upload_progress_tracker.fail_upload(upload_id, str(e))


async def process_document_background(
    upload_id: str,
    file_content: bytes,
    filename: str,
    file_ext: str,
    file_hash: str = None,
    processing_mode: str = "auto"
):
    """Background task to process uploaded document."""
    try:
        import asyncio
        import uuid
        # Small delay to ensure frontend can catch initial state
        await asyncio.sleep(0.1)
        
        # Update progress: Saving file
        upload_progress_tracker.update_progress(
            upload_id,
            status="processing",
            progress=10,
            message="Saving file..."
        )
        
        # Get processor (prefer hybrid for intelligent routing)
        processor = get_active_processor(use_hybrid=True)
        
        # Save file
        if hasattr(processor, 'save_uploaded_file'):
            file_path = processor.save_uploaded_file(file_content, filename)
        else:
            # Fallback for processors without save method
            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
            file_path = os.path.join(settings.upload_dir, unique_filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
        
        # Update progress: Processing document
        upload_progress_tracker.update_progress(
            upload_id,
            status="processing",
            progress=20,
            message=f"Analyzing document structure ({processing_mode} mode)..."
        )
        
        # Process document with hybrid processor
        try:
            # Update for processing start
            upload_progress_tracker.update_progress(
                upload_id,
                status="processing",
                progress=35,
                message="Processing document with intelligent routing..."
            )
            
            # Use hybrid processor with intelligent routing
            chunks_with_metadata, doc_id, num_pages, image_paths = await processor.process_document(
                file_path=file_path,
                filename=filename,
                processing_mode=processing_mode,
                save_images=settings.save_extracted_images
            )
            
            # Update after processing
            upload_progress_tracker.update_progress(
                upload_id,
                status="processing",
                progress=55,
                message=f"Successfully processed {len(chunks_with_metadata)} chunks..."
            )
            
        except Exception as e:
            print(f"Error processing document: {e}")
            raise
        
        # Update progress: Preparing for vectorization
        upload_progress_tracker.update_progress(
            upload_id,
            status="vectorizing",
            progress=65,
            message=f"Preparing {len(chunks_with_metadata)} chunks for vectorization...",
            document_id=doc_id,
            pages=num_pages
        )
        
        # Add file hash to all chunk metadata for duplicate detection
        if file_hash:
            for chunk in chunks_with_metadata:
                chunk["metadata"]["file_hash"] = file_hash
        
        # Update progress: Creating embeddings
        upload_progress_tracker.update_progress(
            upload_id,
            status="vectorizing",
            progress=75,
            message=f"Creating embeddings for {len(chunks_with_metadata)} chunks...",
            document_id=doc_id,
            pages=num_pages
        )
        
        # Add to vector store
        num_chunks = vector_store.add_documents(chunks_with_metadata, doc_id)
        
        # Update progress: Finalizing
        upload_progress_tracker.update_progress(
            upload_id,
            status="vectorizing",
            progress=95,
            message="Finalizing document indexing...",
            document_id=doc_id,
            pages=num_pages,
            chunks=num_chunks
        )
        
        # Complete
        upload_progress_tracker.complete_upload(upload_id, doc_id, num_pages, num_chunks)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in background processing: {error_details}")
        upload_progress_tracker.fail_upload(upload_id, str(e))


@app.get("/upload/progress/{upload_id}", response_model=UploadProgress, tags=["Documents"])
async def get_upload_progress(
    upload_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get the progress of a document upload.
    
    **🔓 Requires authentication - Check upload progress.**
    
    - **upload_id**: The upload ID returned from the upload endpoint
    
    Returns progress information including status, percentage, and messages.
    """
    progress = upload_progress_tracker.get_progress(upload_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    
    return UploadProgress(
        status=progress["status"],
        progress=progress["progress"],
        message=progress["message"],
        document_id=progress.get("document_id"),
        filename=progress.get("filename"),
        pages=progress.get("pages"),
        chunks=progress.get("chunks"),
        error=progress.get("error")
    )


@app.post("/upload", tags=["Documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    processing_mode: str = Form("auto"),  # auto, structured, text, hybrid
    current_user = Depends(get_current_admin_user)
):
    """
    Upload a document for processing with intelligent routing.
    
    **🔒 Requires ADMIN role - Only admins can upload documents.**
    
    - **file**: PDF, TXT, JSON, or CSV file to upload (max 50MB)
    - **processing_mode**: "auto" (detect), "structured" (JSON), "text" (chunking), "hybrid" (both)
    
    Returns upload ID for tracking progress. Use /upload/progress/{upload_id} to check status.
    
    ⚠️ Normal users cannot upload documents. Contact an admin to get uploader permissions.
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.pdf', '.txt', '.text', '.json', '.csv']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Only PDF, TXT, JSON, and CSV files are supported."
            )
        
        # Read file content
        file_content = await file.read()
        
        # Calculate file hash for duplicate detection
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate
        existing_doc = vector_store.find_document_by_hash(file_hash)
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=f"This document already exists in the system. "
                       f"Document ID: {existing_doc['document_id']}, "
                       f"Filename: {existing_doc['filename']}, "
                       f"Chunks: {existing_doc['chunks']}. "
                       f"Please delete the existing document first if you want to re-upload it."
            )
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.2f}MB. Maximum size is {settings.max_file_size_mb}MB."
            )
        
        # Create upload tracking
        upload_id = upload_progress_tracker.create_upload(file.filename)
        
        # Update initial progress immediately
        upload_progress_tracker.update_progress(
            upload_id,
            status="uploading",
            progress=5,
            message="File received, preparing to process..."
        )
        
        # Schedule background processing
        background_tasks.add_task(
            process_document_background,
            upload_id,
            file_content,
            file.filename,
            file_ext,
            file_hash,
            processing_mode
        )
        
        return {
            "success": True,
            "message": "Document upload started. Use the upload_id to track progress.",
            "upload_id": upload_id,
            "filename": file.filename
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting upload: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["Query"])
@limiter.limit("30/minute")  # Max 30 queries per minute per user
async def query_documents(
    request_data: QueryRequest,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Ask a question about the uploaded documents with advanced features.
    
    **🔓 Requires authentication - All authenticated users can query.**
    
    **Parameters:**
    - **question**: Your question about the documents
    - **top_k**: Number of relevant chunks to retrieve (1-20, default: 6)
    - **answer_type**: Type of answer to generate:
      - `default`: Standard Q&A
      - `summary`: Concise summary
      - `detailed`: In-depth explanation
      - `bullet_points`: Key points extracted
      - `compare`: Comparative analysis
      - `explain_simple`: Simple language explanation
    - **filters**: Optional metadata filters (e.g., `{"document_id": "doc_abc123"}`)
    - **session_id**: Conversation session ID for follow-up questions (get from `/conversation/create`)
    
    **Enhanced Features:**
    - 🔍 **Hybrid Search**: Combines vector similarity and keyword matching (BM25)
    - 🎯 **Reranking**: Uses cross-encoder model for better relevance
    - 📚 **Source Citations**: Detailed source information with relevance scores
    - 💬 **Conversation History**: Maintains context for follow-up questions
    - 🎨 **Multiple Answer Types**: Different formats for different needs
    
    Returns a detailed answer with enhanced source citations and retrieval metadata.
    """
    try:
        result = rag_chain.query(
            question=request_data.question,
            top_k=request_data.top_k,
            answer_type=request_data.answer_type.value if hasattr(request_data.answer_type, 'value') else request_data.answer_type,
            filters=request_data.filters,
            session_id=request_data.session_id,
            user_id=current_user.username,
            return_structured=request_data.return_structured
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/documents", response_model=list[DocumentInfo], tags=["Documents"])
async def list_documents(current_user = Depends(get_current_admin_user)):
    """
    List all uploaded documents.
    
    **🔒 Requires ADMIN role - Only admins can view document list.**
    
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


@app.get("/filters", tags=["Documents"])
async def get_available_filters(current_user = Depends(get_current_user)):
    """
    Get available filter values from all documents.
    
    **🔒 Requires authentication.**
    
    Returns unique values for each filterable field (control_owner, priority, compliance_tags, etc.)
    to populate filter dropdowns in the UI.
    """
    try:
        filters = vector_store.get_available_filters()
        return filters
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available filters: {str(e)}")


@app.get("/documents/{document_id}/chunks", response_model=list[DocumentChunk], tags=["Documents"])
async def get_document_chunks(
    document_id: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Get all chunks for a specific document.
    
    **🔒 Requires ADMIN role - Only admins can view document content.**
    
    - **document_id**: ID of the document to retrieve chunks for
    
    Returns all chunks with their content and metadata.
    """
    try:
        chunks = vector_store.get_document_chunks(document_id)
        
        if not chunks:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        
        return [DocumentChunk(**chunk) for chunk in chunks]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving document chunks: {str(e)}")


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


@app.put("/documents/{document_id}", tags=["Documents"])
async def update_document(
    background_tasks: BackgroundTasks,
    document_id: str,
    file: UploadFile = File(...),
    processing_mode: str = Form("auto"),
    current_user = Depends(get_current_admin_user)
):
    """
    Update/replace an existing document with a new file.
    
    **🔒 Requires ADMIN role - Only admins can update documents.**
    
    - **document_id**: ID of the document to update
    - **file**: New PDF, TXT, JSON, or CSV file to replace the existing document (max 50MB)
    - **processing_mode**: "auto" (detect), "structured" (JSON), "text" (chunking), "hybrid" (both)
    
    This will:
    1. Delete the old document and all its chunks
    2. Process the new file in the background with progress tracking
    3. Add new chunks with the same document_id
    
    Returns upload ID for tracking progress. Use /upload/progress/{upload_id} to check status.
    
    ⚠️ Normal users cannot update documents. Contact an admin for document management.
    """
    try:
        # First check if document exists
        existing_docs = vector_store.list_documents()
        doc_exists = any(doc['document_id'] == document_id for doc in existing_docs)
        
        if not doc_exists:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.pdf', '.txt', '.text', '.json', '.csv']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Only PDF, TXT, JSON, and CSV files are supported."
            )
        
        # Read file content
        file_content = await file.read()
        
        # Calculate file hash for duplicate detection
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check if this file is a duplicate of a DIFFERENT document
        existing_doc = vector_store.find_document_by_hash(file_hash)
        if existing_doc and existing_doc['document_id'] != document_id:
            raise HTTPException(
                status_code=409,
                detail=f"This file already exists as a different document. "
                       f"Document ID: {existing_doc['document_id']}, "
                       f"Filename: {existing_doc['filename']}, "
                       f"Chunks: {existing_doc['chunks']}. "
                       f"Please delete that document first or upload a different file."
            )
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.2f}MB. Maximum size is {settings.max_file_size_mb}MB."
            )
        
        # Delete old document chunks
        num_deleted = vector_store.delete_document(document_id)
        
        # Generate upload ID for tracking
        upload_id = f"update_{document_id}_{hashlib.md5(file_content[:1000]).hexdigest()[:8]}"
        
        # Initialize progress tracker
        upload_progress_tracker.start_upload(upload_id, file.filename)
        upload_progress_tracker.update_progress(
            upload_id,
            status="processing",
            progress=2,
            message=f"Updating document (deleted {num_deleted} old chunks)..."
        )
        
        # Process update in background WITH the existing document_id
        background_tasks.add_task(
            process_update_background,
            upload_id=upload_id,
            document_id=document_id,
            file_content=file_content,
            filename=file.filename,
            file_ext=file_ext,
            file_hash=file_hash,
            processing_mode=processing_mode
        )
        
        return {
            "upload_id": upload_id,
            "filename": file.filename,
            "document_id": document_id,
            "message": f"Document update started. Use /upload/progress/{upload_id} to track progress."
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")


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


# ============================================================================
# Conversation Management Endpoints
# ============================================================================

@app.post("/conversation/create", response_model=ConversationSessionResponse, tags=["Conversation"])
async def create_conversation_session(
    data: ConversationSessionCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new conversation session for context-aware follow-up questions.
    
    **🔓 Requires authentication**
    
    Returns a session ID that can be used in `/query` requests to maintain conversation context.
    The system will remember the last 10 messages to provide coherent follow-up answers.
    
    **Example workflow:**
    1. Create a session: `POST /conversation/create`
    2. Ask questions with the session_id: `POST /query` with `"session_id": "<your_session_id>"`
    3. The system maintains context for intelligent follow-ups
    """
    session_id = conversation_history.create_session(user_id=current_user.username)
    from datetime import datetime
    return ConversationSessionResponse(
        session_id=session_id,
        created_at=datetime.now().isoformat()
    )


@app.get("/conversation/{session_id}", response_model=ConversationHistoryResponse, tags=["Conversation"])
async def get_conversation_history(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get conversation history for a session.
    
    **🔓 Requires authentication**
    
    Returns all messages in the conversation session.
    """
    messages = conversation_history.get_history(session_id)
    return ConversationHistoryResponse(
        session_id=session_id,
        messages=messages
    )


@app.delete("/conversation/{session_id}", tags=["Conversation"])
async def clear_conversation_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """
    Clear a conversation session.
    
    **🔓 Requires authentication**
    
    Deletes all history for the specified session.
    """
    conversation_history.clear_session(session_id)
    return {
        "success": True,
        "message": "Conversation session cleared",
        "session_id": session_id
    }


@app.get("/conversation", tags=["Conversation"])
async def list_conversations(
    current_user = Depends(get_current_user)
):
    """
    List all active conversation sessions for the current user.
    
    **🔓 Requires authentication**
    """
    sessions = conversation_history.get_all_sessions(user_id=current_user.username)
    return {
        "sessions": sessions,
        "total": len(sessions)
    }


@app.post("/feedback", tags=["Feedback"])
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user = Depends(get_current_user)
):
    """
    Submit feedback on a query response.
    
    **🔓 Requires authentication**
    
    Helps improve the system by collecting user ratings and feedback.
    
    - **rating**: 1 (poor) to 5 (excellent)
    - **feedback_text**: Optional detailed feedback
    """
    # Store feedback in query log for admin review
    conversation_history.update_query_feedback(
        question=feedback.question,
        answer=feedback.answer,
        rating=feedback.rating,
        feedback_text=feedback.feedback_text,
        user_id=current_user.username
    )
    return {
        "success": True,
        "message": "Thank you for your feedback!",
        "rating": feedback.rating
    }


# ============================================================================
# Admin Analytics Endpoints
# ============================================================================

@app.get("/api/admin/query-log", tags=["Admin"])
async def get_query_log(
    user_id: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_admin_user)
):
    """
    Get the query log for admin review.
    
    **🔒 Requires ADMIN role**
    
    Shows all user queries, answers, ratings, and metadata.
    Useful for understanding how users interact with the RAG system.
    
    - **user_id**: Filter by specific username (optional)
    - **limit**: Max entries to return (default: 100)
    - **offset**: Pagination offset
    """
    return conversation_history.get_query_log(
        user_id=user_id,
        limit=limit,
        offset=offset
    )


@app.get("/api/admin/query-stats", tags=["Admin"])
async def get_query_stats(
    current_user = Depends(get_current_admin_user)
):
    """
    Get aggregated query statistics for admin dashboard.
    
    **🔒 Requires ADMIN role**
    
    Returns total queries, unique users, average rating,
    queries by type, and queries by user.
    """
    stats = conversation_history.get_query_stats()
    # Include cache stats
    from app.services.query_cache import query_cache
    stats["cache_stats"] = query_cache.get_stats()
    return stats


@app.get("/api/admin/sessions", tags=["Admin"])
async def get_all_sessions(
    current_user = Depends(get_current_admin_user)
):
    """
    Get all active conversation sessions across all users.
    
    **🔒 Requires ADMIN role**
    """
    sessions = conversation_history.get_all_sessions()
    return {
        "sessions": sessions,
        "total": len(sessions)
    }


# ============================================================================
# Ticket Endpoints
# ============================================================================

from pydantic import BaseModel, Field
from typing import Optional as Opt

class TicketCreate(BaseModel):
    question: str = Field(..., description="The unanswerable question")
    session_id: Opt[str] = None

class TicketStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: open, in_progress, resolved, closed")
    admin_notes: Opt[str] = None


@app.post("/api/tickets", tags=["Tickets"])
async def create_ticket(
    ticket_data: TicketCreate,
    current_user = Depends(get_current_user)
):
    """
    Raise a ticket for an unanswerable query.
    
    **\U0001f513 Requires authentication - Any user can raise a ticket.**
    
    When the system cannot answer a question, users can raise a ticket
    so admins can review and upload relevant documents.
    """
    ticket = ticket_service.create_ticket(
        user_id=current_user.username,
        question=ticket_data.question,
        session_id=ticket_data.session_id
    )
    return ticket


@app.get("/api/admin/tickets", tags=["Admin"])
async def get_tickets(
    status: str = None,
    user_id: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_admin_user)
):
    """
    Get all tickets (Admin only).
    
    **\U0001f512 Requires ADMIN role**
    
    Optional filters: status (open, in_progress, resolved, closed), user_id
    """
    return ticket_service.get_tickets(
        status=status,
        user_id=user_id,
        limit=limit,
        offset=offset
    )


@app.put("/api/admin/tickets/{ticket_id}", tags=["Admin"])
async def update_ticket(
    ticket_id: str,
    update_data: TicketStatusUpdate,
    current_user = Depends(get_current_admin_user)
):
    """
    Update ticket status (Admin only).
    
    **\U0001f512 Requires ADMIN role**
    """
    updated = ticket_service.update_ticket_status(
        ticket_id=ticket_id,
        status=update_data.status,
        admin_notes=update_data.admin_notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"success": True, "message": "Ticket updated"}


@app.get("/api/admin/ticket-stats", tags=["Admin"])
async def get_ticket_stats(
    current_user = Depends(get_current_admin_user)
):
    """
    Get ticket statistics (Admin only).
    
    **\U0001f512 Requires ADMIN role**
    """
    return ticket_service.get_ticket_stats()


# ============================================================================
# Territory Management Endpoints
# ============================================================================

@app.post("/api/admin/territories/import", response_model=TerritoryBulkImportResponse, tags=["Admin"])
async def import_territories(
    request: TerritoryBulkImportRequest,
    current_user = Depends(get_current_admin_user)
):
    """
    Import bulk territory data (Admin only).

    **🔒 Requires ADMIN role**

    Example data format:
    ```json
    {
        "clear_existing": false,
        "data": [
            {
                "region": "Eastern Hawks",
                "city": "GUJRANWALA",
                "zone": "GREEN_ZONE_1",
                "territories": ["TERRITORY_1", "TERRITORY_2"]
            }
        ]
    }
    ```
    """
    try:
        if request.clear_existing:
            territory_service.clear_all_data()

        stats = territory_service.import_bulk_data([d.dict() for d in request.data])

        return TerritoryBulkImportResponse(
            success=True,
            message=f"Import completed successfully",
            stats=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@app.get("/api/territories/regions", response_model=List[RegionResponse], tags=["Territories"])
async def get_regions(
    current_user = Depends(get_current_user)
):
    """
    Get all regions with city counts.

    **🔓 Requires authentication**
    """
    return territory_service.get_all_regions()


@app.get("/api/territories/regions/{region_id}/cities", response_model=List[CityResponse], tags=["Territories"])
async def get_cities_in_region(
    region_id: int,
    current_user = Depends(get_current_user)
):
    """
    Get all cities in a region.

    **🔓 Requires authentication**
    """
    return territory_service.get_cities_by_region(region_id)


@app.get("/api/territories/cities/{city_id}/zones", response_model=List[ZoneResponse], tags=["Territories"])
async def get_zones_in_city(
    city_id: int,
    current_user = Depends(get_current_user)
):
    """
    Get all zones in a city.

    **🔓 Requires authentication**
    """
    return territory_service.get_zones_by_city(city_id)


@app.get("/api/territories/zones/{zone_id}/territories", response_model=List[TerritoryResponse], tags=["Territories"])
async def get_territories_in_zone(
    zone_id: int,
    current_user = Depends(get_current_user)
):
    """
    Get all territories in a zone.

    **🔓 Requires authentication**
    """
    return territory_service.get_territories_by_zone(zone_id)


@app.get("/api/territories/hierarchy", tags=["Territories"])
async def get_territory_hierarchy(
    current_user = Depends(get_current_user)
):
    """
    Get complete territory hierarchy: regions -> cities -> zones -> territories.

    **🔓 Requires authentication**
    """
    return territory_service.get_full_hierarchy()


@app.get("/api/territories/search", response_model=List[TerritorySearchResult], tags=["Territories"])
async def search_territories(
    q: str,
    current_user = Depends(get_current_user)
):
    """
    Search for territories, zones, cities, or regions by name.

    **🔓 Requires authentication**

    Example: `/api/territories/search?q=gujran`
    """
    return territory_service.search_territories(q)


@app.delete("/api/admin/territories/clear", tags=["Admin"])
async def clear_territory_data(
    current_user = Depends(get_current_admin_user)
):
    """
    Clear all territory data (Admin only). Use with caution!

    **🔒 Requires ADMIN role**
    """
    territory_service.clear_all_data()
    return {"success": True, "message": "All territory data cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
