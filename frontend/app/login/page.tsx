'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { KeyRound, Mail, User as UserIcon, ShieldAlert } from 'lucide-react';

export default function Login() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('Learner'); // Learner, Content Creator, Educator, Administrator
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (isLogin) {
        // --- LOGIN FLOW ---
        // OAuth2PasswordRequestForm expects url-encoded Form Data
        const params = new URLSearchParams();
        params.append('username', email); // Swagger expects email inside 'username'
        params.append('password', password);

        const response = await fetch('http://localhost:8000/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: params.toString(),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Invalid email or password');
        }

        // Store token in localStorage
        localStorage.setItem('token', data.access_token);
        
        setSuccess('Logged in successfully! Redirecting...');
        setTimeout(() => {
          router.push('/dashboard');
        }, 1500);
      } else {
        // --- REGISTER FLOW ---
        // Register expects JSON body
        const response = await fetch('http://localhost:8000/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            password,
            role, // Backend automatically registers as enum value or uses default
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to register account');
        }

        setSuccess('Account registered successfully! Please log in.');
        setIsLogin(true); // Toggle to login tab
        setPassword('');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An error occurred. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 relative overflow-hidden">
      {/* Background styling elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-md z-10">
        {/* Title branding */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400">
            ClipMind AI
          </h1>
          <p className="text-slate-400 text-sm mt-2 font-medium">
            Video Summarization & Key Moments Detection
          </p>
        </div>

        {/* Auth card container */}
        <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-8 shadow-2xl">
          {/* Card Toggle Tabs */}
          <div className="flex border-b border-slate-800 mb-6 pb-2">
            <button
              onClick={() => { setIsLogin(true); setError(''); setSuccess(''); }}
              className={`flex-1 pb-2 text-center text-sm font-semibold transition-colors duration-200 ${
                isLogin ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setIsLogin(false); setError(''); setSuccess(''); }}
              className={`flex-1 pb-2 text-center text-sm font-semibold transition-colors duration-200 ${
                !isLogin ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="flex items-center gap-2 bg-red-950/50 border border-red-800 text-red-300 text-xs p-3 rounded-lg animate-pulse">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="bg-emerald-950/50 border border-emerald-800 text-emerald-300 text-xs p-3 rounded-lg">
                {success}
              </div>
            )}

            {/* Email field */}
            <div className="space-y-1">
              <label className="text-slate-300 text-xs font-semibold">Email Address</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <Mail className="w-4 h-4" />
                </span>
                <input
                  type="email"
                  required
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500/80 transition-colors"
                />
              </div>
            </div>

            {/* Password field */}
            <div className="space-y-1">
              <label className="text-slate-300 text-xs font-semibold">Password</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <KeyRound className="w-4 h-4" />
                </span>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500/80 transition-colors"
                />
              </div>
            </div>

            {/* Role select (ONLY during registration) */}
            {!isLogin && (
              <div className="space-y-1">
                <label className="text-slate-300 text-xs font-semibold">Select Account Role</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                    <UserIcon className="w-4 h-4" />
                  </span>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-100 focus:outline-none focus:border-blue-500/80 transition-colors appearance-none cursor-pointer"
                  >
                    <option value="Learner">Learner (Read-Only)</option>
                    <option value="Content Creator">Content Creator (Can Upload)</option>
                    <option value="Educator">Educator (Can Upload)</option>
                    <option value="Administrator">Administrator (All Access)</option>
                  </select>
                </div>
              </div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-semibold py-2.5 rounded-lg transition-all duration-200 shadow-lg shadow-indigo-600/20 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none mt-2"
            >
              {loading ? 'Processing...' : isLogin ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
