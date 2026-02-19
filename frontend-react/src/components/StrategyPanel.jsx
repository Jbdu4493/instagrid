import React from 'react';
import clsx from 'clsx';
import { Copy, Sparkles, Hash } from 'lucide-react';

function StrategyPanel({ result, onAppendHashtags }) {
    if (!result) return null;
    const { coherence_score, coherence_reasoning, hashtags } = result;

    const getScoreColor = (score) => {
        if (score >= 80) return "text-green-400 border-green-500/50 bg-green-500/10";
        if (score >= 60) return "text-yellow-400 border-yellow-500/50 bg-yellow-500/10";
        return "text-red-400 border-red-500/50 bg-red-500/10";
    };

    // Ensure hashtags is an array (backward compat or robust)
    const ladders = Array.isArray(hashtags) ? hashtags : [hashtags, hashtags, hashtags];
    // Fallback: if single object, replicate (should not happen with new backend)

    return (
        <div className="space-y-6">
            {/* Coherence Score */}
            <div className={clsx(
                "p-6 rounded-xl border flex flex-col md:flex-row items-start gap-6",
                getScoreColor(coherence_score)
            )}>
                <div className="flex-shrink-0 text-center">
                    <div className="text-4xl font-bold">{coherence_score}</div>
                    <div className="text-xs uppercase tracking-wide opacity-80">Score</div>
                </div>
                <div className="h-full w-px bg-current opacity-20 hidden md:block" />
                <div className="flex-1 space-y-2">
                    <h3 className="font-semibold text-lg">Visual Consistency Analysis</h3>
                    <p className="text-sm md:text-base leading-relaxed opacity-90">
                        {coherence_reasoning}
                    </p>
                </div>
            </div>

            {/* Hashtag Ladders x 3 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {ladders.map((ladder, ladderIdx) => (
                    <div key={ladderIdx} className="space-y-4">
                        <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-400 text-center bg-gray-800/50 py-1 rounded-lg">
                            Image {ladderIdx + 1}
                        </h4>

                        {/* Ladder Categories */}
                        {[
                            { label: "Broad", icon: "🌍", tags: ladder?.broad || [] },
                            { label: "Niche", icon: "🎯", tags: ladder?.niche || [] },
                            { label: "Specific", icon: "💎", tags: ladder?.specific || [] },
                        ].map((cat, catIdx) => (
                            <div key={catIdx} className="bg-card border border-border rounded-xl p-4 hover:border-purple-500/30 transition-colors">
                                <h5 className="font-semibold mb-2 flex items-center gap-2 text-white text-sm">
                                    <span>{cat.icon}</span> {cat.label}
                                </h5>
                                <div className="flex flex-wrap gap-1.5 content-start">
                                    {cat.tags.map(tag => (
                                        <span key={tag} className="text-[10px] bg-dark px-1.5 py-0.5 rounded text-gray-300 border border-gray-700">
                                            #{tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                ))}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
                <button
                    onClick={() => onAppendHashtags(ladders)}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl bg-card border border-border hover:border-purple-500 hover:text-purple-400 transition-all text-sm font-semibold shadow-sm hover:shadow-purple-500/10"
                >
                    <Hash size={18} />
                    Apply Hashtags to All Captions
                </button>
            </div>
        </div>
    );
}

export default StrategyPanel;
