import React, { useEffect } from "react";
import { X } from "lucide-react";

interface IOSSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  id?: string;
}

export function IOSSheet({ isOpen, onClose, title, subtitle, children, id }: IOSSheetProps) {
  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      id={id || "ios-sheet-overlay"}
      className="fixed inset-0 bg-[#020306]/85 backdrop-blur-sm z-50 flex items-end justify-center transition-opacity duration-300 animate-fadeIn"
    >
      {/* Background Click to Dismiss */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Sheet Content panel sliding up from the bottom */}
      <div
        id="ios-sheet-panel"
        className="relative w-full max-w-[390px] bg-[#0C101B] border-t border-white/[0.10] rounded-t-[32px] p-6 space-y-4 max-h-[85vh] overflow-y-auto shadow-2xl animate-slideUp z-51 pb-8"
      >
        {/* iOS Grab Handle Drag Indicator */}
        <div className="mx-auto w-12 h-1.5 bg-white/[0.12] rounded-full mb-2 cursor-pointer" onClick={onClose} />

        {/* Title Header */}
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
            {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Core Sheet Contents */}
        <div className="pt-2 text-slate-200">
          {children}
        </div>
      </div>
    </div>
  );
}
