'use client';

import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api, User } from '@/lib/api';

// ── Password strength ──────────────────────────────────────────────────────
function scorePassword(p: string): number {
    if (!p) return 0;
    let s = 0;
    if (p.length >= 8)  s++;
    if (p.length >= 12) s++;
    if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++;
    if (/[0-9]/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    return Math.min(s, 4);
}
const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong'];
const STRENGTH_COLORS = ['', 'bg-red-500', 'bg-yellow-400', 'bg-blue-500', 'bg-green-500'];
const STRENGTH_TEXT   = ['', 'text-red-600', 'text-yellow-600', 'text-blue-600', 'text-green-600'];

function PasswordStrength({ password }: { password: string }) {
    const s = scorePassword(password);
    if (!password) return null;
    return (
        <div className="mt-1.5">
            <div className="flex gap-1 h-1.5">
                {[1,2,3,4].map(i => (
                    <div key={i} className={`flex-1 rounded-full transition-all duration-300 ${
                        i <= s ? STRENGTH_COLORS[s] : 'bg-gray-200'
                    }`} />
                ))}
            </div>
            {s > 0 && (
                <p className={`text-[10px] mt-0.5 font-medium ${STRENGTH_TEXT[s]}`}>
                    {STRENGTH_LABELS[s]} password
                </p>
            )}
        </div>
    );
}

// ── Eye toggle button ──────────────────────────────────────────────────────
function EyeButton({ show, onToggle }: { show: boolean; onToggle: () => void }) {
    return (
        <button type="button" onClick={onToggle} tabIndex={-1}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none">
            {show ? (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                        d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                </svg>
            ) : (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
            )}
        </button>
    );
}

// ── Spinner ────────────────────────────────────────────────────────────────
function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
    return (
        <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
    );
}

// ── Validate helpers ───────────────────────────────────────────────────────
function validateEmail(e: string) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e); }
function validateUsername(u: string) { return u.trim().length >= 3; }
function validatePassword(p: string) { return p.length >= 6; }

export default function UserManagement() {
    const [users, setUsers]           = useState<User[]>([]);
    const [loading, setLoading]       = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [creating, setCreating]     = useState(false);
    const [togglingId, setTogglingId] = useState<number | null>(null);

    const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'user' as 'user' | 'admin' });
    const [newTouched, setNewTouched] = useState({ username: false, email: false, password: false });
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [expandedUserId, setExpandedUserId] = useState<number | null>(null);
    const [userSearch, setUserSearch] = useState('');

    // Edit state
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [editForm, setEditForm]       = useState({ username: '', email: '', password: '', role: 'user' as 'user' | 'admin', is_active: true });
    const [showEditPassword, setShowEditPassword] = useState(false);
    const [saving, setSaving]           = useState(false);

    // Delete state
    const [deletingUserId, setDeletingUserId]             = useState<number | null>(null);
    const [confirmDeleteUsername, setConfirmDeleteUsername] = useState('');
    const [deleting, setDeleting]                          = useState(false);

    useEffect(() => { loadUsers(); }, []);

    const loadUsers = async () => {
        try {
            setLoading(true);
            setUsers(await api.getAllUsers());
        } catch (err: any) {
            toast.error(err.message || 'Failed to load users');
        } finally {
            setLoading(false);
        }
    };

    // ── Validate new user form ────────────────────────────────────────────
    const newUserErrors = {
        username: !validateUsername(newUser.username) ? 'At least 3 characters' : '',
        email:    !validateEmail(newUser.email)        ? 'Enter a valid email'   : '',
        password: !validatePassword(newUser.password)  ? 'At least 6 characters' : '',
    };
    const newUserValid = !newUserErrors.username && !newUserErrors.email && !newUserErrors.password;

    const handleToggleDeletePermission = async (userId: number, currentValue: boolean) => {
        setTogglingId(userId);
        try {
            await api.updateUserPermission(userId, !currentValue);
            const user = users.find(u => u.id === userId);
            toast.success(`${user?.username}: delete-history ${!currentValue ? 'enabled' : 'disabled'}`);
            await loadUsers();
        } catch (err: any) {
            toast.error(err.message || 'Failed to update permission');
        } finally {
            setTogglingId(null);
        }
    };

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        setNewTouched({ username: true, email: true, password: true });
        if (!newUserValid) return;

        setCreating(true);
        const tid = toast.loading(`Creating account for ${newUser.username}…`);
        try {
            await api.createUser(newUser);
            toast.success(`User "${newUser.username}" created successfully`, { id: tid });
            setNewUser({ username: '', email: '', password: '', role: 'user' });
            setNewTouched({ username: false, email: false, password: false });
            setShowCreateForm(false);
            await loadUsers();
        } catch (err: any) {
            toast.error(err.message || 'Failed to create user', { id: tid });
        } finally {
            setCreating(false);
        }
    };

    const openEditModal = (user: User) => {
        setEditingUser(user);
        setEditForm({ username: user.username, email: user.email, password: '', role: user.role, is_active: user.is_active });
        setShowEditPassword(false);
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser) return;

        const payload: Record<string, any> = {};
        if (editForm.username !== editingUser.username)   payload.username  = editForm.username;
        if (editForm.email    !== editingUser.email)       payload.email     = editForm.email;
        if (editForm.password)                             payload.password  = editForm.password;
        if (editForm.role     !== editingUser.role)        payload.role      = editForm.role;
        if (editForm.is_active !== editingUser.is_active)  payload.is_active = editForm.is_active;

        if (Object.keys(payload).length === 0) {
            toast.info('No changes made');
            setEditingUser(null);
            return;
        }

        setSaving(true);
        const tid = toast.loading(`Saving changes for ${editingUser.username}…`);
        try {
            await api.updateUser(editingUser.id, payload);
            toast.success(`"${editingUser.username}" updated`, { id: tid });
            setEditingUser(null);
            await loadUsers();
        } catch (err: any) {
            toast.error(err.message || 'Failed to update user', { id: tid });
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteUser = async (userId: number) => {
        const user = users.find(u => u.id === userId);
        setDeleting(true);
        const tid = toast.loading(`Deleting ${user?.username}…`);
        try {
            await api.deleteUser(userId);
            toast.success(`"${user?.username}" deleted`, { id: tid });
            setDeletingUserId(null);
            setConfirmDeleteUsername('');
            if (expandedUserId === userId) setExpandedUserId(null);
            await loadUsers();
        } catch (err: any) {
            toast.error(err.message || 'Failed to delete user', { id: tid });
        } finally {
            setDeleting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-500">
                <Spinner className="h-8 w-8 text-orange-500" />
                <p className="text-sm">Loading users…</p>
            </div>
        );
    }

    return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-start gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
          <p className="text-sm text-gray-600 mt-1">Manage user accounts and permissions</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <input
              type="text"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Search users…"
              className="pl-8 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 w-48"
            />
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">🔍</span>
          </div>
          <button
            onClick={() => { setShowCreateForm(!showCreateForm); setNewTouched({ username: false, email: false, password: false }); }}
            className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition font-medium text-sm flex items-center gap-2"
          >
            {showCreateForm ? '✕ Cancel' : '+ Create User'}
          </button>
        </div>
      </div>

      {/* Create User Form */}
      {showCreateForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span className="text-orange-500">👤</span> New User Account
          </h3>
          <form onSubmit={handleCreateUser} className="space-y-4" noValidate>
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                type="text"
                value={newUser.username}
                onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                onBlur={() => setNewTouched(t => ({ ...t, username: true }))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 transition ${
                  newTouched.username && newUserErrors.username ? 'border-red-400 bg-red-50' :
                  newTouched.username && !newUserErrors.username ? 'border-green-400' : 'border-gray-300'
                }`}
                placeholder="johndoe"
              />
              {newTouched.username && newUserErrors.username && (
                <p className="mt-1 text-xs text-red-600">⚠ {newUserErrors.username}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={newUser.email}
                onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                onBlur={() => setNewTouched(t => ({ ...t, email: true }))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 transition ${
                  newTouched.email && newUserErrors.email ? 'border-red-400 bg-red-50' :
                  newTouched.email && !newUserErrors.email ? 'border-green-400' : 'border-gray-300'
                }`}
                placeholder="john@example.com"
              />
              {newTouched.email && newUserErrors.email && (
                <p className="mt-1 text-xs text-red-600">⚠ {newUserErrors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  onBlur={() => setNewTouched(t => ({ ...t, password: true }))}
                  className={`w-full px-3 py-2 pr-10 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 transition ${
                    newTouched.password && newUserErrors.password ? 'border-red-400 bg-red-50' :
                    newTouched.password && !newUserErrors.password ? 'border-green-400' : 'border-gray-300'
                  }`}
                  placeholder="Min 6 characters"
                />
                <EyeButton show={showNewPassword} onToggle={() => setShowNewPassword(!showNewPassword)} />
              </div>
              <PasswordStrength password={newUser.password} />
              {newTouched.password && newUserErrors.password && (
                <p className="mt-1 text-xs text-red-600">⚠ {newUserErrors.password}</p>
              )}
            </div>

            {/* Role */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select
                value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value as 'user' | 'admin' })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                <option value="user">User — can query documents</option>
                <option value="admin">Admin — can upload &amp; manage</option>
              </select>
            </div>

            <div className="flex gap-3 pt-1">
              <button
                type="submit"
                disabled={creating}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition font-medium text-sm disabled:opacity-60"
              >
                {creating ? <><Spinner /> Creating…</> : '✓ Create User'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Delete History
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Profile
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users
                .filter(u =>
                  !userSearch.trim() ||
                  u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
                  u.email.toLowerCase().includes(userSearch.toLowerCase())
                )
                .map((user) => (
                <React.Fragment key={user.id}>
                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 font-semibold">
                          {user.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {user.username}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="max-w-[200px] text-sm text-gray-900 truncate" title={user.email}>{user.email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.role === 'admin' 
                        ? 'bg-purple-100 text-purple-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {user.role === 'admin' ? '👑 Admin' : '👤 User'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleToggleDeletePermission(user.id, user.can_delete_history)}
                      disabled={togglingId === user.id}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 disabled:opacity-60 ${
                        user.can_delete_history ? 'bg-orange-500' : 'bg-gray-200'
                      }`}
                      title={user.can_delete_history ? 'Can delete history — click to disable' : 'Cannot delete history — click to enable'}
                    >
                      {togglingId === user.id ? (
                        <span className="absolute inset-0 flex items-center justify-center">
                          <Spinner className="h-3 w-3 text-white" />
                        </span>
                      ) : (
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow ${
                          user.can_delete_history ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      )}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => setExpandedUserId(expandedUserId === user.id ? null : user.id)}
                      className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition"
                    >
                      {expandedUserId === user.id ? 'Hide' : 'View'}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openEditModal(user)}
                        className="px-3 py-1 text-xs font-medium text-amber-700 bg-amber-50 rounded-lg hover:bg-amber-100 transition"
                        title="Edit user"
                      >
                        ✏️ Edit
                      </button>
                      <button
                        onClick={() => { setDeletingUserId(user.id); setConfirmDeleteUsername(''); }}
                        className="px-3 py-1 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition"
                        title="Delete user"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </td>
                </tr>
                {expandedUserId === user.id && (
                  <tr className="bg-gray-50">
                    <td colSpan={8} className="px-6 py-5">
                      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                        <div className="flex items-start gap-5">
                          {/* Avatar */}
                          <div className="flex-shrink-0 h-16 w-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                            <span className="text-white text-2xl font-bold">
                              {user.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          {/* Details */}
                          <div className="flex-1 grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Username</p>
                              <p className="text-sm font-semibold text-gray-900 mt-0.5">{user.username}</p>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Email</p>
                              <p className="text-sm text-gray-900 mt-0.5">{user.email}</p>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">User ID</p>
                              <p className="text-sm text-gray-900 mt-0.5">#{user.id}</p>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Role</p>
                              <p className="text-sm text-gray-900 mt-0.5">{user.role === 'admin' ? '👑 Administrator' : '👤 Regular User'}</p>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Account Status</p>
                              <span className={`inline-flex items-center gap-1 text-sm mt-0.5 ${
                                user.is_active ? 'text-green-700' : 'text-red-700'
                              }`}>
                                <span className={`h-2 w-2 rounded-full ${user.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                                {user.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Created</p>
                              <p className="text-sm text-gray-900 mt-0.5">
                                {new Date(user.created_at).toLocaleDateString('en-US', {
                                  year: 'numeric', month: 'long', day: 'numeric'
                                })}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Delete History Permission</p>
                              <p className="text-sm text-gray-900 mt-0.5">{user.can_delete_history ? '✅ Allowed' : '❌ Not Allowed'}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {users.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No users found
          </div>
        )}
        {users.length > 0 && userSearch && users.filter(u =>
          u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
          u.email.toLowerCase().includes(userSearch.toLowerCase())
        ).length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            No users match &ldquo;{userSearch}&rdquo;
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-2xl font-bold text-gray-900">{users.length}</div>
          <div className="text-sm text-gray-600">Total Users</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-2xl font-bold text-purple-600">
            {users.filter(u => u.role === 'admin').length}
          </div>
          <div className="text-sm text-gray-600">Admins</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-600">
            {users.filter(u => u.is_active).length}
          </div>
          <div className="text-sm text-gray-600">Active Users</div>
        </div>
      </div>

      {/* ===== Edit User Modal ===== */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-lg font-bold text-gray-900">Edit User — {editingUser.username}</h3>
              <button onClick={() => setEditingUser(null)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>

            <form onSubmit={handleUpdateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  type="text"
                  value={editForm.username}
                  onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  minLength={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New Password <span className="text-gray-400 font-normal">(leave blank to keep current)</span>
                </label>
                <div className="relative">
                  <input
                    type={showEditPassword ? 'text' : 'password'}
                    value={editForm.password}
                    onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
                    placeholder="Min 6 characters"
                    minLength={6}
                  />
                  <EyeButton show={showEditPassword} onToggle={() => setShowEditPassword(!showEditPassword)} />
                </div>
                <PasswordStrength password={editForm.password} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                  <select
                    value={editForm.role}
                    onChange={(e) => setEditForm({ ...editForm, role: e.target.value as 'user' | 'admin' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={editForm.is_active ? 'active' : 'inactive'}
                    onChange={(e) => setEditForm({ ...editForm, is_active: e.target.value === 'active' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 pt-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition font-medium text-sm disabled:opacity-60"
                >
                  {saving ? <><Spinner /> Saving…</> : '✓ Save Changes'}
                </button>
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===== Delete Confirmation Modal ===== */}
      {deletingUserId !== null && (() => {
        const userToDelete = users.find(u => u.id === deletingUserId);
        if (!userToDelete) return null;
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-red-600 text-lg">🗑️</span>
                </div>
                <h3 className="text-lg font-bold text-gray-900">Delete User</h3>
              </div>

              <p className="text-sm text-gray-600 mb-2">
                Are you sure you want to permanently delete <strong>{userToDelete.username}</strong>?
                This action cannot be undone.
              </p>

              <p className="text-sm text-gray-500 mb-4">
                Type <strong>{userToDelete.username}</strong> to confirm:
              </p>

              <input
                type="text"
                value={confirmDeleteUsername}
                onChange={(e) => setConfirmDeleteUsername(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
                placeholder={userToDelete.username}
                autoFocus
              />

              <div className="flex gap-3">
                <button
                  onClick={() => handleDeleteUser(userToDelete.id)}
                  disabled={confirmDeleteUsername !== userToDelete.username || deleting}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium text-sm disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {deleting ? <><Spinner /> Deleting…</> : '🗑️ Delete User'}
                </button>
                <button
                  onClick={() => { setDeletingUserId(null); setConfirmDeleteUsername(''); }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
