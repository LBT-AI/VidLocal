import Link from "next/link";
import StatusBadge from "./StatusBadge";
import { Project } from "@/types";

export default function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="block rounded-xl border bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold truncate">{project.title}</h3>
        <StatusBadge status={project.status} />
      </div>
      <p className="text-xs text-muted-foreground">
        {new Date(project.created_at).toLocaleDateString()}
      </p>
    </Link>
  );
}
