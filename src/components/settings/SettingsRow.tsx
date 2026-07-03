import React from "react";
import { ChevronRight } from "lucide-react";

interface SettingsRowProps {
  label: string;
  icon: React.ReactNode;
  value?: string;
  onClick?: () => void;
  type?: "toggle" | "button" | "info";
  checked?: boolean;
  onToggle?: (val: boolean) => void;
  id?: string;
}

export function SettingsRow({ 
  label, 
  icon, 
  value, 
  onClick, 
  type = "info", 
  checked = false, 
  onToggle,
  id
}: SettingsRowProps) {
  const isButton = type === "button" || !!onClick;

  return (
    <div
      id={id || `settings-row-${label.toLowerCase().replace(/\s+/g, "-")}`}
      onClick={isButton ? onClick : undefined}
      className={`flex items-center justify-between p-3.5 bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.05] rounded-2xl transition-all duration-200 ${
        isButton ? "cursor-pointer active:scale-[0.98]" : ""
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-white/[0.04] text-slate-300 border border-white/[0.06] flex items-center justify-center">
          {icon}
        </div>
        <span className="text-xs font-bold text-white tracking-tight">{label}</span>
      </div>

      <div className="flex items-center gap-2">
        {type === "toggle" && onToggle && (
          <button
            onClick={() => onToggle(!checked)}
            className={`w-10 h-6 rounded-full p-1 transition-colors duration-300 relative ${
              checked ? "bg-[#7C3AED]" : "bg-slate-800"
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform duration-300 ${
                checked ? "translate-x-4" : "translate-x-0"
              }`}
            />
          </button>
        )}

        {type === "info" && value && (
          <span className="text-[11px] font-medium text-slate-400 font-mono bg-white/[0.04] border border-white/[0.06] px-2 py-0.5 rounded-lg">
            {value}
          </span>
        )}

        {type === "button" && (
          <div className="flex items-center gap-1.5">
            {value && <span className="text-xs text-slate-400 font-semibold">{value}</span>}
            <ChevronRight className="w-4 h-4 text-slate-500" />
          </div>
        )}
      </div>
    </div>
  );
}
