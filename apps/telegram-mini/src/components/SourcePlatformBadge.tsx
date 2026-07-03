import React from "react";
import { Facebook, Music, Video } from "lucide-react";

interface SourcePlatformBadgeProps {
  platform: "Facebook" | "TikTok";
  id?: string;
}

export function SourcePlatformBadge({ platform, id }: SourcePlatformBadgeProps) {
  const isFb = platform === "Facebook";

  return (
    <span
      id={id || `platform-${platform.toLowerCase()}`}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
        isFb
          ? "bg-blue-600/20 text-blue-400 border border-blue-500/20"
          : "bg-pink-600/20 text-pink-400 border border-pink-500/20"
      }`}
    >
      {isFb ? (
        <Facebook className="w-3 h-3" />
      ) : (
        <Video className="w-3 h-3" />
      )}
      <span>{platform}</span>
    </span>
  );
}
