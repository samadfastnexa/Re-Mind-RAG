import {
    StyleSheet,
    View,
    Text,
    TouchableOpacity,
    FlatList,
    Alert,
    ActivityIndicator,
} from 'react-native';
import { useState, useCallback } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { conversationStorage, type ConversationRecord } from '../services/conversationStorage';

export default function HistoryScreen() {
    const [conversations, setConversations] = useState<ConversationRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useFocusEffect(
        useCallback(() => {
            let active = true;
            (async () => {
                setLoading(true);
                const data = await conversationStorage.getAll();
                if (active) {
                    setConversations(data);
                    setLoading(false);
                }
            })();
            return () => { active = false; };
        }, [])
    );

    const handleOpen = (conv: ConversationRecord) => {
        router.push({ pathname: '/chat', params: { conversationId: conv.id } });
    };

    const handleDelete = (conv: ConversationRecord) => {
        Alert.alert(
            'Delete Conversation',
            `Delete "${conv.title}"?`,
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Delete',
                    style: 'destructive',
                    onPress: async () => {
                        const updated = await conversationStorage.remove(conv.id);
                        setConversations(updated);
                    },
                },
            ]
        );
    };

    const handleClearAll = () => {
        if (conversations.length === 0) return;
        Alert.alert(
            'Clear All History',
            'This will delete all saved conversations. Continue?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Clear All',
                    style: 'destructive',
                    onPress: async () => {
                        await conversationStorage.clearAll();
                        setConversations([]);
                    },
                },
            ]
        );
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    const renderItem = ({ item }: { item: ConversationRecord }) => {
        const messageCount = item.messages.length;
        const userMsgCount = item.messages.filter(m => m.type === 'user').length;

        return (
            <TouchableOpacity
                style={styles.card}
                onPress={() => handleOpen(item)}
                activeOpacity={0.7}
            >
                <View style={styles.cardHeader}>
                    <View style={styles.cardTitleRow}>
                        <Text style={styles.cardIcon}>💬</Text>
                        <Text style={styles.cardTitle} numberOfLines={2}>
                            {item.title}
                        </Text>
                    </View>
                    <TouchableOpacity
                        style={styles.deleteBtn}
                        onPress={() => handleDelete(item)}
                        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                    >
                        <Text style={styles.deleteBtnText}>✕</Text>
                    </TouchableOpacity>
                </View>

                <View style={styles.cardMeta}>
                    <View style={styles.metaBadge}>
                        <Text style={styles.metaBadgeText}>
                            {userMsgCount} {userMsgCount === 1 ? 'question' : 'questions'}
                        </Text>
                    </View>
                    <View style={styles.metaBadge}>
                        <Text style={styles.metaBadgeText}>
                            {messageCount} {messageCount === 1 ? 'message' : 'messages'}
                        </Text>
                    </View>
                    <Text style={styles.dateText}>{formatDate(item.lastUpdated)}</Text>
                </View>

                {/* Preview of first user message */}
                {item.messages.length > 0 && (
                    <Text style={styles.preview} numberOfLines={2}>
                        {item.messages.find(m => m.type === 'user')?.content || ''}
                    </Text>
                )}
            </TouchableOpacity>
        );
    };

    if (loading) {
        return (
            <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color="#3B82F6" />
                <Text style={styles.loadingText}>Loading history...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* Header Actions */}
            <View style={styles.headerBar}>
                <Text style={styles.headerCount}>
                    {conversations.length} {conversations.length === 1 ? 'conversation' : 'conversations'}
                </Text>
                {conversations.length > 0 && (
                    <TouchableOpacity style={styles.clearAllBtn} onPress={handleClearAll}>
                        <Text style={styles.clearAllText}>Clear All</Text>
                    </TouchableOpacity>
                )}
            </View>

            {conversations.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyIcon}>📭</Text>
                    <Text style={styles.emptyTitle}>No History Yet</Text>
                    <Text style={styles.emptyText}>
                        Your chat conversations will appear here.{'\n'}Start chatting to build your history!
                    </Text>
                    <TouchableOpacity
                        style={styles.startChatBtn}
                        onPress={() => router.push('/chat')}
                    >
                        <Text style={styles.startChatText}>Start Chatting</Text>
                    </TouchableOpacity>
                </View>
            ) : (
                <FlatList
                    data={conversations}
                    renderItem={renderItem}
                    keyExtractor={(item) => item.id}
                    contentContainerStyle={styles.list}
                    showsVerticalScrollIndicator={false}
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
    },
    loadingText: {
        marginTop: 12,
        fontSize: 14,
        color: '#666',
    },
    headerBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 12,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#e5e7eb',
    },
    headerCount: {
        fontSize: 14,
        color: '#6b7280',
        fontWeight: '500',
    },
    clearAllBtn: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 8,
        backgroundColor: '#fee2e2',
    },
    clearAllText: {
        fontSize: 13,
        color: '#dc2626',
        fontWeight: '600',
    },
    list: {
        padding: 16,
        paddingBottom: 32,
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: 14,
        padding: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.08,
        shadowRadius: 6,
        elevation: 3,
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    cardTitleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
        marginRight: 8,
    },
    cardIcon: {
        fontSize: 18,
        marginRight: 8,
    },
    cardTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#1f2937',
        flex: 1,
    },
    deleteBtn: {
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: '#f3f4f6',
        justifyContent: 'center',
        alignItems: 'center',
    },
    deleteBtnText: {
        fontSize: 14,
        color: '#9ca3af',
        fontWeight: '600',
    },
    cardMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 10,
        gap: 8,
    },
    metaBadge: {
        backgroundColor: '#eff6ff',
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 6,
    },
    metaBadgeText: {
        fontSize: 11,
        color: '#3b82f6',
        fontWeight: '500',
    },
    dateText: {
        fontSize: 11,
        color: '#9ca3af',
        marginLeft: 'auto',
    },
    preview: {
        marginTop: 10,
        fontSize: 13,
        color: '#6b7280',
        lineHeight: 18,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 32,
    },
    emptyIcon: {
        fontSize: 64,
        marginBottom: 16,
    },
    emptyTitle: {
        fontSize: 22,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    emptyText: {
        fontSize: 14,
        color: '#666',
        textAlign: 'center',
        lineHeight: 22,
        marginBottom: 24,
    },
    startChatBtn: {
        backgroundColor: '#3B82F6',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 12,
    },
    startChatText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
});
