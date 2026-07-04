"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import ProjectCard from "@/components/ProjectCard";
import { Project } from "@/types";
import { Plus } from "lucide-react";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState("");
  const router = useRouter();

  useEffect(() => {
    api.get("/api/projects").then((r) => setProjects(r.data.data || []));
  }, []);

  const create = async () => {
    if (!title) return;
    const res = await api.post("/api/projects", { title });
    router.push(`/projects/${res.data.data.id}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Projects</h1>
        <div className="flex gap-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New project title"
            className="px-3 py-2 border rounded-lg text-sm"
          />
          <button
            onClick={create}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            New
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {projects.map((p) => (
          <ProjectCard key={p.id} project={p} />
        ))}
      </div>
    </div>
  );
}
