import React, { useState } from "react";
import { 
  Users, Key, LineChart, FileText, Settings, Shield, 
  Database, HardDrive, Cpu, Layers, ToggleRight, Check
} from "lucide-react";

export function AdminPanel() {
  const [activeSubTab, setActiveSubTab] = useState<"users" | "keys" | "metrics" | "audit">("metrics");

  // User list state
  const [users, setUsers] = useState([
    { id: "u1", name: "Admin (VidLocal)", role: "Administrator", status: "online" },
    { id: "u2", name: "Nguyễn Văn A", role: "Editor", status: "offline" },
    { id: "u3", name: "Trần Thị B", role: "Editor", status: "online" },
    { id: "u4", name: "Bot Auto-Worker", role: "Service Account", status: "online" }
  ]);

  // Keys configuration
  const [keys, setKeys] = useState({
    gemini: "••••••••••••••••••••••••",
    openai: "••••••••••••••••••••••••",
    youtube: "••••••••••••••••••••••••"
  });

  const [auditLogs, setAuditLogs] = useState([
    { time: "10:14:22", user: "Admin", action: "Đã phê duyệt xuất bản video Iron Man Reel" },
    { time: "10:11:05", user: "Nguyễn Văn A", action: "Đã sửa phụ đề cue số #12" },
    { time: "09:55:40", user: "Trần Thị B", action: "Thêm glossary mới: 'Stark' -> 'Anh Stark'" },
    { time: "09:12:12", user: "System", action: "Khởi tạo thành công pipeline Celery Worker #3" }
  ]);

  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-[24px] p-4 space-y-4 text-xs">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
        <div>
          <h3 className="font-bold text-white text-sm">VidLocal Admin Dashboard</h3>
          <p className="text-[10px] text-slate-500">Quản trị viên hệ thống nâng cao</p>
        </div>
        <Shield className="w-4 h-4 text-purple-400" />
      </div>

      {/* Admin Subtabs navigation */}
      <div className="flex gap-1.5 border-b border-white/[0.03] pb-2 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActiveSubTab("metrics")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold ${
            activeSubTab === "metrics" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <LineChart className="w-3.5 h-3.5" />
          <span>Tải Hệ Thống</span>
        </button>

        <button
          onClick={() => setActiveSubTab("users")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold ${
            activeSubTab === "users" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Thành Viên</span>
        </button>

        <button
          onClick={() => setActiveSubTab("keys")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold ${
            activeSubTab === "keys" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          <span>API Keys</span>
        </button>

        <button
          onClick={() => setActiveSubTab("audit")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold ${
            activeSubTab === "audit" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Lịch Sử Giao Dịch</span>
        </button>
      </div>

      {/* Panel Views */}
      {activeSubTab === "metrics" && (
        <div className="space-y-3">
          <div className="text-[10px] uppercase text-slate-500 font-bold px-0.5">Tải Phần Cứng & Lưu Trữ</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-black/30 border border-white/[0.04] p-3 rounded-2xl space-y-2">
              <div className="flex justify-between items-center text-slate-400">
                <span className="flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span>CPU Worker</span>
                </span>
                <span className="font-mono text-cyan-400 font-bold">14.8%</span>
              </div>
              <div className="h-1.5 bg-white/[0.03] rounded-full overflow-hidden">
                <div className="h-full bg-cyan-400" style={{ width: "14.8%" }} />
              </div>
            </div>

            <div className="bg-black/30 border border-white/[0.04] p-3 rounded-2xl space-y-2">
              <div className="flex justify-between items-center text-slate-400">
                <span className="flex items-center gap-1">
                  <Database className="w-3.5 h-3.5 text-purple-400" />
                  <span>RAM Server</span>
                </span>
                <span className="font-mono text-purple-400 font-bold">42.1%</span>
              </div>
              <div className="h-1.5 bg-white/[0.03] rounded-full overflow-hidden">
                <div className="h-full bg-purple-400" style={{ width: "42.1%" }} />
              </div>
            </div>

            <div className="bg-black/30 border border-white/[0.04] p-3 rounded-2xl space-y-2 col-span-2">
              <div className="flex justify-between items-center text-slate-400">
                <span className="flex items-center gap-1">
                  <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Lưu Trữ R2 / SSD Local</span>
                </span>
                <span className="font-mono text-emerald-400 font-bold">120GB / 500GB (24%)</span>
              </div>
              <div className="h-1.5 bg-white/[0.03] rounded-full overflow-hidden">
                <div className="h-full bg-emerald-400" style={{ width: "24%" }} />
              </div>
            </div>
          </div>

          <div className="bg-[#7C3AED]/5 border border-[#7C3AED]/10 p-3 rounded-2xl flex items-center gap-2.5">
            <ToggleRight className="w-5 h-5 text-purple-400" />
            <div>
              <p className="font-bold text-slate-200 text-[11px]">Tự động dọn dẹp file tạm (Auto-Cleanup)</p>
              <p className="text-[9px] text-slate-500 mt-0.5">Xóa video segments và render tmp sau 24h xuất bản.</p>
            </div>
          </div>
        </div>
      )}

      {activeSubTab === "users" && (
        <div className="space-y-3">
          <div className="text-[10px] uppercase text-slate-500 font-bold px-0.5">Quản lý Thành Viên & Quyền Hạn</div>
          <div className="bg-black/30 border border-white/[0.04] p-2 rounded-2xl space-y-2">
            {users.map(u => (
              <div key={u.id} className="p-2 rounded-xl bg-white/[0.01] flex justify-between items-center hover:bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${u.status === "online" ? "bg-emerald-400" : "bg-slate-600"}`} />
                  <div>
                    <p className="font-bold text-white text-[11px]">{u.name}</p>
                    <p className="text-[9px] text-slate-500 font-mono">{u.role}</p>
                  </div>
                </div>
                <button className="bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-slate-300 font-bold px-2 py-1 rounded-lg">
                  Sửa Quyền
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeSubTab === "keys" && (
        <div className="space-y-3">
          <div className="text-[10px] uppercase text-slate-500 font-bold px-0.5">Cấu hình API Keys Kỹ thuật</div>
          <div className="bg-black/30 border border-white/[0.04] p-3 rounded-2xl space-y-3">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 block uppercase tracking-wider">Gemini API Token</label>
              <input 
                type="password" 
                value={keys.gemini}
                disabled
                className="w-full bg-black/40 border border-white/[0.05] rounded-xl px-3 py-2 text-slate-300 focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 block uppercase tracking-wider">DeepLX API Auth Key</label>
              <input 
                type="password" 
                value={keys.openai}
                disabled
                className="w-full bg-black/40 border border-white/[0.05] rounded-xl px-3 py-2 text-slate-300 focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 block uppercase tracking-wider">YouTube OAuth Client Token</label>
              <input 
                type="password" 
                value={keys.youtube}
                disabled
                className="w-full bg-black/40 border border-white/[0.05] rounded-xl px-3 py-2 text-slate-300 focus:outline-none"
              />
            </div>

            <button className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 rounded-xl flex items-center justify-center gap-1">
              <Check className="w-3.5 h-3.5" />
              <span>Đã Lưu Khóa Trong Secrets UI</span>
            </button>
          </div>
        </div>
      )}

      {activeSubTab === "audit" && (
        <div className="space-y-3">
          <div className="text-[10px] uppercase text-slate-500 font-bold px-0.5">Nhật Ký Bảo Mật & Thao Tác (Audit Logs)</div>
          <div className="bg-black/30 border border-white/[0.04] p-2.5 rounded-2xl space-y-2 font-mono text-[10px]">
            {auditLogs.map((log, idx) => (
              <div key={idx} className="flex gap-2 border-b border-white/[0.02] pb-2 last:border-0 last:pb-0 text-slate-400 leading-relaxed">
                <span className="text-slate-600 select-none">{log.time}</span>
                <span className="text-cyan-400 font-bold">[{log.user}]</span>
                <span className="text-slate-200">{log.action}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
