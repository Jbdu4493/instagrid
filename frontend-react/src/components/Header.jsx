import { LayoutGrid, Sparkles, FileText, Settings } from 'lucide-react';

export default function Header({ activeTab, setActiveTab }) {
    return (
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
    );
}
