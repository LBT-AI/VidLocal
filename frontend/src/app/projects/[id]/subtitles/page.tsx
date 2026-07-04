"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import { SubtitleCue } from "@/types";
import toast from "react-hot-toast";

export default function SubtitleEditorPage() {
  const { id } = useParams();
  const [cues, setCues] = useState<SubtitleCue[]>([]);
  const [activeIdx, setActiveIdx] = useState(0);
  const [provider, setProvider] = useState("deeplx");
  const [subtitleOutputMode, setSubtitleOutputMode] = useState("translated");
  const [translating, setTranslating] = useState(false);

  useEffect(() => {
    api.get(`/api/projects/${id}/cues`).then((r) => setCues(r.data.data || []));
  }, [id]);

  const updateCue = useCallback(
    async (idx: number, vi_text: string) => {
      await api.put(`/api/projects/${id}/cues/${idx}`, { vi_text });
      setCues((prev) => prev.map((c) => (c.cue_index === idx ? { ...c, vi_text } : c)));
      toast.success("Saved");
    },
    [id]
  );

  const handleKeyDown = (e: React.KeyboardEvent, idx: number) => {
    if (e.ctrlKey && e.key === "Enter") {
      e.preventDefault();
      const next = cues.find((c) => c.cue_index === idx + 1);
      if (next) setActiveIdx(next.cue_index);
    }
  };

  const fixCPS = async () => {
    await api.post(`/api/projects/${id}/fix-cps`, {});
    toast.success("Auto-fix CPS triggered");
    window.location.reload();
  };

  const startTranslate = async () => {
    setTranslating(true);
    try {
      await api.post(`/api/projects/${id}/translate`, {
        provider,
        subtitle_output_mode: subtitleOutputMode,
        auto_fix_cps: provider === "gemini",
      });
      toast.success("Translate queued");
    } finally {
      setTranslating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Subtitle Editor</h1>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm bg-white"
          >
            <option value="deeplx">DeepLX</option>
            <option value="gemini">Gemini</option>
          </select>
          <select
            value={subtitleOutputMode}
            onChange={(e) => setSubtitleOutputMode(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm bg-white"
          >
            <option value="translated">Translated</option>
            <option value="bilingual">Bilingual</option>
            <option value="original_plus_translated">Original + Translated</option>
          </select>
          <button
            onClick={startTranslate}
            disabled={translating}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm disabled:opacity-50"
          >
            {translating ? "Queueing..." : "Translate"}
          </button>
          <button onClick={fixCPS} className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm">
            Auto Fix CPS
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground mb-2">Chinese (Original)</h2>
          {cues.map((c) => (
            <div key={c.id} className="p-3 rounded-lg border bg-slate-50 text-sm">
              <span className="text-xs text-muted-foreground">#{c.cue_index}</span>
              <p className="mt-1">{c.zh_text}</p>
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground mb-2">Vietnamese (Edit)</h2>
          {cues.map((c) => (
            <div
              key={c.id}
              className={`p-3 rounded-lg border ${activeIdx === c.cue_index ? "border-primary ring-1 ring-primary" : "bg-white"}`}
              onClick={() => setActiveIdx(c.cue_index)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">#{c.cue_index}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    c.status === "ok"
                      ? "bg-green-100 text-green-700"
                      : c.status === "cps_warning"
                      ? "bg-amber-100 text-amber-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  CPS {c.cps?.toFixed(1)} · {c.status}
                </span>
              </div>
              <textarea
                defaultValue={c.vi_text || ""}
                onBlur={(e) => updateCue(c.cue_index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, c.cue_index)}
                className="w-full text-sm p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                rows={2}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
