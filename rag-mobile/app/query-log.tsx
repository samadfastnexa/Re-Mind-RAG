import { useState, useEffect } from 'react';
import { StyleSheet, View, Text, ScrollView, ActivityIndicator, RefreshControl } from 'react-native';
import { ragApi, type QueryLogEntry } from '../services/api';

export default function QueryLogScreen() {
    const [queries, setQueries] = useState<QueryLogEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        loadQueries();
    }, []);

    const loadQueries = async () => {
        try {
            setLoading(true);
            const result = await ragApi.getQueryLog(undefined, 50, 0);
            setQueries(result.queries || []);
            setTotal(result.total || 0);
        } catch (error) {
            console.error('Failed to load queries:', error);
        } finally {
            setLoading(false);
        }
    };

    const onRefresh = async () => {
        setRefreshing(true);
        await loadQueries();
        setRefreshing(false);
    };

    const getRatingStars = (rating: number | null) => {
        if (rating === null) return '⭐ No rating';
        return '⭐'.repeat(rating);
    };

    const formatDate = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#3B82F6" />
                <Text style={styles.loadingText}>Loading queries...</Text>
            </View>
        );
    }

    return (
        <ScrollView 
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
            }
        >
            <View style={styles.header}>
                <Text style={styles.title}>📊 Query History</Text>
                <Text style={styles.subtitle}>Total: {total} queries</Text>
            </View>

            {queries.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyIcon}>📝</Text>
                    <Text style={styles.emptyTitle}>No queries yet</Text>
                    <Text style={styles.emptyText}>
                        User queries will appear here once they start using the chatbot.
                    </Text>
                </View>
            ) : (
                queries.map((query) => (
                    <View key={query.id} style={styles.queryCard}>
                        <View style={styles.queryHeader}>
                            <Text style={styles.userId}>👤 {query.user_id}</Text>
                            <Text style={styles.timestamp}>{formatDate(query.timestamp)}</Text>
                        </View>

                        <Text style={styles.sectionLabel}>Question:</Text>
                        <Text style={styles.question}>{query.question}</Text>

                        <Text style={styles.sectionLabel}>Answer:</Text>
                        <Text style={styles.answer} numberOfLines={4}>
                            {query.answer}
                        </Text>

                        <View style={styles.queryFooter}>
                            <View style={styles.badgeContainer}>
                                <View style={styles.badge}>
                                    <Text style={styles.badgeText}>
                                        {query.answer_type}
                                    </Text>
                                </View>
                                <View style={[styles.badge, { backgroundColor: '#DBEAFE' }]}>
                                    <Text style={styles.badgeText}>
                                        {query.sources_count} sources
                                    </Text>
                                </View>
                            </View>
                            <Text style={styles.rating}>{getRatingStars(query.rating)}</Text>
                        </View>

                        {query.feedback_text && (
                            <View style={styles.feedbackBox}>
                                <Text style={styles.feedbackLabel}>💬 Feedback:</Text>
                                <Text style={styles.feedbackText}>{query.feedback_text}</Text>
                            </View>
                        )}
                    </View>
                ))
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    content: {
        padding: 16,
        paddingBottom: 32,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
    },
    loadingText: {
        marginTop: 12,
        fontSize: 16,
        color: '#666',
    },
    header: {
        marginBottom: 16,
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 4,
    },
    subtitle: {
        fontSize: 14,
        color: '#666',
    },
    emptyState: {
        alignItems: 'center',
        padding: 48,
        backgroundColor: '#fff',
        borderRadius: 12,
    },
    emptyIcon: {
        fontSize: 64,
        marginBottom: 16,
    },
    emptyTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    emptyText: {
        fontSize: 14,
        color: '#666',
        textAlign: 'center',
    },
    queryCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    queryHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    userId: {
        fontSize: 14,
        fontWeight: '600',
        color: '#3B82F6',
    },
    timestamp: {
        fontSize: 12,
        color: '#999',
    },
    sectionLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: '#666',
        marginTop: 8,
        marginBottom: 4,
    },
    question: {
        fontSize: 14,
        color: '#333',
        fontWeight: '500',
        marginBottom: 8,
    },
    answer: {
        fontSize: 13,
        color: '#555',
        lineHeight: 20,
    },
    queryFooter: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 12,
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: '#eee',
    },
    badgeContainer: {
        flexDirection: 'row',
        gap: 6,
    },
    badge: {
        backgroundColor: '#F3F4F6',
        borderRadius: 12,
        paddingHorizontal: 8,
        paddingVertical: 4,
    },
    badgeText: {
        fontSize: 11,
        color: '#666',
        fontWeight: '500',
    },
    rating: {
        fontSize: 14,
    },
    feedbackBox: {
        marginTop: 12,
        padding: 12,
        backgroundColor: '#FEF3C7',
        borderRadius: 8,
    },
    feedbackLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: '#92400E',
        marginBottom: 4,
    },
    feedbackText: {
        fontSize: 13,
        color: '#78350F',
    },
});
