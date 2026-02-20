import React, { useRef, useState, useCallback } from 'react';
import { Upload, X, CheckCircle, Move } from 'lucide-react';
import clsx from 'clsx';

const CROP_OPTIONS = [
    { value: 'original', label: 'Original' },
    { value: '1:1', label: '1:1' },
    { value: '4:5', label: '4:5' },
    { value: '16:9', label: '16:9' },
];

const ASPECT_RATIOS = {
    'original': null,
    '1:1': '1/1',
    '4:5': '4/5',
    '16:9': '16/9',
};

function UploadSection({ files, previews, onUpload, userContext, setUserContext, individualContexts, onContextChange, cropRatios, onCropChange, cropPositions, onPositionChange }) {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {files.map((file, index) => (
                    <UploadSlot
                        key={index}
                        index={index}
                        file={file}
                        preview={previews[index]}
                        onUpload={onUpload}
                        context={individualContexts[index]}
                        onContextChange={onContextChange}
                        cropRatio={cropRatios?.[index] || 'original'}
                        onCropChange={onCropChange}
                        cropPosition={cropPositions?.[index] || { x: 50, y: 50 }}
                        onPositionChange={onPositionChange}
                    />
                ))}
            </div>

            {/* Common Thread Context */}
            <div className="bg-card border border-border rounded-xl p-4 space-y-2">
                <label className="text-sm font-medium text-purple-300 flex items-center gap-2">
                    <span className="text-lg">🧵</span>
                    Fil Rouge / Common Thread Context
                </label>
                <textarea
                    value={userContext}
                    onChange={(e) => setUserContext(e.target.value)}
                    placeholder="Describe the common theme, mood, or link between all 3 photos..."
                    className="w-full bg-dark border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-purple-500 outline-none min-h-[80px] text-sm"
                />
            </div>
        </div>
    );
}

function UploadSlot({ index, file, preview, onUpload, context, onContextChange, cropRatio, onCropChange, cropPosition, onPositionChange }) {
    const containerRef = useRef(null);
    const [isDragging, setIsDragging] = useState(false);
    const dragStart = useRef({ x: 0, y: 0, posX: 50, posY: 50 });

    const isOriginal = cropRatio === 'original';
    const aspectStyle = isOriginal ? {} : { aspectRatio: ASPECT_RATIOS[cropRatio] };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            if (droppedFile.type.startsWith('image/')) {
                onUpload(index, droppedFile);
            }
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            onUpload(index, e.target.files[0]);
        }
    };

    const handleRemove = (e) => {
        e.preventDefault();
        e.stopPropagation();
        onUpload(index, null);
    };

    // --- Drag-to-position handlers ---
    const handleMouseDown = useCallback((e) => {
        if (isOriginal || !preview) return;
        e.preventDefault();
        setIsDragging(true);
        dragStart.current = {
            x: e.clientX,
            y: e.clientY,
            posX: cropPosition.x,
            posY: cropPosition.y,
        };

        const handleMouseMove = (e) => {
            const rect = containerRef.current?.getBoundingClientRect();
            if (!rect) return;

            const deltaX = e.clientX - dragStart.current.x;
            const deltaY = e.clientY - dragStart.current.y;

            // Convert pixel delta to percentage (inverted: drag right = image moves left = lower x%)
            const sensitivity = 0.5;
            const newX = Math.max(0, Math.min(100, dragStart.current.posX - (deltaX / rect.width) * 100 * sensitivity));
            const newY = Math.max(0, Math.min(100, dragStart.current.posY - (deltaY / rect.height) * 100 * sensitivity));

            onPositionChange(index, { x: Math.round(newX), y: Math.round(newY) });
        };

        const handleMouseUp = () => {
            setIsDragging(false);
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };

        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
    }, [isOriginal, preview, cropPosition, index, onPositionChange]);

    return (
        <div className="space-y-3">
            <div
                ref={containerRef}
                className={clsx(
                    "relative group rounded-xl border-dashed border-2 flex flex-col items-center justify-center transition-all overflow-hidden",
                    preview
                        ? "border-green-500/50 bg-green-500/5"
                        : "border-gray-700 bg-card hover:border-purple-500/50 hover:bg-purple-500/5 cursor-pointer",
                    isDragging && "ring-2 ring-purple-400"
                )}
                style={preview ? { ...aspectStyle, minHeight: isOriginal ? '256px' : undefined } : { height: '256px' }}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
            >
                {preview ? (
                    <>
                        <img
                            src={preview}
                            alt="Preview"
                            className={clsx(
                                "w-full h-full",
                                isOriginal ? "object-contain" : "object-cover"
                            )}
                            style={isOriginal ? {} : { objectPosition: `${cropPosition.x}% ${cropPosition.y}%` }}
                            draggable={false}
                            onMouseDown={handleMouseDown}
                        />

                        {/* Drag hint for cropped images */}
                        {!isOriginal && (
                            <div className={clsx(
                                "absolute top-2 left-2 bg-black/70 text-white text-[10px] px-2 py-1 rounded-full flex items-center gap-1 pointer-events-none transition-opacity",
                                isDragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                            )}>
                                <Move size={10} /> Glisser pour cadrer
                            </div>
                        )}

                        {/* Overlay on hover */}
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center z-10 pointer-events-none">
                            <button
                                onClick={handleRemove}
                                className="bg-red-500/20 text-red-500 p-3 rounded-full hover:bg-red-500/40 transition-colors pointer-events-auto"
                            >
                                <X size={24} />
                            </button>
                        </div>

                        <div className="absolute bottom-3 right-3 bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1 shadow-lg z-20">
                            <CheckCircle size={12} /> Ready
                        </div>

                        {/* Current crop info */}
                        {!isOriginal && (
                            <div className="absolute bottom-3 left-3 bg-purple-600 text-white text-[10px] px-2 py-1 rounded-full shadow-lg z-20">
                                {cropRatio}
                            </div>
                        )}
                    </>
                ) : (
                    <>
                        <div className="text-center p-6 space-y-3 pointer-events-none">
                            <div className="bg-gray-800 p-4 rounded-full inline-block text-gray-400 group-hover:text-purple-400 group-hover:scale-110 transition-transform">
                                <Upload size={32} />
                            </div>
                            <div>
                                <p className="font-semibold text-gray-300">Slot {index + 1}</p>
                                <p className="text-sm text-gray-500">{(['Left', 'Middle', 'Right'])[index]}</p>
                            </div>
                        </div>
                        <input
                            type="file"
                            accept="image/*"
                            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                            onChange={handleChange}
                        />
                    </>
                )}
            </div>

            {/* Per-image crop ratio selector */}
            {preview && (
                <div className="flex gap-1">
                    {CROP_OPTIONS.map(opt => (
                        <button
                            key={opt.value}
                            onClick={() => onCropChange(index, opt.value)}
                            className={`flex-1 py-1.5 rounded text-xs font-semibold transition-all ${cropRatio === opt.value
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-gray-800 text-gray-500 hover:text-white'
                                }`}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            )}

            {/* Individual Context Input */}
            <textarea
                value={context}
                onChange={(e) => onContextChange(index, e.target.value)}
                placeholder={`Context for Image ${index + 1}...`}
                className="w-full bg-card border border-gray-700 rounded-lg p-2 text-white text-xs focus:ring-1 focus:ring-purple-500 outline-none resize-none h-20"
            />
        </div>
    );
}

export default UploadSection;
