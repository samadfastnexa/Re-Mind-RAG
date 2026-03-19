import { useState, useEffect } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { ragApi } from '../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function AdminScreen() {
    const [user, setUser] = useState<any>(null);
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const token = await AsyncStorage.getItem('auth_token');
            if (!token) {
                router.replace('/login');
                return;
            }

            const userInfo = await ragApi.getCurrentUser();
            
            if (userInfo.role !== 'admin') {
                Alert.alert('Access Denied', 'Admin role required');
                router.replace('/');
                return;
            }

            setUser(userInfo);

            // Load query stats
            const queryStats = await ragApi.getQueryStats();
            setStats(queryStats);
        } catch (error) {
            Alert.alert('Error', 'Failed to load admin data');
            router.replace('/login');
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = async () => {
        await AsyncStorage.removeItem('auth_token');
        await AsyncStorage.removeItem('user_info');
        ragApi.logout();
        router.replace('/');
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#3B82F6" />
                <Text style={styles.loadingText}>Loading...</Text>
            </View>
        );
    }

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>👑 Admin Dashboard</Text>
                <Text style={styles.subtitle}>Welcome, {user?.username}</Text>
            </View>

            {/* Stats Cards */}
            <View style={styles.statsGrid}>
                <View style={[styles.statCard, { backgroundColor: '#DBEAFE' }]}>
                    <Text style={styles.statNumber}>{stats?.total_queries || 0}</Text>
                    <Text style={styles.statLabel}>Total Queries</Text>
                </View>
                
                <View style={[styles.statCard, { backgroundColor: '#FEE2E2' }]}>
                    <Text style={styles.statNumber}>{stats?.unique_users || 0}</Text>
                    <Text style={styles.statLabel}>Unique Users</Text>
                </View>

                <View style={[styles.statCard, { backgroundColor: '#FEF3C7' }]}>
                    <Text style={styles.statNumber}>
                        {stats?.avg_rating ? stats.avg_rating.toFixed(1) : 'N/A'}
                    </Text>
                    <Text style={styles.statLabel}>Avg Rating</Text>
                </View>

                <View style={[styles.statCard, { backgroundColor: '#D1FAE5' }]}>
                    <Text style={styles.statNumber}>{stats?.rated_queries || 0}</Text>
                    <Text style={styles.statLabel}>Rated Queries</Text>
                </View>

                <View style={[styles.statCard, { backgroundColor: '#FECACA', borderColor: '#DC2626', borderWidth: 1.5 }]}>
                    <Text style={[styles.statNumber, { color: '#B91C1C' }]}>⚠️ {stats?.unanswerable_queries || 0}</Text>
                    <Text style={[styles.statLabel, { color: '#B91C1C', fontWeight: '600' }]}>Unanswerable</Text>
                    <Text style={[styles.statLabel, { fontSize: 11 }]}>
                        {stats?.total_queries ? `${((stats.unanswerable_queries || 0) / stats.total_queries * 100).toFixed(1)}%` : '0%'}
                    </Text>
                </View>
            </View>

            {/* Admin Actions */}
            <View style={styles.actionsContainer}>
                <Text style={styles.sectionTitle}>Admin Actions</Text>

                <TouchableOpacity 
                    style={styles.actionCard}
                    onPress={() => router.push('/query-log')}
                >
                    <Text style={styles.actionIcon}>📊</Text>
                    <View style={styles.actionContent}>
                        <Text style={styles.actionTitle}>Query History</Text>
                        <Text style={styles.actionDescription}>
                            View all user queries and analytics
                        </Text>
                    </View>
                    <Text style={styles.actionArrow}>→</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                    style={styles.actionCard}
                    onPress={() => router.push('/documents')}
                >
                    <Text style={styles.actionIcon}>📄</Text>
                    <View style={styles.actionContent}>
                        <Text style={styles.actionTitle}>Manage Documents</Text>
                        <Text style={styles.actionDescription}>
                            Upload, view, and delete documents
                        </Text>
                    </View>
                    <Text style={styles.actionArrow}>→</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                    style={styles.actionCard}
                    onPress={() => router.push('/chat')}
                >
                    <Text style={styles.actionIcon}>💬</Text>
                    <View style={styles.actionContent}>
                        <Text style={styles.actionTitle}>Test Chat</Text>
                        <Text style={styles.actionDescription}>
                            Test the RAG system
                        </Text>
                    </View>
                    <Text style={styles.actionArrow}>→</Text>
                </TouchableOpacity>
            </View>

            {/* Logout Button */}
            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
                <Text style={styles.logoutButtonText}>Logout</Text>
            </TouchableOpacity>
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
        paddingBottom: 40,
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
        marginBottom: 24,
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 4,
    },
    subtitle: {
        fontSize: 16,
        color: '#666',
    },
    statsGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        marginBottom: 24,
        gap: 12,
    },
    statCard: {
        flex: 1,
        minWidth: '45%',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    statNumber: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 4,
    },
    statLabel: {
        fontSize: 12,
        color: '#666',
        textAlign: 'center',
    },
    actionsContainer: {
        marginBottom: 24,
    },
    sectionTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 12,
    },
    actionCard: {
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
    actionIcon: {
        fontSize: 32,
        marginRight: 12,
    },
    actionContent: {
        flex: 1,
    },
    actionTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 4,
    },
    actionDescription: {
        fontSize: 13,
        color: '#666',
    },
    actionArrow: {
        fontSize: 24,
        color: '#3B82F6',
    },
    logoutButton: {
        backgroundColor: '#EF4444',
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
    },
    logoutButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
    },
});
