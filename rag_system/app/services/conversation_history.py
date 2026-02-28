"""
Conversation history management for context-aware follow-up questions.
Includes query log for admin analytics.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
from app.services.query_log_service import query_log_service


class ConversationHistory:
    """Manage conversation sessions, history, and query logs."""
    
    def __init__(self, max_messages: int = 10, session_timeout_minutes: int = 60):
        """
        Initialize conversation history manager.
        
        Args:
            max_messages: Maximum number of messages to keep per session
            session_timeout_minutes: Session timeout in minutes
        """
        self.sessions: Dict[str, Dict] = {}
        self.max_messages = max_messages
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        Create a new conversation session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'messages': []
        }
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None, user_id: Optional[str] = None):
        """
        Add a message to the conversation history.
        Also logs user queries to the global query log for admin analytics.
        
        Args:
            session_id: Session identifier
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata (sources, etc.)
            user_id: Optional user identifier (for query logging)
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'user_id': user_id,  # Set user_id when creating session
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'messages': []
            }
        
        session = self.sessions[session_id]
        
        # Update user_id if provided and not set
        if user_id and not session.get('user_id'):
            session['user_id'] = user_id
        
        session['last_activity'] = datetime.now()
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        session['messages'].append(message)
        
        # Log the full Q&A pair when assistant responds (to persistent database)
        if role == 'assistant':
            user_id = session.get('user_id', 'anonymous')
            # Find the most recent user message
            user_messages = [m for m in session['messages'] if m['role'] == 'user']
            question = user_messages[-1]['content'] if user_messages else ''
            
            # Save to persistent database
            query_log_service.add_query(
                session_id=session_id,
                user_id=user_id,
                question=question,
                answer=content,
                answer_type=(metadata or {}).get('answer_type', 'default'),
                sources_count=len((metadata or {}).get('sources', []))
            )
        
        # Keep only the last N messages
        if len(session['messages']) > self.max_messages:
            session['messages'] = session['messages'][-self.max_messages:]
    
    def get_history(self, session_id: str, include_last_n: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            include_last_n: Optional limit for number of messages
            
        Returns:
            List of messages
        """
        if session_id not in self.sessions:
            return []
        
        self._cleanup_expired_sessions()
        
        if session_id not in self.sessions:
            return []
        
        messages = self.sessions[session_id]['messages']
        
        if include_last_n is not None:
            messages = messages[-include_last_n:]
        
        return messages
    
    def get_context_string(self, session_id: str, last_n: int = 3) -> str:
        """
        Get formatted conversation context for LLM.
        
        Args:
            session_id: Session identifier
            last_n: Number of last message pairs to include
            
        Returns:
            Formatted context string
        """
        history = self.get_history(session_id, include_last_n=last_n * 2)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n\n".join(context_parts)
    
    def clear_session(self, session_id: str):
        """
        Clear a conversation session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session['last_activity'] > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]
    
    def get_all_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all active sessions, optionally filtered by user.
        
        Args:
            user_id: Optional user identifier to filter by
            
        Returns:
            List of session information
        """
        self._cleanup_expired_sessions()
        
        sessions = []
        for sid, session in self.sessions.items():
            if user_id is None or session.get('user_id') == user_id:
                sessions.append({
                    'session_id': sid,
                    'user_id': session.get('user_id', 'anonymous'),
                    'created_at': session['created_at'].isoformat(),
                    'last_activity': session['last_activity'].isoformat(),
                    'message_count': len(session['messages'])
                })
        
        return sessions

    def get_query_log(
        self, 
        user_id: Optional[str] = None, 
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        Get query log for admin review (from persistent database).
        
        Args:
            user_id: Filter by specific user (None = all users)
            limit: Max entries to return
            offset: Pagination offset
            
        Returns:
            Dict with queries list and total count
        """
        return query_log_service.get_query_log(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

    def update_query_feedback(self, question: str, answer: str, rating: int, feedback_text: Optional[str] = None, user_id: Optional[str] = None):
        """
        Update the feedback/rating on a query log entry (in persistent database).
        Matches by question + answer content.
        """
        return query_log_service.update_query_feedback(
            question=question,
            answer=answer,
            rating=rating,
            feedback_text=feedback_text,
            user_id=user_id
        )
    
    def get_query_stats(self) -> Dict:
        """
        Get aggregated stats from the query log for admin dashboard (from persistent database).
        """
        return query_log_service.get_query_stats()


# Global instance
conversation_history = ConversationHistory()
