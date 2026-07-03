import React from "react";
import { Project } from "../../types";
import { IOSCard } from "../ui/IOSCard";
import { Calendar, FolderOpen, Play } from "lucide-react";

interface ProjectCardProps {
  key?: React.Key;
  project: Project;
  onClick: () => void | Promise<void>;
  onTriggerNext?: () => void | Promise<void>;
}

export function ProjectCard({ project, onClick, onTriggerNext }: ProjectCardProps) {
  const isCompleted = project.status === "published";
  const isRunning = project.status !== "published" && project.status !== "failed" && project.status !== "pending";

  let statusText = "Mới tạo";
  let statusColor = "text-slate-400 bg-slate-500/10 border-slate-500/10";

  if (project.status === "transcribing") {
    statusText = "Đang Transcribe";
    statusColor = "text-blue-400 bg-blue-500/10 border-blue-500/15";
  } else if (project.status === "translating") {
    statusText = "Đang Dịch Phụ Đề";
    statusColor = "text-purple-400 bg-purple-500/10 border-purple-500/15";
  } else if (project.status === "tts") {
    statusText = "Đang Lồng Tiếng (TTS)";
    statusColor = "text-yellow-400 bg-yellow-500/10 border-yellow-500/15";
  } else if (project.status === "rendering") {
    statusText = "Đang Render Video";
    statusColor = "text-orange-400 bg-orange-500/10 border-orange-500/15";
  } else if (project.status === "published") {
    statusText = "Đã Xuất Bản YT";
    statusColor = "text-emerald-400 bg-emerald-500/10 border-emerald-500/15";
  } else if (project.status === "failed") {
    statusText = "Thất Bại";
    statusColor = "text-red-400 bg-red-500/10 border-red-500/15";
  }

  return (
    <IOSCard
      id={`project-card-${project.id}`}
      onClick={onClick}
      className="space-y-3 border-white/[0.08]"
    >
      <div className="flex justify-between items-start gap-2">
        <div className="flex items-center gap-1.5">
          <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <FolderOpen className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white tracking-tight line-clamp-1">
              {project.name}
            </h4>
            <p className="text-[10px] text-slate-500">
              {new Date(project.created_time).toLocaleDateString("vi-VN")}
            </p>
          </div>
        </div>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${statusColor}`}>
          {statusText}
        </span>
      </div>

      <div className="flex justify-between items-center pt-1 text-xs">
        <div className="flex items-center gap-1.5 text-slate-400">
          <span className="font-bold text-slate-200">{project.video_count}</span>
          <span className="text-[11px] text-slate-500">Video thành phẩm</span>
        </div>
        
        {project.current_step !== "done" && onTriggerNext && (
          <button
            id={`btn-next-step-${project.id}`}
            onClick={(e) => {
              e.stopPropagation();
              onTriggerNext();
            }}
            className="bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 font-bold px-2.5 py-1 rounded-xl text-[10px] flex items-center gap-1 border border-purple-500/20 transition-all duration-200"
          >
            <Play className="w-3 h-3 fill-current" />
            Tiến hành: {project.current_step}
          </button>
        )}
      </div>

      {/* Mini Segment Progress indicator */}
      <div className="grid grid-cols-6 gap-1 pt-1">
        {Object.entries(project.steps).map(([stepKey, stepVal]) => {
          let bg = "bg-white/[0.04]";
          if (stepVal === "completed") bg = "bg-emerald-500";
          else if (stepVal === "running") bg = "bg-purple-500 animate-pulse";
          else if (stepVal === "failed") bg = "bg-red-500";

          return (
            <div key={stepKey} className="h-1 rounded-full overflow-hidden" title={`${stepKey}: ${stepVal}`}>
              <div className={`h-full ${bg}`} />
            </div>
          );
        })}
      </div>
    </IOSCard>
  );
}
