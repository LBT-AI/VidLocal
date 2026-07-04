"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import toast from "react-hot-toast";

export default function RenderPage() {
  const { id } = useParams();
  const [mode, setMode] = useState("hardsub");
  const [loading, setLoading] = useState(false);

  const render = async () => {
    setLoading(true);
    try {
      await api.post(`/api/projects/${id}/render?mode=${mode}`);
      toast.success("Render queued");
    } finally {
      setLoading(false);
    }
  };

  const download = async () => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/projects/${id}/output`, "_blank");
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold mb-6">Render & Export</h1>
      <div className="space-y-3 mb-6">
        {[
          { value: "voice_only", label: "Voice Only (no subtitles)" },
          { value: "softsub", label: "Voice + Soft Subtitle" },
          { value: "hardsub", label: "Voice + Hardcoded Subtitle" },
        ].map((m) => (
          <label key={m.value} className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-slate-50">
            <input
              type="radio"
              name="mode"
              value={m.value}
              checked={mode === m.value}
              onChange={(e) => setMode(e.target.value)}
            />
            <span className="text-sm font-medium">{m.label}</span>
          </label>
        ))}
      </div>
      <div className="flex gap-3">
        <button
          onClick={render}
          disabled={loading}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {loading ? "Queueing..." : "Start Render"}
        </button>
        <button
          onClick={download}
          className="px-6 py-2 border rounded-lg text-sm font-medium hover:bg-slate-50"
        >
          Download MP4
        </button>
      </div>
    </div>
  );
}
