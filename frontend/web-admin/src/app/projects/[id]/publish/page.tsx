"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import toast from "react-hot-toast";

export default function PublishPage() {
  const { id } = useParams();
  const [platform, setPlatform] = useState("youtube");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [privacy, setPrivacy] = useState("private");

  const publish = async () => {
    await api.post(`/api/projects/${id}/publish`, {
      platform,
      title,
      description,
      privacy,
    });
    toast.success("Publish job created");
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold mb-6">Publish</h1>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Platform</label>
          <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm">
            <option value="youtube">YouTube</option>
            <option value="tiktok">TikTok</option>
            <option value="facebook">Facebook</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" rows={4} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Privacy</label>
          <select value={privacy} onChange={(e) => setPrivacy(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm">
            <option value="private">Private</option>
            <option value="unlisted">Unlisted</option>
            <option value="public">Public</option>
          </select>
        </div>
        <button onClick={publish} className="px-6 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium">
          Send to Publish
        </button>
      </div>
    </div>
  );
}
