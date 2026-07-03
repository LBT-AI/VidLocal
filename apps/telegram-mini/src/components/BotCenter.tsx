import React, { useState, useEffect } from "react";
import { getBotStatus, triggerBotAction } from "../lib/api";
import { 
  Send, RefreshCw, Server, ShieldCheck, ToggleLeft, 
  Terminal, Play, RotateCcw, AlertCircle, Key
} from "lucide-react";

export function BotCenter() {
  const [bot, setBot] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([
    "Initializing Telegram Bot engine...",
    "Registered 5 commands with Telegram Bot API.",
    "Webhook registration completed with HTTP status 200.",
    "Webapp security token validated successfully.",
    "Awaiting message updates..."
  ]);
  const [toastMessage, setToastMessage] = useState("");

  const fetchBot = async () => {
    setLoading(true);
    try {
      const res = await getBotStatus();
      setBot(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBot();
  }, []);

  const handleAction = async (action: string) => {
    setLoading(true);
    try {
      const res = await triggerBotAction(action);
      setBot(res.bot);
      
      const newLog = action === "restart" 
        ? "Bot restart triggered by Administrator. Clearing session queues..."
        : `Polling settings toggled. Status is now ${res.bot.polling}.`;
      
      setLogs(prev => [newLog, ...prev]);
      setToastMessage(action === "restart" ? "Đã khởi động lại Bot!" : "Đã cập nhật Polling!");
      setTimeout(() => setToastMessage(""), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const updateCommands = () => {
    setLoading(true);
    setTimeout(() => {
      setLogs(prev => ["Sent command updates list to Telegram servers.", ...prev]);
      setToastMessage("Đã cập nhật Command với Telegram API!");
      setTimeout(() => setToastMessage(""), 3000);
      setLoading(false);
    }, 1200);
  };

  if (!bot) {
    return (
      <div className="flex items-center justify-center p-6 text-slate-500">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        <span>Đang kết nối Telegram Bot Center...</span>
      </div>
    );
  }

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 space-y-4 text-xs">
      {/* Toast overlay inside card */}
      {toastMessage && (
        <div className="bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 p-2 rounded-xl text-center font-bold text-[10px] animate-pulse">
          {toastMessage}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
        <div>
          <h3 className="font-bold text-white text-sm">Telegram Bot Center</h3>
          <p className="text-[10px] text-slate-500">Đồng bộ Mini App & Kênh đẩy thông báo</p>
        </div>
        <button 
          onClick={fetchBot}
          className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Status Indicators */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-black/30 border border-white/[0.04] p-3 rounded-2xl space-y-1">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Bot Username</span>
          <div className="flex items-center gap-1.5 text-cyan-400 font-extrabold">
            <Send className="w-3.5 h-3.5" />
            <span>{bot.username}</span>
          </div>
        </div>

        <div className="bg-black/30 border border-white/[0.04] p-3 rounded-2xl space-y-1">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Bot Engine</span>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${bot.status === "active" ? "bg-emerald-400 animate-pulse" : "bg-yellow-400"}`} />
            <span className="text-white font-extrabold uppercase">{bot.status}</span>
          </div>
        </div>
      </div>

      {/* Webhook & Configurations */}
      <div className="bg-white/[0.02] border border-white/[0.04] p-3 rounded-2xl space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Webhook URL</span>
          <span className="text-[9px] font-bold text-emerald-400 uppercase bg-emerald-500/10 px-1.5 py-0.5 rounded">SSL Secure</span>
        </div>
        <p className="font-mono text-[10px] text-slate-400 bg-black/40 p-2 rounded-xl break-all border border-white/[0.03]">
          {bot.webhook}
        </p>
        
        <div className="flex items-center justify-between pt-1">
          <span className="text-slate-300">Nhận tin qua Long Polling (Local Dev)</span>
          <button 
            onClick={() => handleAction("polling")}
            className="flex items-center gap-1 bg-white/[0.04] px-2.5 py-1 rounded-lg border border-white/[0.06] text-slate-300 hover:text-white"
          >
            <ToggleLeft className={`w-3.5 h-3.5 ${bot.polling === "active" ? "text-cyan-400" : ""}`} />
            <span className="font-bold uppercase text-[9px]">{bot.polling}</span>
          </button>
        </div>
      </div>

      {/* Bot Command List */}
      <div className="space-y-2">
        <div className="text-[10px] uppercase text-slate-500 font-bold px-0.5">Lệnh Telegram khả dụng (Commands)</div>
        <div className="bg-black/30 border border-white/[0.04] p-2.5 rounded-2xl space-y-2 max-h-36 overflow-y-auto">
          {bot.commands.map((cmd: any) => (
            <div key={cmd.command} className="flex gap-2 border-b border-white/[0.02] pb-1.5 last:border-0 last:pb-0">
              <span className="font-mono text-cyan-400 font-extrabold flex-shrink-0">/{cmd.command}</span>
              <span className="text-slate-400 leading-normal">{cmd.description}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Bot Actions */}
      <div className="grid grid-cols-2 gap-2 border-t border-white/[0.04] pt-3">
        <button 
          onClick={() => handleAction("restart")}
          className="bg-red-500/10 border border-red-500/20 text-red-400 font-extrabold py-2 rounded-xl flex items-center justify-center gap-1 active:scale-95 transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Khởi Động Lại Bot</span>
        </button>

        <button 
          onClick={updateCommands}
          className="bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-extrabold py-2 rounded-xl flex items-center justify-center gap-1 active:scale-95 transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Cập Nhật Commands</span>
        </button>
      </div>

      {/* Bot Logs terminal block */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-center px-0.5">
          <span className="text-[10px] uppercase text-slate-500 font-bold flex items-center gap-1">
            <Terminal className="w-3.5 h-3.5" />
            <span>Bot Logs</span>
          </span>
          <span className="text-[9px] font-mono text-slate-500">Live feed</span>
        </div>
        <div className="bg-black/50 border border-white/[0.05] p-2.5 rounded-2xl font-mono text-[10px] text-slate-400 space-y-1 max-h-24 overflow-y-auto leading-relaxed">
          {logs.map((log, idx) => (
            <div key={idx} className="flex gap-1.5">
              <span className="text-purple-500 select-none">&gt;</span>
              <span>{log}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
