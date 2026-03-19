"""
Upload Progress Tracking Service
Tracks document upload and processing progress in memory.
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid


class UploadProgressTracker:
    """Track upload progress for multiple concurrent uploads."""
    
    def __init__(self):
        self._progress: Dict[str, Dict] = {}
        self._cleanup_interval = timedelta(hours=1)  # Clean up completed uploads after 1 hour
    
    def create_upload(self, filename: str) -> str:
        """Create a new upload task and return its ID."""
        upload_id = f"upload_{uuid.uuid4().hex[:12]}"
        self._progress[upload_id] = {
            "status": "uploading",
            "progress": 0,
            "message": "Starting upload...",
            "filename": filename,
            "document_id": None,
            "pages": None,
            "chunks": None,
            "error": None,
            "created_at": datetime.now()
        }
        return upload_id
    
    def update_progress(
        self,
        upload_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        document_id: Optional[str] = None,
        pages: Optional[int] = None,
        chunks: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Update progress for an upload."""
        if upload_id not in self._progress:
            return
        
        if status is not None:
            self._progress[upload_id]["status"] = status
        if progress is not None:
            self._progress[upload_id]["progress"] = min(100, max(0, progress))
        if message is not None:
            self._progress[upload_id]["message"] = message
        if document_id is not None:
            self._progress[upload_id]["document_id"] = document_id
        if pages is not None:
            self._progress[upload_id]["pages"] = pages
        if chunks is not None:
            self._progress[upload_id]["chunks"] = chunks
        if error is not None:
            self._progress[upload_id]["error"] = error
    
    def get_progress(self, upload_id: str) -> Optional[Dict]:
        """Get progress for an upload."""
        return self._progress.get(upload_id)
    
    def complete_upload(self, upload_id: str, document_id: str, pages: int, chunks: int):
        """Mark upload as completed."""
        self.update_progress(
            upload_id,
            status="completed",
            progress=100,
            message="Document uploaded and processed successfully",
            document_id=document_id,
            pages=pages,
            chunks=chunks
        )
    
    def fail_upload(self, upload_id: str, error: str):
        """Mark upload as failed."""
        self.update_progress(
            upload_id,
            status="failed",
            message="Upload failed",
            error=error
        )
    
    def cleanup_old_uploads(self):
        """Remove old completed/failed uploads from memory."""
        now = datetime.now()
        to_remove = []
        
        for upload_id, info in self._progress.items():
            age = now - info["created_at"]
            if age > self._cleanup_interval and info["status"] in ["completed", "failed"]:
                to_remove.append(upload_id)
        
        for upload_id in to_remove:
            del self._progress[upload_id]


# Global instance
upload_progress_tracker = UploadProgressTracker()
