'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  LogOut, Upload, FileVideo, CheckCircle2, AlertTriangle, Cpu, 
  UserCheck, Sparkles, BookOpen, Search, Copy, Check, Tag, Clock
} from 'lucide-react';

interface UserProfile {
  id: number;
  email: string;
  role: string;
}

interface SummaryData {
  video_id: number;
  filename: string;
  short_summary: string;
  key_takeaways: string[];
  keywords: string[];
  word_count: number;
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

  // Milestone 2 States
  const [completedVideoId, setCompletedVideoId] = useState<number | null>(null);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [transcriptText, setTranscriptText] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'summary' | 'transcript'>('summary');
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [fetchingResults, setFetchingResults] = useState(false);

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

  // 2. Fetch AI Summary & Transcript upon completion
  const fetchVideoResults = async (videoId: number) => {
    setFetchingResults(true);
    const token = localStorage.getItem('token');

    try {
      // Fetch Summary
      const summaryRes = await fetch(`http://localhost:8000/api/videos/${videoId}/summary`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (summaryRes.ok) {
        const sumData = await summaryRes.json();
        setSummaryData(sumData);
      }

      // Fetch Transcript
      const transcriptRes = await fetch(`http://localhost:8000/api/videos/${videoId}/transcript`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (transcriptRes.ok) {
        const transData = await transcriptRes.json();
        setTranscriptText(transData.transcript);
      }
    } catch (err) {
      console.error("Error fetching AI results:", err);
    } finally {
      setFetchingResults(false);
    }
  };

  // 3. Handle Logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  // 4. Handle File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
      setSuccess('');
      setSummaryData(null);
      setTranscriptText('');
    }
  };

  // 5. Poll Video Status
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
            setUploadStatus(`Video ID: ${videoId} — Completed! AI Transcription & Summary ready.`);
            setCompletedVideoId(videoId);
            fetchVideoResults(videoId);
            clearInterval(interval);
          } else if (data.status === 'failed') {
            setUploadStatus(`Video ID: ${videoId} — Processing Failed.`);
            clearInterval(interval);
          } else if (data.status === 'transcribing') {
            setUploadStatus(`Video ID: ${videoId} — Transcribing speech with Whisper AI...`);
          } else if (data.status === 'summarizing') {
            setUploadStatus(`Video ID: ${videoId} — Generating NLP Summaries & Key Takeaways...`);
          } else {
            setUploadStatus(`Video ID: ${videoId} — Processing (${data.status})...`);
          }
        }
      } catch (err) {
        console.error("Error polling video status:", err);
        clearInterval(interval);
      }
    }, 2000);
  };

  // 6. Handle Video Upload
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError('');
    setSuccess('');
    setSummaryData(null);
    setTranscriptText('');
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

      setSuccess('Video uploaded! Background pipeline started.');
      setUploadStatus(`Video ID: ${data.video_id} — Extracting audio & preparing AI models...`);
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

  // 7. Copy Transcript Helper
  const handleCopyTranscript = () => {
    navigator.clipboard.writeText(transcriptText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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

  const canUpload = user && user.role !== 'Learner';

  // Highlight search matches in transcript
  const getHighlightedText = (text: string, highlight: string) => {
    if (!highlight.trim()) return text;
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
    return parts.map((part, i) =>
      part.toLowerCase() === highlight.toLowerCase() ? (
        <mark key={i} className="bg-amber-400/30 text-amber-200 px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans pb-16">
      {/* Navbar header */}
      <header className="border-b border-slate-900 bg-slate-900/50 backdrop-blur px-8 py-4 flex justify-between items-center sticky top-0 z-30">
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
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Video Processing & Summarization</h2>
          <p className="text-slate-400 text-sm mt-1">
            Upload videos to automatically generate AI transcripts, concise abstracts, and key bullet takeaways.
          </p>
        </div>

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
                  Your current account role is set as **Learner**. Learners have read-only access and cannot upload new videos.
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
                  {uploading ? 'Uploading...' : 'Process & Summarize Video'}
                </button>
              )}
            </form>
          )}

          {/* Job Processing Status */}
          {uploadStatus && (
            <div className="mt-6 border-t border-slate-800 pt-6">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                Live Pipeline Status:
              </h4>
              <div className="bg-slate-950 font-mono text-xs p-3 rounded-lg border border-slate-800/80 text-blue-300 flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${completedVideoId ? 'bg-emerald-400' : 'bg-blue-500 animate-ping'}`}></div>
                <span>{uploadStatus}</span>
              </div>
            </div>
          )}
        </div>

        {/* Milestone 2: AI Output Display Cards */}
        {(summaryData || transcriptText) && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
            {/* Tabs Header */}
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`flex items-center gap-2 text-sm font-bold pb-2 border-b-2 transition-colors ${
                    activeTab === 'summary'
                      ? 'text-indigo-400 border-indigo-400'
                      : 'text-slate-400 border-transparent hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  AI Summary & Takeaways
                </button>
                <button
                  onClick={() => setActiveTab('transcript')}
                  className={`flex items-center gap-2 text-sm font-bold pb-2 border-b-2 transition-colors ${
                    activeTab === 'transcript'
                      ? 'text-indigo-400 border-indigo-400'
                      : 'text-slate-400 border-transparent hover:text-slate-200'
                  }`}
                >
                  <BookOpen className="w-4 h-4 text-blue-400" />
                  Full Transcript
                </button>
              </div>

              {/* Word Count Metric */}
              {summaryData?.word_count && (
                <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-950 px-3 py-1 rounded-md border border-slate-800">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  <span>{summaryData.word_count} words analyzed</span>
                </div>
              )}
            </div>

            {/* TAB 1: SUMMARY CONTENT */}
            {activeTab === 'summary' && summaryData && (
              <div className="space-y-6">
                {/* Short Overview */}
                <div className="bg-indigo-950/20 border border-indigo-900/40 rounded-xl p-5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300 mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    Executive Overview
                  </h4>
                  <p className="text-slate-200 text-sm leading-relaxed font-normal">
                    {summaryData.short_summary}
                  </p>
                </div>

                {/* Key Takeaways */}
                {summaryData.key_takeaways.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Key Insights & Highlights:
                    </h4>
                    <ul className="space-y-2">
                      {summaryData.key_takeaways.map((takeaway, idx) => (
                        <li key={idx} className="flex items-start gap-2.5 bg-slate-950/70 border border-slate-800/80 p-3 rounded-lg text-sm text-slate-300">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{takeaway}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Keywords Tags */}
                {summaryData.keywords.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-slate-800/60">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Tag className="w-3.5 h-3.5 text-slate-500" />
                      Extracted Keywords:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {summaryData.keywords.map((kw, i) => (
                        <span key={i} className="text-xs bg-slate-950 text-indigo-300 border border-slate-800 px-2.5 py-1 rounded-md font-medium">
                          #{kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: TRANSCRIPT CONTENT */}
            {activeTab === 'transcript' && (
              <div className="space-y-4">
                {/* Search Bar & Copy Button */}
                <div className="flex justify-between items-center gap-3">
                  <div className="relative flex-1">
                    <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Search within transcript text..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                  <button
                    onClick={handleCopyTranscript}
                    className="flex items-center gap-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs px-3 py-2 rounded-lg transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>

                {/* Transcript Box */}
                <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 max-h-72 overflow-y-auto font-sans text-sm text-slate-300 leading-relaxed space-y-2 select-text">
                  <p>{getHighlightedText(transcriptText, searchQuery)}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
