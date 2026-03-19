'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, type TicketResponse, type TicketStatsResponse } from '@/lib/api';

export default function TicketManagement() {
    const [tickets, setTickets] = useState<TicketResponse[]>([]);
    const [stats, setStats] = useState<TicketStatsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterStatus, setFilterStatus] = useState<string>('');
    const [selectedTicket, setSelectedTicket] = useState<TicketResponse | null>(null);
    const [adminNotes, setAdminNotes] = useState('');
    const [updatingId, setUpdatingId] = useState<string | null>(null);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const [ticketRes, statsRes] = await Promise.all([
                api.getTickets(filterStatus || undefined),
                api.getTicketStats(),
            ]);

            setTickets(ticketRes.tickets);
            setStats(statsRes);
        } catch (err) {
            console.error('Ticket load error:', err);
            setError(err instanceof Error ? err.message : 'Failed to load tickets');
        } finally {
            setLoading(false);
        }
    }, [filterStatus]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleStatusUpdate = async (ticketId: string, newStatus: string) => {
        try {
            setUpdatingId(ticketId);
            await api.updateTicket(ticketId, newStatus, adminNotes || undefined);
            setAdminNotes('');
            setSelectedTicket(null);
            await loadData();
        } catch (err) {
            console.error('Failed to update ticket:', err);
        } finally {
            setUpdatingId(null);
        }
    };

    const getStatusBadge = (status: string) => {
        const styles: Record<string, string> = {
            open: 'bg-red-100 text-red-700 border-red-200',
            in_progress: 'bg-yellow-100 text-yellow-700 border-yellow-200',
            resolved: 'bg-green-100 text-green-700 border-green-200',
            closed: 'bg-gray-100 text-gray-600 border-gray-200',
        };
        return (
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[status] || styles.open}`}>
                {status.replace('_', ' ')}
            </span>
        );
    };

    const formatTime = (ts: string) => new Date(ts).toLocaleString();

    return (
        <div className="space-y-6">
            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Total Tickets</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total_tickets}</p>
                    </div>
                    <div className="bg-red-50 rounded-xl border border-red-200 p-4">
                        <p className="text-xs text-red-600 uppercase tracking-wide font-semibold">🔴 Open</p>
                        <p className="text-2xl font-bold text-red-700 mt-1">{stats.open_tickets}</p>
                    </div>
                    <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-4">
                        <p className="text-xs text-yellow-600 uppercase tracking-wide font-semibold">🟡 In Progress</p>
                        <p className="text-2xl font-bold text-yellow-700 mt-1">{stats.in_progress_tickets}</p>
                    </div>
                    <div className="bg-green-50 rounded-xl border border-green-200 p-4">
                        <p className="text-xs text-green-600 uppercase tracking-wide font-semibold">✅ Resolved</p>
                        <p className="text-2xl font-bold text-green-700 mt-1">{stats.resolved_tickets}</p>
                    </div>
                </div>
            )}

            {/* Filter */}
            <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Filter by status:</label>
                <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                >
                    <option value="">All</option>
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                </select>
                <button
                    onClick={loadData}
                    className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition"
                >
                    🔄 Refresh
                </button>
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
                    {error}
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
                </div>
            )}

            {/* Ticket List */}
            {!loading && tickets.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                    <p className="text-4xl mb-2">🎫</p>
                    <p className="font-medium">No tickets found</p>
                    <p className="text-sm">Tickets are created when users can&apos;t find answers</p>
                </div>
            )}

            {!loading && tickets.length > 0 && (
                <div className="space-y-3">
                    {tickets.map((ticket) => (
                        <div
                            key={ticket.id}
                            className={`bg-white rounded-xl border p-4 transition-all cursor-pointer hover:shadow-md ${
                                selectedTicket?.id === ticket.id ? 'border-orange-400 shadow-md' : 'border-gray-200'
                            }`}
                            onClick={() => setSelectedTicket(selectedTicket?.id === ticket.id ? null : ticket)}
                        >
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 mb-1 break-words">
                                        &ldquo;{ticket.question}&rdquo;
                                    </p>
                                    <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                                        <span>👤 {ticket.user_id}</span>
                                        <span>•</span>
                                        <span>📅 {formatTime(ticket.created_at)}</span>
                                        {ticket.resolved_at && (
                                            <>
                                                <span>•</span>
                                                <span>✅ Resolved: {formatTime(ticket.resolved_at)}</span>
                                            </>
                                        )}
                                    </div>
                                </div>
                                <div className="flex-shrink-0">
                                    {getStatusBadge(ticket.status)}
                                </div>
                            </div>

                            {/* Expanded details */}
                            {selectedTicket?.id === ticket.id && (
                                <div className="mt-4 pt-4 border-t border-gray-100">
                                    {ticket.admin_notes && (
                                        <div className="mb-3 p-2 bg-blue-50 rounded-lg text-xs text-blue-700">
                                            <span className="font-semibold">Admin notes:</span> {ticket.admin_notes}
                                        </div>
                                    )}
                                    
                                    <div className="flex flex-col gap-2">
                                        <input
                                            type="text"
                                            value={adminNotes}
                                            onChange={(e) => setAdminNotes(e.target.value)}
                                            placeholder="Add admin notes (optional)..."
                                            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                        <div className="flex gap-2">
                                            {ticket.status !== 'in_progress' && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleStatusUpdate(ticket.id, 'in_progress'); }}
                                                    disabled={updatingId === ticket.id}
                                                    className="px-3 py-1.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition disabled:opacity-50"
                                                >
                                                    🟡 Mark In Progress
                                                </button>
                                            )}
                                            {ticket.status !== 'resolved' && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleStatusUpdate(ticket.id, 'resolved'); }}
                                                    disabled={updatingId === ticket.id}
                                                    className="px-3 py-1.5 text-xs font-medium bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition disabled:opacity-50"
                                                >
                                                    ✅ Resolve
                                                </button>
                                            )}
                                            {ticket.status !== 'closed' && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleStatusUpdate(ticket.id, 'closed'); }}
                                                    disabled={updatingId === ticket.id}
                                                    className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition disabled:opacity-50"
                                                >
                                                    ✖ Close
                                                </button>
                                            )}
                                            {ticket.status === 'closed' && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleStatusUpdate(ticket.id, 'open'); }}
                                                    disabled={updatingId === ticket.id}
                                                    className="px-3 py-1.5 text-xs font-medium bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition disabled:opacity-50"
                                                >
                                                    🔄 Reopen
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
