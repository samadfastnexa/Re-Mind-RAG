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

export interface QueryResponse {
    question: string;
    answer: string;
    sources: Array<{
        document: string;
        chunk: number;
        content: string;
        relevance_score: number;
    }>;
}

export interface UploadResponse {
    success: boolean;
    message: string;
    document_id: string;
    filename: string;
    pages?: number;
    chunks: number;
}

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
});

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
};
