import { useState, useEffect } from 'react';
import { StyleSheet, View, Text, ScrollView, ActivityIndicator } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { ragApi, type DocumentChunk } from '../services/api';

export default function DocumentViewScreen() {
    const { id, name } = useLocalSearchParams<{ id: string; name: string }>();
    const [chunks, setChunks] = useState<DocumentChunk[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadChunks();
    }, [id]);

    const loadChunks = async () => {
        if (!id) return;
        
        try {
            setLoading(true);
            const docChunks = await ragApi.getDocumentChunks(id);
            setChunks(docChunks);
        } catch (error) {
            console.error('Failed to load chunks:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#3B82F6" />
                <Text style={styles.loadingText}>Loading document...</Text>
            </View>
        );
    }

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>📄 {decodeURIComponent(name || 'Document')}</Text>
                <Text style={styles.subtitle}>{chunks.length} chunks</Text>
            </View>

            {chunks.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyIcon}>📭</Text>
                    <Text style={styles.emptyText}>No chunks found</Text>
                </View>
            ) : (
                chunks.map((chunk, index) => (
                    <View key={chunk.chunk_id} style={styles.chunkCard}>
                        <View style={styles.chunkHeader}>
                            <View style={styles.chunkBadge}>
                                <Text style={styles.chunkBadgeText}>
                                    Chunk {chunk.chunk_number + 1} of {chunk.metadata.total_chunks}
                                </Text>
                            </View>
                            <Text style={styles.chunkId}>
                                {chunk.metadata.chunk_length} chars
                            </Text>
                        </View>

                        <Text style={styles.chunkContent}>
                            {chunk.content}
                        </Text>

                        <View style={styles.chunkFooter}>
                            <Text style={styles.chunkIdFull} numberOfLines={1}>
                                ID: {chunk.chunk_id}
                            </Text>
                        </View>
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
        fontSize: 20,
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
    emptyText: {
        fontSize: 16,
        color: '#666',
    },
    chunkCard: {
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
    chunkHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    chunkBadge: {
        backgroundColor: '#FED7AA',
        borderRadius: 12,
        paddingHorizontal: 10,
        paddingVertical: 4,
    },
    chunkBadgeText: {
        fontSize: 11,
        fontWeight: '600',
        color: '#9A3412',
    },
    chunkId: {
        fontSize: 11,
        color: '#999',
    },
    chunkContent: {
        fontSize: 14,
        color: '#333',
        lineHeight: 22,
        marginBottom: 12,
    },
    chunkFooter: {
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: '#eee',
    },
    chunkIdFull: {
        fontSize: 10,
        color: '#999',
        fontFamily: 'monospace',
    },
});
