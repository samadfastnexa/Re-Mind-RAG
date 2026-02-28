/**
 * API client for RAG backend with authentication
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'rag_auth_token';

export interface Document {
    document_id: string;
    filename: string;
    upload_date: string;
    chunks: number;
}

export interface DocumentChunk {
    chunk_id: string;
    content: string;
    chunk_number: number;
    metadata: {
        document_id: string;
        filename: string;
        chunk: number;
        total_chunks: number;
        [key: string]: any;
    };
}

export interface QueryResponse {
    question: string;
    answer: string;
    sources: Array<{
        source_id: number;
        document_id: string;
        document: string;
        chunk: number;
        total_chunks: number;
        position_percent: number;
        content: string;
        relevance_score: number;
        chunk_length: number;
    }>;
    answer_type?: string;
    retrieval_metadata?: {
        total_sources: number;
        hybrid_search_used: boolean;
        reranking_used: boolean;
        filters_applied: boolean;
    };
}

export interface QueryRequest {
    question: string;
    top_k?: number;
    answer_type?: 'default' | 'summary' | 'detailed' | 'bullet_points' | 'compare' | 'explain_simple';
    filters?: Record<string, string>;
    session_id?: string;
}

export interface ConversationSession {
    session_id: string;
    created_at: string;
}

export interface FeedbackRequest {
    session_id?: string;
    question: string;
    answer: string;
    rating: number;
    feedback_text?: string;
}

export interface UploadResponse {
    success: boolean;
    message: string;
    document_id: string;
    filename: string;
    pages?: number;
    chunks: number;
}

export interface User {
    id: number;
    username: string;
    email: string;
    role: 'user' | 'admin';
    is_active: boolean;
    can_delete_history: boolean;
    can_export: boolean;
    created_at: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface QueryLogEntry {
    id: string;
    session_id: string;
    user_id: string;
    question: string;
    answer: string;
    answer_type: string;
    sources_count: number;
    timestamp: string;
    rating: number | null;
    feedback_text: string | null;
}

export interface QueryLogResponse {
    queries: QueryLogEntry[];
    total: number;
    limit: number;
    offset: number;
}

export interface QueryStatsResponse {
    total_queries: number;
    unique_users: number;
    avg_rating: number | null;
    rated_queries: number;
    queries_by_type: Record<string, number>;
    queries_by_user: Record<string, number>;
}

export interface AdminSession {
    session_id: string;
    user_id: string;
    created_at: string;
    last_activity: string;
    message_count: number;
}

// Auth utilities
export const auth = {
    getToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(TOKEN_KEY);
    },

    setToken(token: string): void {
        if (typeof window === 'undefined') return;
        localStorage.setItem(TOKEN_KEY, token);
    },

    clearToken(): void {
        if (typeof window === 'undefined') return;
        localStorage.removeItem(TOKEN_KEY);
    },

    isAuthenticated(): boolean {
        return !!this.getToken();
    }
};

// Helper to get auth headers
function getAuthHeaders(): HeadersInit {
    const token = auth.getToken();
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
}

export const api = {
    // Authentication endpoints
    async login(username: string, password: string): Promise<LoginResponse> {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        auth.setToken(data.access_token);
        return data;
    },

    async getCurrentUser(): Promise<User> {
        const token = auth.getToken();
        if (!token) {
            throw new Error('Not authenticated');
        }

        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            if (response.status === 401) {
                auth.clearToken();
            }
            const errorText = await response.text();
            let detail = 'Failed to get user info';
            try {
                const errorJson = JSON.parse(errorText);
                detail = errorJson.detail || detail;
            } catch {}
            throw new Error(detail);
        }

        return response.json();
    },

    logout(): void {
        auth.clearToken();
    },

    async uploadDocument(file: File): Promise<UploadResponse> {
        const formData = new FormData();
        formData.append('file', file);

        const token = auth.getToken();
        const headers: HeadersInit = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers,
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    },

    async queryDocuments(queryRequest: QueryRequest | string, topK?: number): Promise<QueryResponse> {
        // Support both old and new API
        const body = typeof queryRequest === 'string' 
            ? { question: queryRequest, top_k: topK || 6 }
            : {
                question: queryRequest.question,
                top_k: queryRequest.top_k || 6,
                answer_type: queryRequest.answer_type || 'default',
                filters: queryRequest.filters,
                session_id: queryRequest.session_id
            };

        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }

        return response.json();
    },

    async listDocuments(): Promise<Document[]> {
        const response = await fetch(`${API_BASE_URL}/documents`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Failed to fetch documents');
        }

        return response.json();
    },

    async getDocumentChunks(documentId: string): Promise<DocumentChunk[]> {
        const response = await fetch(`${API_BASE_URL}/documents/${documentId}/chunks`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to fetch document chunks' }));
            throw new Error(error.detail || 'Failed to fetch document chunks');
        }

        return response.json();
    },

    async deleteDocument(documentId: string): Promise<void> {
        const token = auth.getToken();
        const headers: HeadersInit = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
            method: 'DELETE',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Delete failed');
        }
    },

    async getStats() {
        const response = await fetch(`${API_BASE_URL}/stats`);

        if (!response.ok) {
            throw new Error('Failed to fetch stats');
        }

        return response.json();
    },

    async healthCheck() {
        const response = await fetch(`${API_BASE_URL}/health`);

        if (!response.ok) {
            throw new Error('Health check failed');
        }

        return response.json();
    },

    // Admin endpoints
    async getAllUsers(): Promise<User[]> {
        const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Failed to fetch users');
        }

        return response.json();
    },

    async createUser(userData: {
        username: string;
        email: string;
        password: string;
        role: 'user' | 'admin';
    }): Promise<User> {
        const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(userData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create user');
        }

        return response.json();
    },

    async updateUserPermission(userId: number, canDeleteHistory: boolean): Promise<void> {
        const params = new URLSearchParams();
        params.set('can_delete_history', String(canDeleteHistory));

        const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}/permissions?${params}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Failed to update user permissions');
        }
    },

    async updateUser(userId: number, data: {
        username?: string;
        email?: string;
        password?: string;
        role?: 'user' | 'admin';
        is_active?: boolean;
    }): Promise<User> {
        const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update user');
        }

        return response.json();
    },

    async deleteUser(userId: number): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete user');
        }
    },

    // Conversation management endpoints
    async createConversationSession(): Promise<ConversationSession> {
        const response = await fetch(`${API_BASE_URL}/conversation/create`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({}),
        });

        if (!response.ok) {
            throw new Error('Failed to create conversation session');
        }

        return response.json();
    },

    async getConversationHistory(sessionId: string) {
        const response = await fetch(`${API_BASE_URL}/conversation/${sessionId}`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Failed to fetch conversation history');
        }

        return response.json();
    },

    async clearConversationSession(sessionId: string): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/conversation/${sessionId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Failed to clear conversation session');
        }
    },

    async submitFeedback(feedback: FeedbackRequest): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/feedback`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(feedback),
        });

        if (!response.ok) {
            throw new Error('Failed to submit feedback');
        }
    },

    // Admin analytics endpoints
    async getQueryLog(userId?: string, limit = 100, offset = 0): Promise<QueryLogResponse> {
        const params = new URLSearchParams();
        if (userId) params.set('user_id', userId);
        params.set('limit', String(limit));
        params.set('offset', String(offset));

        const response = await fetch(`${API_BASE_URL}/api/admin/query-log?${params}`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.text(); // Use text() to avoid JSON parse error
            throw new Error(error || 'Failed to fetch query log');
        }

        return response.json();
    },

    async getQueryStats(): Promise<QueryStatsResponse> {
        const response = await fetch(`${API_BASE_URL}/api/admin/query-stats`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Failed to fetch query stats');
        }

        return response.json();
    },

    async getAdminSessions(): Promise<{ sessions: AdminSession[]; total: number }> {
        const response = await fetch(`${API_BASE_URL}/api/admin/sessions`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Failed to fetch sessions');
        }

        return response.json();
    },
};
