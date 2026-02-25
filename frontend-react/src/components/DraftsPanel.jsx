import React, { useState, useRef, useCallback } from 'react';
import axios from 'axios';
import { Send, Trash2, RefreshCw, Loader2, Move, ChevronDown, ChevronUp, GripVertical } from 'lucide-react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragOverlay } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getFullImageUrl = (url) => {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `${API_URL}${url.startsWith('/') ? '' : '/'}${url}`;
};

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

function DraftsPanel({ accessToken, igUserId }) {
    const [drafts, setDrafts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [draftPostingId, setDraftPostingId] = useState(null);
    const [expandedDraft, setExpandedDraft] = useState(null);

    const fetchDrafts = useCallback(async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_URL}/drafts`);
            setDrafts(res.data.drafts || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    React.useEffect(() => { fetchDrafts(); }, [fetchDrafts]);

    const handleUpdateDraft = async (draftId, captions, cropRatios, cropPositions, postOrder) => {
        try {
            const payload = {};
            if (captions) payload.captions = captions;
            if (cropRatios) payload.crop_ratios = cropRatios;
            if (cropPositions) payload.crop_positions = cropPositions;
            if (postOrder) payload.post_order = postOrder;
            await axios.put(`${API_URL}/drafts/${draftId}`, payload);
            fetchDrafts();
        } catch (e) {
            alert("Erreur: " + (e.response?.data?.detail || e.message));
        }
    };

    const handleDeleteDraft = async (draftId) => {
        if (!confirm("Supprimer ce brouillon ?")) return;
        try {
            await axios.delete(`${API_URL}/drafts/${draftId}`);
            fetchDrafts();
        } catch (e) {
            alert("Erreur: " + (e.response?.data?.detail || e.message));
        }
    };

    const handlePostDraft = async (draftId) => {
        const draft = drafts.find(d => d.id === draftId);
        if (draft?.status === 'posted') {
            if (!confirm("⚠️ Ce brouillon a déjà été publié. Re-publier ?")) return;
        }
        setDraftPostingId(draftId);
        try {
            const response = await axios.post(`${API_URL}/drafts/${draftId}/post`, {
                access_token: accessToken,
                ig_user_id: igUserId,
                force: draft?.status === 'posted',
            });
            alert(`✅ ${response.data.message}`);
            fetchDrafts();
        } catch (e) {
            alert("Erreur: " + (e.response?.data?.detail || e.message));
        } finally {
            setDraftPostingId(null);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">📋 Brouillons sauvegardés</h2>
                <button
                    onClick={fetchDrafts}
                    disabled={loading}
                    className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    Rafraîchir
                </button>
            </div>

            {drafts.length === 0 ? (
                <div className="bg-card border border-border rounded-xl p-12 text-center text-gray-500">
                    <p className="text-lg">Aucun brouillon sauvegardé</p>
                    <p className="text-sm mt-2">Créez une grille dans l'onglet "Création" et cliquez "💾 Save Draft"</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {drafts.map(draft => (
                        <DraftCard
                            key={draft.id}
                            draft={draft}
                            isExpanded={expandedDraft === draft.id}
                            onToggleExpand={() => setExpandedDraft(expandedDraft === draft.id ? null : draft.id)}
                            onUpdate={handleUpdateDraft}
                            onDelete={handleDeleteDraft}
                            onPost={handlePostDraft}
                            isPosting={draftPostingId === draft.id}
                            allDrafts={drafts}
                            setDrafts={setDrafts}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}


function DraftCard({ draft, isExpanded, onToggleExpand, onUpdate, onDelete, onPost, isPosting, allDrafts, setDrafts }) {
    const [activeId, setActiveId] = useState(null);
    const [isDirty, setIsDirty] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [currentOrder, setCurrentOrder] = useState([0, 1, 2]);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    const handleMove = (oldIndex, newIndex) => {
        const newOrder = arrayMove(currentOrder, oldIndex, newIndex);
        setCurrentOrder(newOrder);

        const reorderedPosts = arrayMove(draft.posts, oldIndex, newIndex);
        draft.posts = reorderedPosts;
        setDrafts([...allDrafts]);
        setIsDirty(true);
    };

    const handleDragStart = (event) => {
        setActiveId(event.active.id);
    };

    const handleDragEnd = (event) => {
        setActiveId(null);
        const { active, over } = event;
        if (over && active.id !== over.id) {
            const oldIndex = draft.posts.findIndex((p) => p.image_key === active.id);
            const newIndex = draft.posts.findIndex((p) => p.image_key === over.id);

            const newOrder = arrayMove(currentOrder, oldIndex, newIndex);
            setCurrentOrder(newOrder);

            const reorderedPosts = arrayMove(draft.posts, oldIndex, newIndex);
            draft.posts = reorderedPosts;
            setDrafts([...allDrafts]);

            setIsDirty(true);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        const captions = draft.posts.map(p => p.caption);
        const cropRatios = draft.posts.map(p => p.crop_ratio);
        const cropPositions = draft.posts.map(p => p.crop_position || { x: 50, y: 50 });

        const orderChanged = currentOrder[0] !== 0 || currentOrder[1] !== 1 || currentOrder[2] !== 2;

        await onUpdate(draft.id, captions, cropRatios, cropPositions, orderChanged ? currentOrder : null);

        setCurrentOrder([0, 1, 2]);
        setIsDirty(false);
        setIsSaving(false);
    };

    return (
        <div className={`bg-card border rounded-xl overflow-hidden transition-all ${draft.status === 'posted' ? 'border-green-500/30' : 'border-border'
            }`}>
            {/* Compact header — always visible */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
                onClick={onToggleExpand}
            >
                <div className="flex items-center gap-3">
                    <span className="text-sm font-mono text-gray-400">#{draft.id}</span>
                    {draft.status === 'posted' ? (
                        <span className="text-xs px-2 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                            ✅ Publié le {new Date(draft.posted_at).toLocaleDateString('fr-FR')}
                        </span>
                    ) : (
                        <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            📝 Brouillon
                        </span>
                    )}
                    {/* Mini thumbnails in collapsed state */}
                    {!isExpanded && (
                        <div className="flex gap-1 ml-2">
                            {draft.posts.map((post, idx) => (
                                <img
                                    key={idx}
                                    src={getFullImageUrl(post.image_url)}
                                    alt=""
                                    className="w-8 h-8 object-cover rounded"
                                />
                            ))}
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">
                        {new Date(draft.created_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {isExpanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </div>
            </div>

            {/* Expanded content — full editing */}
            {isExpanded && (
                <div className="p-6 pt-0 space-y-4 border-t border-gray-800">
                    {/* 3 images with crop editing and drag reordering */}
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
                        <SortableContext items={draft.posts.map((p) => p.image_key)} strategy={horizontalListSortingStrategy}>
                            <div className="grid grid-cols-3 gap-4 mt-4 relative">
                                {draft.posts.map((post, idx) => (
                                    <SortableDraftPostEditor
                                        key={post.image_key}
                                        id={post.image_key}
                                        post={post}
                                        idx={idx}
                                        draft={draft}
                                        onMarkDirty={() => setIsDirty(true)}
                                        onMove={handleMove}
                                        allDrafts={allDrafts}
                                        setDrafts={setDrafts}
                                    />
                                ))}
                            </div>
                        </SortableContext>
                        <DragOverlay adjustScale={true}>
                            {activeId ? (
                                <DraftPostEditor
                                    post={draft.posts.find((p) => p.image_key === activeId)}
                                    idx={draft.posts.findIndex((p) => p.image_key === activeId)}
                                    draft={draft}
                                    onMarkDirty={() => setIsDirty(true)}
                                    allDrafts={allDrafts}
                                    setDrafts={setDrafts}
                                    isOverlay
                                />
                            ) : null}
                        </DragOverlay>
                    </DndContext>

                    {/* Actions */}
                    <div className="flex justify-end gap-2 pt-3 border-t border-gray-800">
                        <button
                            onClick={handleSave}
                            disabled={!isDirty || isSaving}
                            className={`px-6 py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-1.5 transition-all ${isDirty && !isSaving
                                ? 'outline outline-emerald-500/50 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30'
                                : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                                }`}
                        >
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <span>💾</span>}
                            Enregistrer
                        </button>
                        <button
                            onClick={() => onPost(draft.id)}
                            disabled={isPosting}
                            className={`px-6 py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-1.5 transition-all ${isPosting
                                ? 'bg-gray-700 text-gray-400'
                                : draft.status === 'posted'
                                    ? 'bg-amber-600/20 text-amber-400 hover:bg-amber-600/30 border border-amber-500/20'
                                    : 'bg-blue-600 hover:bg-blue-500 text-white'
                                }`}
                        >
                            {isPosting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            {draft.status === 'posted' ? 'Re-publier' : '🚀 Publier'}
                        </button>
                        <button
                            onClick={() => onDelete(draft.id)}
                            className="px-4 py-2.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 border border-red-500/20 transition-all"
                        >
                            <Trash2 size={14} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}


function SortableDraftPostEditor(props) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: props.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div ref={setNodeRef} style={style} {...attributes}>
            <DraftPostEditor {...props} listeners={listeners} />
        </div>
    );
}

function DraftPostEditor({ post, idx, draft, onMarkDirty, onMove, allDrafts, setDrafts, listeners, isOverlay }) {
    const containerRef = useRef(null);
    const [isDragging, setIsDragging] = useState(false);
    const [isRegenerating, setIsRegenerating] = useState(false);
    const dragStart = useRef({ x: 0, y: 0, posX: 50, posY: 50 });

    const cropRatio = post.crop_ratio || 'original';
    const cropPosition = post.crop_position || { x: 50, y: 50 };
    const isOriginal = cropRatio === 'original';

    const handleMouseDown = useCallback((e) => {
        if (isOriginal) return;
        e.preventDefault();
        setIsDragging(true);
        dragStart.current = { x: e.clientX, y: e.clientY, posX: cropPosition.x, posY: cropPosition.y };

        const handleMouseMove = (e) => {
            const rect = containerRef.current?.getBoundingClientRect();
            if (!rect) return;

            const deltaX = e.clientX - dragStart.current.x;
            const deltaY = e.clientY - dragStart.current.y;

            // Inverted delta (same as UploadSection): drag right -> content moves left -> lower x%
            const sensitivity = 0.5;
            const newX = Math.max(0, Math.min(100, dragStart.current.posX - (deltaX / rect.width) * 100 * sensitivity));
            const newY = Math.max(0, Math.min(100, dragStart.current.posY - (deltaY / rect.height) * 100 * sensitivity));

            // Update locally for instant preview
            post.crop_position = { x: Math.round(newX), y: Math.round(newY) };
            setDrafts([...allDrafts]);
        };

        const handleMouseUp = () => {
            setIsDragging(false);
            onMarkDirty();

            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };

        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
    }, [isOriginal, cropPosition, draft, post, onMarkDirty, allDrafts, setDrafts]);

    return (
        <div className={`space-y-2 relative transition-all ${isOverlay ? 'scale-105 shadow-2xl ring-2 ring-purple-500 rounded-xl' : ''}`}>
            {/* Drag Handle Overlay for Reordering */}
            <div
                {...listeners}
                className="absolute top-2 right-2 bg-black/80 text-white p-2 rounded-lg shadow-xl z-20 cursor-grab active:cursor-grabbing hover:bg-purple-600 transition-colors border border-gray-600"
                title="Glisser pour réorganiser (Gauche/Milieu/Droite)"
            >
                <GripVertical size={16} />
            </div>

            {/* Image with crop preview */}
            <div
                ref={containerRef}
                className={`overflow-hidden rounded-lg bg-gray-900 relative group ${isDragging ? 'ring-2 ring-purple-400' : ''}`}
                style={isOriginal ? {} : { aspectRatio: ASPECT_CSS[cropRatio] }}
            >
                <img
                    src={getFullImageUrl(post.image_url)}
                    alt={`Draft ${draft.id} - ${idx}`}
                    className={`w-full h-full ${isOriginal ? 'object-contain' : 'object-cover'}`}
                    style={isOriginal ? {} : { objectPosition: `${cropPosition.x}% ${cropPosition.y}%` }}
                    draggable={false}
                    onMouseDown={handleMouseDown}
                />
                {!isOriginal && (
                    <div className={`absolute top-1 left-1 bg-black/70 text-white text-[9px] px-1.5 py-0.5 rounded-full flex items-center gap-1 pointer-events-none transition-opacity ${isDragging ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                        }`}>
                        <Move size={8} /> Glisser
                    </div>
                )}
                {!isOriginal && (
                    <div className="absolute bottom-1 right-1 bg-purple-600 text-white text-[9px] px-1.5 py-0.5 rounded-full font-bold">
                        {cropRatio}
                    </div>
                )}
            </div>

            {/* Crop ratio buttons */}
            <div className="flex gap-1">
                {CROP_OPTIONS.map(opt => (
                    <button
                        key={opt.value}
                        onClick={() => {
                            post.crop_ratio = opt.value;
                            setDrafts([...allDrafts]);
                            onMarkDirty();
                        }}
                        className={`flex-1 py-1 rounded text-[10px] font-semibold transition-all ${cropRatio === opt.value
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-800 text-gray-500 hover:text-white'
                            }`}
                    >
                        {opt.label}
                    </button>
                ))}
            </div>

            {/* Arrows for reordering */}
            <div className="flex gap-2">
                <button
                    onClick={() => {
                        if (idx > 0 && onMove) {
                            onMove(idx, idx - 1);
                        }
                    }}
                    disabled={idx === 0}
                    className="flex-1 py-1 rounded text-xs font-semibold bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700 disabled:opacity-50"
                >
                    ◀️ Déplacer
                </button>
                <button
                    onClick={() => {
                        if (idx < 2 && onMove) {
                            onMove(idx, idx + 1);
                        }
                    }}
                    disabled={idx === 2}
                    className="flex-1 py-1 rounded text-xs font-semibold bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700 disabled:opacity-50"
                >
                    Déplacer ▶️
                </button>
            </div>

            {/* Caption editor */}
            <textarea
                value={post.caption}
                onChange={(e) => {
                    post.caption = e.target.value;
                    setDrafts([...allDrafts]);
                    onMarkDirty();
                }}
                className="w-full bg-dark border border-gray-700 rounded-lg p-2 text-white text-xs resize-none h-24 focus:ring-2 focus:ring-purple-500 outline-none"
                placeholder="Caption..."
            />

            {/* Regenerate Caption button */}
            <button
                onClick={async () => {
                    setIsRegenerating(true);
                    try {
                        let imgB64 = "";
                        try {
                            // Always fetch via backend proxy to avoid S3 CORS issues on client-side
                            const filename = post.image_key ? post.image_key.split('/').pop() : post.image_url.split('/').pop();
                            const url = `${API_URL}/drafts/image/${filename}`;

                            const res = await axios.get(url, { responseType: 'blob' });
                            const reader = new FileReader();
                            const b64Promise = new Promise(resolve => {
                                reader.onloadend = () => resolve(reader.result);
                            });
                            reader.readAsDataURL(res.data);
                            const b64DataUrl = await b64Promise;
                            imgB64 = b64DataUrl.split(',')[1];
                        } catch (e) {
                            console.error("Image fetch error:", e);
                            alert("Impossible de récupérer l'image pour la régénération.");
                            setIsRegenerating(false);
                            return;
                        }

                        const payload = {
                            image_base64: imgB64,
                            captions_history: [post.caption] // Send current caption as context history
                        };

                        const regRes = await axios.post(`${API_URL}/regenerate_caption`, payload);
                        if (regRes.status === 200) {
                            post.caption = regRes.data.caption;
                            setDrafts([...allDrafts]);
                            onMarkDirty();
                        }
                    } catch (error) {
                        alert("Erreur: " + (error.response?.data?.detail || error.message));
                    } finally {
                        setIsRegenerating(false);
                    }
                }}
                disabled={isRegenerating}
                className="w-full py-1.5 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white flex justify-center items-center gap-1 transition-colors disabled:opacity-50"
            >
                {isRegenerating ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                Régénérer
            </button>
        </div>
    );
}

export default DraftsPanel;
