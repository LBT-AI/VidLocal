"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { Project } from "@/types";

export default function ProjectDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    api.get(`/api/projects/${id}`).then((r) => setProject(r.data.data));
  }, [id]);

  if (!project) return <div className="p-8">Loading...</div>;

  const steps = [
    { key: "upload", label: "Upload Video", done: !!project.original_video_path },
    { key: "transcribe", label: "Transcribe", done: !!project.zh_srt_path },
    { key: "translate", label: "Translate", done: !!project.vi_srt_path },
    { key: "tts", label: "TTS", done: project.status === "done" || project.status === "tts" },
    { key: "render", label: "Render", done: project.status === "done" },
  ];

  const startTranscribe = async () => {
    await api.post(`/api/projects/${id}/transcribe`);
    window.location.reload();
  };

  const startTranslate = async () => {
    await api.post(`/api/projects/${id}/translate`, { provider: "gemini", auto_fix_cps: true });
    window.location.reload();
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{project.title}</h1>
          <StatusBadge status={project.status} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-8">
        {steps.map((s) => (
          <div
            key={s.key}
            className={`p-4 rounded-lg border text-center ${s.done ? "bg-green-50 border-green-200" : "bg-white"}`}
          >
            <p className="text-sm font-medium">{s.label}</p>
            <p className="text-xs mt-1">{s.done ? "Done" : "Pending"}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        {!project.zh_srt_path && (
          <button onClick={startTranscribe} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">
            Start Transcribe
          </button>
        )}
        {project.zh_srt_path && !project.vi_srt_path && (
          <button onClick={startTranslate} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium">
            Start Translate
          </button>
        )}
        <button
          onClick={() => router.push(`/projects/${id}/subtitles`)}
          className="px-4 py-2 border rounded-lg text-sm font-medium hover:bg-slate-50"
        >
          Edit Subtitles
        </button>
        <button
          onClick={() => router.push(`/projects/${id}/voice`)}
          className="px-4 py-2 border rounded-lg text-sm font-medium hover:bg-slate-50"
        >
          TTS Studio
        </button>
        <button
          onClick={() => router.push(`/projects/${id}/render`)}
          className="px-4 py-2 border rounded-lg text-sm font-medium hover:bg-slate-50"
        >
          Render & Export
        </button>
        <button
          onClick={() => router.push(`/projects/${id}/publish`)}
          className="px-4 py-2 border rounded-lg text-sm font-medium hover:bg-slate-50"
        >
          Publish
        </button>
      </div>
    </div>
  );
}
