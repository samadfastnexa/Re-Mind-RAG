'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api, auth, type QueryResponse, type User } from '@/lib/api';
import jsPDF from 'jspdf';
import FilterPanel from './FilterPanel';

interface Message {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    sources?: QueryResponse['sources'];
    structured_data?: Array<Record<string, any>>;
    answerType?: string;
    retrievalMetadata?: any;
    timestamp: Date;
    rating?: number;
    responseTime?: number;
    unanswerable?: boolean;
    ticketRaised?: boolean;
}

interface ConversationStorage {
    sessionId: string;
    title: string;
    messages: Message[];
    lastUpdated: string;
}

type AnswerType = 'default' | 'summary' | 'detailed' | 'bullet_points' | 'compare' | 'explain_simple';

const STORAGE_KEY = 'rag_conversations';
const MAX_STORED_CONVERSATIONS = 50;

export default function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [showHistory, setShowHistory] = useState(false);
    const [topK] = useState(8);
    const [activeFilters, setActiveFilters] = useState<Record<string, any>>({});
    const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [conversations, setConversations] = useState<ConversationStorage[]>([]);
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    // localStorage helpers
    const saveConversations = useCallback((convs: ConversationStorage[]) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
        } catch (error) {
            console.error('Failed to save conversations:', error);
        }
    }, []);

    const loadConversations = useCallback((): ConversationStorage[] => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Convert timestamp strings back to Date objects
                return parsed.map((conv: any) => ({
                    ...conv,
                    messages: conv.messages.map((msg: any) => ({
                        ...msg,
                        timestamp: new Date(msg.timestamp),
                    })),
                }));
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
        return [];
    }, []);

    const saveCurrentConversation = useCallback(() => {
        if (!sessionId || messages.length === 0) return;

        const allConvs = loadConversations();
        const title = messages.find(m => m.type === 'user')?.content.slice(0, 50) || 'New Conversation';
        
        const existingIndex = allConvs.findIndex(c => c.sessionId === sessionId);
        const updatedConv: ConversationStorage = {
            sessionId,
            title,
            messages,
            lastUpdated: new Date().toISOString(),
        };

        if (existingIndex >= 0) {
            allConvs[existingIndex] = updatedConv;
        } else {
            allConvs.unshift(updatedConv);
        }

        // Keep only last MAX_STORED_CONVERSATIONS
        const trimmed = allConvs.slice(0, MAX_STORED_CONVERSATIONS);
        saveConversations(trimmed);
        setConversations(trimmed);
    }, [sessionId, messages, loadConversations, saveConversations]);

    const loadConversation = useCallback((conv: ConversationStorage) => {
        setMessages(conv.messages);
        setSessionId(conv.sessionId);
        setShowHistory(false);
    }, []);

    const createNewSession = useCallback(async () => {
        try {
            const session = await api.createConversationSession();
            setSessionId(session.session_id);
        } catch (error) {
            console.error('Failed to create session:', error);
        }
    }, []);

    const deleteConversation = useCallback((convSessionId: string) => {
        // Check if user has permission to delete
        if (!currentUser?.can_delete_history) {
            toast.error('You do not have permission to delete conversation history.');
            return;
        }
        
        const allConvs = loadConversations().filter(c => c.sessionId !== convSessionId);
        saveConversations(allConvs);
        setConversations(allConvs);
        if (sessionId === convSessionId) {
            setMessages([]);
            createNewSession();
        }
    }, [sessionId, currentUser, loadConversations, saveConversations, createNewSession]);

    const clearConversation = async () => {
        if (sessionId) {
            try {
                await api.clearConversationSession(sessionId);
            } catch (error) {
                console.error('Failed to clear session:', error);
                // Continue anyway - clear local state
            }
        }
        setMessages([]);
        await createNewSession();
    };

    // Load conversations on mount
    useEffect(() => {
        const stored = loadConversations();
        setConversations(stored);
    }, [loadConversations]);

    // Fetch current user
    useEffect(() => {
        const fetchUser = async () => {
            if (!auth.isAuthenticated()) {
                return;
            }
            try {
                const user = await api.getCurrentUser();
                setCurrentUser(user);
            } catch (error) {
                console.error('Failed to fetch current user:', error);
                // Don't throw - parent component handles auth
            }
        };
        fetchUser();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Save messages to localStorage whenever they change
    useEffect(() => {
        if (messages.length > 0) {
            saveCurrentConversation();
        }
    }, [messages, saveCurrentConversation]);

    const copyToClipboard = useCallback(async (text: string, messageId: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedId(messageId);
            setTimeout(() => setCopiedId(null), 2000);
        } catch {
            console.error('Failed to copy');
        }
    }, []);

    const toggleSources = useCallback((messageId: string) => {
        setExpandedSources(prev => ({ ...prev, [messageId]: !prev[messageId] }));
    }, []);

    // Create a conversation session on mount
    useEffect(() => {
        createNewSession();
    }, [createNewSession]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            type: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        const startTime = Date.now();

        try {
            const response = await api.queryDocuments({
                question: input,
                top_k: topK,
                answer_type: 'default',
                filters: Object.keys(activeFilters).length > 0 ? activeFilters : undefined,
                return_structured: true,
                session_id: sessionId || undefined
            });

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: response.answer,
                sources: response.sources,
                structured_data: response.structured_data,
                answerType: response.answer_type,
                retrievalMetadata: response.retrieval_metadata,
                timestamp: new Date(),
                responseTime: ((Date.now() - startTime) / 1000),
                unanswerable: response.unanswerable || false,
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: error instanceof Error ? error.message : 'Failed to get response',
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    const handleRating = async (messageId: string, rating: number) => {
        // Update local state
        setMessages(prev => prev.map(msg => 
            msg.id === messageId ? { ...msg, rating } : msg
        ));

        // Submit feedback to backend
        const message = messages.find(m => m.id === messageId);
        if (message && message.type === 'assistant') {
            try {
                await api.submitFeedback({
                    session_id: sessionId || undefined,
                    question: messages[messages.findIndex(m => m.id === messageId) - 1]?.content || '',
                    answer: message.content,
                    rating
                });
            } catch (error) {
                console.error('Failed to submit feedback:', error);
            }
        }
    };

    const exportConversation = () => {
        if (!currentUser?.can_export) {
            toast.error('You do not have permission to export conversations');
            return;
        }

        try {
            const doc = new jsPDF();
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 15;
        const maxWidth = pageWidth - (margin * 2);
        let yPosition = 20;

        // Title
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text('RAG Chat Conversation', margin, yPosition);
        yPosition += 10;

        // Session info
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text(`Session ID: ${sessionId || 'N/A'}`, margin, yPosition);
        yPosition += 6;
        doc.text(`Exported: ${new Date().toLocaleString()}`, margin, yPosition);
        yPosition += 10;

        // Messages
        messages.forEach((message, index) => {
            // Check if we need a new page
            if (yPosition > pageHeight - 30) {
                doc.addPage();
                yPosition = 20;
            }

            // Message header
            doc.setFontSize(11);
            doc.setFont('helvetica', 'bold');
            if (message.type === 'user') {
                doc.setTextColor(255, 117, 22); // Orange
                doc.text('USER:', margin, yPosition);
            } else {
                doc.setTextColor(0, 0, 0);
                doc.text('ASSISTANT:', margin, yPosition);
            }
            yPosition += 6;

            // Message content
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(10);
            doc.setTextColor(0, 0, 0);
            
            // Split text to fit width
            const lines = doc.splitTextToSize(message.content, maxWidth);
            lines.forEach((line: string) => {
                if (yPosition > pageHeight - 20) {
                    doc.addPage();
                    yPosition = 20;
                }
                doc.text(line, margin, yPosition);
                yPosition += 5;
            });

            // Timestamp
            doc.setFontSize(8);
            doc.setTextColor(128, 128, 128);
            doc.text(message.timestamp.toLocaleString(), margin, yPosition);
            yPosition += 8;

            // Add spacing between messages
            yPosition += 5;
        });

        // Save PDF
        doc.save(`conversation-${sessionId || 'export'}-${Date.now()}.pdf`);
        toast.success('Conversation exported successfully');
        } catch (error) {
            console.error('Export failed:', error);
            toast.error('Failed to export conversation. Please try again.');
        }
    };

    return (
        <div className="flex h-full">
            {/* History Sidebar - Toggleable */}
            {showHistory && (
                <div className="w-80 border-r bg-white overflow-y-auto flex-shrink-0">
                    <div className="p-2 border-b bg-gray-50 sticky top-0 z-10">
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="font-semibold text-gray-900">Chat History</h3>
                            <button
                                onClick={() => setShowHistory(false)}
                                className="text-gray-400 hover:text-gray-700 transition"
                                title="Close sidebar"
                            >
                                ✕
                            </button>
                        </div>
                        <button
                            onClick={() => { clearConversation(); setShowHistory(false); }}
                            className="w-full px-3 py-2 text-sm bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-lg hover:from-orange-600 hover:to-orange-700 transition shadow-sm"
                        >
                            + New Chat
                        </button>
                    </div>
                    <div className="p-2">
                        {conversations.length === 0 ? (
                            <p className="text-center text-gray-400 text-sm py-8">No history yet</p>
                        ) : (
                            conversations.map((conv) => (
                                <div
                                    key={conv.sessionId}
                                    className={`group p-2.5 mb-2 rounded-lg cursor-pointer transition-all ${ 
                                        conv.sessionId === sessionId
                                            ? 'bg-orange-50 border border-orange-200'
                                            : 'hover:bg-gray-50 border border-transparent'
                                    }`}
                                >
                                    <div onClick={() => loadConversation(conv)}>
                                        <p className="text-sm font-medium text-gray-800 truncate mb-1">
                                            {conv.title}
                                        </p>
                                        <div className="flex items-center justify-between text-xs text-gray-500">
                                            <span>{conv.messages.length} messages</span>
                                            <span>{new Date(conv.lastUpdated).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    {currentUser?.can_delete_history && (
                                        <button
                                            onClick={(e) => { e.stopPropagation(); deleteConversation(conv.sessionId); }}
                                            className="text-xs text-red-600 opacity-0 group-hover:opacity-100 transition-opacity mt-2 hover:underline"
                                        >
                                            Delete
                                        </button>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* Main Chat Area */}
            <div className="flex flex-col flex-1">
            {/* Header with controls */}
            <div className="border-b p-2 bg-white">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setShowHistory(!showHistory)}
                            className="p-2 hover:bg-gray-100 rounded-lg transition"
                            title="Toggle history sidebar"
                        >
                            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                        <h2 className="text-lg font-semibold text-gray-900">Enhanced RAG Chat</h2>
                    </div>
                    <div className="flex gap-2">
                        {messages.length > 0 && currentUser?.can_export && (
                            <button
                                onClick={exportConversation}
                                className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                            >
                                💾 Export
                            </button>
                        )}
                        <button
                            onClick={clearConversation}
                            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                        >
                            🗑️ Clear
                        </button>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-2 space-y-3 bg-gray-50">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 py-8">
                        <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-full flex items-center justify-center mb-3 shadow-lg">
                            <span className="text-3xl">💬</span>
                        </div>
                        <p className="text-xl font-bold text-gray-800 mb-2">Welcome to RAG Chat</p>
                        <p className="text-sm text-gray-500 mb-6">Ask anything about your documents</p>
                        <div className="max-w-md text-center">
                            <p className="text-sm text-gray-600">Powered by hybrid search & AI reranking</p>
                        </div>
                    </div>
                )}

                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[92%] rounded-2xl p-3 shadow-sm ${
                                message.type === 'user'
                                    ? 'bg-gradient-to-br from-orange-500 to-orange-600 text-white'
                                    : 'bg-white text-gray-900 border border-gray-200'
                            }`}
                        >
                            {/* Message content with markdown rendering */}
                            {message.type === 'assistant' ? (
                                <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1.5 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-blockquote:border-l-orange-400 prose-blockquote:bg-orange-50 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded-r prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-orange-700 prose-code:text-xs prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-strong:text-gray-900 prose-table:text-sm prose-th:bg-gray-100 prose-th:p-2 prose-td:p-2 prose-td:border prose-th:border">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {message.content}
                                    </ReactMarkdown>
                                </div>
                            ) : (
                                <p className="whitespace-pre-wrap">{message.content}</p>
                            )}

                            {/* Metadata badges */}
                            {message.type === 'assistant' && (
                                <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
                                    {message.retrievalMetadata?.cache_hit && (
                                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium">
                                            ⚡ Instant (cached)
                                        </span>
                                    )}
                                    {message.retrievalMetadata?.cache_match_type === 'fuzzy' && (
                                        <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full font-medium">
                                            🔤 Typo-corrected ({((message.retrievalMetadata?.cache_match_score || 0) * 100).toFixed(0)}% match)
                                        </span>
                                    )}
                                    {!message.retrievalMetadata?.cache_hit && message.retrievalMetadata?.hybrid_search_used && (
                                        <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">
                                            🔍 Hybrid Search
                                        </span>
                                    )}
                                    {!message.retrievalMetadata?.cache_hit && message.retrievalMetadata?.reranking_used && (
                                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">
                                            🎯 Reranked
                                        </span>
                                    )}
                                    {message.answerType && message.answerType !== 'default' && (
                                        <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full font-medium">
                                            📋 {message.answerType.replace('_', ' ')}
                                        </span>
                                    )}
                                    {message.responseTime != null && (
                                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full font-medium">
                                            ⚡ {message.responseTime.toFixed(1)}s
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Collapsible sources */}
                            {message.sources && message.sources.length > 0 && (
                                <div className="mt-3">
                                    <button
                                        onClick={() => toggleSources(message.id)}
                                        className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-gray-800 transition-colors"
                                    >
                                        <span className={`transform transition-transform text-[10px] ${expandedSources[message.id] ? 'rotate-90' : ''}`}>▶</span>
                                        📚 Sources ({message.sources.length})
                                    </button>
                                    {expandedSources[message.id] && (
                                        <div className="mt-2 space-y-2">
                                            {message.sources.map((source, idx) => {
                                                const isExpanded = expandedSources[`${message.id}_src_${idx}`];
                                                const docName = (source.document || '').split(/[\\/]/).pop() || source.document || 'Unknown Document';
                                                const relevance = Math.round((source.relevance_score || 0) * 100);
                                                const relevanceColor = relevance >= 70
                                                    ? 'bg-green-100 text-green-700'
                                                    : relevance >= 40
                                                        ? 'bg-yellow-100 text-yellow-700'
                                                        : 'bg-red-50 text-red-600';
                                                const contentPreview = source.content.length > 250
                                                    ? source.content.slice(0, 250) + '…'
                                                    : source.content;
                                                return (
                                                    <div key={idx} className="text-xs rounded-lg border border-gray-200 overflow-hidden shadow-sm">
                                                        {/* Source header */}
                                                        <div className="flex items-center justify-between px-2.5 py-1.5 bg-white border-b border-gray-100">
                                                            <div className="flex items-center gap-2 min-w-0">
                                                                <span className="shrink-0 px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded font-bold text-[10px]">
                                                                    #{idx + 1}
                                                                </span>
                                                                <span className="truncate font-semibold text-gray-800 max-w-[200px]" title={docName}>
                                                                    {docName}
                                                                </span>
                                                            </div>
                                                            <div className="flex items-center gap-1.5 shrink-0 ml-2">
                                                                {relevance > 0 && (
                                                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${relevanceColor}`}>
                                                                        {relevance}% match
                                                                    </span>
                                                                )}
                                                                {source.total_chunks > 0 && (
                                                                    <span className="text-gray-400 text-[10px] whitespace-nowrap">
                                                                        chunk {source.chunk}/{source.total_chunks}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        {/* Location row: section + page */}
                                                        {(source.section_id || source.page || source.page_range) && (
                                                            <div className="flex items-center gap-2 px-2.5 py-1 bg-orange-50 border-b border-orange-100">
                                                                {source.section_id && (
                                                                    <span className="flex items-center gap-1 text-orange-700 font-semibold text-[10px]">
                                                                        § {source.section_id}
                                                                    </span>
                                                                )}
                                                                {(source.page || source.page_range) && (
                                                                    <span className="flex items-center gap-1 text-gray-500 text-[10px]">
                                                                        📄 p.{source.page_range ?? source.page}
                                                                    </span>
                                                                )}
                                                                {source.has_table && (
                                                                    <span className="text-blue-600 text-[10px] font-medium">📊 contains table</span>
                                                                )}
                                                            </div>
                                                        )}
                                                        {/* Source content */}
                                                        <div className="p-2.5 bg-gray-50">
                                                            <p className="text-gray-600 leading-relaxed border-l-2 border-orange-300 pl-2 italic whitespace-pre-wrap">
                                                                &ldquo;{isExpanded ? source.content : contentPreview}&rdquo;
                                                            </p>
                                                            {source.content.length > 250 && (
                                                                <button
                                                                    onClick={() => setExpandedSources(prev => ({
                                                                        ...prev,
                                                                        [`${message.id}_src_${idx}`]: !prev[`${message.id}_src_${idx}`],
                                                                    }))}
                                                                    className="mt-1.5 text-orange-600 hover:text-orange-800 text-[10px] font-semibold"
                                                                >
                                                                    {isExpanded ? '▲ Show less' : '▼ Show more'}
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            )}
                            {/* Structured Data Display */}
                            {message.structured_data && message.structured_data.length > 0 && (
                                <div className="mt-3">
                                    <button
                                        onClick={() => setExpandedSources(prev => ({...prev, [`${message.id}_structured`]: !prev[`${message.id}_structured`]}))}
                                        className="flex items-center gap-1 text-xs font-semibold text-gray-600 hover:text-gray-800 transition-colors"
                                    >
                                        <span className={`transform transition-transform ${expandedSources[`${message.id}_structured`] ? 'rotate-90' : ''}`}>▶</span>
                                        📊 Structured Data ({message.structured_data.length} items)
                                    </button>
                                    {expandedSources[`${message.id}_structured`] && (
                                        <div className="mt-2 space-y-2">
                                            {message.structured_data.map((item, idx) => (
                                                <div key={idx} className="text-xs bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded-lg border border-blue-200">
                                                    <div className="space-y-1">
                                                        {Object.entries(item).map(([key, value]) => (
                                                            <div key={key} className="flex gap-2">
                                                                <span className="font-semibold text-blue-700 min-w-[120px]">{key}:</span>
                                                                <span className="text-gray-700 flex-1">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                            {/* Ticket prompt for unanswerable queries */}
                            {message.type === 'assistant' && message.unanswerable && !message.ticketRaised && (
                                <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                                    <p className="text-sm font-medium text-amber-800 mb-2">🎫 Would you like to raise a ticket?</p>
                                    <p className="text-xs text-amber-600 mb-3">Our team will review your question and upload relevant documents.</p>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={async () => {
                                                try {
                                                    const userMsg = messages[messages.findIndex(m => m.id === message.id) - 1];
                                                    await api.createTicket(userMsg?.content || message.content, sessionId || undefined);
                                                    setMessages(prev => prev.map(m =>
                                                        m.id === message.id ? { ...m, ticketRaised: true, content: m.content + '\n\n✅ **Ticket raised successfully!** Our team will look into this.' } : m
                                                    ));
                                                } catch (err) {
                                                    console.error('Failed to create ticket:', err);
                                                }
                                            }}
                                            className="px-4 py-1.5 text-sm font-medium bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition shadow-sm"
                                        >
                                            ✅ Yes
                                        </button>
                                        <button
                                            onClick={() => {
                                                setMessages(prev => prev.map(m =>
                                                    m.id === message.id ? { ...m, ticketRaised: true } : m
                                                ));
                                            }}
                                            className="px-4 py-1.5 text-sm font-medium bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                                        >
                                            ❌ No
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Ticket raised confirmation */}
                            {message.type === 'assistant' && message.unanswerable && message.ticketRaised && (
                                <div className="mt-2">
                                    <span className="text-xs text-green-600 font-medium">🎫 Ticket handled</span>
                                </div>
                            )}

                            {/* Footer: timestamp, copy, rating */}
                            <div className="flex justify-between items-center mt-3 pt-2 border-t border-gray-100">
                                <p className="text-xs opacity-60">
                                    {message.timestamp.toLocaleTimeString()}
                                </p>

                                <div className="flex items-center gap-2">
                                    {/* Copy button */}
                                    {message.type === 'assistant' && (
                                        <button
                                            onClick={() => copyToClipboard(message.content, message.id)}
                                            className="text-xs px-2 py-0.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                                            title="Copy response"
                                        >
                                            {copiedId === message.id ? '✅ Copied' : '📋 Copy'}
                                        </button>
                                    )}

                                    {/* Star rating */}
                                    {message.type === 'assistant' && (
                                        <div className="flex gap-0.5">
                                            {[1, 2, 3, 4, 5].map((star) => (
                                                <button
                                                    key={star}
                                                    onClick={() => handleRating(message.id, star)}
                                                    className={`text-sm transition-all hover:scale-125 ${
                                                        message.rating && star <= message.rating
                                                            ? 'text-yellow-400'
                                                            : 'text-gray-300 hover:text-yellow-300'
                                                    }`}
                                                    title={`Rate ${star} stars`}
                                                >
                                                    ★
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-200">
                            <div className="flex items-center space-x-3">
                                <div className="flex space-x-1.5">
                                    <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{animationDelay: '0.15s'}}></div>
                                    <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{animationDelay: '0.3s'}}></div>
                                </div>
                                <span className="text-xs text-gray-400">Searching documents & generating response...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* FilterPanel */}
            <div className="border-t p-2 bg-gray-50">
                <FilterPanel 
                    onFiltersChange={setActiveFilters}
                    activeFilters={activeFilters}
                />
                
                {/* Active Filter Badges */}
                {Object.keys(activeFilters).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                        <span className="text-xs font-medium text-gray-600">Active Filters:</span>
                        {Object.entries(activeFilters).map(([key, value]) => (
                            <span 
                                key={key}
                                className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full flex items-center gap-1"
                            >
                                <strong>{key}:</strong>
                                {Array.isArray(value) ? value.join(', ') : String(value)}
                                <button
                                    onClick={() => {
                                        const newFilters = { ...activeFilters };
                                        delete newFilters[key];
                                        setActiveFilters(newFilters);
                                    }}
                                    className="ml-1 hover:text-blue-900"
                                >
                                    ×
                                </button>
                            </span>
                        ))}
                    </div>
                )}
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="border-t p-2 bg-white">
                <div className="flex space-x-2 items-end">
                    <div className="flex-1 relative">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey && input.trim() && !loading) {
                                    handleSubmit(e);
                                }
                            }}
                            placeholder="Ask a question about your documents..."
                            disabled={loading}
                            className="w-full px-3 py-2.5 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:opacity-50 text-sm"
                        />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none hidden sm:inline">
                            Enter ↵
                        </span>
                    </div>
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="px-4 py-2.5 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-xl hover:from-orange-600 hover:to-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm hover:shadow-md text-sm"
                    >
                        {loading ? (
                            <span className="flex items-center gap-1.5">
                                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Thinking
                            </span>
                        ) : 'Send'}
                    </button>
                </div>
                <p className="text-xs text-gray-400 mt-1.5 text-center">
                    {sessionId && <span>Session active • AI-powered search</span>}
                    {!sessionId && <span>Start a conversation</span>}
                </p>
            </form>            </div>        </div>
    );
}
