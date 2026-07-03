import React from "react";
import { AlertTriangle, ShieldAlert } from "lucide-react";

interface RiskFlagBadgeProps {
  key?: React.Key;
  flag: string;
  id?: string;
}

export function RiskFlagBadge({ flag, id }: RiskFlagBadgeProps) {
  // Translate labels if needed, or keep high density look
  const labelMap: Record<string, string> = {
    copyright: "Bản quyền",
    reup: "Reup Risk",
    sensitive: "Nhạy cảm",
    duplicate_content: "Trùng lặp"
  };

  const label = labelMap[flag.toLowerCase()] || flag;

  return (
    <span
      id={id || `risk-${flag}`}
      className="inline-flex items-center gap-1 bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded text-[11px] font-medium"
    >
      <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
      <span>{label}</span>
    </span>
  );
}
