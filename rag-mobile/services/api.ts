/**
 * API client for RAG backend - Mobile
 */
import axios from 'axios';

// Change this to your computer's IP address when testing on physical device
// Example: http://192.168.1.100:8000
const API_BASE_URL = 'http://localhost:8000';

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
        chunk_index: number;
        total_chunks: number;
        chunk_length: number;
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
        cache_hit?: boolean;
        cache_match_type?: string;
        cache_match_score?: number;
    };
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

export interface UploadResponse {
    success: boolean;
    message: string;
    document_id: string;
    filename: string;
    pages?: number;
    chunks: number;
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

export interface QueryStatsResponse {
    total_queries: number;
    unique_users: number;
    avg_rating: number | null;
    rated_queries: number;
    queries_by_type: { [key: string]: number };
    queries_by_user: { [key: string]: number };
}

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
});

let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
    authToken = token;
    if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
        delete api.defaults.headers.common['Authorization'];
    }
};

export const getAuthToken = () => authToken;

export const ragApi = {
    async uploadDocument(uri: string, fileName: string): Promise<UploadResponse> {
        const formData = new FormData();
        formData.append('file', {
            uri,
            name: fileName,
            type: fileName.endsWith('.pdf') ? 'application/pdf' : 'text/plain',
        } as any);

        const response = await api.post('/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data;
    },

    async queryDocuments(question: string, topK: number = 4): Promise<QueryResponse> {
        const response = await api.post('/query', {
            question,
            top_k: topK,
        });

        return response.data;
    },

    async listDocuments(): Promise<Document[]> {
        const response = await api.get('/documents');
        return response.data;
    },

    async deleteDocument(documentId: string): Promise<void> {
        await api.delete(`/documents/${documentId}`);
    },

    async getStats() {
        const response = await api.get('/stats');
        return response.data;
    },

    async healthCheck() {
        const response = await api.get('/health');
        return response.data;
    },

    async getDocumentChunks(documentId: string): Promise<DocumentChunk[]> {
        const response = await api.get(`/documents/${documentId}/chunks`);
        return response.data;
    },

    // Authentication
    async login(username: string, password: string): Promise<LoginResponse> {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/api/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        const token = response.data.access_token;
        setAuthToken(token);
        return response.data;
    },

    async getCurrentUser(): Promise<User> {
        const response = await api.get('/api/auth/me');
        return response.data;
    },

    logout() {
        setAuthToken(null);
    },

    // Admin APIs
    async getQueryLog(userId?: string, limit: number = 100, offset: number = 0) {
        const params = new URLSearchParams();
        if (userId) params.append('user_id', userId);
        params.append('limit', limit.toString());
        params.append('offset', offset.toString());

        const response = await api.get(`/api/admin/query-log?${params}`);
        return response.data;
    },

    async getQueryStats(): Promise<QueryStatsResponse> {
        const response = await api.get('/api/admin/query-stats');
        return response.data;
    },

    async updateUserPermission(
        userId: number,
        canDeleteHistory: boolean,
        canExport: boolean
    ): Promise<User> {
        const response = await api.put(`/api/auth/users/${userId}/permissions`, {
            can_delete_history: canDeleteHistory,
            can_export: canExport,
        });
        return response.data;
    },
};
