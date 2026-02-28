'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, type QueryLogEntry, type QueryStatsResponse } from '@/lib/api';

export default function QueryHistory() {
    const [queries, setQueries] = useState<QueryLogEntry[]>([]);
    const [stats, setStats] = useState<QueryStatsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterUser, setFilterUser] = useState('');
    const [selectedQuery, setSelectedQuery] = useState<QueryLogEntry | null>(null);
    const [page, setPage] = useState(0);
    const [total, setTotal] = useState(0);
    const PAGE_SIZE = 20;

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const [logRes, statsRes] = await Promise.all([
                api.getQueryLog(filterUser || undefined, PAGE_SIZE, page * PAGE_SIZE),
                api.getQueryStats(),
            ]);

            setQueries(logRes.queries);
            setTotal(logRes.total);
            setStats(statsRes);
        } catch (err) {
            console.error('Query history error:', err);
            setError(err instanceof Error ? err.message : 'Failed to load query history');
        } finally {
            setLoading(false);
        }
    }, [filterUser, page]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const totalPages = Math.ceil(total / PAGE_SIZE);

    const getRatingStars = (rating: number | null) => {
        if (rating === null) return <span className="text-gray-400 text-xs">No rating</span>;
        return (
            <span className="text-yellow-500">
                {'★'.repeat(rating)}
                {'☆'.repeat(5 - rating)}
            </span>
        );
    };

    const getAnswerTypeBadge = (type: string) => {
        const styles: Record<string, string> = {
            default: 'bg-gray-100 text-gray-700',
            summary: 'bg-blue-100 text-blue-700',
            detailed: 'bg-purple-100 text-purple-700',
            bullet_points: 'bg-green-100 text-green-700',
            compare: 'bg-orange-100 text-orange-700',
            explain_simple: 'bg-pink-100 text-pink-700',
        };
        return (
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[type] || styles.default}`}>
                {type.replace('_', ' ')}
            </span>
        );
    };

    const formatTime = (ts: string) => {
        const d = new Date(ts);
        return d.toLocaleString();
    };

    return (
        <div className="space-y-6">
            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Total Queries</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total_queries}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Unique Users</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.unique_users}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Avg Rating</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">
                            {stats.avg_rating !== null ? `${stats.avg_rating} ★` : '—'}
                        </p>
                        <p className="text-xs text-gray-400">{stats.rated_queries} rated</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Top Answer Type</p>
                        <p className="text-lg font-bold text-gray-900 mt-1">
                            {stats.queries_by_type && Object.keys(stats.queries_by_type).length > 0
                                ? Object.entries(stats.queries_by_type).sort((a, b) => b[1] - a[1])[0][0].replace('_', ' ')
                                : '—'}
                        </p>
                    </div>
                </div>
            )}

            {/* Queries by User mini chart */}
            {stats && stats.queries_by_user && Object.keys(stats.queries_by_user).length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Queries by User</h3>
                    <div className="space-y-2">
                        {Object.entries(stats.queries_by_user)
                            .sort((a, b) => b[1] - a[1])
                            .map(([user, count]) => {
                                const maxCount = Math.max(...Object.values(stats.queries_by_user));
                                const pct = (count / maxCount) * 100;
                                return (
                                    <div key={user} className="flex items-center gap-3">
                                        <span className="text-sm font-medium text-gray-700 w-24 truncate">{user}</span>
                                        <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                                            <div
                                                className="bg-blue-500 h-full rounded-full transition-all flex items-center justify-end pr-2"
                                                style={{ width: `${Math.max(pct, 10)}%` }}
                                            >
                                                <span className="text-xs text-white font-semibold">{count}</span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => { setFilterUser(user); setPage(0); }}
                                            className="text-xs text-blue-600 hover:underline whitespace-nowrap"
                                        >
                                            Filter
                                        </button>
                                    </div>
                                );
                            })}
                    </div>
                </div>
            )}

            {/* Filter bar */}
            <div className="flex items-center gap-3">
                <div className="flex-1 relative">
                    <input
                        type="text"
                        value={filterUser}
                        onChange={(e) => { setFilterUser(e.target.value); setPage(0); }}
                        placeholder="Filter by username..."
                        className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
                </div>
                {filterUser && (
                    <button
                        onClick={() => { setFilterUser(''); setPage(0); }}
                        className="px-3 py-2 text-sm bg-gray-100 rounded-lg hover:bg-gray-200"
                    >
                        Clear filter
                    </button>
                )}
                <button
                    onClick={loadData}
                    className="px-3 py-2 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
                >
                    🔄 Refresh
                </button>
                <span className="text-sm text-gray-500">
                    {total} {total === 1 ? 'query' : 'queries'}
                    {filterUser && ` from "${filterUser}"`}
                </span>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : queries.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                    <p className="text-lg mb-1">No queries yet</p>
                    <p className="text-sm">User queries will appear here once they start using the chatbot.</p>
                </div>
            ) : (
                <>
                    {/* Query table */}
                    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600">User</th>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600">Question</th>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600">Sources</th>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600">Rating</th>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600">Time</th>
                                    <th className="text-left px-4 py-3 font-medium text-gray-600"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {queries.map((q) => (
                                    <tr key={q.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-4 py-3">
                                            <span className="inline-flex items-center gap-1.5">
                                                <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">
                                                    {q.user_id.charAt(0).toUpperCase()}
                                                </span>
                                                <span className="font-medium text-gray-800">{q.user_id}</span>
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 max-w-xs">
                                            <p className="truncate text-gray-800" title={q.question}>
                                                {q.question}
                                            </p>
                                        </td>
                                        <td className="px-4 py-3">{getAnswerTypeBadge(q.answer_type)}</td>
                                        <td className="px-4 py-3 text-gray-600">{q.sources_count}</td>
                                        <td className="px-4 py-3">{getRatingStars(q.rating)}</td>
                                        <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                                            {formatTime(q.timestamp)}
                                        </td>
                                        <td className="px-4 py-3">
                                            <button
                                                onClick={() => setSelectedQuery(selectedQuery?.id === q.id ? null : q)}
                                                className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                                            >
                                                {selectedQuery?.id === q.id ? 'Hide' : 'View'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between">
                            <button
                                onClick={() => setPage(p => Math.max(0, p - 1))}
                                disabled={page === 0}
                                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
                            >
                                ← Previous
                            </button>
                            <span className="text-sm text-gray-600">
                                Page {page + 1} of {totalPages}
                            </span>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                                disabled={page >= totalPages - 1}
                                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </>
            )}

            {/* Selected query detail modal */}
            {selectedQuery && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedQuery(null)}>
                    <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 rounded-t-2xl flex justify-between items-start">
                            <div>
                                <h3 className="font-bold text-gray-900">Query Detail</h3>
                                <p className="text-xs text-gray-500 mt-0.5">
                                    {selectedQuery.user_id} • {formatTime(selectedQuery.timestamp)}
                                </p>
                            </div>
                            <button onClick={() => setSelectedQuery(null)} className="text-gray-400 hover:text-gray-700 text-xl leading-none">×</button>
                        </div>
                        <div className="px-6 py-4 space-y-4">
                            {/* Question */}
                            <div>
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Question</label>
                                <div className="mt-1 p-3 bg-blue-50 rounded-lg text-sm text-gray-800">
                                    {selectedQuery.question}
                                </div>
                            </div>

                            {/* Answer */}
                            <div>
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Answer</label>
                                <div className="mt-1 p-3 bg-gray-50 rounded-lg text-sm text-gray-800 whitespace-pre-wrap max-h-64 overflow-y-auto">
                                    {selectedQuery.answer}
                                </div>
                            </div>

                            {/* Metadata */}
                            <div className="flex flex-wrap gap-3 text-sm">
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500">Type:</span>
                                    {getAnswerTypeBadge(selectedQuery.answer_type)}
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500">Sources:</span>
                                    <span className="font-medium">{selectedQuery.sources_count}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500">Rating:</span>
                                    {getRatingStars(selectedQuery.rating)}
                                </div>
                            </div>

                            {selectedQuery.feedback_text && (
                                <div>
                                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">User Feedback</label>
                                    <div className="mt-1 p-3 bg-yellow-50 rounded-lg text-sm text-gray-800">
                                        {selectedQuery.feedback_text}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
