import { StyleSheet, View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { Link } from 'expo-router';

export default function HomeScreen() {
    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>RAG Chat System</Text>
                <Text style={styles.subtitle}>AI-powered document Q&A</Text>
            </View>

            <View style={styles.grid}>
                <Link href="/upload" asChild>
                    <TouchableOpacity style={[styles.card, styles.uploadCard]}>
                        <Text style={styles.cardIcon}>📤</Text>
                        <Text style={styles.cardTitle}>Upload</Text>
                        <Text style={styles.cardText}>Upload PDF or TXT documents</Text>
                    </TouchableOpacity>
                </Link>

                <Link href="/chat" asChild>
                    <TouchableOpacity style={[styles.card, styles.chatCard]}>
                        <Text style={styles.cardIcon}>💬</Text>
                        <Text style={styles.cardTitle}>Chat</Text>
                        <Text style={styles.cardText}>Ask questions about your documents</Text>
                    </TouchableOpacity>
                </Link>

                <Link href="/documents" asChild>
                    <TouchableOpacity style={[styles.card, styles.docsCard]}>
                        <Text style={styles.cardIcon}>📚</Text>
                        <Text style={styles.cardTitle}>Documents</Text>
                        <Text style={styles.cardText}>Manage uploaded documents</Text>
                    </TouchableOpacity>
                </Link>

                <Link href="/history" asChild>
                    <TouchableOpacity style={[styles.card, styles.historyCard]}>
                        <Text style={styles.cardIcon}>🕘</Text>
                        <Text style={styles.cardTitle}>History</Text>
                        <Text style={styles.cardText}>View and resume past conversations</Text>
                    </TouchableOpacity>
                </Link>

                <Link href="/login" asChild>
                    <TouchableOpacity style={[styles.card, styles.adminCard]}>
                        <Text style={styles.cardIcon}>🔐</Text>
                        <Text style={styles.cardTitle}>Admin</Text>
                        <Text style={styles.cardText}>Login to access admin features</Text>
                    </TouchableOpacity>
                </Link>
            </View>

            <View style={styles.footer}>
                <Text style={styles.footerText}>Powered by ChromaDB, OpenAI & LangChain</Text>
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
        alignItems: 'center',
        marginTop: 40,
        marginBottom: 40,
    },
    title: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 16,
        color: '#666',
    },
    grid: {
        gap: 16,
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 24,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
        elevation: 4,
    },
    uploadCard: {
        borderLeftWidth: 4,
        borderLeftColor: '#10B981',
    },
    chatCard: {
        borderLeftWidth: 4,
        borderLeftColor: '#3B82F6',
    },
    docsCard: {
        borderLeftWidth: 4,
        borderLeftColor: '#8B5CF6',
    },
    historyCard: {
        borderLeftWidth: 4,
        borderLeftColor: '#F59E0B',
    },
    adminCard: {
        borderLeftWidth: 4,
        borderLeftColor: '#8B5CF6',
    },
    cardIcon: {
        fontSize: 48,
        marginBottom: 12,
    },
    cardTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    cardText: {
        fontSize: 14,
        color: '#666',
        textAlign: 'center',
    },
    footer: {
        marginTop: 40,
        alignItems: 'center',
    },
    footerText: {
        fontSize: 12,
        color: '#999',
    },
});
