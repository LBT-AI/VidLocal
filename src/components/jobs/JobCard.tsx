import React from "react";
import { VideoJob } from "../../types";
import { IOSCard } from "../ui/IOSCard";
import { SourcePlatformBadge } from "../SourcePlatformBadge";
import { StatusBadge } from "../StatusBadge";
import { Calendar, ChevronRight, Play, Youtube, AlertTriangle } from "lucide-react";

interface JobCardProps {
  key?: React.Key;
  job: VideoJob;
  onClick: () => void | Promise<void>;
  onReviewCharacters?: () => void | Promise<void>;
  onReviewMetadata?: () => void | Promise<void>;
  onRetry?: () => void | Promise<void>;
}

export function JobCard({ job, onClick, onReviewCharacters, onReviewMetadata, onRetry }: JobCardProps) {
  const isWaitingGlossary = job.status === "waiting_approval" && job.current_step === "glossary_review";
  const isWaitingMetadata = job.status === "waiting_approval" && job.current_step === "seo_metadata";
  const isFailed = job.status === "failed";
  const isCompleted = job.status === "completed";

  // Style customization based on status
  let cardBorderClass = "border-white/[0.08]";
  let glowColor: string | undefined;

  if (isWaitingGlossary || isWaitingMetadata) {
    cardBorderClass = "border-yellow-500/30 border-dashed bg-yellow-500/[0.02]";
    glowColor = "rgba(245, 158, 11, 0.05)";
  } else if (isFailed) {
    cardBorderClass = "border-red-500/20 bg-red-500/[0.01]";
  } else if (isCompleted) {
    cardBorderClass = "border-emerald-500/25 bg-emerald-500/[0.01]";
  }

  const timeAgo = (dateStr: string) => {
    const elapsed = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(elapsed / 60000);
    if (minutes < 1) return "Vừa xong";
    if (minutes < 60) return `${minutes} phút trước`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} giờ trước`;
    return new Date(dateStr).toLocaleDateString("vi-VN");
  };

  return (
    <IOSCard
      id={`job-card-${job.id}`}
      onClick={onClick}
      className={`${cardBorderClass} space-y-3 relative`}
      glowColor={glowColor}
    >
      {/* Quick pulsating indicators for actions */}
      {(isWaitingGlossary || isWaitingMetadata) && (
        <span className="absolute top-3 right-3 flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500"></span>
        </span>
      )}

      {/* Header Info */}
      <div className="flex justify-between items-start gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <SourcePlatformBadge platform={job.platform} />
          <span className="text-[10px] text-slate-500">•</span>
          <span className="text-[10px] text-slate-400 font-medium font-mono">
            {job.id}
          </span>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Title */}
      <div className="space-y-1">
        <h4 className="text-sm font-bold text-white leading-snug line-clamp-2">
          {job.title}
        </h4>
        <p className="text-[11px] text-slate-500 flex items-center gap-1">
          <Calendar className="w-3 h-3 text-slate-600" />
          <span>{timeAgo(job.created_time)} • Admin</span>
        </p>
      </div>

      {/* Progress section if active */}
      {!isCompleted && !isFailed && (
        <div className="space-y-1 pt-1">
          <div className="flex justify-between text-[11px] font-semibold">
            <span className="text-slate-400 uppercase tracking-widest text-[9px]">
              Tiến trình {job.current_step.replace("_", " ")}
            </span>
            <span className="text-purple-400 font-mono">{job.progress}%</span>
          </div>
          <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden border border-white/[0.04]">
            <div
              style={{ width: `${job.progress}%` }}
              className="h-full bg-gradient-to-r from-purple-500 via-[#7C3AED] to-cyan-400 transition-all duration-1000"
            />
          </div>
        </div>
      )}

      {/* Show URL links for completed / failed */}
      {isCompleted && job.youtube_url && (
        <div className="flex items-center gap-1.5 bg-cyan-950/20 border border-cyan-500/25 p-2 rounded-xl text-[11px] text-cyan-400 font-medium">
          <Youtube className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="truncate flex-1">{job.youtube_url}</span>
          <ChevronRight className="w-3.5 h-3.5 text-cyan-500" />
        </div>
      )}

      {isFailed && (
        <div className="flex items-center gap-1.5 bg-red-950/10 border border-red-500/20 p-2 rounded-xl text-[11px] text-red-400">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="truncate flex-1">Lỗi tải xuống hoặc xử lý.</span>
        </div>
      )}

      {/* Context Actions right on the card for UX flow */}
      {isWaitingGlossary && onReviewCharacters && (
        <button
          id={`btn-review-char-${job.id}`}
          onClick={(e) => {
            e.stopPropagation();
            onReviewCharacters();
          }}
          className="w-full mt-1 bg-[#7C3AED] hover:bg-purple-600 text-white font-bold py-2 px-3 rounded-2xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-purple-500/20 active:scale-95 transition-all duration-200"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          Duyệt Nhân Vật ({job.glossary?.length || 0})
        </button>
      )}

      {isWaitingMetadata && onReviewMetadata && (
        <button
          id={`btn-review-meta-${job.id}`}
          onClick={(e) => {
            e.stopPropagation();
            onReviewMetadata();
          }}
          className="w-full mt-1 bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-2 px-3 rounded-2xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-cyan-500/20 active:scale-95 transition-all duration-200"
        >
          <Youtube className="w-3.5 h-3.5" />
          Duyệt SEO & Đăng YouTube
        </button>
      )}

      {isFailed && onRetry && (
        <button
          id={`btn-retry-${job.id}`}
          onClick={(e) => {
            e.stopPropagation();
            onRetry();
          }}
          className="w-full mt-1 bg-white/[0.06] hover:bg-white/[0.10] border border-white/[0.10] text-white font-bold py-2 px-3 rounded-2xl text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all duration-200"
        >
          Thử Lại Pipeline
        </button>
      )}
    </IOSCard>
  );
}
