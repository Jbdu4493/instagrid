import { Loader2, RefreshCw } from 'lucide-react';

export default function SettingsPanel({
    igUserId,
    setIgUserId,
    accessToken,
    setAccessToken,
    fbAppConfigured,
    handleExchangeToken,
    isExchanging,
    exchangeResult,
    handleLogout
}) {
    return (
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
    );
}
