import React, { useState, useEffect } from "react";
import { getFiles, deleteFile, uploadFile } from "../lib/api";
import { 
  Folder, File, Download, Trash2, Eye, UploadCloud, 
  ChevronRight, RefreshCw, CheckCircle2, AlertCircle, FileText
} from "lucide-react";

export function FileManager() {
  const [folders, setFolders] = useState<Record<string, Array<{name: string, size: string, date: string}>> | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string>("videos");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // Simulated file preview Modal State
  const [previewFile, setPreviewFile] = useState<{name: string, folder: string} | null>(null);

  const fetchFiles = async () => {
    try {
      const res = await getFiles();
      setFolders(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleDelete = async (fileName: string) => {
    setLoading(true);
    try {
      const res = await deleteFile(selectedFolder, fileName);
      setFolders(res.files);
      setToast("Đã xóa file thành công!");
      setTimeout(() => setToast(""), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Mock upload action
  const triggerMockUpload = async (fileName?: string, sizeStr?: string) => {
    setLoading(true);
    try {
      const mockNames: Record<string, string> = {
        videos: "fb_watch_review_superhero.mp4",
        subtitles: "translated_subtitle_draft.srt",
        tts: "hoaimy_narrator_chapter3.mp3",
        render: "temp_ffmpeg_stitch.mp4",
        output: "final_export_facebook_yt.mp4",
        logs: "error_dump_celery.log"
      };
      
      const targetName = fileName || mockNames[selectedFolder] || "uploaded_file.bin";
      const targetSize = sizeStr || "8.4 MB";

      const res = await uploadFile(selectedFolder, targetName, targetSize);
      setFolders(res.files);
      setToast(`Đã tải lên tệp: ${targetName}`);
      setTimeout(() => setToast(""), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // HTML5 Drag and Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1) + " MB";
      triggerMockUpload(file.name, sizeMB);
    }
  };

  if (!folders) {
    return (
      <div className="flex items-center justify-center p-6 text-slate-500">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        <span>Đang đọc cấu hình tệp tin...</span>
      </div>
    );
  }

  const folderKeys = Object.keys(folders);
  const currentFiles = folders[selectedFolder] || [];

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 space-y-4 text-xs relative">
      {/* Toast Box */}
      {toast && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-2 rounded-xl text-center font-bold text-[10px] animate-pulse">
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
        <div>
          <h3 className="font-bold text-white text-sm">File Manager Explorer</h3>
          <p className="text-[10px] text-slate-500">Quản lý tệp tạm, phụ đề và đầu ra video</p>
        </div>
        <button 
          onClick={fetchFiles}
          className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Drag & Drop Target Area */}
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => triggerMockUpload()}
        className={`border-2 border-dashed rounded-2xl p-4 flex flex-col items-center justify-center gap-1.5 cursor-pointer transition-all ${
          isDragging 
            ? "border-purple-500 bg-purple-500/10" 
            : "border-white/[0.08] bg-white/[0.01] hover:bg-white/[0.03] hover:border-white/[0.15]"
        }`}
      >
        <UploadCloud className="w-6 h-6 text-purple-400" />
        <div className="text-center">
          <p className="font-bold text-white text-[10px] uppercase tracking-wider">Kéo thả tệp vào đây</p>
          <p className="text-[9px] text-slate-500 mt-0.5">Hỗ trợ tệp Video, Phụ đề, Thuyết minh, Hình thu nhỏ</p>
        </div>
      </div>

      {/* Folder Navigation Row */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {folderKeys.map(key => (
          <button
            key={key}
            onClick={() => setSelectedFolder(key)}
            className={`px-3 py-1.5 rounded-xl text-[10px] uppercase tracking-wider font-bold transition-all flex items-center gap-1 flex-shrink-0 ${
              selectedFolder === key
                ? "bg-purple-600 text-white"
                : "bg-white/[0.03] text-slate-400 border border-white/[0.05] hover:bg-white/[0.06]"
            }`}
          >
            <Folder className="w-3.5 h-3.5" />
            <span>{key}/</span>
            <span className="text-[8px] opacity-60">({folders[key]?.length || 0})</span>
          </button>
        ))}
      </div>

      {/* File List Block */}
      <div className="bg-black/30 border border-white/[0.04] rounded-2xl p-2 max-h-56 overflow-y-auto space-y-1.5">
        {currentFiles.map(file => (
          <div 
            key={file.name}
            className="p-2.5 rounded-xl bg-white/[0.01] border border-white/[0.03] flex justify-between items-center gap-3 hover:bg-white/[0.03]"
          >
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="w-4 h-4 text-cyan-400 flex-shrink-0" />
              <div className="min-w-0">
                <p className="font-bold text-white truncate text-[11px]">{file.name}</p>
                <div className="flex items-center gap-1.5 text-[9px] text-slate-500 font-mono mt-0.5">
                  <span>{file.size}</span>
                  <span>•</span>
                  <span>{file.date}</span>
                </div>
              </div>
            </div>

            {/* Actions for File */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <button 
                onClick={() => setPreviewFile({ name: file.name, folder: selectedFolder })}
                className="p-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] text-slate-300 border border-white/[0.05]"
                title="Preview"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
              
              <a 
                href={`#download-${file.name}`}
                onClick={(e) => {
                  e.preventDefault();
                  setToast(`Đang tải xuống tệp: ${file.name}`);
                  setTimeout(() => setToast(""), 3000);
                }}
                className="p-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] text-slate-300 border border-white/[0.05]"
                title="Download"
              >
                <Download className="w-3.5 h-3.5" />
              </a>

              <button 
                onClick={() => handleDelete(file.name)}
                className="p-1 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20"
                title="Xóa"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}

        {currentFiles.length === 0 && (
          <div className="text-center py-6 text-slate-500">
            Thư mục này hiện đang trống
          </div>
        )}
      </div>

      {/* Simulated File Preview Modal Box */}
      {previewFile && (
        <div className="absolute inset-4 z-50 bg-[#05070D] border border-white/[0.08] rounded-2xl p-4 flex flex-col justify-between shadow-2xl">
          <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
            <div className="flex items-center gap-1 text-cyan-400">
              <Eye className="w-4 h-4" />
              <span className="font-bold">Xem Trước File</span>
            </div>
            <button 
              onClick={() => setPreviewFile(null)}
              className="text-slate-400 hover:text-white font-extrabold text-sm"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 flex flex-col justify-center items-center py-4">
            <FileText className="w-10 h-10 text-purple-400 animate-bounce mb-3" />
            <p className="font-bold text-white text-xs text-center break-all px-2">{previewFile.name}</p>
            <p className="text-[10px] text-slate-500 mt-1 uppercase font-bold tracking-widest">{previewFile.folder}/ directory</p>

            {previewFile.folder === "subtitles" ? (
              <div className="mt-3 bg-black/40 border border-white/[0.04] p-3 rounded-xl font-mono text-[9px] text-slate-400 text-left w-full max-h-24 overflow-y-auto">
                1<br />00:01:05,000 --&gt; 00:01:08,500<br />Tony Stark announces he is Iron Man.
              </div>
            ) : previewFile.folder === "logs" ? (
              <div className="mt-3 bg-black/40 border border-white/[0.04] p-3 rounded-xl font-mono text-[9px] text-slate-400 text-left w-full max-h-24 overflow-y-auto">
                [INFO] starting worker thread.<br />[SUCCESS] yt-dlp binary fetched.
              </div>
            ) : (
              <p className="text-[10px] text-slate-400 text-center mt-3 bg-black/30 p-2.5 rounded-xl border border-white/[0.03]">
                Tệp nhị phân đa phương tiện. Xem trước ngoại tuyến đã được tối ưu hóa.
              </p>
            )}
          </div>

          <button 
            onClick={() => setPreviewFile(null)}
            className="w-full bg-[#7C3AED] text-white font-bold py-2 rounded-xl active:scale-95 transition-all"
          >
            Đóng Xem Trước
          </button>
        </div>
      )}
    </div>
  );
}
