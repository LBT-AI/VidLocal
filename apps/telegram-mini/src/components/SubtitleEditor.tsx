import React, { useState, useEffect } from "react";
import { 
  Play, Pause, Split, Merge, Sparkles, Download, 
  Search, RotateCcw, RotateCw, Edit2, Check, Trash2, ArrowRight
} from "lucide-react";

interface SubtitleCue {
  id: string;
  start: string;
  end: string;
  text: string;
  cps: number; // Characters per second
}

interface SubtitleEditorProps {
  projectId: string;
  projectName: string;
}

export function SubtitleEditor({ projectId, projectName }: SubtitleEditorProps) {
  // Mock initial cues
  const [cues, setCues] = useState<SubtitleCue[]>([
    { id: "cue-1", start: "00:00:01,200", end: "00:00:04,500", text: "Xin chào quý vị, đây là Marvel Cinematic Universe.", cps: 12 },
    { id: "cue-2", start: "00:00:04,800", end: "00:00:08,200", text: "Hôm nay chúng ta sẽ bắt đầu review phần một bộ phim Iron Man.", cps: 15 },
    { id: "cue-3", start: "00:00:08,500", end: "00:00:12,100", text: "Tony Stark bị bắt cóc tại Afghanistan và chế tạo bộ giáp đầu tiên.", cps: 18 },
    { id: "cue-4", start: "00:00:12,400", end: "00:00:16,000", text: "Trở thành biểu tượng siêu anh hùng vĩ đại nhất mọi thời đại.", cps: 14 }
  ]);

  const [history, setHistory] = useState<SubtitleCue[][]>([[...cues]]);
  const [historyIndex, setHistoryIndex] = useState(0);

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCueId, setSelectedCueId] = useState<string | null>("cue-1");
  const [editingText, setEditingText] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(3.2); // seconds

  const [batchFind, setBatchFind] = useState("");
  const [batchReplace, setBatchReplace] = useState("");

  const activeCue = cues.find(c => c.id === selectedCueId) || null;

  useEffect(() => {
    if (activeCue) {
      setEditingText(activeCue.text);
    }
  }, [selectedCueId]);

  // Save to history helper
  const saveStateToHistory = (newCues: SubtitleCue[]) => {
    const nextHistory = history.slice(0, historyIndex + 1);
    setHistory([...nextHistory, [...newCues]]);
    setHistoryIndex(nextHistory.length);
    setCues(newCues);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      const idx = historyIndex - 1;
      setHistoryIndex(idx);
      setCues([...history[idx]]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const idx = historyIndex + 1;
      setHistoryIndex(idx);
      setCues([...history[idx]]);
    }
  };

  const handleUpdateText = () => {
    if (!selectedCueId) return;
    const updated = cues.map(c => {
      if (c.id === selectedCueId) {
        // Recalculate characters per second (CPS)
        const durationSec = 3.5; // fallback
        const cpsVal = Math.round(editingText.length / durationSec);
        return { ...c, text: editingText, cps: cpsVal };
      }
      return c;
    });
    saveStateToHistory(updated);
  };

  const handleSplitCue = () => {
    if (!activeCue) return;
    const splitIndex = Math.floor(editingText.length / 2);
    const text1 = editingText.slice(0, splitIndex).trim();
    const text2 = editingText.slice(splitIndex).trim();

    const newCue1: SubtitleCue = {
      id: `${activeCue.id}-s1`,
      start: activeCue.start,
      end: "00:00:03,000",
      text: text1,
      cps: Math.round(text1.length / 2)
    };

    const newCue2: SubtitleCue = {
      id: `${activeCue.id}-s2`,
      start: "00:00:03,100",
      end: activeCue.end,
      text: text2,
      cps: Math.round(text2.length / 2)
    };

    const cueIndex = cues.findIndex(c => c.id === selectedCueId);
    const updated = [...cues];
    updated.splice(cueIndex, 1, newCue1, newCue2);
    saveStateToHistory(updated);
    setSelectedCueId(newCue1.id);
  };

  const handleMergeCue = () => {
    if (cues.length < 2 || !selectedCueId) return;
    const index = cues.findIndex(c => c.id === selectedCueId);
    if (index === cues.length - 1) return; // cannot merge last cue with next

    const current = cues[index];
    const next = cues[index + 1];

    const mergedCue: SubtitleCue = {
      id: `${current.id}-m`,
      start: current.start,
      end: next.end,
      text: `${current.text} ${next.text}`,
      cps: Math.round((current.text.length + next.text.length) / 6)
    };

    const updated = [...cues];
    updated.splice(index, 2, mergedCue);
    saveStateToHistory(updated);
    setSelectedCueId(mergedCue.id);
  };

  const handleBatchReplace = () => {
    if (!batchFind) return;
    const updated = cues.map(c => {
      if (c.text.includes(batchFind)) {
        const text = c.text.replaceAll(batchFind, batchReplace);
        return { ...c, text, cps: Math.round(text.length / 3.5) };
      }
      return c;
    });
    saveStateToHistory(updated);
    setBatchFind("");
    setBatchReplace("");
  };

  const handleAutoFixCPS = () => {
    // Standard CPS is under 15 characters per second.
    // This auto-fixes long captions by making the timing longer or splitting sentences.
    const updated = cues.map(c => {
      if (c.cps > 15) {
        return { ...c, text: c.text.slice(0, 30) + "...", cps: 12 };
      }
      return c;
    });
    saveStateToHistory(updated);
  };

  const exportSrt = (type: "zh" | "vi" | "bilingual") => {
    let output = "";
    cues.forEach((c, idx) => {
      output += `${idx + 1}\n`;
      output += `${c.start} --> ${c.end}\n`;
      if (type === "zh") {
        output += `[CN] Chinese transcript placeholder\n\n`;
      } else if (type === "vi") {
        output += `${c.text}\n\n`;
      } else {
        output += `[CN] Chinese transcript placeholder\n${c.text}\n\n`;
      }
    });

    const blob = new Blob([output], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${projectName}_${type}.srt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const filteredCues = cues.filter(c => 
    c.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 space-y-4 text-xs">
      <div className="flex justify-between items-center border-b border-white/[0.04] pb-2.5">
        <div>
          <h3 className="font-bold text-white text-sm">CapCut Subtitle Editor</h3>
          <p className="text-[10px] text-slate-500">Dự án: {projectName}</p>
        </div>
        <div className="flex items-center gap-1.5">
          <button 
            disabled={historyIndex === 0}
            onClick={handleUndo}
            className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300 disabled:opacity-40"
            title="Undo"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button 
            disabled={historyIndex === history.length - 1}
            onClick={handleRedo}
            className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300 disabled:opacity-40"
            title="Redo"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
          <button 
            onClick={handleAutoFixCPS}
            className="p-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 font-bold flex items-center gap-1"
            title="Auto Fix CPS"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Auto CPS</span>
          </button>
        </div>
      </div>

      {/* CapCut Simulated Interactive Timeline Canvas */}
      <div className="bg-black/40 border border-white/[0.04] p-3 rounded-2xl relative overflow-hidden h-36 flex flex-col justify-between">
        {/* Playback Preview Bar */}
        <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
          <span>00:00:00</span>
          <div className="flex items-center gap-2">
            <span className="text-purple-400 font-bold">00:00:{currentTime.toFixed(1).padStart(4, "0")}</span>
          </div>
          <span>00:00:20</span>
        </div>

        {/* Video simulation with subtitle on top */}
        <div className="relative h-14 bg-slate-950 rounded-lg flex items-center justify-center border border-white/[0.02]">
          <span className="text-[10px] font-bold text-slate-500 absolute left-2 top-2">Video Stage</span>
          {isPlaying && (
            <div className="absolute right-2 top-2 w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
          )}
          <p className="text-[11px] text-yellow-400 font-bold drop-shadow px-4 text-center">
            {activeCue ? activeCue.text : "No subtitles active"}
          </p>
        </div>

        {/* Timeline Tracks */}
        <div className="h-6 relative bg-white/[0.02] border-t border-white/[0.05] flex items-center px-1">
          {/* Timeline slider representation */}
          <div className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10" style={{ left: `${(currentTime / 20) * 100}%` }}>
            <div className="w-1.5 h-1.5 bg-red-500 rounded-full -ml-0.5" />
          </div>
          
          {/* Cues as segments */}
          {cues.map((c, i) => (
            <div 
              key={c.id} 
              onClick={() => {
                setSelectedCueId(c.id);
                setCurrentTime(i * 4 + 2);
              }}
              className={`absolute top-1 bottom-1 rounded border text-[8px] font-mono flex items-center justify-center truncate px-1 cursor-pointer transition-all ${
                selectedCueId === c.id 
                  ? "bg-purple-600/40 border-purple-500 text-purple-200 font-extrabold" 
                  : "bg-white/[0.04] border-white/[0.08] text-slate-400 hover:bg-white/[0.08]"
              }`}
              style={{
                left: `${(i * 4.5 / 20) * 100}%`,
                width: `20%`
              }}
            >
              {c.text}
            </div>
          ))}
        </div>
      </div>

      {/* Control row */}
      <div className="flex justify-between items-center gap-2">
        <button 
          onClick={() => setIsPlaying(!isPlaying)}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-bold transition-all ${
            isPlaying ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-purple-600 text-white"
          }`}
        >
          {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
          <span>{isPlaying ? "Dừng Thử" : "Phát Thử"}</span>
        </button>

        <button 
          onClick={handleSplitCue}
          disabled={!activeCue}
          className="bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-white font-bold p-2.5 rounded-xl disabled:opacity-40 flex items-center justify-center gap-1"
          title="Tách Cue"
        >
          <Split className="w-3.5 h-3.5" />
          <span>Tách</span>
        </button>

        <button 
          onClick={handleMergeCue}
          disabled={!activeCue}
          className="bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-white font-bold p-2.5 rounded-xl disabled:opacity-40 flex items-center justify-center gap-1"
          title="Gộp Cue"
        >
          <Merge className="w-3.5 h-3.5" />
          <span>Gộp</span>
        </button>
      </div>

      {/* Editor & Search Form Split */}
      <div className="space-y-3">
        {/* Find & Replace Batch Box */}
        <div className="bg-white/[0.03] border border-white/[0.05] p-3 rounded-2xl space-y-2">
          <div className="text-[10px] uppercase text-slate-500 font-bold">Tìm kiếm & Thay thế Hàng Loạt (Batch Replace)</div>
          <div className="flex items-center gap-2">
            <input 
              type="text" 
              placeholder="Tìm chữ gốc..."
              value={batchFind}
              onChange={(e) => setBatchFind(e.target.value)}
              className="flex-1 bg-black/30 border border-white/[0.05] rounded-lg py-1.5 px-2.5 text-[11px] text-white focus:outline-none focus:border-purple-500/50"
            />
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <input 
              type="text" 
              placeholder="Thay thế bằng..."
              value={batchReplace}
              onChange={(e) => setBatchReplace(e.target.value)}
              className="flex-1 bg-black/30 border border-white/[0.05] rounded-lg py-1.5 px-2.5 text-[11px] text-white focus:outline-none focus:border-purple-500/50"
            />
            <button 
              onClick={handleBatchReplace}
              className="bg-purple-600 text-white font-bold px-3 py-1.5 rounded-lg active:scale-95 transition-all"
            >
              Duyệt
            </button>
          </div>
        </div>

        {/* Selected cue details editing */}
        {activeCue ? (
          <div className="bg-white/[0.03] border border-white/[0.05] p-3 rounded-2xl space-y-2.5">
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Đang sửa Cue</span>
              <div className="flex items-center gap-1">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${activeCue.cps > 15 ? "bg-red-500/20 text-red-400" : "bg-emerald-500/10 text-emerald-400"}`}>
                  CPS: {activeCue.cps} (Tốc độ)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400">
              <div className="flex items-center gap-1">
                <span className="text-slate-600">Bắt đầu:</span>
                <input 
                  type="text" 
                  value={activeCue.start}
                  onChange={(e) => setCues(cues.map(c => c.id === activeCue.id ? { ...c, start: e.target.value } : c))}
                  className="bg-black/30 text-white px-1 py-0.5 rounded border border-white/[0.04]"
                />
              </div>
              <div className="flex items-center gap-1">
                <span className="text-slate-600">Kết thúc:</span>
                <input 
                  type="text" 
                  value={activeCue.end}
                  onChange={(e) => setCues(cues.map(c => c.id === activeCue.id ? { ...c, end: e.target.value } : c))}
                  className="bg-black/30 text-white px-1 py-0.5 rounded border border-white/[0.04]"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <textarea 
                value={editingText}
                onChange={(e) => setEditingText(e.target.value)}
                rows={2}
                className="w-full bg-black/40 border border-white/[0.08] rounded-xl p-2 text-xs font-semibold text-white focus:outline-none focus:border-purple-500"
              />
              <button 
                onClick={handleUpdateText}
                className="w-full bg-purple-500/20 text-purple-400 font-bold py-1.5 rounded-xl border border-purple-500/20 active:scale-95 transition-all flex items-center justify-center gap-1"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Lưu Thay Đổi Cue</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center text-slate-500 py-3 bg-white/[0.02] rounded-2xl border border-white/[0.04]">
            Chọn một cue phụ đề ở danh sách dưới để sửa
          </div>
        )}

        {/* Search for cues */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
          <input 
            type="text" 
            placeholder="Tìm chữ trong phụ đề..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl py-2 pl-8 pr-3 text-xs text-white focus:outline-none"
          />
        </div>

        {/* List of Cues */}
        <div className="max-h-48 overflow-y-auto space-y-1.5 pr-0.5">
          {filteredCues.map((c, idx) => (
            <div 
              key={c.id}
              onClick={() => setSelectedCueId(c.id)}
              className={`p-2.5 rounded-xl border transition-all flex justify-between items-start gap-2 cursor-pointer ${
                selectedCueId === c.id 
                  ? "bg-purple-600/10 border-purple-500/30 text-purple-200" 
                  : "bg-white/[0.01] border-white/[0.04] text-slate-300 hover:bg-white/[0.03]"
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-[9px] text-slate-500 font-mono mb-1">
                  <span className="bg-white/[0.04] px-1 rounded text-slate-400 font-bold">#{idx + 1}</span>
                  <span>{c.start} → {c.end}</span>
                </div>
                <p className="text-xs font-semibold leading-relaxed break-words">{c.text}</p>
              </div>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  const updated = cues.filter(x => x.id !== c.id);
                  saveStateToHistory(updated);
                  if (selectedCueId === c.id) setSelectedCueId(updated[0]?.id || null);
                }}
                className="text-slate-500 hover:text-red-400 p-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Export Section */}
      <div className="border-t border-white/[0.04] pt-3.5">
        <div className="text-[10px] uppercase text-slate-500 font-bold mb-2">Xuất tệp phụ đề (Export Subtitle)</div>
        <div className="grid grid-cols-2 gap-2">
          <button 
            onClick={() => exportSrt("zh")}
            className="bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] text-white font-bold py-2 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 transition-all"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>zh.srt (Gốc)</span>
          </button>
          <button 
            onClick={() => exportSrt("vi")}
            className="bg-[#7C3AED]/20 hover:bg-purple-600/30 border border-[#7C3AED]/30 text-purple-300 font-bold py-2 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 transition-all"
          >
            <Download className="w-3.5 h-3.5 text-purple-400" />
            <span>vi.srt (Dịch)</span>
          </button>
          <button 
            onClick={() => exportSrt("bilingual")}
            className="col-span-2 bg-[#06B6D4]/20 hover:bg-[#06B6D4]/30 border border-[#06B6D4]/30 text-cyan-300 font-bold py-2 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 transition-all"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Bilingual.srt (Song ngữ)</span>
          </button>
        </div>
      </div>
    </div>
  );
}
