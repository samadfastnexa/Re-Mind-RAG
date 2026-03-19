import { StyleSheet, View, Text, FlatList, TouchableOpacity, Alert } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { ragApi, type Document } from '../services/api';
import * as DocumentPicker from 'expo-document-picker';

export default function DocumentsScreen() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState<string | null>(null);
    const router = useRouter();

    const loadDocuments = async () => {
        try {
            setLoading(true);
            const docs = await ragApi.listDocuments();
            setDocuments(docs);
        } catch (error) {
            Alert.alert('Error', 'Failed to load documents');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDocuments();
    }, []);

    const handleDelete = (doc: Document) => {
        Alert.alert(
            'Delete Document',
            `Are you sure you want to delete "${doc.filename}"?`,
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Delete',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            await ragApi.deleteDocument(doc.document_id);
                            await loadDocuments();
                            Alert.alert('Success', 'Document deleted');
                        } catch (error) {
                            Alert.alert('Error', 'Failed to delete document');
                        }
                    },
                },
            ]
        );
    };

    const handleUpdate = async (doc: Document) => {
        try {
            // Pick a new document
            const result = await DocumentPicker.getDocumentAsync({
                type: ['application/pdf', 'text/plain'],
                copyToCacheDirectory: true
            });

            if (result.canceled || !result.assets?.[0]) {
                return;
            }

            const file = result.assets[0];

            // Confirm update
            Alert.alert(
                'Update Document',
                `Replace "${doc.filename}" with "${file.name}"?\n\nThis will replace all ${doc.chunks} existing chunks.`,
                [
                    { text: 'Cancel', style: 'cancel' },
                    {
                        text: 'Update',
                        onPress: async () => {
                            try {
                                setUpdating(doc.document_id);
                                await ragApi.updateDocument(doc.document_id, file.uri, file.name);
                                await loadDocuments();
                                Alert.alert('Success', 'Document updated successfully!');
                            } catch (error) {
                                Alert.alert('Error', 'Failed to update document');
                            } finally {
                                setUpdating(null);
                            }
                        },
                    },
                ]
            );
        } catch (error) {
            Alert.alert('Error', 'Failed to pick document');
        }
    };

    if (loading) {
        return (
            <View style={styles.centerContainer}>
                <Text style={styles.loadingText}>Loading...</Text>
            </View>
        );
    }

    if (documents.length === 0) {
        return (
            <View style={styles.centerContainer}>
                <Text style={styles.emptyIcon}>📭</Text>
                <Text style={styles.emptyText}>No documents yet</Text>
                <Text style={styles.emptySubtext}>Upload a document to get started</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <FlatList
                data={documents}
                keyExtractor={(item) => item.document_id}
                renderItem={({ item }) => (
                    <View style={styles.documentCard}>
                        <View style={styles.documentInfo}>
                            <Text style={styles.documentName} numberOfLines={1}>
                                {item.filename}
                            </Text>
                            <Text style={styles.documentMeta}>{item.chunks} chunks</Text>
                        </View>
                        <View style={styles.actionButtons}>
                            <TouchableOpacity
                                style={styles.viewButton}
                                onPress={() => router.push(`/document-view?id=${item.document_id}&name=${encodeURIComponent(item.filename)}`)}
                            >
                                <Text style={styles.viewButtonText}>👁️</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.updateButton, updating === item.document_id && styles.disabledButton]}
                                onPress={() => handleUpdate(item)}
                                disabled={updating === item.document_id}
                            >
                                <Text style={styles.updateButtonText}>
                                    {updating === item.document_id ? '⏳' : '🔄'}
                                </Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.deleteButton, updating === item.document_id && styles.disabledButton]}
                                onPress={() => handleDelete(item)}
                                disabled={updating === item.document_id}
                            >
                                <Text style={styles.deleteButtonText}>🗑️</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                )}
                contentContainerStyle={styles.listContent}
            />
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
        fontSize: 16,
        color: '#666',
    },
    emptyIcon: {
        fontSize: 64,
        marginBottom: 16,
    },
    emptyText: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    emptySubtext: {
        fontSize: 14,
        color: '#666',
    },
    listContent: {
        padding: 16,
    },
    documentCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        flexDirection: 'row',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    documentInfo: {
        flex: 1,
    },
    documentName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#333',
        marginBottom: 4,
    },
    documentMeta: {
        fontSize: 12,
        color: '#666',
    },
    actionButtons: {
        flexDirection: 'row',
        gap: 8,
    },
    viewButton: {
        backgroundColor: '#DBEAFE',
        borderRadius: 8,
        width: 40,
        height: 40,
        justifyContent: 'center',
        alignItems: 'center',
    },
    viewButtonText: {
        fontSize: 20,
    },
    updateButton: {
        backgroundColor: '#D1FAE5',
        borderRadius: 8,
        width: 40,
        height: 40,
        justifyContent: 'center',
        alignItems: 'center',
    },
    updateButtonText: {
        fontSize: 20,
    },
    deleteButton: {
        padding: 8,
    },
    deleteButtonText: {
        fontSize: 24,
    },
    disabledButton: {
        opacity: 0.5,
    },
});
