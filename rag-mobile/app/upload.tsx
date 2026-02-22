import { StyleSheet, View, Text, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { useState } from 'react';
import * as DocumentPicker from 'expo-document-picker';
import { ragApi, type UploadResponse } from '../services/api';

export default function UploadScreen() {
    const [uploading, setUploading] = useState(false);
    const [lastUpload, setLastUpload] = useState<UploadResponse | null>(null);

    const handlePickDocument = async () => {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: ['application/pdf', 'text/plain'],
                copyToCacheDirectory: true,
            });

            if (result.canceled) return;

            const file = result.assets[0];

            // Validate file size (50MB)
            if (file.size && file.size > 50 * 1024 * 1024) {
                Alert.alert('Error', 'File size must be less than 50MB');
                return;
            }

            setUploading(true);

            const response = await ragApi.uploadDocument(file.uri, file.name);
            setLastUpload(response);
            Alert.alert('Success', `Uploaded ${response.filename} successfully!`);
        } catch (error) {
            Alert.alert('Error', error instanceof Error ? error.message : 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>Upload Document</Text>
                <Text style={styles.subtitle}>Upload PDF or TXT files to ask questions about them</Text>
            </View>

            <TouchableOpacity
                style={[styles.uploadButton, uploading && styles.uploadButtonDisabled]}
                onPress={handlePickDocument}
                disabled={uploading}
            >
                <Text style={styles.uploadIcon}>📄</Text>
                <Text style={styles.uploadText}>
                    {uploading ? 'Uploading...' : 'Choose File'}
                </Text>
                <Text style={styles.uploadSubtext}>PDF or TXT (MAX. 50MB)</Text>
            </TouchableOpacity>

            {lastUpload && (
                <View style={styles.successCard}>
                    <Text style={styles.successTitle}>✅ Last Upload</Text>
                    <Text style={styles.successText}>File: {lastUpload.filename}</Text>
                    <Text style={styles.successText}>Chunks: {lastUpload.chunks}</Text>
                    {lastUpload.pages && (
                        <Text style={styles.successText}>Pages: {lastUpload.pages}</Text>
                    )}
                </View>
            )}

            <View style={styles.infoCard}>
                <Text style={styles.infoTitle}>How it works:</Text>
                <Text style={styles.infoText}>1. Upload your PDF or text document</Text>
                <Text style={styles.infoText}>2. The document is processed and indexed</Text>
                <Text style={styles.infoText}>3. Go to Chat to ask questions about it</Text>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    content: {
        padding: 20,
    },
    header: {
        marginBottom: 30,
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 14,
        color: '#666',
    },
    uploadButton: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 40,
        alignItems: 'center',
        borderWidth: 2,
        borderColor: '#3B82F6',
        borderStyle: 'dashed',
    },
    uploadButtonDisabled: {
        opacity: 0.5,
    },
    uploadIcon: {
        fontSize: 48,
        marginBottom: 16,
    },
    uploadText: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#3B82F6',
        marginBottom: 8,
    },
    uploadSubtext: {
        fontSize: 12,
        color: '#666',
    },
    successCard: {
        backgroundColor: '#D1FAE5',
        borderRadius: 12,
        padding: 16,
        marginTop: 20,
    },
    successTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#065F46',
        marginBottom: 8,
    },
    successText: {
        fontSize: 14,
        color: '#065F46',
        marginBottom: 4,
    },
    infoCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 20,
        marginTop: 20,
    },
    infoTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 12,
    },
    infoText: {
        fontSize: 14,
        color: '#666',
        marginBottom: 8,
    },
});
