import { Stack } from 'expo-router';

export default function RootLayout() {
    return (
        <Stack
            screenOptions={{
                headerStyle: {
                    backgroundColor: '#3B82F6',
                },
                headerTintColor: '#fff',
                headerTitleStyle: {
                    fontWeight: 'bold',
                },
            }}
        >
            <Stack.Screen
                name="index"
                options={{
                    title: 'RAG Chat',
                }}
            />
            <Stack.Screen
                name="upload"
                options={{
                    title: 'Upload Document',
                }}
            />
            <Stack.Screen
                name="chat"
                options={{
                    title: 'Chat',
                }}
            />
            <Stack.Screen
                name="documents"
                options={{
                    title: 'My Documents',
                }}
            />
            <Stack.Screen
                name="document-view"
                options={{
                    title: 'View Document',
                }}
            />
            <Stack.Screen
                name="history"
                options={{
                    title: 'Chat History',
                }}
            />
            <Stack.Screen
                name="login"
                options={{
                    title: 'Login',
                }}
            />
            <Stack.Screen
                name="admin"
                options={{
                    title: 'Admin Dashboard',
                    headerStyle: {
                        backgroundColor: '#8B5CF6',
                    },
                }}
            />
            <Stack.Screen
                name="query-log"
                options={{
                    title: 'Query History',
                }}
            />
        </Stack>
    );
}
