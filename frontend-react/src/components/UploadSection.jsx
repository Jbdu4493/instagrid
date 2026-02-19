import React from 'react';
import { Upload, X, CheckCircle } from 'lucide-react';
import clsx from 'clsx';

function UploadSection({ files, previews, onUpload, userContext, setUserContext, individualContexts, onContextChange }) {
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
                    />
                ))}
            </div>

            {/* Common Thread Context - Moved here for better flow */}
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

function UploadSlot({ index, file, preview, onUpload, context, onContextChange }) {
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

    return (
        <div className="space-y-3">
            <div
                className={clsx(
                    "relative group h-64 rounded-xl border-dashed border-2 flex flex-col items-center justify-center transition-all overflow-hidden",
                    preview
                        ? "border-green-500/50 bg-green-500/5"
                        : "border-gray-700 bg-card hover:border-purple-500/50 hover:bg-purple-500/5 cursor-pointer"
                )}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
            >
                {preview ? (
                    <>
                        <img src={preview} alt="Preview" className="w-full h-full object-cover" />

                        {/* Overlay on hover */}
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center z-10">
                            <button
                                onClick={handleRemove}
                                className="bg-red-500/20 text-red-500 p-3 rounded-full hover:bg-red-500/40 transition-colors"
                            >
                                <X size={24} />
                            </button>
                        </div>

                        <div className="absolute bottom-3 right-3 bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1 shadow-lg z-20">
                            <CheckCircle size={12} /> Ready
                        </div>
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
