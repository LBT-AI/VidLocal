import React from "react";
import { CheckCircle2, Circle, PlayCircle, XCircle } from "lucide-react";

export type StepState = "pending" | "running" | "completed" | "failed";

interface StepItem {
  key: string;
  label: string;
  status: StepState;
  progress?: number;
}

interface ProgressStepperProps {
  steps: StepItem[];
  currentStepKey: string;
  id?: string;
}

export function ProgressStepper({ steps, currentStepKey, id }: ProgressStepperProps) {
  return (
    <div id={id || "progress-stepper"} className="space-y-4">
      {/* Horizontal Overview Pills */}
      <div className="flex gap-1 overflow-x-auto pb-2 scrollbar-none">
        {steps.map((step) => {
          const isActive = step.key === currentStepKey;
          const isCompleted = step.status === "completed";
          const isFailed = step.status === "failed";
          const isRunning = step.status === "running";

          let pillBg = "bg-white/[0.04] text-slate-500 border-white/[0.04]";
          if (isActive || isRunning) {
            pillBg = "bg-purple-600/20 text-purple-400 border-purple-500/30";
          } else if (isCompleted) {
            pillBg = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
          } else if (isFailed) {
            pillBg = "bg-red-500/10 text-red-400 border-red-500/20";
          }

          return (
            <div
              key={step.key}
              className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border transition-all duration-300 ${pillBg}`}
            >
              {isCompleted && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
              {(isActive || isRunning) && <PlayCircle className="w-3 h-3 text-purple-400 animate-pulse" />}
              {isFailed && <XCircle className="w-3 h-3 text-red-400" />}
              {!isCompleted && !isActive && !isRunning && !isFailed && <Circle className="w-3 h-3 text-slate-600" />}
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      {/* Vertical Interactive Timeline */}
      <div className="relative pl-5 border-l border-white/[0.06] ml-2.5 space-y-4 py-1">
        {steps.map((step, idx) => {
          const isActive = step.key === currentStepKey;
          const isCompleted = step.status === "completed";
          const isFailed = step.status === "failed";
          const isRunning = step.status === "running";

          let dotColor = "bg-slate-800 border-slate-700 text-slate-600";
          if (isActive || isRunning) {
            dotColor = "bg-purple-600 border-purple-500 ring-4 ring-purple-500/20 text-white animate-pulse";
          } else if (isCompleted) {
            dotColor = "bg-emerald-500 border-emerald-400 text-white";
          } else if (isFailed) {
            dotColor = "bg-red-500 border-red-400 text-white";
          }

          return (
            <div key={step.key} className="relative group">
              {/* Timeline Connector Dot */}
              <div
                className={`absolute -left-7.5 top-0.5 w-5 h-5 rounded-full border flex items-center justify-center text-[9px] font-bold transition-all duration-300 ${dotColor}`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-3 h-3 text-white" />
                ) : isFailed ? (
                  <span className="text-white">!</span>
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>

              {/* Step Info */}
              <div className="flex flex-col">
                <div className="flex justify-between items-center">
                  <h4
                    className={`text-xs font-bold transition-colors duration-300 ${
                      isActive || isRunning
                        ? "text-purple-400"
                        : isCompleted
                        ? "text-emerald-400"
                        : isFailed
                        ? "text-red-400"
                        : "text-slate-400"
                    }`}
                  >
                    {step.label}
                  </h4>
                  {isRunning && step.progress !== undefined && (
                    <span className="text-[11px] font-mono font-bold text-purple-400">
                      {step.progress}%
                    </span>
                  )}
                </div>

                {/* Progress bar inside step if running */}
                {isRunning && step.progress !== undefined && (
                  <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden mt-1.5 border border-white/[0.05]">
                    <div
                      style={{ width: `${step.progress}%` }}
                      className="h-full bg-gradient-to-r from-purple-500 to-cyan-400 transition-all duration-500"
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
