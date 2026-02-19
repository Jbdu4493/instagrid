import { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Camera, Sparkles, Send, LayoutGrid, Instagram, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import UploadSection from './components/UploadSection';
import GridEditor from './components/GridEditor';
import StrategyPanel from './components/StrategyPanel';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
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

  // Instagram Credentials (Graph API)
  const [accessToken, setAccessToken] = useState('');
  const [igUserId, setIgUserId] = useState('');

  // Token Exchange
  const [isExchanging, setIsExchanging] = useState(false);
  const [exchangeResult, setExchangeResult] = useState(null);
  const [fbAppConfigured, setFbAppConfigured] = useState(false);

  // Fetch Config
  useEffect(() => {
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
    fetchConfig();
  }, []);

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

  const handleGenerateStrategy = async () => {
    if (files.some(f => !f)) return;

    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));

      if (userContext) formData.append('user_context', userContext);

      individualContexts.forEach((ctx, idx) => {
        if (ctx) formData.append(`context_${idx}`, ctx);
      });

      const response = await axios.post(`${API_URL}/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const res = response.data;
      setAnalysisResult(res);

      const newPosts = res.suggested_order.map((originalIndex, orderIndex) => ({
        id: `post-${originalIndex}`,
        originalIndex: originalIndex,
        file: files[originalIndex],
        preview: previews[originalIndex],
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

  const handleRegenerateCaption = async (postId) => {
    const postIndex = posts.findIndex(p => p.id === postId);
    if (postIndex === -1) return;

    const post = posts[postIndex];
    const ctxIndex = post.originalIndex;

    try {
      const payload = {
        image_base64: post.preview.split(',')[1],
        common_context: userContext,
        individual_context: individualContexts[ctxIndex],
        captions_history: post.captions,
        common_thread_fr: analysisResult?.common_thread_fr || "",
        common_thread_en: analysisResult?.common_thread_en || ""
      };

      const response = await axios.post(`${API_URL}/regenerate_caption`, payload);
      const newCaption = response.data.caption;

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


  return (
    <div className="min-h-screen bg-dark text-white p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-12">

        {/* Header */}
        <header className="flex items-center space-x-4 border-b border-border pb-6">
          <div className="p-3 bg-gradient-to-br from-pink-500 to-purple-600 rounded-xl">
            <Camera size={32} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500">
              InstaGrid AI
            </h1>
            <p className="text-gray-400">Create the perfect 3-post grid sequence.</p>
          </div>
        </header>

        {/* Token Management (always visible) */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-4">
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <div className={`rounded-lg p-3 text-sm ${exchangeResult.status === 'success'
                ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
              }`}>
              {exchangeResult.message}
              {exchangeResult.token_type === 'permanent_page' && (
                <span className="ml-2 font-semibold">♾️ Permanent</span>
              )}
              {exchangeResult.expires_in_days && (
                <span className="ml-2 text-amber-300">⏳ {exchangeResult.expires_in_days}j</span>
              )}
            </div>
          )}
        </section>

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
          />

          <div className="flex justify-end pt-4">
            <button
              onClick={handleGenerateStrategy}
              disabled={files.some(f => !f) || isAnalyzing}
              className={`
                flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-lg transition-all
                ${files.some(f => !f)
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 shadow-lg hover:shadow-pink-500/25'}
              `}
            >
              {isAnalyzing ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {isAnalyzing ? 'Analyzing Visual Flow...' : 'Generate Strategy'}
            </button>
          </div>
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

              <div className="pt-4 border-t border-gray-800">
                <button
                  onClick={handlePostToInstagram}
                  disabled={isPosting}
                  className={`
                    w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all
                    ${isPosting
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 hover:shadow-lg hover:shadow-blue-500/25'}
                  `}
                >
                  {isPosting ? <Loader2 className="animate-spin" /> : <Send />}
                  {isPosting ? 'Posting to Instagram...' : 'Post to Instagram Grid'}
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

      </div>
    </div>
  )
}

export default App
