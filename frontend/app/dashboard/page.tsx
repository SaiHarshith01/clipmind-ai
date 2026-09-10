'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  LogOut, Upload, FileVideo, CheckCircle2, AlertTriangle, Cpu, 
  Sparkles, Search, Copy, Check, Tag, Clock,
  Trash2, Play, Download, Star, Gauge, FileText, Activity,
  Send, Bot, User as UserIcon, X, Plus, Film, Video
} from 'lucide-react';

interface UserProfile {
  id: number;
  email: string;
  role: string;
}

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface VideoHistoryItem {
  id: number;
  title: string;
  filename: string;
  status: string;
  uploaded_at: string;
}

interface KeyTakeaway {
  hook?: string;
  start?: number;
  thumbnail_url?: string;
  [key: string]: unknown;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestampCitations?: number[];
}

interface SummaryData {
  video_id: number;
  filename: string;
  short_summary: string;
  detailed_summary?: string;
  key_takeaways: KeyTakeaway[];
  keywords: string[];
  sentiment?: string;
  tone?: string;
  key_entities?: string[];
  analytics?: {
    duration_seconds?: number;
    speaking_wpm?: number;
    reading_time_minutes?: number;
    time_saved_minutes?: number;
    pacing_label?: string;
  };
  word_count: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let msgSequence = 0;
function createMsgId(prefix: string): string {
  msgSequence += 1;
  return `${prefix}-${msgSequence}-${Date.now()}`;
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
  const [historyList, setHistoryList] = useState<VideoHistoryItem[]>([]);
  const [historySearch, setHistorySearch] = useState('');

  // Video and Intelligence States
  const [completedVideoId, setCompletedVideoId] = useState<number | null>(null);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [transcriptText, setTranscriptText] = useState<string>('');
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  
  // Tab states: summary | transcript | moments | insights
  const [activeTab, setActiveTab] = useState<'summary' | 'transcript' | 'moments' | 'insights'>('summary');
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [fetchingResults, setFetchingResults] = useState(false);
  
  // Upload modal / tabs
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploaderTab, setUploaderTab] = useState<'file' | 'youtube'>('file');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  
  // Actions
  const [isBookmarked, setIsBookmarked] = useState<boolean>(false);
  const [downloadingExport, setDownloadingExport] = useState<string | null>(null);

  // Floating Chatbot states
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (isChatOpen && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isChatOpen]);

  // 1.0 Fetch Video History List
  const fetchHistoryList = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API_BASE_URL}/api/videos/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error("Error fetching video history list:", err);
    }
  };

  // 1. Authenticate user session
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetch(`${API_BASE_URL}/api/auth/me`, {
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
        fetchHistoryList();
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
      const summaryRes = await fetch(`${API_BASE_URL}/api/videos/${videoId}/summary`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (summaryRes.ok) {
        const sumData = await summaryRes.json();
        setSummaryData(sumData);
      }

      // Fetch Transcript
      const transcriptRes = await fetch(`${API_BASE_URL}/api/videos/${videoId}/transcript`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (transcriptRes.ok) {
        const transData = await transcriptRes.json();
        setTranscriptText(transData.transcript);
        setSegments(transData.segments || []);
      }

      // Check Bookmark status
      fetch(`${API_BASE_URL}/api/videos/${videoId}/is_bookmarked`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).then(r => r.json()).then(d => setIsBookmarked(Boolean(d.bookmarked))).catch(() => {});
    } catch (err) {
      console.error("Error fetching AI results:", err);
    } finally {
      setFetchingResults(false);
    }
  };

  const handleExport = async (format: 'txt' | 'docx' | 'json') => {
    if (!completedVideoId) return;
    setDownloadingExport(format);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/api/videos/${completedVideoId}/export/${format}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clipmind_${completedVideoId}.${format === 'docx' ? 'docx' : (format === 'json' ? 'json' : 'txt')}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error(err);
      alert("Failed to download export file.");
    } finally {
      setDownloadingExport(null);
    }
  };

  const handleToggleBookmark = async () => {
    if (!completedVideoId) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/api/videos/${completedVideoId}/bookmark`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIsBookmarked(data.bookmarked);
      }
    } catch (err) {
      console.error("Error toggling bookmark:", err);
    }
  };

  const handleSendQuestion = async (queryOverride?: string) => {
    const query = (queryOverride || chatInput).trim();
    if (!query || !completedVideoId || isAsking) return;

    const userMsg: ChatMessage = {
      id: createMsgId('user'),
      sender: 'user',
      text: query
    };

    setChatMessages(prev => [...prev, userMsg]);
    if (!queryOverride) setChatInput('');
    setIsAsking(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/api/videos/${completedVideoId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: query })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Bot error");

      const botMsg: ChatMessage = {
        id: createMsgId('bot'),
        sender: 'bot',
        text: data.answer,
        timestampCitations: data.timestamp_citations || []
      };

      setChatMessages(prev => [...prev, botMsg]);
    } catch {
      const errMsg: ChatMessage = {
        id: createMsgId('bot-err'),
        sender: 'bot',
        text: "Sorry, I had trouble analyzing that question. Please try asking again."
      };
      setChatMessages(prev => [...prev, errMsg]);
    } finally {
      setIsAsking(false);
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
    }
  };

  // 5. Poll Video Status
  const pollVideoStatus = (videoId: number) => {
    const token = localStorage.getItem('token');
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/videos/${videoId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        const data = await response.json();
        
        if (response.ok) {
          if (data.status === 'completed') {
            setUploadStatus(`Video #${videoId} ready! Summaries & Key Moments available.`);
            setCompletedVideoId(videoId);
            fetchVideoResults(videoId);
            fetchHistoryList();
            setShowUploadModal(false);
            clearInterval(interval);
          } else if (data.status === 'failed') {
            setUploadStatus(`Video #${videoId} — Processing failed.`);
            fetchHistoryList();
            clearInterval(interval);
          } else if (data.status === 'transcribing') {
            setUploadStatus(`Video #${videoId} — Transcribing speech with Whisper GPU...`);
          } else if (data.status === 'summarizing') {
            setUploadStatus(`Video #${videoId} — Generating NLP Summaries & Key Moments...`);
          } else {
            setUploadStatus(`Video #${videoId} — Processing (${data.status})...`);
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
    setUploadStatus('Uploading file to backend...');

    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/videos/upload`, {
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
      setUploadStatus(`Video #${data.video_id} — Extracting audio & preparing AI models...`);
      setFile(null);
      fetchHistoryList();
      pollVideoStatus(data.video_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An error occurred during upload.';
      setError(message);
      setUploadStatus('');
    } finally {
      setUploading(false);
    }
  };

  const handleYouTubeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;

    setUploading(true);
    setError('');
    setSuccess('');
    setUploadStatus('Submitting YouTube URL to backend...');

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_BASE_URL}/api/videos/youtube`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ url: youtubeUrl.trim() }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'YouTube queue failed.');
      }

      setSuccess('YouTube video queued successfully!');
      setUploadStatus(`Video #${data.video_id} — Initiating download stream...`);
      setYoutubeUrl('');
      fetchHistoryList();
      pollVideoStatus(data.video_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An error occurred during queue submission.';
      setError(message);
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

  const seekTo = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.muted = false;
      videoRef.current.play().catch(err => {
        console.warn("Play interrupted by browser autoplay restrictions:", err);
      });
    }
  };

  const handleSelectHistoryVideo = (v: VideoHistoryItem) => {
    setSummaryData(null);
    setTranscriptText('');
    setSegments([]);
    setCompletedVideoId(null);
    setError('');
    setSuccess('');
    
    if (v.status === 'completed') {
      setCompletedVideoId(v.id);
      setUploadStatus('');
      fetchVideoResults(v.id);
    } else if (v.status === 'failed') {
      setUploadStatus(`Video #${v.id} — Processing Failed.`);
    } else {
      setUploadStatus(`Video #${v.id} — Processing (${v.status})...`);
      pollVideoStatus(v.id);
    }
  };

  const handleDeleteVideo = async (videoId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this video and its AI summaries?")) {
      return;
    }

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_BASE_URL}/api/videos/${videoId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setSuccess("Video deleted successfully.");
        if (completedVideoId === videoId) {
          setCompletedVideoId(null);
          setSummaryData(null);
          setTranscriptText('');
          setSegments([]);
          setUploadStatus('');
        }
        fetchHistoryList();
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to delete video.");
      }
    } catch {
      setError("Network error while trying to delete video.");
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

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

  // Render markdown helper
  const renderMarkdown = (text: string | string[] | null | undefined) => {
    if (!text) return null;
    let textString = "";
    if (Array.isArray(text)) {
      textString = text.join("\n");
    } else if (typeof text === 'string') {
      textString = text;
    } else {
      return null;
    }
    const lines = textString.split('\n');
    return (
      <div className="space-y-2">
        {lines.map((line, idx) => {
          let trimmed = line.trim();
          if (!trimmed) return <div key={idx} className="h-2" />;
          
          const isBullet = trimmed.startsWith('- ') || trimmed.startsWith('* ');
          if (isBullet) {
            trimmed = trimmed.replace(/^[-*]\s+/, '');
          }

          const parts = trimmed.split(/(\**.*?\**)/g);
          const parsed = parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={pIdx} className="text-indigo-300 font-semibold">{part.slice(2, -2)}</strong>;
            }
            return part;
          });

          return (
            <div key={idx} className={`text-xs text-slate-300 leading-relaxed ${isBullet ? 'flex gap-2 items-start pl-2' : ''}`}>
              {isBullet && <span className="text-indigo-400 font-bold select-none">•</span>}
              <div>{parsed}</div>
            </div>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex justify-center items-center text-slate-400">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm">Loading ClipMind Studio...</span>
        </div>
      </div>
    );
  }

  const canUpload = user && user.role !== 'Learner';
  const filteredHistory = historyList.filter(v => 
    v.title.toLowerCase().includes(historySearch.toLowerCase()) || 
    v.filename.toLowerCase().includes(historySearch.toLowerCase())
  );
  const activeVideo = historyList.find(v => v.id === completedVideoId);

  return (
    <div className="h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 flex flex-col font-sans select-none">
      
      {/* ========================================================================= */}
      {/* 3-COLUMN STUDIO LAYOUT                                                   */}
      {/* ========================================================================= */}
      <div className="flex-1 flex overflow-hidden">

        {/* --------------------------------------------------------------------- */}
        {/* COLUMN 1: HISTORY & LIBRARY (Left Sidebar)                            */}
        {/* --------------------------------------------------------------------- */}
        <aside className="w-72 xl:w-80 flex-shrink-0 flex flex-col border-r border-slate-800/80 bg-slate-950/95 backdrop-blur-md h-full">
          
          {/* Logo & Header */}
          <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-600/30">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-tight bg-gradient-to-r from-white via-indigo-200 to-purple-300 bg-clip-text text-transparent">
                  ClipMind AI
                </h1>
                <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">Video Studio</p>
              </div>
            </div>

            {canUpload && (
              <button
                onClick={() => setShowUploadModal(true)}
                className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all hover:scale-105 active:scale-95"
                title="Upload New Video"
              >
                <Plus className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Search Videos Input */}
          <div className="p-3 border-b border-slate-800/60">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input 
                type="text"
                placeholder="Search history..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                className="w-full bg-slate-900/90 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
              />
              {historySearch && (
                <button 
                  onClick={() => setHistorySearch('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* Video List Header */}
          <div className="px-4 py-2 flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            <span>Video History</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 font-mono">
              {filteredHistory.length}
            </span>
          </div>

          {/* Scrollable Video History List */}
          <div className="flex-1 overflow-y-auto px-2.5 py-1 space-y-1.5 custom-scrollbar">
            {filteredHistory.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 space-y-2">
                <FileVideo className="w-8 h-8 mx-auto text-slate-600 opacity-60" />
                <p>{historySearch ? "No matching videos found." : "No videos in your history."}</p>
                {canUpload && (
                  <button
                    onClick={() => setShowUploadModal(true)}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                  >
                    + Upload your first video
                  </button>
                )}
              </div>
            ) : (
              filteredHistory.map((item) => {
                const isSelected = completedVideoId === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => handleSelectHistoryVideo(item)}
                    className={`group relative rounded-xl p-2.5 flex items-start gap-2.5 cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500/70 shadow-md shadow-indigo-950/50'
                        : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-900/80 hover:border-slate-700/80'
                    }`}
                  >
                    {/* Status Icon */}
                    <div className="mt-0.5 flex-shrink-0">
                      {item.status === 'completed' ? (
                        <div className="w-7 h-7 rounded-lg bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </div>
                      ) : item.status === 'failed' ? (
                        <div className="w-7 h-7 rounded-lg bg-red-950/60 border border-red-800/60 flex items-center justify-center text-red-400">
                          <AlertTriangle className="w-3.5 h-3.5" />
                        </div>
                      ) : (
                        <div className="w-7 h-7 rounded-lg bg-indigo-950/60 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
                          <Cpu className="w-3.5 h-3.5 animate-spin" />
                        </div>
                      )}
                    </div>

                    {/* Video Info */}
                    <div className="flex-1 min-w-0 pr-6">
                      <p className={`text-xs font-semibold truncate ${isSelected ? 'text-indigo-200' : 'text-slate-200 group-hover:text-white'}`}>
                        {item.title || item.filename}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[10px] uppercase font-bold tracking-wider ${
                          item.status === 'completed' ? 'text-emerald-400' :
                          item.status === 'failed' ? 'text-red-400' : 'text-indigo-400'
                        }`}>
                          {item.status}
                        </span>
                        <span className="text-[10px] text-slate-500">•</span>
                        <span className="text-[10px] text-slate-500 truncate">
                          {new Date(item.uploaded_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                        </span>
                      </div>
                    </div>

                    {/* Delete Action (Admin/Creator) */}
                    {canUpload && (
                      <button
                        onClick={(e) => handleDeleteVideo(item.id, e)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md hover:bg-red-950/60 hover:text-red-400 text-slate-500 absolute right-2 top-2.5 transition-all"
                        title="Delete video"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* User Profile Footer */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-950 flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-indigo-300">
                {user?.email ? user.email.charAt(0).toUpperCase() : <UserIcon className="w-4 h-4" />}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">{user?.email}</p>
                <span className="inline-block px-1.5 py-0.2 rounded text-[10px] font-semibold bg-indigo-950/60 border border-indigo-800/50 text-indigo-300">
                  {user?.role}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg hover:bg-slate-900 text-slate-400 hover:text-red-400 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </aside>

        {/* --------------------------------------------------------------------- */}
        {/* COLUMN 2: VIDEO PLAYBACK (Center Workspace)                           */}
        {/* --------------------------------------------------------------------- */}
        <main className="flex-1 flex flex-col h-full overflow-y-auto border-r border-slate-800/80 bg-slate-900/20 relative">
          
          {/* Top Bar for Selected Video */}
          <div className="px-6 py-3.5 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40 backdrop-blur-sm">
            <div className="flex items-center gap-3 min-w-0">
              <div className="p-1.5 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-indigo-400">
                <Video className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h2 className="text-sm font-bold text-slate-100 truncate">
                  {activeVideo ? (activeVideo.title || activeVideo.filename) : "No Video Selected"}
                </h2>
                <p className="text-[11px] text-slate-500 truncate">
                  {activeVideo ? `ID: #${activeVideo.id} • ${activeVideo.filename}` : "Select a video from the history panel or upload a new one"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {completedVideoId && (
                <button
                  onClick={handleToggleBookmark}
                  className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all ${
                    isBookmarked 
                      ? 'bg-amber-950/40 border-amber-500/60 text-amber-300' 
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Star className={`w-3.5 h-3.5 ${isBookmarked ? 'fill-amber-400 text-amber-400' : ''}`} />
                  <span className="hidden sm:inline">{isBookmarked ? 'Saved' : 'Bookmark'}</span>
                </button>
              )}

              {canUpload && (
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-md shadow-indigo-600/20"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload / Import</span>
                </button>
              )}
            </div>
          </div>

          {/* Center Playback Area */}
          <div className="flex-1 p-6 flex flex-col justify-start items-center overflow-y-auto space-y-4">
            
            {/* Status alerts */}
            {uploadStatus && (
              <div className="w-full max-w-3xl flex items-center gap-3 p-3 rounded-xl bg-indigo-950/40 border border-indigo-800/60 text-indigo-300 text-xs shadow-lg animate-pulse">
                <Cpu className="w-4 h-4 shrink-0 animate-spin text-indigo-400" />
                <span className="font-mono">{uploadStatus}</span>
              </div>
            )}

            {success && (
              <div className="w-full max-w-3xl flex items-center gap-2 p-3 rounded-xl bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 text-xs">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{success}</span>
              </div>
            )}

            {error && (
              <div className="w-full max-w-3xl flex items-center gap-2 p-3 rounded-xl bg-red-950/50 border border-red-800/60 text-red-300 text-xs">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {completedVideoId ? (
              <div className="w-full max-w-4xl space-y-3">
                {/* HTML5 Video Player */}
                <div className="overflow-hidden rounded-2xl border border-slate-800 bg-black aspect-video flex items-center justify-center shadow-2xl relative group">
                  <video
                    ref={videoRef}
                    src={`${API_BASE_URL}/api/videos/${completedVideoId}/stream?token=${localStorage.getItem('token')}`}
                    controls
                    className="w-full h-full object-contain focus:outline-none"
                  />
                </div>

                {/* Under-player interactive hint */}
                <div className="flex items-center justify-between text-xs px-4 py-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-slate-400">
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Click any <strong>Transcript timestamp</strong> or <strong>Key Moment</strong> to jump video playback instantly.</span>
                  </div>
                  {summaryData?.analytics?.duration_seconds && (
                    <span className="font-mono text-slate-500 text-[11px]">
                      Duration: {formatTime(summaryData.analytics.duration_seconds)}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              /* Empty State / Upload Prompt */
              <div className="w-full max-w-lg my-auto text-center p-8 rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-indigo-950/50 border border-indigo-800/60 flex items-center justify-center mx-auto text-indigo-400 shadow-inner">
                  <FileVideo className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-200">No Video Loaded</h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Select an analyzed video from the <strong>History</strong> sidebar on the left, or upload a new video to generate AI intelligence.
                  </p>
                </div>
                {canUpload && (
                  <button
                    onClick={() => setShowUploadModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-lg shadow-indigo-600/30 hover:scale-105 active:scale-95"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Upload or Import Video</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </main>

        {/* --------------------------------------------------------------------- */}
        {/* COLUMN 3: AI INTELLIGENCE (Right Sidebar Tabs)                        */}
        {/* --------------------------------------------------------------------- */}
        <aside className="w-96 xl:w-[420px] flex-shrink-0 flex flex-col h-full bg-slate-950/95 border-l border-slate-800/80 relative">
          
          {/* Tabs Navigation Header */}
          <div className="p-2 border-b border-slate-800/80 bg-slate-950 flex items-center gap-1">
            {[
              { id: 'summary', label: 'Summary', icon: Sparkles },
              { id: 'transcript', label: 'Transcript', icon: FileText },
              { id: 'moments', label: 'Key Moments', icon: Play },
              { id: 'insights', label: 'Insights', icon: Activity },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as 'summary' | 'transcript' | 'moments' | 'insights')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-1 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Loading data state */}
          {fetchingResults && (
            <div className="flex items-center gap-2 px-4 py-2 bg-indigo-950/40 border-b border-indigo-800/40 text-[11px] text-indigo-300 animate-pulse">
              <div className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
              <span>Updating AI intelligence data...</span>
            </div>
          )}

          {/* Scrollable Tab Content Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 select-text custom-scrollbar pb-24">
            {!completedVideoId ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-2">
                <Cpu className="w-8 h-8 text-slate-600 opacity-60" />
                <p className="text-xs font-semibold text-slate-400">No Intelligence Loaded</p>
                <p className="text-[11px]">Select a completed video to view its summary, transcript, moments, and analytics.</p>
              </div>
            ) : (
              <>
                {/* ---------------- TAB 1: AI SUMMARY ---------------- */}
                {activeTab === 'summary' && (
                  <div className="space-y-4">
                    {/* Executive Summary Hook */}
                    <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">Executive Hook</span>
                        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      </div>
                      <p className="text-xs text-slate-200 font-medium leading-relaxed">
                        {summaryData?.short_summary || "Generating short executive summary..."}
                      </p>
                    </div>

                    {/* Thematic Detailed Breakdown */}
                    {summaryData?.detailed_summary && (
                      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm space-y-2.5">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Thematic Analysis</span>
                        {renderMarkdown(summaryData.detailed_summary)}
                      </div>
                    )}

                    {/* Extracted Keywords */}
                    {summaryData?.keywords && summaryData.keywords.length > 0 && (
                      <div className="space-y-2 pt-1">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
                          <Tag className="w-3 h-3" /> Core Topics & Keywords
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {summaryData.keywords.map((kw, i) => (
                            <span key={i} className="px-2 py-1 rounded-md bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
                              #{kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Export Center */}
                    <div className="pt-2 border-t border-slate-800/80 space-y-2">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Download Reports</span>
                      <div className="grid grid-cols-3 gap-2">
                        <button
                          onClick={() => handleExport('docx')}
                          disabled={Boolean(downloadingExport)}
                          className="flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-indigo-500/50 text-xs font-semibold text-indigo-300 hover:text-white transition-all disabled:opacity-50"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>.DOCX</span>
                        </button>
                        <button
                          onClick={() => handleExport('txt')}
                          disabled={Boolean(downloadingExport)}
                          className="flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-indigo-500/50 text-xs font-semibold text-slate-300 hover:text-white transition-all disabled:opacity-50"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>.TXT</span>
                        </button>
                        <button
                          onClick={() => handleExport('json')}
                          disabled={Boolean(downloadingExport)}
                          className="flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-indigo-500/50 text-xs font-semibold text-purple-300 hover:text-white transition-all disabled:opacity-50"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>.JSON</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* ---------------- TAB 2: TRANSCRIPT ---------------- */}
                {activeTab === 'transcript' && (
                  <div className="space-y-3">
                    {/* Transcript Controls */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="relative flex-1">
                        <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          placeholder="Search spoken dialogue..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80"
                        />
                      </div>
                      <button
                        onClick={handleCopyTranscript}
                        className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-colors"
                        title="Copy full transcript"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>

                    {/* Timeline Segments */}
                    <div className="space-y-2">
                      {segments.length > 0 ? (
                        segments
                          .filter(s => s.text.toLowerCase().includes(searchQuery.toLowerCase()))
                          .map((seg, idx) => (
                            <div
                              key={idx}
                              onClick={() => seekTo(seg.start)}
                              className="group p-2.5 rounded-lg bg-slate-900/40 border border-slate-800/60 hover:border-indigo-500/50 hover:bg-slate-900/80 transition-all cursor-pointer flex gap-2.5 items-start"
                            >
                              <span className="px-1.5 py-0.5 rounded bg-indigo-950/80 border border-indigo-800/60 text-[10px] font-mono text-indigo-300 shrink-0 mt-0.5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                                {formatTime(seg.start)}
                              </span>
                              <p className="text-xs text-slate-300 group-hover:text-slate-100 leading-relaxed">
                                {getHighlightedText(seg.text, searchQuery)}
                              </p>
                            </div>
                          ))
                      ) : (
                        <p className="text-xs text-slate-400 leading-relaxed p-3 bg-slate-900/40 rounded-xl border border-slate-800">
                          {transcriptText || "No transcript available."}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* ---------------- TAB 3: KEY MOMENTS ---------------- */}
                {activeTab === 'moments' && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-400">
                      Visual highlight moments detected with pause segmentation. Click any card to jump to that timestamp:
                    </p>

                    {summaryData?.key_takeaways && summaryData.key_takeaways.length > 0 ? (
                      <div className="space-y-3">
                        {summaryData.key_takeaways.map((takeaway, idx) => {
                          const isNewFormat = typeof takeaway === 'object' && takeaway !== null && 'hook' in takeaway;
                          const hookText = (isNewFormat && typeof takeaway.hook === 'string') ? takeaway.hook : String(takeaway || '');
                          const startTime = (isNewFormat && typeof takeaway.start === 'number') ? takeaway.start : 0.0;
                          const thumbUrl = isNewFormat && typeof takeaway.thumbnail_url === 'string' 
                            ? `${API_BASE_URL}${takeaway.thumbnail_url}?token=${localStorage.getItem('token')}`
                            : null;

                          return (
                            <div
                              key={idx}
                              onClick={() => seekTo(startTime)}
                              className="group relative overflow-hidden bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 flex flex-col gap-2.5 cursor-pointer hover:border-indigo-500/50 hover:bg-slate-900/90 transition-all active:scale-[0.99]"
                            >
                              {thumbUrl ? (
                                <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-black border border-slate-800">
                                  {/* eslint-disable-next-line @next/next/no-img-element */}
                                  <img 
                                    src={thumbUrl} 
                                    alt={hookText}
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                    loading="lazy"
                                  />
                                  <div className="absolute inset-0 bg-slate-950/20 group-hover:bg-slate-950/10 transition-colors flex items-center justify-center">
                                    <div className="w-8 h-8 rounded-full bg-indigo-600/90 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 scale-90 group-hover:scale-100 transition-all shadow-md">
                                      <Play className="w-3.5 h-3.5 fill-white ml-0.5" />
                                    </div>
                                  </div>
                                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-slate-950/80 border border-slate-800 text-[10px] text-indigo-300 font-mono font-semibold">
                                    {formatTime(startTime)}
                                  </span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <span className="px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-800 text-[10px] text-indigo-300 font-mono font-semibold">
                                    {formatTime(startTime)}
                                  </span>
                                </div>
                              )}
                              <p className="text-xs text-slate-200 font-medium line-clamp-2">
                                {hookText}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No key moments extracted yet.</p>
                    )}
                  </div>
                )}

                {/* ---------------- TAB 4: INSIGHTS ---------------- */}
                {activeTab === 'insights' && (
                  <div className="space-y-4">
                    {/* Tone & Sentiment */}
                    <div className="grid grid-cols-2 gap-2.5">
                      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Sentiment</span>
                        <p className="text-xs font-semibold text-emerald-300">
                          {summaryData?.sentiment || "Positive / Constructive"}
                        </p>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Tone</span>
                        <p className="text-xs font-semibold text-indigo-300 truncate">
                          {summaryData?.tone || "Informative"}
                        </p>
                      </div>
                    </div>

                    {/* Speaking Pace & Metrics */}
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
                          <Gauge className="w-3.5 h-3.5 text-indigo-400" /> Speaking Pace & Metrics
                        </span>
                        {summaryData?.analytics?.pacing_label && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-950 border border-indigo-800 text-indigo-300">
                            {summaryData.analytics.pacing_label} Pace
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-1">
                        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                          <span className="text-[10px] text-slate-500">Speaking Pace</span>
                          <p className="text-base font-bold text-slate-100 font-mono mt-0.5">
                            {summaryData?.analytics?.speaking_wpm || 0} <span className="text-xs font-normal text-slate-400">WPM</span>
                          </p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                          <span className="text-[10px] text-slate-500">Time Saved</span>
                          <p className="text-base font-bold text-emerald-400 font-mono mt-0.5">
                            ~{summaryData?.analytics?.time_saved_minutes || 0} <span className="text-xs font-normal text-emerald-500">mins</span>
                          </p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                          <span className="text-[10px] text-slate-500">Reading Time</span>
                          <p className="text-base font-bold text-slate-100 font-mono mt-0.5">
                            ~{summaryData?.analytics?.reading_time_minutes || 1} <span className="text-xs font-normal text-slate-400">min</span>
                          </p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                          <span className="text-[10px] text-slate-500">Word Count</span>
                          <p className="text-base font-bold text-slate-100 font-mono mt-0.5">
                            {summaryData?.word_count || 0} <span className="text-xs font-normal text-slate-400">words</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </aside>
      </div>

      {/* ========================================================================= */}
      {/* FLOATING 🤖 ASK AI WIDGET (Bottom-Right Floating Popover)                 */}
      {/* ========================================================================= */}
      {!isChatOpen ? (
        <button
          onClick={() => setIsChatOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 rounded-full bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 text-white font-semibold shadow-2xl shadow-indigo-600/40 hover:scale-105 active:scale-95 transition-all group"
          title="Open AI Video Assistant"
        >
          <div className="relative">
            <Bot className="w-5 h-5 text-white" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full ring-2 ring-slate-950 animate-pulse" />
          </div>
          <span className="text-xs tracking-wide">Ask AI</span>
          <Sparkles className="w-3.5 h-3.5 text-amber-300 group-hover:rotate-12 transition-transform" />
        </button>
      ) : (
        <div className="fixed bottom-6 right-6 z-50 w-96 sm:w-[420px] h-[520px] bg-slate-900/95 backdrop-blur-xl border border-indigo-500/40 rounded-2xl shadow-2xl shadow-black/80 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-6 duration-200">
          
          {/* Chat Header */}
          <div className="p-3.5 border-b border-slate-800/80 bg-slate-950/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  ClipMind Video Assistant
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                </h4>
                <p className="text-[10px] text-slate-400">Ask about dialogue, cast, singer, or summaries</p>
              </div>
            </div>
            <button
              onClick={() => setIsChatOpen(false)}
              className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Minimize chat"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Chat Message Thread */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 select-text custom-scrollbar">
            {chatMessages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-4 text-slate-500 space-y-3">
                <Bot className="w-10 h-10 text-slate-600" />
                <div>
                  <p className="text-xs font-semibold text-slate-300">Ask the Video Assistant</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    I know what&apos;s spoken in the video, its description, credits, singer, and highlights.
                  </p>
                </div>
                {/* Prompt suggestion chips */}
                <div className="flex flex-wrap gap-1.5 justify-center pt-2">
                  {[
                    "Who is the singer or actor?",
                    "What is this video about?",
                    "Summarize key highlights",
                    "What are they talking about?"
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendQuestion(prompt)}
                      className="text-[10px] px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 hover:border-indigo-500/60 hover:text-indigo-300 text-slate-400 transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-2.5 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.sender === 'bot' && (
                    <div className="w-6 h-6 rounded-md bg-indigo-600 flex items-center justify-center text-white shrink-0 mt-0.5 text-xs">
                      <Bot className="w-3.5 h-3.5" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                      msg.sender === 'user'
                        ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-tr-none'
                        : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-tl-none space-y-2'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.text}</div>

                    {/* Timestamp Citations */}
                    {msg.timestampCitations && msg.timestampCitations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-slate-800/80">
                        <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                          <Play className="w-2.5 h-2.5 text-indigo-400 fill-indigo-400" /> Jump to:
                        </span>
                        {msg.timestampCitations.map((sec, cIdx) => (
                          <button
                            key={cIdx}
                            onClick={() => seekTo(sec)}
                            className="px-1.5 py-0.5 rounded bg-indigo-950/80 border border-indigo-800/60 text-[10px] font-mono text-indigo-300 hover:bg-indigo-600 hover:text-white transition-colors"
                          >
                            [{formatTime(sec)}]
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {isAsking && (
              <div className="flex gap-2.5 items-center text-xs text-indigo-400 animate-pulse">
                <Bot className="w-4 h-4 animate-spin" />
                <span>Assistant is analyzing the video credits & dialogue...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-950/90">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuestion();
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                placeholder={completedVideoId ? "Ask about actors, dialogue, topics..." : "Select a video first to ask questions"}
                value={chatInput}
                disabled={!completedVideoId || isAsking}
                onChange={(e) => setChatInput(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || !completedVideoId || isAsking}
                className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors shadow-md shadow-indigo-600/20 shrink-0"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* UPLOAD MODAL / DRAWER                                                     */}
      {/* ========================================================================= */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Upload className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-100">Add New Video</h3>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Upload Tabs Toggle */}
            <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800">
              <button
                type="button"
                onClick={() => setUploaderTab('file')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                  uploaderTab === 'file'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Video className="w-3.5 h-3.5" />
                <span>Upload File</span>
              </button>
              <button
                type="button"
                onClick={() => setUploaderTab('youtube')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                  uploaderTab === 'youtube'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Film className="w-3.5 h-3.5 text-red-400" />
                <span>YouTube URL</span>
              </button>
            </div>

            {/* Tab A: Local File Upload */}
            {uploaderTab === 'file' && (
              <form onSubmit={handleUpload} className="space-y-4">
                <div className="border-2 border-dashed border-slate-800 hover:border-indigo-500/60 rounded-xl p-6 text-center cursor-pointer transition-colors bg-slate-950/40 relative">
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleFileChange}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                  />
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-xs font-semibold text-slate-300">
                    {file ? file.name : "Choose an MP4, MOV, or AVI file"}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">Directly extracted with GPU Whisper</p>
                </div>

                <button
                  type="submit"
                  disabled={!file || uploading}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50"
                >
                  {uploading ? "Uploading..." : "Start AI Processing"}
                </button>
              </form>
            )}

            {/* Tab B: YouTube Ingestion */}
            {uploaderTab === 'youtube' && (
              <form onSubmit={handleYouTubeSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">YouTube Video URL</label>
                  <div className="relative">
                    <Film className="w-4 h-4 text-red-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="url"
                      placeholder="https://www.youtube.com/watch?v=..."
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={!youtubeUrl.trim() || uploading}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-indigo-600 hover:from-red-500 hover:to-indigo-500 text-white text-xs font-semibold transition-all shadow-lg shadow-red-600/20 disabled:opacity-50"
                >
                  {uploading ? "Queueing Download..." : "Import & Analyze Video"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
