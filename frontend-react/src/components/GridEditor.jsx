import React from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragOverlay } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, RefreshCw, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import clsx from 'clsx';

function GridEditor({ posts, setPosts, onRegenerate, onHistoryNav, availableAiProviders }) {
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const [activeId, setActiveId] = React.useState(null);

    const handleDragStart = (event) => {
        setActiveId(event.active.id);
    };

    const handleDragEnd = (event) => {
        const { active, over } = event;

        if (active.id !== over.id) {
            setPosts((items) => {
                const oldIndex = items.findIndex((item) => item.id === active.id);
                const newIndex = items.findIndex((item) => item.id === over.id);
                return arrayMove(items, oldIndex, newIndex);
            });
        }

        setActiveId(null);
    };

    const handleCaptionChange = (id, newCaption) => {
        setPosts(prevPosts =>
            prevPosts.map(post =>
                post.id === id ? { ...post, caption: newCaption } : post
            )
        );
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <SortableContext
                items={posts.map(p => p.id)}
                strategy={horizontalListSortingStrategy}
            >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {posts.map((post, index) => (
                        <SortableItem
                            key={post.id}
                            id={post.id}
                            post={post}
                            index={index}
                            onCaptionChange={handleCaptionChange}
                            onRegenerate={onRegenerate}
                            onHistoryNav={onHistoryNav}
                            availableAiProviders={availableAiProviders}
                        />
                    ))}
                </div>
            </SortableContext>
            <DragOverlay adjustScale={true}>
                {activeId ? (
                    <PostCard
                        post={posts.find(p => p.id === activeId)}
                        index={posts.findIndex(p => p.id === activeId)}
                        isOverlay
                    />
                ) : null}
            </DragOverlay>
        </DndContext>
    );
}

function SortableItem(props) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: props.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div ref={setNodeRef} style={style} {...attributes}>
            <PostCard {...props} listeners={listeners} />
        </div>
    );
}

function PostCard({ post, index, onCaptionChange, onRegenerate, onHistoryNav, listeners, isOverlay, availableAiProviders }) {
    const [isRegenerating, setIsRegenerating] = React.useState(false);
    const [selectedAi, setSelectedAi] = React.useState(availableAiProviders?.[0]?.id || 'openai');

    // Update selectedAi if availableAiProviders changes and no value is set
    React.useEffect(() => {
        if (availableAiProviders?.length > 0 && (!selectedAi || availableAiProviders.findIndex(p => p.id === selectedAi) === -1)) {
            setSelectedAi(availableAiProviders[0].id);
        }
    }, [availableAiProviders, selectedAi]);

    const handleRegenerateClick = async () => {
        setIsRegenerating(true);
        await onRegenerate?.(post.id, selectedAi);
        setIsRegenerating(false);
    };

    if (!post) return null;

    const ASPECT_MAP = { 'original': null, '1:1': '1/1', '4:5': '4/5', '16:9': '16/9' };
    const cropRatio = post.cropRatio || 'original';
    const cropPosition = post.cropPosition || { x: 50, y: 50 };
    const isOriginal = cropRatio === 'original';
    const aspectStyle = isOriginal ? {} : { aspectRatio: ASPECT_MAP[cropRatio] };

    return (
        <div className={clsx(
            "bg-card rounded-xl border border-border overflow-hidden flex flex-col h-full shadow-lg transition-shadow",
            isOverlay && "shadow-2xl ring-2 ring-purple-500 scale-105 cursor-grabbing"
        )}>
            {/* Image Header with Drag Handle */}
            <div className="relative group cursor-grab active:cursor-grabbing overflow-hidden" style={isOriginal ? { height: '256px' } : aspectStyle}>
                <img
                    src={post.preview}
                    alt="Post"
                    className="w-full h-full object-cover"
                    style={isOriginal ? {} : { objectPosition: `${cropPosition.x}% ${cropPosition.y}%` }}
                />

                {/* Score Badge */}
                {post.score !== null && post.score !== undefined && (
                    <div className={clsx(
                        "absolute top-2 left-2 px-2 py-1 rounded-lg text-xs font-bold shadow-lg border border-white/20 backdrop-blur-md",
                        post.score >= 80 ? "bg-green-500/80 text-white" :
                            post.score >= 60 ? "bg-yellow-500/80 text-white" :
                                "bg-red-500/80 text-white"
                    )}>
                        {post.score}/100
                    </div>
                )}

                <div
                    className="absolute top-2 right-2 bg-black/60 p-2 rounded-lg text-white/80 hover:text-white hover:bg-black/80 transition-colors"
                    {...listeners}
                >
                    <GripVertical size={20} />
                </div>

                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 flex items-end justify-between">
                    <p className="text-xs text-secondary-foreground font-mono">
                        Position {index + 1} ({['Left', 'Middle', 'Right'][index]}) - ID: {post.originalIndex}
                    </p>
                    {!isOriginal && (
                        <span className="bg-purple-600 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
                            {cropRatio}
                        </span>
                    )}
                </div>
            </div>
            {/* Caption Editor */}
            <div className="p-4 flex-1 flex flex-col gap-2">
                <div className="flex justify-between items-center">
                    <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Caption</label>

                    {/* History Controls */}
                    {(post.captions && post.captions.length > 0) && (
                        <div className="flex items-center bg-dark/50 rounded-lg p-1 gap-1">
                            <button
                                onClick={() => onHistoryNav?.(post.id, 'prev')}
                                disabled={post.currentCaptionIndex === 0}
                                className="p-1 hover:text-white text-gray-400 disabled:opacity-30 disabled:hover:text-gray-400"
                            >
                                <ChevronLeft size={14} />
                            </button>
                            <span className="text-[10px] font-mono text-gray-400 min-w-[20px] text-center">
                                v{post.currentCaptionIndex + 1}/{post.captions.length}
                            </span>
                            <button
                                onClick={() => onHistoryNav?.(post.id, 'next')}
                                disabled={post.currentCaptionIndex === post.captions.length - 1}
                                className="p-1 hover:text-white text-gray-400 disabled:opacity-30 disabled:hover:text-gray-400"
                            >
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    )}
                </div>

                <div className="relative">
                    <textarea
                        className="w-full bg-dark border border-gray-700 rounded-lg p-3 text-sm text-gray-200 resize-none h-32 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all scrollbar-hide pr-10"
                        value={post.caption}
                        onChange={(e) => onCaptionChange?.(post.id, e.target.value)}
                        placeholder="Write a caption..."
                    />

                    {/* Regenerate Controls (Absolute inside/next to textarea) */}
                    <div className="absolute bottom-2 right-2 flex items-center gap-2">
                        {availableAiProviders && availableAiProviders.length > 0 && (
                            <select
                                value={selectedAi}
                                onChange={(e) => setSelectedAi(e.target.value)}
                                disabled={isRegenerating}
                                className="bg-gray-800/80 backdrop-blur-md border border-gray-700 text-purple-300 text-[10px] font-bold py-1 px-2 pr-6 rounded focus:ring-purple-500 focus:border-purple-500 appearance-none h-8 outline-none"
                            >
                                {availableAiProviders.map(provider => (
                                    <option key={provider.id} value={provider.id}>
                                        {provider.id === 'openai' ? 'OpenAI' : 'Gemini'}
                                    </option>
                                ))}
                            </select>
                        )}
                        <button
                            onClick={handleRegenerateClick}
                            disabled={isRegenerating || (availableAiProviders && availableAiProviders.length === 0)}
                            title="Regenerate this caption"
                            className="p-2 h-8 bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 rounded transition-colors disabled:opacity-50 flex items-center justify-center"
                        >
                            {isRegenerating ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default GridEditor;
