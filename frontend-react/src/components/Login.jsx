import React, { useState } from 'react';
import { Lock, ArrowRight, Loader2, Disc } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Login({ onLoginSuccess }) {
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!password) return;

        setIsLoading(true);
        setError('');

        try {
            // Temporarily set the header to verify
            const response = await axios.get(`${API_URL}/verify-password`, {
                headers: {
                    'X-App-Password': password
                }
            });

            if (response.data.valid) {
                onLoginSuccess(password);
            }
        } catch (err) {
            setError('Mot de passe incorrect ou serveur inaccessible.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-dark flex flex-col items-center justify-center p-4 font-sans text-white">
            <div className="w-full max-w-sm space-y-8">
                {/* Logo */}
                <div className="flex flex-col items-center justify-center gap-3">
                    <div className="relative group">
                        <div className="absolute inset-0 bg-gradient-to-br from-pink-500 via-purple-500 to-indigo-500 rounded-2xl blur opacity-60"></div>
                        <div className="relative flex items-center justify-center bg-dark p-4 rounded-2xl border border-gray-700/50">
                            <Disc size={36} className="text-purple-400" />
                        </div>
                    </div>
                    <h1 className="text-3xl font-black tracking-tight text-center">
                        Insta<span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-indigo-500">Grid</span> AI
                    </h1>
                    <p className="text-gray-400 text-sm text-center font-medium">Accès Restreint</p>
                </div>

                {/* Form */}
                <form onSubmit={handleLogin} className="bg-card border border-border rounded-2xl p-6  space-y-6 shadow-xl">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                            <Lock size={16} /> Mot de passe de l'application
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••••••"
                            className="w-full bg-dark border border-gray-700 rounded-xl p-3.5 text-white focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                            autoFocus
                        />
                    </div>

                    {error && (
                        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={isLoading || !password}
                        className={`w-full flex items-center justify-center gap-2 py-3.5 rounded-xl font-bold transition-all
              ${(!password || isLoading)
                                ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                                : 'bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 shadow-lg shadow-purple-500/25 text-white'}`}
                    >
                        {isLoading ? <Loader2 className="animate-spin" size={20} /> : <ArrowRight size={20} />}
                        {isLoading ? 'Vérification...' : 'Déverrouiller'}
                    </button>
                </form>
            </div>
        </div>
    );
}
