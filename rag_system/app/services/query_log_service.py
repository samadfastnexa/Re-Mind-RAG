"""
SQLite-based query log service for persistent storage.
Replaces in-memory query log with database storage.
"""
import sqlite3
import os
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class QueryLogService:
    """Manage persistent query logs using SQLite."""
    
    def __init__(self, db_path: str = "data/query_log.db"):
        """Initialize query log database."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create query_log table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                answer_type TEXT DEFAULT 'default',
                sources_count INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                rating INTEGER,
                feedback_text TEXT
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON query_log(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON query_log(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id ON query_log(session_id)
        """)
        
        conn.commit()
        conn.close()
    
    def add_query(
        self,
        session_id: str,
        user_id: str,
        question: str,
        answer: str,
        answer_type: str = 'default',
        sources_count: int = 0
    ) -> str:
        """
        Add a new query to the log.
        
        Returns:
            Query ID
        """
        query_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO query_log (
                id, session_id, user_id, question, answer,
                answer_type, sources_count, timestamp, rating, feedback_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        """, (query_id, session_id, user_id, question, answer, answer_type, sources_count, timestamp))
        
        conn.commit()
        conn.close()
        
        return query_id
    
    def get_query_log(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        Get query log with optional filtering and pagination.
        
        Args:
            user_id: Filter by user ID (optional)
            limit: Max entries to return
            offset: Pagination offset
            
        Returns:
            Dict with queries list and total count
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query based on filters
        if user_id:
            cursor.execute("""
                SELECT COUNT(*) as count FROM query_log WHERE user_id = ?
            """, (user_id,))
            total = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT * FROM query_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM query_log")
            total = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT * FROM query_log
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        queries = [dict(row) for row in rows]
        
        return {
            'queries': queries,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    def update_query_feedback(
        self,
        question: str,
        answer: str,
        rating: int,
        feedback_text: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update feedback/rating for a query.
        Matches by question + answer content (most recent match).
        
        Returns:
            True if updated, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find the most recent matching query
        if user_id:
            cursor.execute("""
                SELECT id FROM query_log
                WHERE question = ? AND answer = ? AND user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (question, answer, user_id))
        else:
            cursor.execute("""
                SELECT id FROM query_log
                WHERE question = ? AND answer = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (question, answer))
        
        result = cursor.fetchone()
        
        if result:
            query_id = result[0]
            cursor.execute("""
                UPDATE query_log
                SET rating = ?, feedback_text = ?
                WHERE id = ?
            """, (rating, feedback_text, query_id))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def get_query_stats(self) -> Dict:
        """
        Get aggregated statistics from query log.
        
        Returns:
            Dict with total queries, unique users, avg rating, etc.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Total queries
        cursor.execute("SELECT COUNT(*) as count FROM query_log")
        total_queries = cursor.fetchone()['count']
        
        if total_queries == 0:
            conn.close()
            return {
                'total_queries': 0,
                'unique_users': 0,
                'avg_rating': None,
                'rated_queries': 0,
                'queries_by_type': {},
                'queries_by_user': {}
            }
        
        # Unique users
        cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM query_log")
        unique_users = cursor.fetchone()['count']
        
        # Average rating
        cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(rating) as rated_count
            FROM query_log
            WHERE rating IS NOT NULL
        """)
        rating_stats = cursor.fetchone()
        avg_rating = rating_stats['avg_rating']
        rated_queries = rating_stats['rated_count']
        
        # Queries by answer type
        cursor.execute("""
            SELECT answer_type, COUNT(*) as count
            FROM query_log
            GROUP BY answer_type
        """)
        queries_by_type = {row['answer_type']: row['count'] for row in cursor.fetchall()}
        
        # Queries by user
        cursor.execute("""
            SELECT user_id, COUNT(*) as count
            FROM query_log
            GROUP BY user_id
        """)
        queries_by_user = {row['user_id']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_queries': total_queries,
            'unique_users': unique_users,
            'avg_rating': round(avg_rating, 2) if avg_rating is not None else None,
            'rated_queries': rated_queries,
            'queries_by_type': queries_by_type,
            'queries_by_user': queries_by_user
        }
    
    def clear_all(self):
        """Clear all query logs (for testing/debugging)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_log")
        conn.commit()
        conn.close()


# Global instance
query_log_service = QueryLogService()
