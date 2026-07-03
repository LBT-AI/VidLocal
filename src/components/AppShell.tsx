import React, { useEffect, useState } from "react";
import { 
  Home as HomeIcon, 
  ListVideo, 
  PlusCircle, 
  Folder, 
  Settings as SettingsIcon,
  Wifi,
  Battery,
  User
} from "lucide-react";

interface AppShellProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onNavigateHome: () => void;
  toast: { message: string; type: "success" | "error" | "info" } | null;
  setToast: (toast: any) => void;
}

export function AppShell({ 
  children, 
  activeTab, 
  setActiveTab, 
  onNavigateHome,
  toast,
  setToast
}: AppShellProps) {
  const [currentTime, setCurrentTime] = useState("");
  const [telegramUser, setTelegramUser] = useState<any>(null);

  useEffect(() => {
    // Set up real time for the iOS status bar
    const updateClock = () => {
      const now = new Date();
      let hours = now.getHours();
      let minutes: string | number = now.getMinutes();
      minutes = minutes < 10 ? "0" + minutes : minutes;
      setCurrentTime(`${hours}:${minutes}`);
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);

    // Telegram WebApp setup
    try {
      const tg = (window as any).Telegram?.WebApp;
      if (tg) {
        tg.ready();
        tg.expand();
        // Set header color matching background
        if (tg.setHeaderColor) {
          tg.setHeaderColor("#05070D");
        }
        if (tg.initDataUnsafe?.user) {
          setTelegramUser(tg.initDataUnsafe.user);
        }
      }
    } catch (e) {
      console.warn("Telegram WebApp API not available:", e);
    }

    return () => clearInterval(interval);
  }, []);

  // Handle Toast auto-clear
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast, setToast]);

  // Haptic feedback simulator
  const triggerHaptic = (type: "light" | "medium" | "heavy" | "success" | "error" = "light") => {
    try {
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.HapticFeedback) {
        if (type === "success" || type === "error") {
          tg.HapticFeedback.notificationOccurred(type);
        } else {
          tg.HapticFeedback.impactOccurred(type);
        }
      }
    } catch (e) {
      // ignore fallback
    }
  };

  const handleTabClick = (tab: string) => {
    triggerHaptic("medium");
    setActiveTab(tab);
    if (tab === "home") {
      onNavigateHome();
    }
  };

  return (
    <div id="ios-root-container" className="min-h-screen bg-[#020306] flex items-center justify-center p-0 sm:p-4 select-none">
      {/* iOS Device Bezel Frame (Simulating high density iPhone on desktop, invisible on mobile) */}
      <div 
        id="iphone-frame" 
        className="w-full h-screen sm:h-[820px] sm:w-[390px] sm:rounded-[50px] sm:border-[12px] sm:border-[#1A2235] bg-[#05070D] flex flex-col relative overflow-hidden shadow-2xl sm:shadow-indigo-500/10 transition-all duration-300"
      >
        {/* Dynamic Island / Notch (Only visible on simulated frame) */}
        <div className="hidden sm:block absolute top-0 left-1/2 -translate-x-1/2 w-32 h-6 bg-black rounded-b-2xl z-55 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-[#0d0d0d] absolute left-3"></div>
          <div className="w-12 h-1.5 bg-[#0d0d0d] rounded-full absolute right-3"></div>
        </div>

        {/* iOS Native-looking Status Bar (Only on desktop frame to enhance the premium aesthetic) */}
        <div className="flex justify-between items-center px-6 pt-3 pb-1 text-white text-[11px] font-medium tracking-tight z-50 bg-[#05070D]">
          <span className="font-semibold">{currentTime || "09:41"}</span>
          <div className="flex items-center gap-1.5 text-slate-400">
            <Wifi className="w-3.5 h-3.5" />
            <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1 rounded uppercase font-bold text-[9px] tracking-wide">5G</span>
            <Battery className="w-4 h-4 text-white" />
          </div>
        </div>

        {/* Toast Notification */}
        {toast && (
          <div 
            id="toast-notification"
            className={`absolute top-14 left-4 right-4 z-50 p-3 rounded-2xl border backdrop-blur-md flex items-center gap-2 shadow-lg animate-bounce transition-all duration-300 ${
              toast.type === "success" 
                ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-200" 
                : toast.type === "error"
                ? "bg-red-500/15 border-red-500/30 text-red-200"
                : "bg-blue-500/15 border-blue-500/30 text-blue-200"
            }`}
          >
            <div className={`w-2 h-2 rounded-full ${
              toast.type === "success" ? "bg-emerald-400" : toast.type === "error" ? "bg-red-400" : "bg-blue-400"
            } animate-pulse`} />
            <p className="text-xs font-semibold leading-snug flex-1">{toast.message}</p>
          </div>
        )}

        {/* App Main Body Viewport */}
        <main id="app-viewport" className="flex-1 overflow-y-auto px-4 pt-2 pb-24 scroll-smooth">
          {children}
        </main>

        {/* Premium Bottom Tab Bar */}
        <nav 
          id="ios-bottom-bar" 
          className="absolute bottom-0 left-0 right-0 bg-[#0A0E1A]/80 backdrop-blur-xl border-t border-white/[0.08] px-6 py-3 flex justify-between items-center z-40 pb-5"
        >
          <button 
            id="tab-home"
            onClick={() => handleTabClick("home")}
            className={`flex flex-col items-center gap-1 transition-all duration-300 ${
              activeTab === "home" 
                ? "text-[#7C3AED] scale-105 filter drop-shadow-[0_0_8px_rgba(124,58,237,0.3)]" 
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <HomeIcon className="w-5.5 h-5.5" />
            <span className="text-[9px] font-bold uppercase tracking-wider">Studio</span>
          </button>

          <button 
            id="tab-jobs"
            onClick={() => handleTabClick("jobs")}
            className={`flex flex-col items-center gap-1 transition-all duration-300 ${
              activeTab === "jobs" 
                ? "text-[#7C3AED] scale-105 filter drop-shadow-[0_0_8px_rgba(124,58,237,0.3)]" 
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <ListVideo className="w-5.5 h-5.5" />
            <span className="text-[9px] font-bold uppercase tracking-wider">Jobs</span>
          </button>

          <button 
            id="tab-new"
            onClick={() => handleTabClick("new")}
            className={`flex flex-col items-center gap-1 transition-all duration-300 ${
              activeTab === "new" 
                ? "text-[#06B6D4] scale-105 filter drop-shadow-[0_0_8px_rgba(6,182,212,0.3)]" 
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <PlusCircle className="w-6 h-6 text-cyan-400" />
            <span className="text-[9px] font-bold uppercase tracking-wider">New Job</span>
          </button>

          <button 
            id="tab-projects"
            onClick={() => handleTabClick("projects")}
            className={`flex flex-col items-center gap-1 transition-all duration-300 ${
              activeTab === "projects" 
                ? "text-[#7C3AED] scale-105 filter drop-shadow-[0_0_8px_rgba(124,58,237,0.3)]" 
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <Folder className="w-5.5 h-5.5" />
            <span className="text-[9px] font-bold uppercase tracking-wider">Projects</span>
          </button>

          <button 
            id="tab-settings"
            onClick={() => handleTabClick("settings")}
            className={`flex flex-col items-center gap-1 transition-all duration-300 ${
              activeTab === "settings" 
                ? "text-[#7C3AED] scale-105 filter drop-shadow-[0_0_8px_rgba(124,58,237,0.3)]" 
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <SettingsIcon className="w-5.5 h-5.5" />
            <span className="text-[9px] font-bold uppercase tracking-wider">Settings</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
