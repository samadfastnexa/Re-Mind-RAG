'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';

// Password strength scorer — returns 0‑4
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
const STRENGTH_COLORS = ['', 'bg-red-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];
const STRENGTH_TEXT   = ['', 'text-red-600', 'text-yellow-600', 'text-blue-600', 'text-green-600'];

export default function LoginPage() {
    const [username, setUsername]       = useState('');
    const [password, setPassword]       = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading]         = useState(false);
    const [shake, setShake]             = useState(false);
    const [capsLock, setCapsLock]       = useState(false);
    const [touched, setTouched]         = useState({ username: false, password: false });
    const usernameRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

    // Auto-focus username on mount
    useEffect(() => { usernameRef.current?.focus(); }, []);

    const usernameErr = touched.username && username.trim().length < 3
        ? 'Username must be at least 3 characters'
        : '';
    const passwordErr = touched.password && password.length < 6
        ? 'Password must be at least 6 characters'
        : '';
    const canSubmit = !loading && username.trim().length >= 3 && password.length >= 6;

    const pwStrength = scorePassword(password);

    const triggerShake = () => {
        setShake(true);
        setTimeout(() => setShake(false), 600);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setTouched({ username: true, password: true });
        if (!canSubmit) { triggerShake(); return; }

        setLoading(true);
        const toastId = toast.loading('Signing in…');
        try {
            await api.login(username.trim(), password);
            toast.success('Welcome back!', { id: toastId, duration: 1500 });
            router.push('/');
        } catch (err: any) {
            const msg = err.message || 'Login failed';
            toast.error(msg, { id: toastId, duration: 5000 });
            triggerShake();
            setLoading(false);
        }
    };

    const handleCapsLock = (e: React.KeyboardEvent) => {
        setCapsLock(e.getModifierState('CapsLock'));
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 via-white to-orange-100 px-4">
            <div className={`bg-white rounded-2xl shadow-2xl w-full max-w-md transition-all ${
                shake ? 'animate-[shake_0.5s_ease-in-out]' : ''
            }`}
                style={shake ? { animation: 'shake 0.5s' } : {}}
            >
                {/* Top accent bar */}
                <div className="h-1.5 rounded-t-2xl bg-gradient-to-r from-orange-400 to-orange-600" />

                <div className="px-8 py-8">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl shadow-lg mb-4">
                            <span className="text-white text-2xl">🔐</span>
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900">Welcome back</h1>
                        <p className="text-sm text-gray-500 mt-1">Sign in to your RAG System account</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                        {/* Username */}
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1.5">
                                Username
                            </label>
                            <input
                                ref={usernameRef}
                                id="username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                onBlur={() => setTouched(t => ({ ...t, username: true }))}
                                className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition text-sm ${
                                    usernameErr ? 'border-red-400 bg-red-50' :
                                    touched.username && username.trim().length >= 3 ? 'border-green-400' :
                                    'border-gray-300'
                                }`}
                                placeholder="Enter your username"
                                autoComplete="username"
                                disabled={loading}
                            />
                            {usernameErr && (
                                <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
                                    <span>⚠</span> {usernameErr}
                                </p>
                            )}
                        </div>

                        {/* Password */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
                                Password
                            </label>
                            <div className="relative">
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    onBlur={() => setTouched(t => ({ ...t, password: true }))}
                                    onKeyDown={handleCapsLock}
                                    onKeyUp={handleCapsLock}
                                    className={`w-full px-4 py-3 pr-12 border rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition text-sm ${
                                        passwordErr ? 'border-red-400 bg-red-50' :
                                        touched.password && password.length >= 6 ? 'border-green-400' :
                                        'border-gray-300'
                                    }`}
                                    placeholder="Enter your password"
                                    autoComplete="current-password"
                                    disabled={loading}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none transition"
                                    tabIndex={-1}
                                >
                                    {showPassword ? (
                                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                                        </svg>
                                    ) : (
                                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                        </svg>
                                    )}
                                </button>
                            </div>

                            {/* Password strength bar (only shown when typing) */}
                            {password.length > 0 && (
                                <div className="mt-2">
                                    <div className="flex gap-1 h-1.5">
                                        {[1,2,3,4].map(i => (
                                            <div key={i} className={`flex-1 rounded-full transition-all duration-300 ${
                                                i <= pwStrength ? STRENGTH_COLORS[pwStrength] : 'bg-gray-200'
                                            }`} />
                                        ))}
                                    </div>
                                    {pwStrength > 0 && (
                                        <p className={`text-xs mt-1 font-medium ${STRENGTH_TEXT[pwStrength]}`}>
                                            {STRENGTH_LABELS[pwStrength]} password
                                        </p>
                                    )}
                                </div>
                            )}

                            {passwordErr && (
                                <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
                                    <span>⚠</span> {passwordErr}
                                </p>
                            )}

                            {/* Caps Lock warning */}
                            {capsLock && !showPassword && (
                                <p className="mt-1 text-xs text-amber-600 flex items-center gap-1">
                                    <span>⇪</span> Caps Lock is on
                                </p>
                            )}
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 disabled:from-gray-400 disabled:to-gray-400 text-white font-semibold py-3 px-6 rounded-xl transition-all shadow-md hover:shadow-lg disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                                    </svg>
                                    Signing in…
                                </>
                            ) : 'Sign In'}
                        </button>
                    </form>

                    {/* Default credentials hint */}
                    <div className="mt-6 p-4 bg-orange-50 border border-orange-200 rounded-xl">
                        <p className="text-xs font-semibold text-orange-900 mb-2">Default Admin Credentials</p>
                        <div className="flex gap-4 text-xs text-orange-800">
                            <span>Username: <code className="bg-orange-100 px-1.5 py-0.5 rounded font-mono">admin</code></span>
                            <span>Password: <code className="bg-orange-100 px-1.5 py-0.5 rounded font-mono">admin123</code></span>
                        </div>
                        <p className="text-xs text-orange-600 mt-2">
                            ⚠️ Change password after first login
                        </p>
                    </div>

                    <p className="mt-4 text-center text-xs text-gray-400">
                        Contact admin to create your account
                    </p>
                </div>
            </div>

            {/* Shake keyframe */}
            <style>{`
                @keyframes shake {
                    0%,100%{ transform:translateX(0) }
                    20%{ transform:translateX(-8px) }
                    40%{ transform:translateX(8px) }
                    60%{ transform:translateX(-6px) }
                    80%{ transform:translateX(6px) }
                }
            `}</style>
        </div>
    );
}
