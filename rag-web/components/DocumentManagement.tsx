'use client';

import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { api, type Document, type DocumentChunk } from '@/lib/api';
import DocumentUpload from './DocumentUpload';

export default function DocumentManagement() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [updatingId, setUpdatingId] = useState<string | null>(null);
    const [updateProgress, setUpdateProgress] = useState<{[key: string]: any}>({});
    const [searchQuery, setSearchQuery] = useState('');
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [chunks, setChunks] = useState<DocumentChunk[]>([]);
    const [loadingChunks, setLoadingChunks] = useState(false);
    const [showUpload, setShowUpload] = useState(false);
    const fileInputRef = useRef<{ [key: string]: HTMLInputElement | null }>({});
    const updatePollIntervalRef = useRef<{[key: string]: NodeJS.Timeout}>({});

    const loadDocuments = async () => {
        try {
            setLoading(true);
            setError(null);
            const docs = await api.listDocuments();
            setDocuments(docs);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load documents');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDocuments();
        
        // Cleanup polling on unmount
        return () => {
            Object.values(updatePollIntervalRef.current).forEach(interval => {
                if (interval) clearInterval(interval);
            });
        };
    }, []);

    const handleDelete = async (doc: Document) => {
        if (!confirm(`Are you sure you want to delete "${doc.filename}"?\n\nThis will remove:\n• ${doc.chunks} chunks from the database\n• All associated embeddings\n\nThis action cannot be undone.`)) {
            return;
        }

        setDeletingId(doc.document_id);
        try {
            await api.deleteDocument(doc.document_id);
            setDocuments(prev => prev.filter(d => d.document_id !== doc.document_id));
            toast.success(`Deleted "${doc.filename}" successfully`);
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to delete document';
            toast.error(errorMsg);
        } finally {
            setDeletingId(null);
        }
    };

    const handleUpdateClick = (documentId: string) => {
        // Trigger file input click for this document
        fileInputRef.current[documentId]?.click();
    };

    const handleFileSelect = async (doc: Document, event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        if (!confirm(`Are you sure you want to update "${doc.filename}"?\n\nThis will:\n• Replace all ${doc.chunks} existing chunks\n• Re-process the document with the new file\n\nOld content will be permanently replaced.`)) {
            // Reset file input
            event.target.value = '';
            return;
        }

        setUpdatingId(doc.document_id);
        setUpdateProgress(prev => ({ ...prev, [doc.document_id]: { progress: 2, message: 'Starting update...' } }));
        
        try {
            // Start update
            const result = await api.updateDocument(doc.document_id, file, 'auto');
            
            // Poll for progress
            const pollUpdateProgress = async () => {
                try {
                    const progressData = await api.getUploadProgress(result.upload_id);
                    setUpdateProgress(prev => ({ ...prev, [doc.document_id]: progressData }));
                    
                    if (progressData.status === 'completed') {
                        // Clear polling
                        if (updatePollIntervalRef.current[doc.document_id]) {
                            clearInterval(updatePollIntervalRef.current[doc.document_id]);
                            delete updatePollIntervalRef.current[doc.document_id];
                        }
                        
                        // Reload documents to get updated data
                        await loadDocuments();
                        
                        setUpdatingId(null);
                        setUpdateProgress(prev => ({
                            ...prev,
                            [doc.document_id]: { progress: 100, message: 'Complete!' }
                        }));
                        
                        setTimeout(() => {
                            setUpdateProgress(prev => {
                                const newProgress = { ...prev };
                                delete newProgress[doc.document_id];
                                return newProgress;
                            });
                        }, 2000);
                        
                        toast.success(`Document updated successfully!\nProcessed ${progressData.chunks} chunks from ${progressData.pages} pages`);
                    } else if (progressData.status === 'failed') {
                        // Clear polling
                        if (updatePollIntervalRef.current[doc.document_id]) {
                            clearInterval(updatePollIntervalRef.current[doc.document_id]);
                            delete updatePollIntervalRef.current[doc.document_id];
                        }
                        
                        setUpdatingId(null);
                        toast.error(`Update failed: ${progressData.error}`);
                    }
                } catch (err) {
                    console.error('Error polling update progress:', err);
                }
            };
            
            // Start polling
            updatePollIntervalRef.current[doc.document_id] = setInterval(pollUpdateProgress, 500);
            pollUpdateProgress(); // Initial poll
            
        } catch (err) {
            setUpdatingId(null);
            const errorMsg = err instanceof Error ? err.message : 'Failed to update document';
            toast.error(errorMsg);
        } finally {
            // Reset file input
            event.target.value = '';
        }
    };

    const handleView = async (doc: Document) => {
        setViewingDoc(doc);
        setLoadingChunks(true);
        try {
            const docChunks = await api.getDocumentChunks(doc.document_id);
            setChunks(docChunks);
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to load document content';
            toast.error(errorMsg);
            setViewingDoc(null);
        } finally {
            setLoadingChunks(false);
        }
    };

    const closeModal = () => {
        setViewingDoc(null);
        setChunks([]);
    };

    const filteredDocuments = documents.filter(doc =>
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const totalChunks = documents.reduce((sum, doc) => sum + doc.chunks, 0);

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading documents...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <div className="flex items-start gap-3">
                    <svg className="w-6 h-6 text-red-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                        <h3 className="text-sm font-medium text-red-800">Error loading documents</h3>
                        <p className="text-sm text-red-600 mt-1">{error}</p>
                        <button
                            onClick={loadDocuments}
                            className="mt-3 px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-orange-100 rounded-lg">
                            <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">Total Documents</p>
                            <p className="text-2xl font-bold text-gray-900">{documents.length}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-blue-100 rounded-lg">
                            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                            </svg>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">Total Chunks</p>
                            <p className="text-2xl font-bold text-gray-900">{totalChunks}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-green-100 rounded-lg">
                            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">Avg Chunks/Doc</p>
                            <p className="text-2xl font-bold text-gray-900">
                                {documents.length > 0 ? Math.round(totalChunks / documents.length) : 0}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Search and Actions */}
            <div className="flex items-center justify-between gap-4">
                <div className="flex-1 relative">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search documents..."
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    />
                    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <button
                    onClick={() => setShowUpload(true)}
                    className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Upload Document
                </button>
                <button
                    onClick={loadDocuments}
                    className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh
                </button>
            </div>

            {/* Documents Table */}
            {filteredDocuments.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
                        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {searchQuery ? 'No documents found' : 'No documents yet'}
                    </h3>
                    <p className="text-sm text-gray-500 mb-4">
                        {searchQuery 
                            ? `No documents match "${searchQuery}"`
                            : 'Upload documents to get started with the RAG system'}
                    </p>
                    {!searchQuery && (
                        <button
                            onClick={() => setShowUpload(true)}
                            className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition inline-flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            Upload Your First Document
                        </button>
                    )}
                </div>
            ) : (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Document
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Document ID
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Chunks
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Upload Date
                                </th>
                                <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filteredDocuments.map((doc) => (
                                <React.Fragment key={doc.document_id}>
                                <tr className="hover:bg-gray-50 transition">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="flex-shrink-0 w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                                                <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                </svg>
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <p className="text-sm font-medium text-gray-900 truncate">
                                                    {doc.filename}
                                                </p>
                                                <p className="text-xs text-gray-500">
                                                    {doc.filename.endsWith('.pdf') 
                                                        ? 'PDF Document' 
                                                        : doc.filename.endsWith('.json')
                                                        ? 'JSON Data'
                                                        : doc.filename.endsWith('.csv')
                                                        ? 'CSV Data'
                                                        : 'Text Document'}
                                                </p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600">
                                            {doc.document_id.slice(0, 12)}...
                                        </code>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                            {doc.chunks} chunks
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <p className="text-sm text-gray-500">
                                            {new Date(doc.upload_date).toLocaleDateString()}
                                        </p>
                                        <p className="text-xs text-gray-400">
                                            {new Date(doc.upload_date).toLocaleTimeString()}
                                        </p>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            {/* Hidden file input for update */}
                                            <input
                                                type="file"
                                                ref={(el) => { fileInputRef.current[doc.document_id] = el; }}
                                                accept=".pdf,.txt,.text,.json,.csv"
                                                onChange={(e) => handleFileSelect(doc, e)}
                                                className="hidden"
                                            />
                                            
                                            <button
                                                onClick={() => handleView(doc)}
                                                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 transition"
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                </svg>
                                                View
                                            </button>
                                            
                                            <button
                                                onClick={() => handleUpdateClick(doc.document_id)}
                                                disabled={updatingId === doc.document_id || deletingId === doc.document_id}
                                                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-green-700 bg-green-50 rounded-lg hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
                                            >
                                                {updatingId === doc.document_id ? (
                                                    <>
                                                        <div className="w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin" />
                                                        Updating...
                                                    </>
                                                ) : (
                                                    <>
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                        </svg>
                                                        Update
                                                    </>
                                                )}
                                            </button>
                                            
                                            <button
                                                onClick={() => handleDelete(doc)}
                                                disabled={deletingId === doc.document_id || updatingId === doc.document_id}
                                                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
                                            >
                                                {deletingId === doc.document_id ? (
                                                    <>
                                                        <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
                                                        Deleting...
                                                    </>
                                                ) : (
                                                    <>
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                        </svg>
                                                        Delete
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                                {/* Update Progress Row */}
                                {updatingId === doc.document_id && updateProgress[doc.document_id] && (
                                    <tr key={`${doc.document_id}-progress`}>
                                        <td colSpan={5} className="px-6 py-3 bg-green-50">
                                            <div className="space-y-2">
                                                <div className="flex items-center justify-between text-sm">
                                                    <span className="text-green-700 font-medium">
                                                        {updateProgress[doc.document_id].message || 'Updating...'}
                                                    </span>
                                                    <span className="text-green-600 font-semibold">
                                                        {updateProgress[doc.document_id].progress || 0}%
                                                    </span>
                                                </div>
                                                <div className="w-full bg-green-200 rounded-full h-2 overflow-hidden">
                                                    <div 
                                                        className="bg-green-600 h-full transition-all duration-300 ease-out"
                                                        style={{ width: `${updateProgress[doc.document_id].progress || 0}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                                </React.Fragment>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* View Document Modal */}
            {viewingDoc && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">
                                    {viewingDoc.filename}
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    {viewingDoc.chunks} chunks • Document ID: {viewingDoc.document_id.slice(0, 12)}...
                                </p>
                            </div>
                            <button
                                onClick={closeModal}
                                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="flex-1 overflow-y-auto px-6 py-4">
                            {loadingChunks ? (
                                <div className="flex items-center justify-center p-12">
                                    <div className="text-center">
                                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                                        <p className="mt-4 text-gray-600">Loading document content...</p>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    {chunks.length > 0 && chunks[0].chunk_id.startsWith('_chunk') && (
                                        <div className="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                                            <div className="flex items-start gap-2">
                                                <svg className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                                </svg>
                                                <div className="text-sm">
                                                    <p className="font-medium text-yellow-800">Old Document Format</p>
                                                    <p className="text-yellow-700 mt-1">
                                                        This document was uploaded with an older version. Consider deleting and re-uploading for better formatting and complete chunk IDs.
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                    <div className="space-y-4">
                                    {chunks.map((chunk) => (
                                        <div
                                            key={chunk.chunk_id}
                                            className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-orange-300 transition"
                                        >
                                            <div className="flex items-center justify-between mb-3">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                                                        Chunk {chunk.chunk_number + 1} of {chunk.metadata.total_chunks}
                                                    </span>
                                                    {/* Chunk type badge */}
                                                    {chunk.metadata.chunk_type && (
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                                            chunk.metadata.chunk_type === 'sop_procedure'   ? 'bg-blue-100 text-blue-800' :
                                                            chunk.metadata.chunk_type === 'matrix_row'      ? 'bg-purple-100 text-purple-800' :
                                                            chunk.metadata.chunk_type === 'image_reference' ? 'bg-pink-100 text-pink-800' :
                                                            chunk.metadata.chunk_type === 'structured_chunk'? 'bg-teal-100 text-teal-800' :
                                                            'bg-gray-100 text-gray-600'
                                                        }`}>
                                                            {chunk.metadata.chunk_type.replace(/_/g, ' ')}
                                                        </span>
                                                    )}
                                                    {chunk.metadata.page && (
                                                        <span className="text-xs text-gray-500">
                                                            Page {chunk.metadata.page}
                                                        </span>
                                                    )}
                                                    <span className="text-xs text-gray-400">
                                                        {chunk.metadata.chunk_length} chars
                                                    </span>
                                                </div>
                                                <code 
                                                    className="text-xs bg-white px-2 py-1 rounded border border-gray-200 text-gray-600 max-w-xs truncate"
                                                    title={chunk.chunk_id}
                                                >
                                                    {chunk.chunk_id}
                                                </code>
                                            </div>
                                            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap break-words overflow-x-auto">
                                                {chunk.content}
                                            </p>
                                        </div>
                                    ))}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Modal Footer */}
                        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                            <button
                                onClick={closeModal}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Upload Document Modal */}
            {showUpload && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">
                                    Upload Document
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Upload PDF or TXT files to add to the knowledge base
                                </p>
                            </div>
                            <button
                                onClick={() => setShowUpload(false)}
                                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="px-6 py-4">
                            <DocumentUpload 
                                onUploadSuccess={(response) => {
                                    setShowUpload(false);
                                    loadDocuments(); // Refresh the list
                                }}
                            />
                        </div>

                        {/* Modal Footer */}
                        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                            <button
                                onClick={() => setShowUpload(false)}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
