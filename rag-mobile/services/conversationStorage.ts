/**
 * Conversation history persistence using AsyncStorage (mobile equivalent of localStorage)
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface StoredMessage {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    sources?: Array<{
        source_id?: number;
        document_id?: string;
        document: string;
        chunk: number;
        total_chunks?: number;
        position_percent?: number;
        content: string;
        relevance_score: number;
        chunk_length?: number;
    }>;
    timestamp: string; // ISO string for serialization
}

export interface ConversationRecord {
    id: string;
    title: string;
    messages: StoredMessage[];
    createdAt: string;
    lastUpdated: string;
}

const STORAGE_KEY = 'rag_mobile_conversations';
const MAX_CONVERSATIONS = 50;

export const conversationStorage = {
    async getAll(): Promise<ConversationRecord[]> {
        try {
            const raw = await AsyncStorage.getItem(STORAGE_KEY);
            if (raw) {
                return JSON.parse(raw) as ConversationRecord[];
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
        return [];
    },

    async save(conversations: ConversationRecord[]): Promise<void> {
        try {
            const trimmed = conversations.slice(0, MAX_CONVERSATIONS);
            await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
        } catch (error) {
            console.error('Failed to save conversations:', error);
        }
    },

    async upsert(conversation: ConversationRecord): Promise<ConversationRecord[]> {
        const all = await this.getAll();
        const existingIndex = all.findIndex(c => c.id === conversation.id);

        if (existingIndex >= 0) {
            all[existingIndex] = conversation;
        } else {
            all.unshift(conversation);
        }

        const trimmed = all.slice(0, MAX_CONVERSATIONS);
        await this.save(trimmed);
        return trimmed;
    },

    async remove(conversationId: string): Promise<ConversationRecord[]> {
        const all = await this.getAll();
        const filtered = all.filter(c => c.id !== conversationId);
        await this.save(filtered);
        return filtered;
    },

    async clearAll(): Promise<void> {
        try {
            await AsyncStorage.removeItem(STORAGE_KEY);
        } catch (error) {
            console.error('Failed to clear conversations:', error);
        }
    },
};
