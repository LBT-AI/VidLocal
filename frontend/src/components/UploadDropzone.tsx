"use client";
import { useRef, useState } from "react";
import { Upload } from "lucide-react";

export default function UploadDropzone({ onUpload }: { onUpload: (file: File) => void }) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) onUpload(e.dataTransfer.files[0]);
  };

  return (
    <div
      onDragEnter={() => setDragActive(true)}
      onDragLeave={() => setDragActive(false)}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className="border-2 border-dashed rounded-xl p-10 text-center cursor-pointer hover:bg-slate-50 transition-colors"
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/x-msvideo,video/webm"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
      />
      <Upload className="w-10 h-10 mx-auto mb-4 text-muted-foreground" />
      {dragActive ? (
        <p>Drop the video here...</p>
      ) : (
        <p className="text-sm text-muted-foreground">Drag & drop a video, or click to select</p>
      )}
      <p className="text-xs text-muted-foreground mt-2">MP4/MOV/AVI up to 2GB</p>
    </div>
  );
}
