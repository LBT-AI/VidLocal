import React from "react";

interface StatusBadgeProps {
  status: "pending" | "downloading" | "transcribing" | "waiting_approval" | "approved" | "completed" | "failed";
  id?: string;
}

export function StatusBadge({ status, id }: StatusBadgeProps) {
  const styles: Record<string, { bg: string; text: string; label: string; dot: string; border: string }> = {
    pending: {
      bg: "bg-gray-500/10",
      text: "text-gray-400",
      border: "border-gray-500/20",
      dot: "bg-gray-400",
      label: "Pending"
    },
    downloading: {
      bg: "bg-blue-500/10",
      text: "text-blue-400",
      border: "border-blue-500/20",
      dot: "bg-blue-400 animate-pulse",
      label: "Downloading"
    },
    transcribing: {
      bg: "bg-purple-500/10",
      text: "text-purple-400",
      border: "border-purple-500/20",
      dot: "bg-purple-400 animate-bounce",
      label: "Transcribing"
    },
    waiting_approval: {
      bg: "bg-yellow-500/10",
      text: "text-yellow-400",
      border: "border-yellow-500/25",
      dot: "bg-yellow-400 animate-pulse",
      label: "Waiting Approval"
    },
    approved: {
      bg: "bg-emerald-500/10",
      text: "text-emerald-400",
      border: "border-emerald-500/20",
      dot: "bg-emerald-400",
      label: "Approved"
    },
    completed: {
      bg: "bg-cyan-500/10",
      text: "text-cyan-400",
      border: "border-cyan-500/20",
      dot: "bg-cyan-400",
      label: "Completed"
    },
    failed: {
      bg: "bg-red-500/10",
      text: "text-red-400",
      border: "border-red-500/20",
      dot: "bg-red-400",
      label: "Failed"
    }
  };

  const current = styles[status] || styles.pending;

  return (
    <span
      id={id || `status-${status}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${current.bg} ${current.text} ${current.border}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`} />
      <span>{current.label}</span>
    </span>
  );
}
