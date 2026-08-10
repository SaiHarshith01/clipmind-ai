'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, Upload, FileVideo, CheckCircle2, AlertTriangle, Cpu, UserCheck } from 'lucide-react';

interface UserProfile {
  id: number;
  email: string;
  role: string;
}

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 1. Authenticate user session
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetch('http://localhost:8000/api/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error('Session expired');
        }
        return res.json();
      })
      .then((data) => {
        setUser(data);
        setLoading(false);
      })
      .catch(() => {
        localStorage.removeItem('token');
        router.push('/login');
      });
  }, [router]);

  // 2. Handle Logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  // 3. Handle File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
      setSuccess('');
    }
  };

  // 4. Poll Video Status
  const pollVideoStatus = (videoId: number) => {
    const token = localStorage.getItem('token');
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/videos/${videoId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        const data = await response.json();
        
        if (response.ok) {
          if (data.status === 'completed') {
            setUploadStatus(`Video ID: ${videoId} - Completed! Audio extracted successfully.`);
            clearInterval(interval);
          } else if (data.status === 'failed') {
            setUploadStatus(`Video ID: ${videoId} - Processing Failed.`);
            clearInterval(interval);
          } else {
            setUploadStatus(`Video ID: ${videoId} - Processing: (${data.status})...`);
          }
        }
      } catch (err) {
        console.error("Error polling video status:", err);
        clearInterval(interval);
      }
    }, 2500); // Poll every 2.5 seconds
  };

  // 5. Handle Video Upload
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError('');
    setSuccess('');
    setUploadStatus('Uploading file to backend...');

    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/videos/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to upload video');
      }

      setSuccess('Video successfully uploaded! FFmpeg processing started in background.');
      setUploadStatus(`Video ID: ${data.video_id} - Processing started...`);
      setFile(null);
      
      // Start polling status
      pollVideoStatus(data.video_id);
    } catch (err: any) {
      setError(err.message || 'An error occurred during upload.');
      setUploadStatus('');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex justify-center items-center text-slate-400">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading Dashboard...</span>
        </div>
      </div>
    );
  }

  // Check if role is authorized to upload
  const canUpload = user && user.role !== 'Learner';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar header */}
      <header className="border-b border-slate-900 bg-slate-900/50 backdrop-blur px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Cpu className="w-6 h-6 text-indigo-400" />
          <span className="font-extrabold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
            ClipMind AI
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
            <UserCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-400 font-semibold">{user?.email}</span>
            <span className="bg-indigo-950 border border-indigo-800 text-indigo-300 px-2 py-0.5 rounded font-bold text-[10px]">
              {user?.role}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 bg-red-950/20 hover:bg-red-950/50 border border-red-900/50 hover:border-red-800/80 text-red-300 text-xs px-3 py-1.5 rounded-lg transition-colors font-semibold active:scale-[0.98]"
          >
            <LogOut className="w-3.5 h-3.5" />
            Log Out
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-10 space-y-8">
          <h2 className="text-2xl font-bold tracking-tight">Video Upload Dashboard</h2>
          <p className="text-slate-400 text-sm mt-1">
            Upload video files to extract transcripts, generate summaries, and analyze key moments.
          </p>

        {/* Video uploader card */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-8 shadow-xl">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileVideo className="w-5 h-5 text-indigo-400" />
            Video Processing Center
          </h3>

          {!canUpload ? (
            /* RBAC Warning for Learners */
            <div className="flex items-start gap-3 bg-amber-950/30 border border-amber-800/60 p-4 rounded-xl text-amber-300 text-sm">
              <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
              <div>
                <h4 className="font-bold mb-1">Role Permission Restriction</h4>
                <p className="text-amber-400/80 leading-relaxed">
                  Your current account role is set as **Learner**. Learners are restricted to read-only access and do not have permission to execute video uploads or trigger background processing tasks.
                </p>
              </div>
            </div>
          ) : (
            /* Uploader layout for Creator/Educator/Admin */
            <form onSubmit={handleUpload} className="space-y-6">
              {error && (
                <div className="flex items-center gap-2 bg-red-950/40 border border-red-800 text-red-300 text-xs p-3 rounded-lg">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="flex items-center gap-2 bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs p-3 rounded-lg">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{success}</span>
                </div>
              )}

              {/* Upload Drop Zone */}
              <div className="border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-xl p-8 transition-colors flex flex-col items-center justify-center cursor-pointer relative bg-slate-950/50">
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={uploading}
                />
                <Upload className="w-10 h-10 text-slate-500 mb-3" />
                {file ? (
                  <div className="text-center">
                    <span className="text-indigo-400 font-semibold text-sm block max-w-xs truncate mx-auto">
                      {file.name}
                    </span>
                    <span className="text-slate-500 text-xs mt-1 block">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>
                ) : (
                  <div className="text-center">
                    <span className="text-slate-300 text-sm font-medium block">
                      Drag & drop your video file here, or click to browse
                    </span>
                    <span className="text-slate-500 text-xs mt-1 block">
                      Supports MP4, WebM, AVI, MOV (Max 50MB)
                    </span>
                  </div>
                )}
              </div>

              {/* Upload Button */}
              {file && (
                <button
                  type="submit"
                  disabled={uploading}
                  className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-semibold py-2.5 rounded-lg text-sm transition-all shadow-lg shadow-indigo-600/10 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none"
                >
                  {uploading ? 'Uploading...' : 'Process Video'}
                </button>
              )}
            </form>
          )}

          {/* Job Processing Status */}
          {uploadStatus && (
            <div className="mt-6 border-t border-slate-800 pt-6">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                Live Processing Log:
              </h4>
              <div className="bg-slate-950 font-mono text-xs p-3 rounded-lg border border-slate-800/80 text-blue-300 flex items-center gap-2">
                <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-ping"></div>
                <span>{uploadStatus}</span>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
