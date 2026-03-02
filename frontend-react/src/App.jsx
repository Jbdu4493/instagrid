import { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Camera, Sparkles, Send, LayoutGrid, Instagram, AlertCircle, Loader2, RefreshCw, Save, Trash2, Edit3, Eye, FileText, Settings, Heart, MessageCircle } from 'lucide-react';
import UploadSection from './components/UploadSection';
import GridEditor from './components/GridEditor';
import StrategyPanel from './components/StrategyPanel';
import DraftsPanel from './components/DraftsPanel';
import Login from './components/Login';

let API_URL = (window._env_ && window._env_.VITE_API_URL) || import.meta.env.VITE_API_URL || 'http://localhost:8000';
if (API_URL && !API_URL.startsWith('http')) {
  API_URL = `https://${API_URL}`;
}

const CROP_OPTIONS = [
  { value: 'original', label: 'Original' },
  { value: '1:1', label: '1:1' },
  { value: '4:5', label: '4:5' },
  { value: '16:9', label: '16:9' },
];

const ASPECT_CSS = {
  'original': 'auto',
  '1:1': '1/1',
  '4:5': '4/5',
  '16:9': '16/9',
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Tab navigation
  const [activeTab, setActiveTab] = useState('create');
  // State for Upload Phase
  const [files, setFiles] = useState([null, null, null]);
  const [previews, setPreviews] = useState([null, null, null]);
  const [userContext, setUserContext] = useState('');
  const [individualContexts, setIndividualContexts] = useState(['', '', '']);

  // State for Editor Phase
  const [posts, setPosts] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPosting, setIsPosting] = useState(false);
  const [postLogs, setPostLogs] = useState([]);

  // Drafts
  const [drafts, setDrafts] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [draftPostingId, setDraftPostingId] = useState(null);
  const [cropRatios, setCropRatios] = useState(['original', 'original', 'original']);
  const [cropPositions, setCropPositions] = useState([{ x: 50, y: 50 }, { x: 50, y: 50 }, { x: 50, y: 50 }]);

  // Instagram Credentials (Graph API)
  const [accessToken, setAccessToken] = useState('');
  const [igUserId, setIgUserId] = useState('');

  // Token Exchange
  const [isExchanging, setIsExchanging] = useState(false);
  const [exchangeResult, setExchangeResult] = useState(null);
  const [fbAppConfigured, setFbAppConfigured] = useState(false);

  // Recent Posts (IG Grid)
  const [recentPosts, setRecentPosts] = useState([]);
  const [isLoadingRecent, setIsLoadingRecent] = useState(false);

  // AI Providers (Strategy Pattern)
  const [availableAiProviders, setAvailableAiProviders] = useState([]);
  const [selectedAi, setSelectedAi] = useState('openai');
  const [streamedOutput, setStreamedOutput] = useState("");
  const [isCheckingAi, setIsCheckingAi] = useState(false);

  // Fetch Config
  useEffect(() => {
    // 1. Check local storage for existing session
    const savedPassword = localStorage.getItem('app_password');
    if (savedPassword) {
      applyAxiosInterceptor(savedPassword);
      setIsAuthenticated(true);
    }

    async function fetchConfig() {
      try {
        const res = await axios.get(`${API_URL}/config`);
        if (res.data.ig_user_id) setIgUserId(res.data.ig_user_id);
        if (res.data.ig_access_token) setAccessToken(res.data.ig_access_token);
        if (res.data.fb_app_configured) setFbAppConfigured(true);
      } catch (e) {
        console.error("Failed to load config", e);
      }
    }

    async function fetchAiProviders() {
      setIsCheckingAi(true);
      try {
        const res = await axios.get(`${API_URL}/ai-providers`);
        if (res.data.providers) {
          setAvailableAiProviders(res.data.providers);
          if (res.data.providers.length > 0) {
            setSelectedAi(res.data.providers[0].id);
          }
        }
      } catch (e) {
        console.error("Failed to fetch AI providers", e);
      } finally {
        setIsCheckingAi(false);
      }
    }

    if (isAuthenticated) {
      fetchConfig();
      fetchDrafts();
      fetchAiProviders();
    }
  }, [isAuthenticated]);

  const applyAxiosInterceptor = (password) => {
    // Inject the password header into every single request
    axios.defaults.headers.common['X-App-Password'] = password;

    // Handle 401 globally (e.g. if the backend password was changed)
    axios.interceptors.response.use(
      response => response,
      error => {
        if (error.response?.status === 401) {
          handleLogout();
        }
        return Promise.reject(error);
      }
    );
  };

  const handleLoginSuccess = (password) => {
    localStorage.setItem('app_password', password);
    applyAxiosInterceptor(password);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('app_password');
    delete axios.defaults.headers.common['X-App-Password'];
    setIsAuthenticated(false);
    setAccessToken('');
    setIgUserId('');
  };

  useEffect(() => {
    if (igUserId && accessToken) {
      fetchRecentPosts();
    }
  }, [igUserId, accessToken]);

  const fetchRecentPosts = async () => {
    setIsLoadingRecent(true);
    try {
      const res = await axios.get(`${API_URL}/ig-posts?ig_user_id=${igUserId}&access_token=${accessToken}`);
      setRecentPosts(res.data.posts || []);
    } catch (error) {
      console.error("Failed to load recent posts", error);
    } finally {
      setIsLoadingRecent(false);
    }
  };

  const fetchDrafts = async () => {
    try {
      const res = await axios.get(`${API_URL}/drafts`);
      setDrafts(res.data.drafts || []);
    } catch (e) {
      console.error("Failed to load drafts", e);
    }
  };

  const handleExchangeToken = async () => {
    if (!accessToken) {
      alert("Collez d'abord votre token court (depuis Graph API Explorer)");
      return;
    }
    setIsExchanging(true);
    setExchangeResult(null);
    try {
      const res = await axios.post(`${API_URL}/exchange-token`, {
        short_lived_token: accessToken
      });
      setExchangeResult(res.data);
      // Re-fetch config to get the updated token
      const configRes = await axios.get(`${API_URL}/config`);
      if (configRes.data.ig_access_token) setAccessToken(configRes.data.ig_access_token);
    } catch (error) {
      setExchangeResult({
        status: 'error',
        message: error.response?.data?.detail || error.message
      });
    } finally {
      setIsExchanging(false);
    }
  };

  const handleFileUpload = (index, file) => {
    setFiles(prev => {
      const newFiles = [...prev];
      newFiles[index] = file;
      return newFiles;
    });

    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviews(prev => {
          const newPreviews = [...prev];
          newPreviews[index] = reader.result;
          return newPreviews;
        });
      };
      reader.readAsDataURL(file);
    } else {
      setPreviews(prev => {
        const newPreviews = [...prev];
        newPreviews[index] = null;
        return newPreviews;
      });
    }
  };

  const handleContextChange = (index, value) => {
    setIndividualContexts(prev => {
      const newContexts = [...prev];
      newContexts[index] = value;
      return newContexts;
    });
  };

  // --- Canvas-based crop for sending to GPT ---
  const RATIO_VALUES = { 'original': null, '1:1': 1, '4:5': 4 / 5, '16:9': 16 / 9 };

  const cropImageCanvas = (file, ratio, position) => {
    return new Promise((resolve) => {
      if (ratio === 'original' || !RATIO_VALUES[ratio]) {
        resolve(file);
        return;
      }
      const img = new window.Image();
      img.onload = () => {
        const targetRatio = RATIO_VALUES[ratio];
        const imgRatio = img.width / img.height;
        const posX = (position?.x ?? 50) / 100;
        const posY = (position?.y ?? 50) / 100;
        let sx = 0, sy = 0, sw = img.width, sh = img.height;

        if (imgRatio > targetRatio) {
          sw = Math.round(img.height * targetRatio);
          const maxLeft = img.width - sw;
          sx = Math.round(maxLeft * posX);
        } else if (imgRatio < targetRatio) {
          sh = Math.round(img.width / targetRatio);
          const maxTop = img.height - sh;
          sy = Math.round(maxTop * posY);
        }

        const canvas = document.createElement('canvas');
        canvas.width = sw;
        canvas.height = sh;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
        canvas.toBlob((blob) => {
          resolve(new File([blob], file.name.replace(/\.[^/.]+$/, "") + ".webp", { type: 'image/webp' }));
        }, 'image/webp', 0.92);
      };
      img.src = URL.createObjectURL(file);
    });
  };

  const handleGenerateStrategy = async () => {
    if (files.some(f => !f)) return;

    setIsAnalyzing(true);
    setStreamedOutput("");
    setPosts([]); // Clear previous analysis immediately
    try {
      // Crop images client-side before sending to GPT
      const croppedFiles = await Promise.all(
        files.map((file, idx) => cropImageCanvas(file, cropRatios[idx], cropPositions[idx]))
      );
      const individualContexts = posts.map(
        (_, i) => document.getElementById(`context_${i}`)?.value || ""
      );

      const formData = new FormData();
      croppedFiles.forEach(file => formData.append('files', file));

      formData.append('ai_provider', selectedAi);
      if (userContext) formData.append('user_context', userContext);

      individualContexts.forEach((ctx, idx) => {
        if (ctx) formData.append(`context_${idx}`, ctx);
      });

      const fetchUrl = `${API_URL}/analyze`;
      const response = await fetch(fetchUrl, {
        method: 'POST',
        headers: {
          'X-App-Password': localStorage.getItem('app_password')
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let rawJsonData = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        rawJsonData += chunk;
        setStreamedOutput(rawJsonData); // Update UI
      }

      const res = JSON.parse(rawJsonData);
      setAnalysisResult(res);

      let orderArr = res.suggested_order || [0, 1, 2];
      // Backend should handle 0-based conversion, but safety first
      if (orderArr.some(x => x > 2)) {
        orderArr = orderArr.map(x => x - 1);
      }

      const newPosts = orderArr.map((originalIndex, orderIndex) => ({
        id: `post-${originalIndex}`,
        originalIndex: originalIndex,
        file: files[originalIndex],
        preview: previews[originalIndex],
        cropRatio: cropRatios[originalIndex],
        cropPosition: cropPositions[originalIndex],
        caption: res.captions[orderIndex],
        captions: [res.captions[orderIndex]],
        currentCaptionIndex: 0,
        score: res.individual_scores ? res.individual_scores[orderIndex] : null
      }));

      setPosts(newPosts);

    } catch (error) {
      console.error("Analysis failed:", error);
      alert("Analysis failed. See console for details.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // --- Caption Management ---

  const handleRegenerateCaption = async (postId, aiProvider = 'openai') => {
    const postIndex = posts.findIndex(p => p.id === postId);
    if (postIndex === -1) return;

    const post = posts[postIndex];
    const ctxIndex = post.originalIndex;

    try {
      const payload = {
        image_base64: post.preview.split(',')[1],
        common_context: userContext,
        individual_context: individualContexts[ctxIndex] || "Aucun",
        captions_history: post.captions,
        common_thread_fr: analysisResult?.common_thread_fr || "",
        common_thread_en: analysisResult?.common_thread_en || "",
        ai_provider: aiProvider
      };

      const response = await fetch(`${API_URL}/regenerate_caption`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-App-Password': localStorage.getItem('app_password')
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("Erreur serveur lors de la régénération");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let rawJsonData = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        rawJsonData += decoder.decode(value, { stream: true });
      }

      // Backend fastAPI regenerates `RegenerateResponseParts` structured json chunks, but then router wraps 
      // it into a string? Wait, backend router /regenerate_caption used to return `RegenerateResponse(caption=full)`.
      // But now it returns `StreamingResponse` yielding chunks of `RegenerateResponseParts`.
      // The frontend must parse that parts object.
      // Wait, let's parse the parts JSON.
      const parts = JSON.parse(rawJsonData);
      const newCaption = `${parts.specific_fr || ''} ${payload.common_thread_fr || ''}\n\n${parts.specific_en || ''} ${payload.common_thread_en || ''}`;

      setPosts(prev => {
        const newPosts = [...prev];
        const p = newPosts[postIndex];
        const newCaptions = [...p.captions, newCaption];
        newPosts[postIndex] = {
          ...p,
          captions: newCaptions,
          currentCaptionIndex: newCaptions.length - 1,
          caption: newCaption
        };
        return newPosts;
      });

    } catch (error) {
      console.error("Regeneration failed:", error);
      alert("Failed to regenerate caption.");
    }
  };

  const handleCaptionHistory = (postId, direction) => {
    setPosts(prev => {
      return prev.map(p => {
        if (p.id !== postId) return p;

        let newIndex = p.currentCaptionIndex;
        if (direction === 'prev') newIndex = Math.max(0, newIndex - 1);
        if (direction === 'next') newIndex = Math.min(p.captions.length - 1, newIndex + 1);

        if (newIndex === p.currentCaptionIndex) return p;

        return {
          ...p,
          currentCaptionIndex: newIndex,
          caption: p.captions[newIndex]
        };
      });
    });
  };

  const handlePostToInstagram = async () => {
    setIsPosting(true);
    setPostLogs([]);

    try {
      const payload = {
        posts: posts.map(p => ({
          image_base64: p.preview.split(',')[1],
          caption: p.caption
        }))
      };

      if (!accessToken || !igUserId) {
        alert("Please fill in Access Token and User ID.");
        setIsPosting(false);
        return;
      }
      payload.access_token = accessToken;
      payload.ig_user_id = igUserId;

      const response = await axios.post(`${API_URL}/post`, payload);
      setPostLogs(response.data.logs);
      alert("Posted successfully!");

    } catch (error) {
      console.error("Posting failed:", error);
      alert("Posting failed: " + (error.response?.data?.detail || error.message));
    } finally {
      setIsPosting(false);
    }
  };

  const handleReset = () => {
    if (!confirm("Effacer tout le projet en cours ?")) return;
    setFiles([null, null, null]);
    setPreviews([null, null, null]);
    setUserContext('');
    setIndividualContexts(['', '', '']);
    setPosts([]);
    setAnalysisResult(null);
    setPostLogs([]);
    setCropRatios(['original', 'original', 'original']);
    setCropPositions([{ x: 50, y: 50 }, { x: 50, y: 50 }, { x: 50, y: 50 }]);
  };

  const handleSaveDraft = async () => {
    setIsSaving(true);
    try {
      const payload = {
        posts: posts.map(p => ({
          image_base64: p.preview.split(',')[1],
          caption: p.caption
        })),
        crop_ratios: cropRatios,
        crop_positions: cropPositions
      };
      const response = await axios.post(`${API_URL}/drafts`, payload);
      alert(`Brouillon sauvegardé ! (ID: ${response.data.draft.id})`);
      fetchDrafts();
    } catch (error) {
      alert("Erreur: " + (error.response?.data?.detail || error.message));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteDraft = async (draftId) => {
    if (!confirm("Supprimer ce brouillon ?")) return;
    try {
      await axios.delete(`${API_URL}/drafts/${draftId}`);
      fetchDrafts();
    } catch (error) {
      alert("Erreur: " + (error.response?.data?.detail || error.message));
    }
  };

  const handlePostDraft = async (draftId, force = false) => {
    setDraftPostingId(draftId);
    try {
      const payload = {
        access_token: accessToken,
        ig_user_id: igUserId,
        force
      };
      const response = await axios.post(`${API_URL}/drafts/${draftId}/post`, payload);
      alert(response.data.message);
      fetchDrafts();
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      if (error.response?.status === 409) {
        if (confirm(detail + "\n\nRe-publier quand même ?")) {
          handlePostDraft(draftId, true);
          return;
        }
      } else {
        alert("Erreur: " + detail);
      }
    } finally {
      setDraftPostingId(null);
    }
  };

  const handleUpdateDraftCaption = async (draftId, captions, cropRatios = null) => {
    try {
      const payload = {};
      if (captions) payload.captions = captions;
      if (cropRatios) payload.crop_ratios = cropRatios;
      await axios.put(`${API_URL}/drafts/${draftId}`, payload);
      fetchDrafts();
    } catch (error) {
      alert("Erreur: " + (error.response?.data?.detail || error.message));
    }
  };


  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-dark text-white p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-12">

        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between border-b border-border pb-6 gap-4">
          <div className="flex items-center space-x-4">
            {/* Custom CSS Logo */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-pink-500 via-purple-500 to-indigo-500 rounded-2xl blur opacity-40 group-hover:opacity-60 transition duration-500"></div>
              <div className="relative flex items-center justify-center bg-dark p-3.5 rounded-2xl border border-gray-700/50 group-hover:border-purple-500/50 transition-colors">
                <LayoutGrid size={28} className="text-transparent" style={{ stroke: 'url(#ig-grad)' }} />
                <Sparkles size={14} className="absolute -top-1 -right-1 text-pink-400 animate-pulse" />
                {/* SVG details to allow linearGradient stroke on Lucide icons */}
                <svg width="0" height="0" className="absolute">
                  <linearGradient id="ig-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop stopColor="#EC4899" offset="0%" />
                    <stop stopColor="#A855F7" offset="50%" />
                    <stop stopColor="#6366F1" offset="100%" />
                  </linearGradient>
                </svg>
              </div>
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight flex items-center gap-2">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500">
                  InstaGrid
                </span>
                <span className="text-white">AI</span>
              </h1>
              <p className="text-gray-400 font-medium">Create the perfect 3-post grid sequence.</p>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('create')}
              className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${activeTab === 'create'
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/25'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
            >
              <Sparkles size={16} />
              Création
            </button>
            <button
              onClick={() => setActiveTab('drafts')}
              className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${activeTab === 'drafts'
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/25'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
            >
              <FileText size={16} />
              Brouillons
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${activeTab === 'settings'
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/25'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
            >
              <Settings size={16} />
              Paramètres
            </button>
          </div>
        </header>

        {activeTab === 'settings' && (
          <section className="bg-card border border-border rounded-xl p-6 space-y-4 max-w-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                🔑 Token Instagram
              </h2>
              {accessToken && (
                <span className="text-xs px-2 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                  Token configuré
                </span>
              )}
            </div>

            <div className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-400">Instagram User ID</label>
                <input type="text" value={igUserId} onChange={(e) => setIgUserId(e.target.value)}
                  className="w-full bg-dark border border-gray-700 rounded-lg p-2.5 text-white text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="1784140xxxxxxx" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-400">Access Token</label>
                <div className="flex gap-2">
                  <input type="password" value={accessToken} onChange={(e) => setAccessToken(e.target.value)}
                    className="flex-1 bg-dark border border-gray-700 rounded-lg p-2.5 text-white text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="EAAB..." />
                  {fbAppConfigured && (
                    <button
                      onClick={handleExchangeToken}
                      disabled={isExchanging || !accessToken}
                      title="Échanger contre un token permanent"
                      className={`px-4 rounded-lg font-semibold text-sm flex items-center gap-1.5 transition-all whitespace-nowrap
                    ${isExchanging ? 'bg-gray-700 text-gray-400' : 'bg-amber-600 hover:bg-amber-500 text-white'}`}
                    >
                      {isExchanging ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                      Étendre
                    </button>
                  )}
                </div>
              </div>
            </div>

            {exchangeResult && (
              <div className={`rounded-lg p-3 text-sm flex flex-col gap-1 ${exchangeResult.status === 'success'
                ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
                }`}>
                <span>{exchangeResult.message}</span>
                {exchangeResult.token_type === 'permanent_page' && (
                  <span className="font-semibold">♾️ Permanent</span>
                )}
                {exchangeResult.expires_in_days && (
                  <span className="text-amber-300">⏳ Expire dans {exchangeResult.expires_in_days} jours</span>
                )}
              </div>
            )}

            {/* Logout Section */}
            <div className="border-t border-gray-800 pt-6 mt-6">
              <button
                onClick={handleLogout}
                className="px-4 py-2.5 rounded-lg font-semibold text-sm bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 transition-all flex items-center gap-2"
              >
                Déconnexion Sécurisée
              </button>
            </div>
          </section>
        )}

        {activeTab === 'drafts' && (
          <DraftsPanel accessToken={accessToken} igUserId={igUserId} />
        )}

        {activeTab === 'create' && (
          <>

            {/* 0. Current Instagram Grid */}
            {(igUserId && accessToken) && (
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <span className="bg-gray-800 w-8 h-8 flex items-center justify-center rounded-full text-sm">0</span>
                    Grille Instagram Actuelle
                  </h2>
                  <button onClick={fetchRecentPosts} className="text-sm text-gray-400 hover:text-white transition-colors">
                    <RefreshCw size={16} className={`inline mr-1 ${isLoadingRecent ? 'animate-spin' : ''}`} /> Rafraîchir
                  </button>
                </div>

                <div className="bg-card border border-border rounded-xl p-6">
                  {isLoadingRecent && recentPosts.length === 0 ? (
                    <div className="flex justify-center py-8"><Loader2 className="animate-spin text-purple-500" /></div>
                  ) : recentPosts.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">Aucun post récent trouvé.</div>
                  ) : (
                    <div className="grid grid-cols-3 gap-1 md:gap-4">
                      {recentPosts.map(post => (
                        <a
                          key={post.id}
                          href={post.permalink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="relative aspect-square overflow-hidden group rounded-lg bg-gray-900 border border-gray-800"
                        >
                          {post.media_type === 'VIDEO' ? (
                            <img src={post.thumbnail_url || post.media_url} alt="" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity" />
                          ) : (
                            <img src={post.media_url} alt="" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity" />
                          )}
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-6">
                            <div className="flex items-center gap-2 text-white font-bold text-lg drop-shadow-md">
                              <Heart size={24} fill="currentColor" />
                              <span>{post.like_count || 0}</span>
                            </div>
                            <div className="flex items-center gap-2 text-white font-bold text-lg drop-shadow-md">
                              <MessageCircle size={24} fill="currentColor" />
                              <span>{post.comments_count || 0}</span>
                            </div>
                          </div>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* 1. Upload Section */}
            <section className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <span className="bg-gray-800 w-8 h-8 flex items-center justify-center rounded-full text-sm">1</span>
                Upload & Context
              </h2>
              <UploadSection
                files={files}
                previews={previews}
                onUpload={handleFileUpload}
                userContext={userContext}
                setUserContext={setUserContext}
                individualContexts={individualContexts}
                onContextChange={handleContextChange}
                cropRatios={cropRatios}
                onCropChange={(idx, value) => {
                  const newRatios = [...cropRatios];
                  newRatios[idx] = value;
                  setCropRatios(newRatios);
                }}
                cropPositions={cropPositions}
                onPositionChange={(idx, pos) => {
                  const newPos = [...cropPositions];
                  newPos[idx] = pos;
                  setCropPositions(newPos);
                }}
              />

              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-800">

                {/* AI Provider Selector */}
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-400">Moteur IA :</span>
                  {isCheckingAi ? (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="animate-spin" size={16} /> Vérification...
                    </div>
                  ) : availableAiProviders.length === 0 ? (
                    <span className="text-sm text-red-400">Aucune IA disponible.</span>
                  ) : (
                    <select
                      value={selectedAi}
                      onChange={(e) => setSelectedAi(e.target.value)}
                      className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block p-2.5"
                    >
                      {availableAiProviders.map(provider => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Generate Button */}
                <button
                  onClick={handleGenerateStrategy}
                  disabled={files.some(f => !f) || isAnalyzing || availableAiProviders.length === 0}
                  className={`
                flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-lg transition-all
                ${(files.some(f => !f) || availableAiProviders.length === 0)
                      ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 shadow-lg hover:shadow-pink-500/25'}
              `}
                >
                  {isAnalyzing ? <Loader2 className="animate-spin" /> : <Sparkles />}
                  {isAnalyzing ? 'Analyse en cours...' : '✨ Analyser la grille'}
                </button>
              </div>

              {/* Streaming Output Display */}
              {isAnalyzing && streamedOutput && (
                <div className="mt-8 p-6 bg-gray-900 border border-purple-500/30 rounded-xl shadow-inner w-full text-left overflow-hidden">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-xs text-green-500 uppercase tracking-wider font-bold">Flux de données en direct</span>
                  </div>
                  <p className="text-gray-300 font-mono text-sm whitespace-pre-wrap break-words">{streamedOutput}</p>
                </div>
              )}
            </section>

            {/* 2. Editor Section */}
            {posts.length > 0 && (
              <section className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <span className="bg-gray-800 w-8 h-8 flex items-center justify-center rounded-full text-sm">2</span>
                    Grid Editor (Visual Flow & Captions)
                  </h2>
                  <div className="text-sm text-gray-400 bg-card px-4 py-2 rounded-lg border border-border">
                    Review the AI-suggested order and captions. You can reorder if needed.
                  </div>
                </div>

                <GridEditor
                  posts={posts}
                  setPosts={setPosts}
                  onRegenerate={handleRegenerateCaption}
                  onHistoryNav={handleCaptionHistory}
                  availableAiProviders={availableAiProviders}
                />
              </section>
            )}

            {/* 3. Strategy Section */}
            {analysisResult && (
              <section className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <span className="bg-gray-800 w-8 h-8 flex items-center justify-center rounded-full text-sm">3</span>
                  Strategy & Coherence
                </h2>
                <StrategyPanel
                  result={analysisResult}
                  onAppendHashtags={(ladders) => {
                    setPosts(prevPosts => prevPosts.map((p, idx) => {
                      const ladder = ladders[idx];
                      if (!ladder) return p;

                      const tagsString = [...(ladder.broad || []), ...(ladder.niche || []), ...(ladder.specific || [])]
                        .map(t => t.startsWith('#') ? t : `#${t}`).join(' ');

                      return {
                        ...p,
                        caption: p.caption + "\n\n" + tagsString
                      };
                    }));
                  }}
                />
              </section>
            )}

            {/* 4. Publication Section */}
            {posts.length > 0 && (
              <section className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200 pb-20">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <span className="bg-gray-800 w-8 h-8 flex items-center justify-center rounded-full text-sm">4</span>
                  Publication
                </h2>

                <div className="bg-card border border-border rounded-xl p-8 space-y-6">

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-300">Instagram User ID</label>
                      <input type="text" value={igUserId} onChange={(e) => setIgUserId(e.target.value)}
                        className="w-full bg-dark border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-purple-500 outline-none"
                        placeholder="1784140xxxxxxx" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-300">Access Token</label>
                      <div className="flex gap-2">
                        <input type="password" value={accessToken} onChange={(e) => setAccessToken(e.target.value)}
                          className="flex-1 bg-dark border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-purple-500 outline-none"
                          placeholder="EAAB..." />
                        {fbAppConfigured && (
                          <button
                            onClick={handleExchangeToken}
                            disabled={isExchanging || !accessToken}
                            title="Étendre le token (permanent)"
                            className={`px-4 rounded-lg font-semibold text-sm flex items-center gap-1.5 transition-all whitespace-nowrap
                          ${isExchanging ? 'bg-gray-700 text-gray-400' : 'bg-amber-600 hover:bg-amber-500 text-white'}`}
                          >
                            {isExchanging ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                            Étendre
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {exchangeResult && (
                    <div className={`rounded-lg p-4 text-sm font-mono ${exchangeResult.status === 'success'
                      ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                      : 'bg-red-500/10 border border-red-500/20 text-red-400'
                      }`}>
                      {exchangeResult.message}
                      {exchangeResult.token_type === 'permanent_page' && (
                        <div className="mt-1 text-green-300 font-sans font-semibold">♾️ Ce token ne expire jamais.</div>
                      )}
                      {exchangeResult.expires_in_days && (
                        <div className="mt-1 text-amber-300 font-sans">⏳ Expire dans {exchangeResult.expires_in_days} jours.</div>
                      )}
                    </div>
                  )}

                  <div className="pt-4 border-t border-gray-800 flex gap-3">
                    <button
                      onClick={handleReset}
                      className="px-4 py-4 rounded-xl text-red-400 hover:bg-red-500/10 border border-red-500/20 transition-all flex items-center justify-center"
                      title="Effacer le projet en cours"
                    >
                      <Trash2 />
                    </button>
                    <button
                      onClick={handleSaveDraft}
                      disabled={isSaving}
                      className={`
                    flex-1 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all
                    ${isSaving
                          ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                          : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 hover:shadow-lg hover:shadow-emerald-500/25'}
                  `}
                    >
                      {isSaving ? <Loader2 className="animate-spin" /> : <Save />}
                      {isSaving ? 'Saving...' : '💾 Save Draft'}
                    </button>
                    <button
                      onClick={handlePostToInstagram}
                      disabled={isPosting}
                      className={`
                    flex-1 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all
                    ${isPosting
                          ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                          : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 hover:shadow-lg hover:shadow-blue-500/25'}
                  `}
                    >
                      {isPosting ? <Loader2 className="animate-spin" /> : <Send />}
                      {isPosting ? 'Posting...' : '🚀 Post Now'}
                    </button>
                  </div>

                  {postLogs.length > 0 && (
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-green-400 text-sm font-mono">
                      {postLogs.map((log, i) => <div key={i}>✅ {log}</div>)}
                    </div>
                  )}
                </div>
              </section>
            )}
          </>
        )}

      </div>
    </div>
  )
}

export default App
