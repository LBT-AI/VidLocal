"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import { SubtitleCue } from "@/types";
import toast from "react-hot-toast";

export default function VoiceStudioPage() {
  const { id } = useParams();
  const [cues, setCues] = useState<SubtitleCue[]>([]);
  const [voice, setVoice] = useState("vi-VN-HoaiMyNeural");

  useEffect(() => {
    api.get(`/api/projects/${id}/cues`).then((r) => setCues(r.data.data || []));
  }, [id]);

  const startTTS = async () => {
    await api.post(`/api/projects/${id}/tts?voice=${voice}`);
    toast.success("TTS queued");
  };

  const playAudio = (idx: number) => {
    const audio = new Audio(`${process.env.NEXT_PUBLIC_API_URL}/api/projects/${id}/tts/${idx}`);
    audio.play();
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold mb-6">TTS Studio</h1>
      <div className="flex items-center gap-4 mb-6">
        <select
          value={voice}
          onChange={(e) => setVoice(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm"
        >
          <option value="vi-VN-HoaiMyNeural">Female (HoaiMy)</option>
          <option value="vi-VN-NamMinhNeural">Male (NamMinh)</option>
        </select>
        <button onClick={startTTS} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium">
          Generate All TTS
        </button>
      </div>
      <div className="space-y-3">
        {cues.map((c) => (
          <div key={c.id} className="flex items-center justify-between p-4 border rounded-lg bg-white">
            <div>
              <p className="text-sm font-medium">#{c.cue_index}</p>
              <p className="text-xs text-muted-foreground">{c.vi_text}</p>
            </div>
            <button
              onClick={() => playAudio(c.cue_index)}
              className="px-3 py-1.5 border rounded-md text-xs font-medium hover:bg-slate-50"
            >
              Play
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
