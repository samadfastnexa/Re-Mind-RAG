'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, auth, User } from '@/lib/api';
import UserManagement from '@/components/UserManagement';
import QueryHistory from '@/components/QueryHistory';
import DocumentManagement from '@/components/DocumentManagement';

type Tab = 'users' | 'queries' | 'documents';

export default function AdminPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('queries');
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      if (!auth.isAuthenticated()) {
        router.push('/login');
        return;
      }

      try {
        const userData = await api.getCurrentUser();
        
        // Check if user is admin
        if (userData.role !== 'admin') {
          router.push('/');
          return;
        }
        
        setUser(userData);
      } catch (error) {
        console.error('Auth check failed:', error);
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  const handleLogout = () => {
    api.logout();
    router.push('/login');
  };

  const navigateToHome = () => {
    router.push('/');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">👑 Admin Dashboard</h1>
            <p className="text-sm text-gray-600 mt-1">
              Manage users and system settings
            </p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={navigateToHome}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              ← Back to Chat
            </button>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{user?.username}</p>
              <p className="text-xs text-gray-500">Administrator</p>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6">
        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('queries')}
            className={`px-5 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === 'queries'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📊 Query History
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-5 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === 'users'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            👥 Users
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-5 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === 'documents'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📄 Documents
          </button>
        </div>

        {activeTab === 'queries' && <QueryHistory />}
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'documents' && <DocumentManagement />}
      </div>
    </main>
  );
}
