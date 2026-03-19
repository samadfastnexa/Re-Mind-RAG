'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { api, type UploadResponse, type UploadProgress } from '@/lib/api';

interface DocumentUploadProps {
    onUploadSuccess?: (response: UploadProgress) => void;
}

export default function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
    const [uploading, setUploading] = useState(false);
    const [dragActive, setDragActive] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [progress, setProgress] = useState<UploadProgress | null>(null);
    const [processingMode, setProcessingMode] = useState<string>('hybrid');
    const [autoSelectedMode, setAutoSelectedMode] = useState<boolean>(false);
    const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
    const uploadIdRef = useRef<string | null>(null);
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const pollCountRef = useRef<number>(0);

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearTimeout(pollIntervalRef.current);
            }
        };
    }, []);

    const pollProgress = useCallback(async (uploadId: string) => {
        try {
            const progressData = await api.getUploadProgress(uploadId);
            setProgress(progressData);
            pollCountRef.current += 1;

            if (progressData.status === 'completed') {
                const successMsg = `Successfully uploaded ${progressData.filename} (${progressData.chunks} chunks, ${progressData.pages} pages)`;
                setSuccess(successMsg);
                toast.success(successMsg);
                setUploading(false);
                if (pollIntervalRef.current) {
                    clearTimeout(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
                onUploadSuccess?.(progressData);
            } else if (progressData.status === 'failed') {
                const errorMsg = progressData.error || 'Upload failed';
                setError(errorMsg);
                toast.error(errorMsg);
                setUploading(false);
                if (pollIntervalRef.current) {
                    clearTimeout(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
            }
        } catch (err) {
            console.error('Error polling progress:', err);
        }
    }, [onUploadSuccess]);

    const getModeForFile = useCallback((file: File): string => {
        const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
        if (ext === '.pdf') return 'hybrid';
        if (ext === '.txt' || ext === '.text') return 'text';
        return 'hybrid';
    }, []);

    const handleFile = useCallback(async (file: File) => {
        // Auto-select processing mode based on file type
        const autoMode = getModeForFile(file);
        setProcessingMode(autoMode);
        setAutoSelectedMode(true);
        setSelectedFileName(file.name);

        console.log('Uploading file:', { name: file.name, type: file.type, size: file.size, processingMode: autoMode });
        
        // Validate file type
        const validTypes = ['application/pdf', 'text/plain', 'application/json', 'text/csv'];
        const validExtensions = ['.pdf', '.txt', '.text', '.json', '.csv'];
        const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
        
        console.log('File validation:', { fileExtension, fileType: file.type, validType: validTypes.includes(file.type), validExt: validExtensions.includes(fileExtension) });
        
        if (!validTypes.includes(file.type) && !validExtensions.includes(fileExtension)) {
            const errorMsg = 'Only PDF, TXT, JSON, and CSV files are supported';
            setError(errorMsg);
            toast.error(errorMsg);
            return;
        }

        // Validate file size (50MB)
        if (file.size > 50 * 1024 * 1024) {
            const errorMsg = 'File size must be less than 50MB';
            setError(errorMsg);
            toast.error(errorMsg);
            return;
        }

        setUploading(true);
        setError(null);
        setSuccess(null);
        pollCountRef.current = 0;
        setProgress(null);

        try {
            const response = await api.uploadDocument(file, autoMode);
            
            if (response.upload_id) {
                // Start polling for progress
                uploadIdRef.current = response.upload_id;
                setProgress({
                    status: 'uploading',
                    progress: 2,
                    message: 'Initializing upload...',
                    filename: response.filename
                });
                
                // Poll aggressively initially (every 300ms), then slow down
                const pollWithAdaptiveInterval = () => {
                    if (uploadIdRef.current) {
                        pollProgress(uploadIdRef.current);
                        
                        // Adjust polling interval based on number of polls
                        // First 8 polls: 300ms, then 500ms
                        const interval = pollCountRef.current < 8 ? 300 : 500;
                        
                        pollIntervalRef.current = setTimeout(pollWithAdaptiveInterval, interval);
                    }
                };
                
                // Start first poll after brief delay to let backend initialize
                setTimeout(pollWithAdaptiveInterval, 100);
            } else {
                // Old API response without progress tracking
                setSuccess(`Successfully uploaded ${response.filename} (${response.chunks} chunks)`);
                setUploading(false);
                onUploadSuccess?.(response as any);
            }
        } catch (err) {
            console.error('Upload error caught:', err);
            const errorMessage = err instanceof Error ? err.message : 'Upload failed';
            console.error('Error message:', errorMessage);
            setError(errorMessage);
            toast.error(errorMessage);
            setUploading(false);
            setProgress(null);
            // Clear polling interval on error
            if (pollIntervalRef.current) {
                clearTimeout(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        }
    }, [onUploadSuccess, pollProgress, getModeForFile]);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    }, [handleFile]);

    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    }, [handleFile]);

    return (
        <div className="w-full">
            {/* Processing Mode Selector */}
            <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                        Processing Mode
                    </label>
                    {autoSelectedMode && selectedFileName && (
                        <span className="inline-flex items-center gap-1 text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-medium">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Auto-selected for {selectedFileName.split('.').pop()?.toUpperCase()}
                        </span>
                    )}
                </div>
                <select
                    value={processingMode}
                    onChange={(e) => { setProcessingMode(e.target.value); setAutoSelectedMode(false); }}
                    disabled={uploading}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                    <option value="hybrid">🔀 Hybrid (PDFs, Manuals, SOPs)</option>
                    <option value="text">📄 Text (Narrative Reports)</option>
                </select>
                <p className="mt-1.5 text-xs text-gray-500">
                    {processingMode === 'hybrid' && '✅ Recommended for PDFs — keeps procedures & tables intact with SOP-aware chunking'}
                    {processingMode === 'text' && 'Optimized for narrative essays, reports, and plain-text content'}
                </p>
            </div>

            <form
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className="relative"
            >
                <input
                    type="file"
                    id="file-upload"
                    accept=".pdf,.txt,.text,.json,.csv,application/pdf,text/plain,application/json,text/csv"
                    onChange={handleChange}
                    disabled={uploading}
                    className="hidden"
                />
                <label
                    htmlFor="file-upload"
                    className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${dragActive
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
                        } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <svg
                            className="w-10 h-10 mb-3 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                            />
                        </svg>
                        <p className="mb-2 text-sm text-gray-500">
                            {uploading ? (
                                <span className="font-semibold">Processing...</span>
                            ) : (
                                <>
                                    <span className="font-semibold">Click to upload</span> or drag and drop
                                </>
                            )}
                        </p>
                        <p className="text-xs text-gray-500">PDF, TXT, JSON, or CSV (MAX. 50MB)</p>
                    </div>
                </label>
            </form>

            {/* Progress bar */}
            {progress && uploading && (
                <div className={`mt-4 p-4 border rounded-lg ${
                    progress.status === 'completed' ? 'bg-green-50 border-green-200' :
                    progress.status === 'failed' ? 'bg-red-50 border-red-200' :
                    progress.status === 'vectorizing' ? 'bg-purple-50 border-purple-200' :
                    'bg-blue-50 border-blue-200'
                }`}>
                    <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            {progress.status === 'vectorizing' && (
                                <svg className="animate-spin h-4 w-4 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            )}
                            {progress.status === 'processing' && (
                                <svg className="animate-pulse h-4 w-4 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            )}
                            <span className={`text-sm font-medium ${
                                progress.status === 'completed' ? 'text-green-700' :
                                progress.status === 'failed' ? 'text-red-700' :
                                progress.status === 'vectorizing' ? 'text-purple-700' :
                                'text-blue-700'
                            }`}>{progress.message}</span>
                        </div>
                        <span className={`text-sm font-semibold ${
                            progress.status === 'completed' ? 'text-green-700' :
                            progress.status === 'failed' ? 'text-red-700' :
                            progress.status === 'vectorizing' ? 'text-purple-700' :
                            'text-blue-700'
                        }`}>{Math.round(progress.progress)}%</span>
                    </div>
                    <div className={`w-full rounded-full h-2.5 ${
                        progress.status === 'completed' ? 'bg-green-200' :
                        progress.status === 'failed' ? 'bg-red-200' :
                        progress.status === 'vectorizing' ? 'bg-purple-200' :
                        'bg-blue-200'
                    }`}>
                        <div 
                            className={`h-2.5 rounded-full transition-all duration-500 ease-out ${
                                progress.status === 'completed' ? 'bg-green-600' :
                                progress.status === 'failed' ? 'bg-red-600' :
                                progress.status === 'vectorizing' ? 'bg-purple-600' :
                                'bg-blue-600'
                            }`}
                            style={{ width: `${progress.progress}%` }}
                        ></div>
                    </div>
                    {progress.filename && (
                        <p className={`mt-2 text-xs ${
                            progress.status === 'completed' ? 'text-green-600' :
                            progress.status === 'failed' ? 'text-red-600' :
                            progress.status === 'vectorizing' ? 'text-purple-600' :
                            'text-blue-600'
                        }`}>
                            File: {progress.filename}
                        </p>
                    )}
                </div>
            )}

            {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{error}</p>
                </div>
            )}

            {success && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-600">{success}</p>
                </div>
            )}
        </div>
    );
}
