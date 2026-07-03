import React, { useState, useEffect } from "react";
import { getQueues, triggerQueueAction } from "../lib/api";
import { 
  Play, Pause, RefreshCw, X, AlertCircle, 
  Layers, CheckCircle2, RotateCw
} from "lucide-react";

export function QueueMonitor() {
  const [queues, setQueues] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  const fetchQueues = async () => {
    try {
      const res = await getQueues();
      setQueues(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchQueues();
    const interval = setInterval(fetchQueues, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (queueName: string, action: string) => {
    setLoading(true);
    try {
      const res = await triggerQueueAction(queueName, action);
      setQueues(res.queues);
      
      let VietnameseActionText = "tạm dừng";
      if (action === "resume") VietnameseActionText = "kích hoạt lại";
      if (action === "cancel") VietnameseActionText = "hủy bỏ job";

      setToast(`Đã ${VietnameseActionText} thành công hàng đợi ${queueName}!`);
      setTimeout(() => setToast(""), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (!queues) {
    return (
      <div className="flex items-center justify-center p-6 text-slate-500">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        <span>Đang đọc hàng đợi Celery...</span>
      </div>
    );
  }

  const queueKeys = Object.keys(queues);

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 space-y-4 text-xs">
      {/* Toast Inside Container */}
      {toast && (
        <div className="bg-purple-500/10 border border-purple-500/20 text-purple-400 p-2.5 rounded-xl font-bold text-[10px] text-center animate-pulse">
          {toast}
        </div>
      )}

      <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
        <div>
          <h3 className="font-bold text-white text-sm">Celery Queue Monitor</h3>
          <p className="text-[10px] text-slate-500">Quản lý luồng xử lý đa tiến trình chạy nền</p>
        </div>
        <button 
          onClick={fetchQueues}
          className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Queues List */}
      <div className="space-y-2.5">
        {queueKeys.map(key => {
          const q = queues[key];
          const isPaused = q.status === "paused";
          
          return (
            <div 
              key={key} 
              className={`p-3 rounded-2xl border transition-all ${
                isPaused 
                  ? "bg-red-500/[0.02] border-red-500/20" 
                  : "bg-white/[0.02] border-white/[0.05]"
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-1.5">
                  <Layers className={`w-4 h-4 ${isPaused ? "text-red-400" : "text-purple-400"}`} />
                  <span className="font-bold text-white text-xs uppercase tracking-wide">{key} Queue</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                    isPaused 
                      ? "bg-red-500/10 text-red-400" 
                      : q.active > 0 
                      ? "bg-emerald-500/10 text-emerald-400" 
                      : "bg-slate-500/10 text-slate-400"
                  }`}>
                    {q.status}
                  </span>
                </div>
              </div>

              {/* Counts */}
              <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 mb-2.5">
                <div className="bg-black/20 p-1.5 rounded-lg flex justify-between px-2">
                  <span>Đang chạy (Active)</span>
                  <span className="font-bold text-slate-200">{q.active}</span>
                </div>
                <div className="bg-black/20 p-1.5 rounded-lg flex justify-between px-2">
                  <span>Hàng đợi (Queued)</span>
                  <span className="font-bold text-slate-200">{q.queued}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                {isPaused ? (
                  <button 
                    onClick={() => handleAction(key, "resume")}
                    className="flex-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-extrabold py-1.5 rounded-lg border border-emerald-500/20 flex items-center justify-center gap-1 active:scale-95 transition-all text-[10px]"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>Kích Hoạt Lại</span>
                  </button>
                ) : (
                  <button 
                    onClick={() => handleAction(key, "pause")}
                    className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-extrabold py-1.5 rounded-lg border border-red-500/20 flex items-center justify-center gap-1 active:scale-95 transition-all text-[10px]"
                  >
                    <Pause className="w-3 h-3" />
                    <span>Tạm Dừng</span>
                  </button>
                )}

                <button 
                  onClick={() => handleAction(key, "cancel")}
                  disabled={q.queued === 0}
                  className="bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 font-bold px-3 py-1.5 rounded-lg border border-white/[0.06] disabled:opacity-30 disabled:pointer-events-none text-[10px] flex items-center gap-1"
                >
                  <X className="w-3 h-3" />
                  <span>Bỏ Hàng Đợi</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
