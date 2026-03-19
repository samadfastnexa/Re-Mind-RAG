'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api, type Document } from '@/lib/api';

interface DocumentListProps {
    isAdmin: boolean;
}

export default function DocumentList({ isAdmin }: DocumentListProps) {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadDocuments = async () => {
        try {
            setLoading(true);
            const docs = await api.listDocuments();
            setDocuments(docs);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load documents');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDocuments();
    }, []);

    const handleDelete = async (documentId: string) => {
        if (!isAdmin) {
            toast.error('Only admins can delete documents');
            return;
        }

        if (!confirm('Are you sure you want to delete this document?')) return;

        try {
            await api.deleteDocument(documentId);
            await loadDocuments();
            toast.success('Document deleted successfully');
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to delete document';
            toast.error(errorMsg);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
            </div>
        );
    }

    if (documents.length === 0) {
        return (
            <div className="text-center p-8 text-gray-500">
                <p className="text-sm">No documents uploaded yet</p>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {documents.map((doc) => (
                <div
                    key={doc.document_id}
                    className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                >
                    <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                            <h3 className="text-sm font-medium text-gray-900 truncate">
                                {doc.filename}
                            </h3>
                            <p className="text-xs text-gray-500 mt-1">
                                {doc.chunks} chunks
                            </p>
                        </div>
                        {isAdmin && (
                            <button
                                onClick={() => handleDelete(doc.document_id)}
                                className="ml-2 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                title="Delete document"
                            >
                                <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                    />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}
