"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import UploadDropzone from "@/components/UploadDropzone";

export default function NewProjectPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [projectId, setProjectId] = useState<string | null>(null);

  const create = async () => {
    const res = await api.post("/api/projects", { title });
    setProjectId(res.data.data.id);
  };

  const upload = async (file: File) => {
    if (!projectId) return;
    const formData = new FormData();
    formData.append("file", file);
    await api.post(`/api/projects/${projectId}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    router.push(`/projects/${projectId}`);
  };

  if (!projectId) {
    return (
      <div className="max-w-md mx-auto px-4 py-20">
        <h1 className="text-xl font-bold mb-4">Create New Project</h1>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Project title"
          className="w-full px-3 py-2 border rounded-lg mb-4"
        />
        <button onClick={create} className="w-full bg-primary text-primary-foreground py-2 rounded-lg font-medium">
          Continue
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-12">
      <h1 className="text-xl font-bold mb-4">Upload Video</h1>
      <UploadDropzone onUpload={upload} />
    </div>
  );
}
