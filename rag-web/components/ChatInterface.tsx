'use client';

import { useState, useRef, useEffect } from 'react';
import { api, type QueryResponse } from '@/lib/api';

interface Message {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    sources?: QueryResponse['sources'];
    answerType?: string;
    retrievalMetadata?: any;
    timestamp: Date;
    rating?: number;
}

type AnswerType = 'default' | 'summary' | 'detailed' | 'bullet_points' | 'compare' | 'explain_simple';

export default function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [answerType, setAnswerType] = useState<AnswerType>('default');
    const [showSettings, setShowSettings] = useState(false);
    const [topK, setTopK] = useState(6);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Create a conversation session on mount
    useEffect(() => {
        const createSession = async () => {
            try {
                const session = await api.createConversationSession();
                setSessionId(session.session_id);
            } catch (error) {
                console.error('Failed to create session:', error);
            }
        };
        createSession();
    }, []);

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

        try {
            const response = await api.queryDocuments({
                question: input,
                top_k: topK,
                answer_type: answerType,
                session_id: sessionId || undefined
            });

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: response.answer,
                sources: response.sources,
                answerType: response.answer_type,
                retrievalMetadata: response.retrieval_metadata,
                timestamp: new Date(),
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

    const clearConversation = async () => {
        if (sessionId) {
            try {
                await api.clearConversationSession(sessionId);
                const newSession = await api.createConversationSession();
                setSessionId(newSession.session_id);
            } catch (error) {
                console.error('Failed to clear session:', error);
            }
        }
        setMessages([]);
    };

    const getScoreBadgeColor = (score: number) => {
        if (score >= 0.8) return 'bg-green-100 text-green-800';
        if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header with controls */}
            <div className="border-b p-4 bg-white">
                <div className="flex justify-between items-center mb-2">
                    <h2 className="text-lg font-semibold">Enhanced RAG Chat</h2>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setShowSettings(!showSettings)}
                            className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
                        >
                            ⚙️ Settings
                        </button>
                        <button
                            onClick={clearConversation}
                            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                        >
                            🗑️ Clear
                        </button>
                    </div>
                </div>

                {showSettings && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-3">
                        <div>
                            <label className="block text-sm font-medium mb-1">Answer Type:</label>
                            <select
                                value={answerType}
                                onChange={(e) => setAnswerType(e.target.value as AnswerType)}
                                className="w-full px-3 py-2 border rounded-lg text-sm"
                            >
                                <option value="default">Standard Q&A</option>
                                <option value="summary">Summary</option>
                                <option value="detailed">Detailed Explanation</option>
                                <option value="bullet_points">Key Points</option>
                                <option value="compare">Comparison</option>
                                <option value="explain_simple">Simple Explanation</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Chunks to Retrieve: {topK}</label>
                            <input
                                type="range"
                                min="3"
                                max="15"
                                value={topK}
                                onChange={(e) => setTopK(Number(e.target.value))}
                                className="w-full"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 mt-8">
                        <p className="text-lg font-semibold mb-2">🚀 Welcome to Enhanced RAG Chat!</p>
                        <p className="text-sm mb-4">Upload a document and start asking questions.</p>
                        <div className="text-left max-w-md mx-auto bg-blue-50 p-4 rounded-lg">
                            <p className="font-semibold text-blue-900 mb-2">✨ New Features:</p>
                            <ul className="text-xs text-blue-800 space-y-1">
                                <li>🔍 Hybrid search (Vector + Keyword)</li>
                                <li>🎯 AI-powered reranking</li>
                                <li>💬 Conversation history</li>
                                <li>📊 Multiple answer types</li>
                                <li>⭐ Rate responses</li>
                            </ul>
                        </div>
                    </div>
                )}

                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[85%] rounded-lg p-4 shadow-sm ${
                                message.type === 'user'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-white text-gray-900 border border-gray-200'
                            }`}
                        >
                            <p className="whitespace-pre-wrap">{message.content}</p>

                            {message.retrievalMetadata && (
                                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                                    {message.retrievalMetadata.hybrid_search_used && (
                                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                                            🔍 Hybrid Search
                                        </span>
                                    )}
                                    {message.retrievalMetadata.reranking_used && (
                                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
                                            🎯 Reranked
                                        </span>
                                    )}
                                    {message.answerType && message.answerType !== 'default' && (
                                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                                            📋 {message.answerType.replace('_', ' ')}
                                        </span>
                                    )}
                                </div>
                            )}

                            {message.sources && message.sources.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-gray-200">
                                    <p className="text-xs font-semibold mb-2 text-gray-700">📚 Sources ({message.sources.length}):</p>
                                    <div className="space-y-2">
                                        {message.sources.map((source, idx) => (
                                            <div key={idx} className="text-xs bg-gray-50 p-2 rounded border border-gray-100">
                                                <div className="flex justify-between items-start mb-1">
                                                    <span className="font-medium text-gray-800">
                                                        {source.document}
                                                    </span>
                                                    <span className={`px-2 py-0.5 rounded text-xs ${getScoreBadgeColor(source.relevance_score)}`}>
                                                        {(source.relevance_score * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                                <div className="text-gray-600 mb-1">
                                                    Section {source.chunk} of {source.total_chunks} 
                                                    <span className="ml-2 text-gray-500">
                                                        ({source.position_percent.toFixed(0)}% through doc)
                                                    </span>
                                                </div>
                                                <p className="text-gray-700 italic mt-1 leading-relaxed">
                                                    "{source.content}"
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-between items-center mt-3 pt-2 border-t border-gray-200">
                                <p className="text-xs opacity-70">
                                    {message.timestamp.toLocaleTimeString()}
                                </p>
                                
                                {message.type === 'assistant' && (
                                    <div className="flex gap-1">
                                        {[1, 2, 3, 4, 5].map((star) => (
                                            <button
                                                key={star}
                                                onClick={() => handleRating(message.id, star)}
                                                className={`text-sm ${
                                                    message.rating && star <= message.rating
                                                        ? 'text-yellow-500'
                                                        : 'text-gray-300'
                                                } hover:text-yellow-400 transition-colors`}
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
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                            <div className="flex space-x-2">
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="border-t p-4 bg-white">
                <div className="flex space-x-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a question about your documents..."
                        disabled={loading}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                    >
                        {loading ? '⏳' : '📤'} Send
                    </button>
                </div>
            </form>
        </div>
    );
}
