import { StyleSheet, View, Text, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { ragApi, type QueryResponse } from '../services/api';
import { conversationStorage, type ConversationRecord, type StoredMessage } from '../services/conversationStorage';

interface Message {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    sources?: QueryResponse['sources'];
    timestamp: Date;
}

export default function ChatScreen() {
    const { conversationId } = useLocalSearchParams<{ conversationId?: string }>();

    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentConvId, setCurrentConvId] = useState<string>(
        conversationId || Date.now().toString()
    );
    const scrollViewRef = useRef<ScrollView>(null);

    useEffect(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
    }, [messages]);

    // Load existing conversation if navigated from history
    useEffect(() => {
        if (conversationId) {
            (async () => {
                const all = await conversationStorage.getAll();
                const found = all.find(c => c.id === conversationId);
                if (found) {
                    setCurrentConvId(found.id);
                    setMessages(
                        found.messages.map(m => ({
                            ...m,
                            timestamp: new Date(m.timestamp),
                        }))
                    );
                }
            })();
        }
    }, [conversationId]);

    // Save conversation after each message exchange
    const saveToHistory = useCallback(async (msgs: Message[]) => {
        if (msgs.length === 0) return;

        const title = msgs.find(m => m.type === 'user')?.content.slice(0, 60) || 'New Conversation';
        const storedMessages: StoredMessage[] = msgs.map(m => ({
            id: m.id,
            type: m.type,
            content: m.content,
            sources: m.sources?.map(s => ({
                source_id: s.source_id,
                document_id: s.document_id,
                document: s.document,
                chunk: s.chunk,
                total_chunks: s.total_chunks,
                position_percent: s.position_percent,
                content: s.content,
                relevance_score: s.relevance_score,
                chunk_length: s.chunk_length,
            })),
            timestamp: m.timestamp.toISOString(),
        }));

        const record: ConversationRecord = {
            id: currentConvId,
            title,
            messages: storedMessages,
            createdAt: msgs[0].timestamp.toISOString(),
            lastUpdated: new Date().toISOString(),
        };

        await conversationStorage.upsert(record);
    }, [currentConvId]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            type: 'user',
            content: input,
            timestamp: new Date(),
        };

        const updatedWithUser = [...messages, userMessage];
        setMessages(updatedWithUser);
        setInput('');
        setLoading(true);

        try {
            const response = await ragApi.queryDocuments(input);

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: response.answer,
                sources: response.sources,
                timestamp: new Date(),
            };

            const updatedWithAssistant = [...updatedWithUser, assistantMessage];
            setMessages(updatedWithAssistant);
            await saveToHistory(updatedWithAssistant);
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: error instanceof Error ? error.message : 'Failed to get response',
                timestamp: new Date(),
            };

            const updatedWithError = [...updatedWithUser, errorMessage];
            setMessages(updatedWithError);
            await saveToHistory(updatedWithError);
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            keyboardVerticalOffset={100}
        >
            <ScrollView
                ref={scrollViewRef}
                style={styles.messagesContainer}
                contentContainerStyle={styles.messagesContent}
            >
                {messages.length === 0 && (
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyTitle}>Welcome to RAG Chat!</Text>
                        <Text style={styles.emptyText}>Upload a document and start asking questions.</Text>
                    </View>
                )}

                {messages.map((message) => (
                    <View
                        key={message.id}
                        style={[
                            styles.messageBubble,
                            message.type === 'user' ? styles.userBubble : styles.assistantBubble,
                        ]}
                    >
                        <Text style={message.type === 'user' ? styles.userText : styles.assistantText}>
                            {message.content}
                        </Text>

                        {message.sources && message.sources.length > 0 && (
                            <View style={styles.sources}>
                                <Text style={styles.sourcesTitle}>Sources:</Text>
                                {message.sources.map((source, idx) => (
                                    <Text key={idx} style={styles.sourceText}>
                                        • {source.document} (Chunk {source.chunk})
                                    </Text>
                                ))}
                            </View>
                        )}

                        <Text style={styles.timestamp}>
                            {message.timestamp.toLocaleTimeString()}
                        </Text>
                    </View>
                ))}

                {loading && (
                    <View style={[styles.messageBubble, styles.assistantBubble]}>
                        <Text style={styles.assistantText}>Thinking...</Text>
                    </View>
                )}
            </ScrollView>

            <View style={styles.inputContainer}>
                <TextInput
                    style={styles.input}
                    value={input}
                    onChangeText={setInput}
                    placeholder="Ask a question..."
                    editable={!loading}
                    multiline
                />
                <TouchableOpacity
                    style={[styles.sendButton, (!input.trim() || loading) && styles.sendButtonDisabled]}
                    onPress={handleSend}
                    disabled={!input.trim() || loading}
                >
                    <Text style={styles.sendButtonText}>Send</Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    messagesContainer: {
        flex: 1,
    },
    messagesContent: {
        padding: 16,
    },
    emptyState: {
        alignItems: 'center',
        marginTop: 60,
    },
    emptyTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    emptyText: {
        fontSize: 14,
        color: '#666',
    },
    messageBubble: {
        maxWidth: '80%',
        padding: 12,
        borderRadius: 16,
        marginBottom: 12,
    },
    userBubble: {
        alignSelf: 'flex-end',
        backgroundColor: '#3B82F6',
    },
    assistantBubble: {
        alignSelf: 'flex-start',
        backgroundColor: '#fff',
    },
    userText: {
        color: '#fff',
        fontSize: 16,
    },
    assistantText: {
        color: '#333',
        fontSize: 16,
    },
    sources: {
        marginTop: 8,
        paddingTop: 8,
        borderTopWidth: 1,
        borderTopColor: '#e0e0e0',
    },
    sourcesTitle: {
        fontSize: 12,
        fontWeight: 'bold',
        marginBottom: 4,
        color: '#666',
    },
    sourceText: {
        fontSize: 11,
        color: '#666',
        marginBottom: 2,
    },
    timestamp: {
        fontSize: 10,
        color: '#999',
        marginTop: 4,
    },
    inputContainer: {
        flexDirection: 'row',
        padding: 16,
        backgroundColor: '#fff',
        borderTopWidth: 1,
        borderTopColor: '#e0e0e0',
    },
    input: {
        flex: 1,
        backgroundColor: '#f5f5f5',
        borderRadius: 20,
        paddingHorizontal: 16,
        paddingVertical: 8,
        marginRight: 8,
        maxHeight: 100,
    },
    sendButton: {
        backgroundColor: '#3B82F6',
        borderRadius: 20,
        paddingHorizontal: 20,
        paddingVertical: 10,
        justifyContent: 'center',
    },
    sendButtonDisabled: {
        opacity: 0.5,
    },
    sendButtonText: {
        color: '#fff',
        fontWeight: 'bold',
    },
});
