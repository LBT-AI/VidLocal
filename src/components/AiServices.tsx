import React, { useState, useEffect } from "react";
import { getAiServices } from "../lib/api";
import { 
  Sparkles, RefreshCw, Cpu, Gauge, ShieldCheck, 
  ArrowUpRight, Database, Coins
} from "lucide-react";

export function AiServices() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const res = await getAiServices();
      setMetrics(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) {
    return (
      <div className="flex items-center justify-center p-6 text-slate-500">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        <span>Đang đọc cấu hình dịch vụ AI...</span>
      </div>
    );
  }

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 space-y-4 text-xs">
      <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
        <div>
          <h3 className="font-bold text-white text-sm">AI Engine Matrix</h3>
          <p className="text-[10px] text-slate-500">Giám sát tải trọng dịch vụ dịch thuật & STT</p>
        </div>
        <button 
          onClick={fetchMetrics}
          className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Services Grid */}
      <div className="space-y-3">
        {/* Gemini Service Card */}
        <div className="bg-gradient-to-r from-purple-500/5 via-transparent to-transparent border border-white/[0.04] p-3 rounded-2xl space-y-2 relative overflow-hidden">
          <div className="absolute right-3 top-3 w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />
          
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Sparkles className="w-3.5 h-3.5" />
              </span>
              <div>
                <h4 className="font-bold text-white text-xs">Gemini 3.5 Flash</h4>
                <p className="text-[9px] text-slate-500">SEO, Glossary Extract & Translator</p>
              </div>
            </div>
            <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full uppercase">
              {metrics.gemini.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="bg-black/30 p-2 rounded-xl border border-white/[0.02]">
              <span className="text-[9px] text-slate-500 block">Token Tiêu Thụ</span>
              <span className="text-xs font-bold text-slate-200 font-mono flex items-center gap-1 mt-0.5">
                <Coins className="w-3 h-3 text-yellow-500" />
                {metrics.gemini.tokenUsage.toLocaleString()}
              </span>
            </div>
            <div className="bg-black/30 p-2 rounded-xl border border-white/[0.02]">
              <span className="text-[9px] text-slate-500 block">Requests (Hôm Nay)</span>
              <span className="text-xs font-bold text-slate-200 font-mono mt-0.5 block">
                {metrics.gemini.requestsToday} / 1,000
              </span>
            </div>
          </div>
        </div>

        {/* Whisper Service Card */}
        <div className="bg-gradient-to-r from-cyan-500/5 via-transparent to-transparent border border-white/[0.04] p-3 rounded-2xl space-y-2">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Cpu className="w-3.5 h-3.5" />
              </span>
              <div>
                <h4 className="font-bold text-white text-xs">Whisper v3 Speech-To-Text</h4>
                <p className="text-[9px] text-slate-500">Transcribe engine on GPU cloud</p>
              </div>
            </div>
            <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full uppercase">
              {metrics.whisper.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="bg-black/30 p-2 rounded-xl border border-white/[0.02]">
              <span className="text-[9px] text-slate-500 block">GPU VRAM Load</span>
              <span className="text-xs font-bold text-slate-200 font-mono flex items-center gap-1 mt-0.5">
                <Gauge className="w-3.5 h-3.5 text-cyan-400" />
                <span>{metrics.whisper.gpuUsage}%</span>
              </span>
            </div>
            <div className="bg-black/30 p-2 rounded-xl border border-white/[0.02]">
              <span className="text-[9px] text-slate-500 block">STT Speed</span>
              <span className="text-xs font-bold text-slate-200 font-mono mt-0.5 block text-cyan-400">
                {metrics.whisper.speed}
              </span>
            </div>
          </div>
        </div>

        {/* DeepLX Service Card */}
        <div className="bg-gradient-to-r from-emerald-500/5 via-transparent to-transparent border border-white/[0.04] p-3 rounded-2xl space-y-2">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Database className="w-3.5 h-3.5" />
              </span>
              <div>
                <h4 className="font-bold text-white text-xs">DeepLX Pro Translator</h4>
                <p className="text-[9px] text-slate-500">Subtitle dictionary provider</p>
              </div>
            </div>
            <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full uppercase">
              {metrics.deeplx.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="bg-black/30 p-2 rounded-xl border border-white/[0.02]">
              <span className="text-[9px] text-slate-500 block">Duyệt Dịch (Char count)</span>
              <span className="text-xs font-bold text-slate-200 font-mono mt-0.5 block">
                {metrics.deeplx.requests.toLocaleString()}
              </span>
            </div>
            <div className="bg-black/30 p-2 rounded-xl border border-white/[0.02]">
              <span className="text-[9px] text-slate-500 block">Thạn ngạch tháng</span>
              <span className="text-xs font-bold text-slate-200 font-mono mt-0.5 block">
                {metrics.deeplx.limit.toLocaleString()} / mo
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
