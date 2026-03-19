"""
SQLite-based ticket service for unanswerable query tickets.
Users can raise tickets when the system cannot answer their question.
"""
import sqlite3
import os
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class TicketService:
    """Manage support tickets for unanswerable queries."""
    
    def __init__(self, db_path: str = "data/tickets.db"):
        """Initialize ticket database."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create tickets table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                session_id TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                admin_notes TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_user ON tickets(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_status ON tickets(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_created ON tickets(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    def create_ticket(
        self,
        user_id: str,
        question: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Create a new ticket for an unanswerable query.
        
        Returns:
            Dict with ticket details
        """
        ticket_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tickets (id, user_id, question, session_id, status, created_at)
            VALUES (?, ?, ?, ?, 'open', ?)
        """, (ticket_id, user_id, question, session_id, created_at))
        
        conn.commit()
        conn.close()
        
        return {
            'id': ticket_id,
            'user_id': user_id,
            'question': question,
            'session_id': session_id,
            'status': 'open',
            'created_at': created_at
        }
    
    def get_tickets(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        Get tickets with optional filtering.
        
        Returns:
            Dict with tickets list and total count
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Count
        cursor.execute(f"SELECT COUNT(*) as count FROM tickets {where_clause}", params)
        total = cursor.fetchone()['count']
        
        # Fetch
        cursor.execute(f"""
            SELECT * FROM tickets {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            'tickets': [dict(row) for row in rows],
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        admin_notes: Optional[str] = None
    ) -> bool:
        """
        Update ticket status (open, in_progress, resolved, closed).
        
        Returns:
            True if updated, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        resolved_at = datetime.now().isoformat() if status in ('resolved', 'closed') else None
        
        cursor.execute("""
            UPDATE tickets
            SET status = ?, admin_notes = ?, resolved_at = ?
            WHERE id = ?
        """, (status, admin_notes, resolved_at, ticket_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    def get_ticket_stats(self) -> Dict:
        """Get ticket statistics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets")
        total = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'open'")
        open_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'in_progress'")
        in_progress = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status IN ('resolved', 'closed')")
        resolved = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            'total_tickets': total,
            'open_tickets': open_count,
            'in_progress_tickets': in_progress,
            'resolved_tickets': resolved
        }


# Global instance
ticket_service = TicketService()
