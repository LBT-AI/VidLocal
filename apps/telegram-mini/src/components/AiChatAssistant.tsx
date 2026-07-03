import React, { useState, useEffect, useRef } from "react";
import { postAiChat, getJobs } from "../lib/api";
import { VideoJob } from "../types";
import { 
  Sparkles, Send, RefreshCw, MessageSquare, Bot, 
  AlertTriangle, Check, BrainCircuit, X
} from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  time: string;
}

export function AiChatAssistant() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "m-init",
      sender: "ai",
      text: "Chào bạn! Tôi là Trợ lý AI Kỹ thuật của VidLocal Studio. Hãy chọn một video job bị lỗi ở trên hoặc gõ câu hỏi để tôi phân tích logs chi tiết.",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Suggested quick questions
  const quickQuestions = [
    "Vì sao render fail?",
    "Video này lỗi gì?",
    "Subtitle bị lệch timeline?"
  ];

  useEffect(() => {
    getJobs().then(data => {
      setJobs(data);
      // Auto-select the first failed/running job if exists
      const priorityJob = data.find(j => j.logs.some(l => l.level === "error")) || data[0];
      if (priorityJob) {
        setSelectedJobId(priorityJob.id);
      }
    });
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text) return;

    if (!textToSend) setInputText("");

    const userMsg: Message = {
      id: `m-user-${Date.now()}`,
      sender: "user",
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await postAiChat(text, selectedJobId || undefined);
      const aiMsg: Message = {
        id: `m-ai-${Date.now()}`,
        sender: "ai",
        text: res.response,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (e) {
      console.error(e);
      const errMsg: Message = {
        id: `m-ai-err-${Date.now()}`,
        sender: "ai",
        text: "Xin lỗi, đã xảy ra lỗi kết nối với máy chủ AI. Vui lòng kiểm tra API key của Gemini trong bảng điều khiển và thử lại.",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const selectedJob = jobs.find(j => j.id === selectedJobId);

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 flex flex-col h-[400px] text-xs">
      {/* Header */}
      <div className="border-b border-white/[0.04] pb-2 flex-shrink-0">
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-1.5 text-purple-400">
            <BrainCircuit className="w-4 h-4" />
            <span className="font-bold text-white text-xs">AI Troubleshooter Chat</span>
          </div>
          <span className="text-[9px] uppercase font-bold text-slate-500 flex items-center gap-1 bg-white/[0.03] px-1.5 py-0.5 rounded">
            <Sparkles className="w-3 h-3 text-purple-400" />
            <span>Gemini Active</span>
          </span>
        </div>

        {/* Job selector dropdown */}
        <div className="flex gap-1.5 items-center">
          <span className="text-[10px] text-slate-500 font-medium">Bối cảnh:</span>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="flex-1 bg-black/40 border border-white/[0.06] text-white rounded-lg py-1 px-2 focus:outline-none"
          >
            <option value="">-- Câu hỏi chung về hệ thống --</option>
            {jobs.map(j => {
              const hasErr = j.logs.some(l => l.level === "error");
              return (
                <option key={j.id} value={j.id}>
                  {hasErr ? "⚠️ [LỖI] " : ""}
                  {j.title.length > 30 ? j.title.slice(0, 30) + "..." : j.title}
                </option>
              );
            })}
          </select>
        </div>
      </div>

      {/* Message Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-3 space-y-3 pr-0.5"
      >
        {messages.map(m => (
          <div 
            key={m.id}
            className={`flex gap-2 max-w-[85%] ${m.sender === "user" ? "ml-auto flex-row-reverse" : ""}`}
          >
            {/* Avatar */}
            <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${
              m.sender === "user" ? "bg-purple-600/20 text-purple-400" : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
            }`}>
              {m.sender === "user" ? "Me" : <Bot className="w-3.5 h-3.5" />}
            </div>

            {/* Bubble */}
            <div className={`p-2.5 rounded-2xl relative ${
              m.sender === "user" 
                ? "bg-purple-600 text-white rounded-tr-none" 
                : "bg-white/[0.03] border border-white/[0.05] text-slate-200 rounded-tl-none"
            }`}>
              <p className="leading-relaxed whitespace-pre-wrap break-words">{m.text}</p>
              <span className="text-[8px] text-slate-500 block text-right mt-1 font-mono">{m.time}</span>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-2 max-w-[85%]">
            <div className="w-6 h-6 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center justify-center">
              <Bot className="w-3.5 h-3.5 animate-bounce" />
            </div>
            <div className="bg-white/[0.02] border border-white/[0.04] p-3 rounded-2xl rounded-tl-none flex items-center gap-1.5 text-slate-500">
              <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
              <span>Gemini đang phân tích logs...</span>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Questions */}
      <div className="flex gap-1.5 overflow-x-auto pb-2 scrollbar-none flex-shrink-0">
        {quickQuestions.map(q => (
          <button
            key={q}
            onClick={() => handleSendMessage(q)}
            className="px-2.5 py-1 rounded-full bg-white/[0.02] hover:bg-white/[0.05] text-slate-400 hover:text-slate-200 border border-white/[0.04] text-[10px] whitespace-nowrap active:scale-95 transition-all"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <div className="flex gap-1.5 flex-shrink-0">
        <input 
          type="text" 
          placeholder="Hỏi AI chẩn đoán lỗi..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
          className="flex-1 bg-black/30 border border-white/[0.06] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500/50"
        />
        <button 
          onClick={() => handleSendMessage()}
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold p-2.5 rounded-xl active:scale-95 transition-all flex-shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
