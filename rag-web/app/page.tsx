'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import DocumentUpload from '@/components/DocumentUpload';
import ChatInterface from '@/components/ChatInterface';
import DocumentList from '@/components/DocumentList';
import { api, auth, User } from '@/lib/api';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'documents'>('chat');
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      if (!auth.isAuthenticated()) {
        router.push('/login');
        return;
      }

      try {
        const userData = await api.getCurrentUser();
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

  const navigateToAdmin = () => {
    router.push('/admin');
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

  const isAdmin = user?.role === 'admin';

  return (
    <main className="flex min-h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">RAG Chat System</h1>
            <p className="text-sm text-gray-600 mt-1">
              Upload documents and ask questions powered by AI
            </p>
          </div>
          <div className="flex items-center gap-4">
            {isAdmin && (
              <button
                onClick={navigateToAdmin}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition"
              >
                👑 Admin Panel
              </button>
            )}
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{user?.username}</p>
              <p className="text-xs text-gray-500">
                {isAdmin ? '👑 Admin' : '👤 User'}
              </p>
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
          {/* Left Sidebar - Desktop */}
          <div className="hidden lg:block lg:col-span-1 space-y-6">
            {isAdmin && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4">Upload Document</h2>
                <DocumentUpload />
              </div>
            )}

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">Your Documents</h2>
              <DocumentList isAdmin={isAdmin} />
            </div>
          </div>

          {/* Main Chat Area */}
          <div className="lg:col-span-2">
            {/* Mobile Tabs */}
            <div className="lg:hidden mb-4">
              <div className="flex space-x-2 bg-white rounded-lg p-1 shadow-sm">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'chat'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  Chat
                </button>
                {isAdmin && (
                  <button
                    onClick={() => setActiveTab('upload')}
                    className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'upload'
                        ? 'bg-blue-500 text-white'
                        : 'text-gray-600 hover:bg-gray-100'
                      }`}
                  >
                    Upload
                  </button>
                )}
                <button
                  onClick={() => setActiveTab('documents')}
                  className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'documents'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  Documents
                </button>
              </div>
            </div>

            {/* Mobile Content */}
            <div className="lg:hidden">
              {activeTab === 'chat' && (
                <div className="bg-white rounded-lg shadow-sm h-[calc(100vh-250px)]">
                  <ChatInterface />
                </div>
              )}
              {activeTab === 'upload' && isAdmin && (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h2 className="text-lg font-semibold mb-4">Upload Document</h2>
                  <DocumentUpload />
                </div>
              )}
              {activeTab === 'documents' && (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h2 className="text-lg font-semibold mb-4">Your Documents</h2>
                  <DocumentList isAdmin={isAdmin} />
                </div>
              )}
            </div>

            {/* Desktop Chat */}
            <div className="hidden lg:block bg-white rounded-lg shadow-sm h-[calc(100vh-180px)]">
              <ChatInterface />
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 px-6 py-4 mt-auto">
        <div className="max-w-7xl mx-auto text-center text-sm text-gray-600">
          <p>Powered by ChromaDB, OpenAI GPT-3.5-turbo, and LangChain</p>
        </div>
      </footer>
    </main>
  );
}
