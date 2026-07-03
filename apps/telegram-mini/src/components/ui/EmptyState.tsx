import React from "react";
import { Sparkles } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  id?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ title, description, id, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div id={id || "empty-state-container"} className="py-12 px-4 flex flex-col items-center text-center space-y-4">
      <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-purple-400 shadow-xl shadow-purple-500/[0.03]">
        <Sparkles className="w-7 h-7 text-purple-400" />
      </div>
      <div className="space-y-1">
        <h4 className="text-sm font-bold text-white">{title}</h4>
        <p className="text-xs text-slate-400 max-w-xs leading-relaxed">{description}</p>
      </div>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="bg-purple-600 hover:bg-purple-500 text-white font-bold py-2 px-4 rounded-full text-xs active:scale-95 transition-all duration-200 shadow-lg shadow-purple-500/10"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
