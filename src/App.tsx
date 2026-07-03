import React, { useState, useEffect } from "react";
import { AppShell } from "./components/AppShell";
import { 
  getJobs, getJob, createFacebookToYouTubeJob, createTikTokToYouTubeJob,
  approveGlossary, skipGlossary, regenerateMetadata, approveUpload, 
  cancelJob, retryJob, getProjects, createProject, getProject,
  triggerProjectStep, getGlossary, createGlossaryEntry, deleteGlossaryEntry,
  getConnectSettings, toggleYoutubeAuth, updateSystemSettings, subscribeToJobs,
  getSystemLogs, generateThumbnailPrompts, uploadThumbnailImage, skipThumbnail
} from "./lib/api";
import { VideoJob, Project, GlossaryEntry, SystemSettings } from "./types";
import { JobCard } from "./components/jobs/JobCard";
import { ProjectCard } from "./components/projects/ProjectCard";
import { GlossaryItemCard } from "./components/glossary/GlossaryItemCard";
import { EmptyState } from "./components/ui/EmptyState";
import { IOSCard } from "./components/ui/IOSCard";
import { IOSSheet } from "./components/ui/IOSSheet";
import { ProgressStepper } from "./components/ui/ProgressStepper";
import { SettingsRow } from "./components/settings/SettingsRow";
import { RiskFlagBadge } from "./components/RiskFlagBadge";
import { SourcePlatformBadge } from "./components/SourcePlatformBadge";
import { 
  Play, Plus, Search, Calendar, RefreshCw, X, Link, Eye, 
  CheckCircle, Sliders, Volume2, ShieldAlert, BookOpen, AlertCircle, Trash2, Edit2,
  Folder, Layers, MessageSquare, Terminal, Shield, Sparkles, Coins, Cpu, Database, HardDrive, Send
} from "lucide-react";

// --- Custom Subcomponents for Extended iOS 18 Administrative/Manager Capabilities ---
import { SubtitleEditor } from "./components/SubtitleEditor";
import { BotCenter } from "./components/BotCenter";
import { AiServices } from "./components/AiServices";
import { QueueMonitor } from "./components/QueueMonitor";
import { FileManager } from "./components/FileManager";
import { AdminPanel } from "./components/AdminPanel";
import { AiChatAssistant } from "./components/AiChatAssistant";

export default function App() {
  // Navigation / UI States
  const [activeTab, setActiveTab] = useState<string>("home"); // home, jobs, new, projects, settings
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [settingsSubTab, setSettingsSubTab] = useState<string>("settings"); // settings, bot, queues, files, admin, chat, logs

  // Logs state
  const [systemLogs, setSystemLogs] = useState<Array<{ time: string, level: string, section: string, message: string }>>([]);

  // Data States
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [glossaries, setGlossaries] = useState<GlossaryEntry[]>([]);
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null);

  // Search & Filter States
  const [jobSearch, setJobSearch] = useState("");
  const [jobFilter, setJobFilter] = useState("all"); // all, facebook, tiktok, waiting, failed, completed
  const [projectSearch, setProjectSearch] = useState("");
  const [glossarySearch, setGlossarySearch] = useState("");

  // Create Job Form state
  const [newUrl, setNewUrl] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newPlatform, setNewPlatform] = useState<"Auto" | "Facebook" | "TikTok">("Auto");
  const [newOptions, setNewOptions] = useState({
    extract_characters: true,
    generate_seo: true,
    add_watermark: true,
    upload_privacy: "private" as "private" | "unlisted" | "public",
    enable_dubbing: false
  });

  // Create Project state
  const [newProjName, setNewProjName] = useState("");

  // Edit / Approve / Dialog States
  const [isGlossarySheetOpen, setIsGlossarySheetOpen] = useState(false);
  const [isMetadataSheetOpen, setIsMetadataSheetOpen] = useState(false);
  const [isAddProjSheetOpen, setIsAddProjSheetOpen] = useState(false);
  const [isConfirmUploadOpen, setIsConfirmUploadOpen] = useState(false);
  const [isEditGlossaryEntryOpen, setIsEditGlossaryEntryOpen] = useState(false);

  // Active Draft glossary list for editing
  const [draftGlossary, setDraftGlossary] = useState<GlossaryEntry[]>([]);
  const [activeDraftEntry, setActiveDraftEntry] = useState<Partial<GlossaryEntry> | null>(null);

  // Active Draft Metadata for approval editing
  const [draftMetadata, setDraftMetadata] = useState<{
    title: string;
    description: string;
    tags: string;
    hashtags: string;
    category: string;
    privacy: "private" | "unlisted" | "public";
  } | null>(null);

  // Thumbnail AI State Integration
  const [thumbnailMode, setThumbnailMode] = useState(false);
  const [thumbnailPrompts, setThumbnailPrompts] = useState<string[]>([]);
  const [thumbnailImageUrl, setThumbnailImageUrl] = useState<string | null>(null);
  const [thumbnailStatus, setThumbnailStatus] = useState<"pending" | "approved" | "skipped" | null>(null);
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(false);

  // Toast State
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch all initial data
  const loadData = async (silent = false) => {
    if (!silent) setIsLoading(true);
    try {
      const [fetchedJobs, fetchedProjects, fetchedGlossary, fetchedSettings, fetchedLogs] = await Promise.all([
        getJobs(),
        getProjects(),
        getGlossary(),
        getConnectSettings(),
        getSystemLogs().catch(() => [])
      ]);
      setJobs(fetchedJobs);
      setProjects(fetchedProjects);
      setGlossaries(fetchedGlossary);
      setSystemSettings(fetchedSettings);
      setSystemLogs(fetchedLogs);
    } catch (err: any) {
      console.error(err);
      setToast({ message: "Lỗi đồng bộ dữ liệu với Backend", type: "error" });
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch of static data & settings
    loadData();

    // Subscribe to real-time job updates via Server-Sent Events (SSE)
    const unsubscribe = subscribeToJobs((updatedJobs) => {
      setJobs(updatedJobs);
    }, (error) => {
      console.warn("SSE connection error, fallback to silent manual reload", error);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  // Update selected job state dynamically as it completes steps in background
  const activeJob = jobs.find(j => j.id === selectedJobId) || null;
  const activeProject = projects.find(p => p.id === selectedProjectId) || null;

  // Sync draft states when selecting review action
  const startReviewGlossary = (job: VideoJob) => {
    setDraftGlossary(job.glossary ? [...job.glossary] : []);
    setIsGlossarySheetOpen(true);
  };

  const startReviewMetadata = (job: VideoJob) => {
    setThumbnailMode(false);
    setThumbnailPrompts(job.thumbnail?.prompts || []);
    setThumbnailImageUrl(job.thumbnail?.image_url || null);
    setThumbnailStatus(job.thumbnail?.status || null);
    setSelectedJobId(job.id);

    if (job.metadata) {
      setDraftMetadata({
        title: job.metadata.title,
        description: job.metadata.description,
        tags: job.metadata.tags.join(", "),
        hashtags: job.metadata.hashtags.join(", "),
        category: job.metadata.category,
        privacy: job.metadata.privacy || "private"
      });
    } else {
      setDraftMetadata({
        title: job.title,
        description: "Review thuyết minh mới.",
        tags: "review, video",
        hashtags: "#review, #vidlocal",
        category: "Entertainment",
        privacy: "private"
      });
    }
    setIsMetadataSheetOpen(true);
  };

  // Action wrappers with Toast feedbacks
  const handleCreateJob = async () => {
    if (!newUrl) {
      setToast({ message: "Vui lòng nhập đường dẫn video", type: "error" });
      return;
    }
    setIsLoading(true);
    try {
      // Auto resolve platform
      let resolvedPlatform: "Facebook" | "TikTok" = "Facebook";
      if (newPlatform === "TikTok" || (newPlatform === "Auto" && newUrl.toLowerCase().includes("tiktok"))) {
        resolvedPlatform = "TikTok";
      }

      if (resolvedPlatform === "Facebook") {
        await createFacebookToYouTubeJob(newUrl, newOptions, newTitle);
      } else {
        await createTikTokToYouTubeJob(newUrl, newOptions, newTitle);
      }

      setToast({ message: "Đã tạo VideoJob mới thành công!", type: "success" });
      setNewUrl("");
      setNewTitle("");
      setActiveTab("jobs");
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi khi tạo Job mới", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveGlossary = async () => {
    if (!activeJob) return;
    setIsLoading(true);
    try {
      await approveGlossary(activeJob.id, draftGlossary);
      setToast({ message: "Đã duyệt bảng nhân vật!", type: "success" });
      setIsGlossarySheetOpen(false);
      loadData(true);
    } catch (e) {
      setToast({ message: "Thao tác thất bại", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkipGlossary = async () => {
    if (!activeJob) return;
    setIsLoading(true);
    try {
      await skipGlossary(activeJob.id);
      setToast({ message: "Đã bỏ qua Glossary!", type: "info" });
      setIsGlossarySheetOpen(false);
      loadData(true);
    } catch (e) {
      setToast({ message: "Thao tác thất bại", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerateMetadata = async () => {
    if (!activeJob) return;
    setIsLoading(true);
    try {
      const updated = await regenerateMetadata(activeJob.id);
      if (updated.metadata) {
        setDraftMetadata({
          title: updated.metadata.title,
          description: updated.metadata.description,
          tags: updated.metadata.tags.join(", "),
          hashtags: updated.metadata.hashtags.join(", "),
          category: updated.metadata.category,
          privacy: updated.metadata.privacy || "private"
        });
        setToast({ message: "Gemini đã tối ưu lại tiêu đề & thẻ SEO!", type: "success" });
      }
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi kết nối Gemini AI", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchThumbnailPrompts = async (forceRegen = false) => {
    if (!activeJob) return;
    setIsLoadingPrompts(true);
    try {
      const updated = await generateThumbnailPrompts(activeJob.id);
      if (updated.thumbnail?.prompts) {
        setThumbnailPrompts(updated.thumbnail.prompts);
        setToast({ message: forceRegen ? "Đã làm mới và sinh 4 ý tưởng prompt mới!" : "Gemini đã sinh thành công 4 ý tưởng prompt hình thu nhỏ!", type: "success" });
      }
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi kết nối Gemini AI tạo prompts", type: "error" });
    } finally {
      setIsLoadingPrompts(false);
    }
  };

  const handleUploadThumbnailFile = async (file: File) => {
    if (!activeJob) return;
    setIsLoading(true);
    try {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64String = reader.result as string;
        const updated = await uploadThumbnailImage(activeJob.id, base64String);
        setThumbnailImageUrl(updated.thumbnail?.image_url || null);
        setThumbnailStatus("approved");
        setToast({ message: "Đã tải lên ảnh Thumbnail và phê duyệt thành công!", type: "success" });
        loadData(true);
      };
      reader.readAsDataURL(file);
    } catch (e) {
      setToast({ message: "Lỗi đọc tệp ảnh", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkipThumbnailAction = async () => {
    if (!activeJob) return;
    setIsLoading(true);
    try {
      await skipThumbnail(activeJob.id);
      setThumbnailStatus("skipped");
      setToast({ message: "Đã bỏ qua thiết lập Thumbnail cho Job này.", type: "info" });
      setThumbnailMode(false);
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi thực thi bỏ qua", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveUpload = async () => {
    if (!activeJob || !draftMetadata) return;
    setIsLoading(true);
    try {
      const parsedMeta = {
        title: draftMetadata.title,
        description: draftMetadata.description,
        tags: draftMetadata.tags.split(",").map(t => t.trim()).filter(Boolean),
        hashtags: draftMetadata.hashtags.split(",").map(t => t.trim()).filter(Boolean),
        category: draftMetadata.category,
        privacy: draftMetadata.privacy
      };
      await approveUpload(activeJob.id, parsedMeta);
      setToast({ message: "Đã phê duyệt! Bắt đầu chèn Watermark & đăng tải YouTube.", type: "success" });
      setIsMetadataSheetOpen(false);
      setIsConfirmUploadOpen(false);
      loadData(true);
    } catch (e) {
      setToast({ message: "Thao tác thất bại", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelJob = async (id: string) => {
    try {
      await cancelJob(id);
      setToast({ message: "Đã dừng xử lý video.", type: "info" });
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi khi dừng job", type: "error" });
    }
  };

  const handleRetryJob = async (id: string) => {
    try {
      await retryJob(id);
      setToast({ message: "Đang tải lại video và reset pipeline...", type: "success" });
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi khi chạy lại job", type: "error" });
    }
  };

  const handleCreateProject = async () => {
    if (!newProjName) return;
    setIsLoading(true);
    try {
      await createProject(newProjName);
      setToast({ message: "Đã khởi tạo project mới thành công!", type: "success" });
      setNewProjName("");
      setIsAddProjSheetOpen(false);
      loadData(true);
    } catch (e) {
      setToast({ message: "Lỗi tạo project", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerProjectStep = async (projId: string, nextStep: string) => {
    setIsLoading(true);
    try {
      await triggerProjectStep(projId, nextStep);
      setToast({ message: `Bắt đầu xử lý bước: ${nextStep}`, type: "success" });
      loadData(true);
    } catch (e) {
      setToast({ message: "Thao tác thất bại", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddDraftEntry = () => {
    const newEntry: GlossaryEntry = {
      id: `draft-${Date.now()}`,
      source_name: "Tên Tiếng Anh",
      target_name: "Tên Việt Hóa",
      aliases: "",
      role: "Phụ",
      gender: "Nam",
      pronoun_style: "Tôi",
      notes: ""
    };
    setDraftGlossary([...draftGlossary, newEntry]);
    setActiveDraftEntry(newEntry);
    setIsEditGlossaryEntryOpen(true);
  };

  const handleSaveDraftEntry = () => {
    if (!activeDraftEntry) return;
    setDraftGlossary(
      draftGlossary.map(item => item.id === activeDraftEntry.id ? (activeDraftEntry as GlossaryEntry) : item)
    );
    setIsEditGlossaryEntryOpen(false);
    setActiveDraftEntry(null);
  };

  const handleDeleteDraftEntry = (id: string) => {
    setDraftGlossary(draftGlossary.filter(item => item.id !== id));
  };

  // Filter and Search computations
  const filteredJobs = jobs.filter(job => {
    const matchSearch = job.title.toLowerCase().includes(jobSearch.toLowerCase()) || 
                        job.url.toLowerCase().includes(jobSearch.toLowerCase());
    
    if (jobFilter === "all") return matchSearch;
    if (jobFilter === "facebook") return job.platform === "Facebook" && matchSearch;
    if (jobFilter === "tiktok") return job.platform === "TikTok" && matchSearch;
    if (jobFilter === "waiting") return job.status === "waiting_approval" && matchSearch;
    if (jobFilter === "failed") return job.status === "failed" && matchSearch;
    if (jobFilter === "completed") return job.status === "completed" && matchSearch;
    return matchSearch;
  });

  const waitingJobsCount = jobs.filter(j => j.status === "waiting_approval").length;
  const completedTodayCount = jobs.filter(j => j.status === "completed").length;
  const processingCount = jobs.filter(j => j.status === "downloading" || j.status === "transcribing" || j.status === "approved").length;

  return (
    <AppShell 
      activeTab={activeTab} 
      setActiveTab={setActiveTab}
      onNavigateHome={() => {
        setSelectedJobId(null);
        setSelectedProjectId(null);
      }}
      toast={toast}
      setToast={setToast}
    >
      {/* 1. DASHBOARD VIEW (HOME) */}
      {activeTab === "home" && !selectedJobId && !selectedProjectId && (
        <div id="view-dashboard" className="space-y-6">
          {/* iOS Header */}
          <div className="flex justify-between items-center py-2">
            <div>
              <h2 className="text-xl font-extrabold tracking-tight text-white font-display">
                VidLocal Studio
              </h2>
              <p className="text-[11px] text-cyan-400 font-bold uppercase tracking-widest mt-0.5">
                Admin Automation
              </p>
            </div>
            {systemSettings?.youtube_connected ? (
              <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full text-[10px] text-emerald-400 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>YouTube Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full text-[10px] text-red-400 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                <span>YT Disconnected</span>
              </div>
            )}
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white/[0.03] border border-white/[0.06] p-3 rounded-[20px] flex flex-col justify-between h-20">
              <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Waiting Approve</span>
              <span className="text-2xl font-black text-yellow-500 font-mono">{waitingJobsCount}</span>
            </div>
            <div className="bg-white/[0.03] border border-white/[0.06] p-3 rounded-[20px] flex flex-col justify-between h-20">
              <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Processing</span>
              <span className="text-2xl font-black text-purple-400 font-mono">{processingCount}</span>
            </div>
            <div className="bg-white/[0.03] border border-white/[0.06] p-3 rounded-[20px] flex flex-col justify-between h-20">
              <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Completed</span>
              <span className="text-2xl font-black text-cyan-400 font-mono">{completedTodayCount}</span>
            </div>
          </div>

          {/* Advanced System Metrics Row (iOS 18 High Density) */}
          <div className="space-y-2.5">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">System Infrastructure Health</h3>
            <div className="grid grid-cols-2 gap-3">
              {/* CPU & RAM Card */}
              <div className="bg-white/[0.02] border border-white/[0.05] p-3 rounded-[22px] space-y-2 text-[10px]">
                <div className="flex justify-between items-center text-slate-400 font-medium">
                  <span className="flex items-center gap-1">
                    <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                    <span>CPU Load</span>
                  </span>
                  <span className="font-mono text-cyan-400 font-bold">14.8%</span>
                </div>
                <div className="flex justify-between items-center text-slate-400 font-medium">
                  <span className="flex items-center gap-1">
                    <Database className="w-3.5 h-3.5 text-purple-400" />
                    <span>RAM Used</span>
                  </span>
                  <span className="font-mono text-purple-400 font-bold">42.1%</span>
                </div>
              </div>

              {/* Workers & Storage Card */}
              <div className="bg-white/[0.02] border border-white/[0.05] p-3 rounded-[22px] space-y-2 text-[10px]">
                <div className="flex justify-between items-center text-slate-400 font-medium">
                  <span className="flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Celery Workers</span>
                  </span>
                  <span className="text-emerald-400 font-bold uppercase">4 Online</span>
                </div>
                <div className="flex justify-between items-center text-slate-400 font-medium">
                  <span className="flex items-center gap-1">
                    <HardDrive className="w-3.5 h-3.5 text-yellow-500" />
                    <span>Disk Space</span>
                  </span>
                  <span className="font-mono text-yellow-500 font-bold">120G/500G</span>
                </div>
              </div>

              {/* Bot & Webhook Card */}
              <div className="bg-white/[0.02] border border-white/[0.05] p-3 rounded-[22px] space-y-1 text-[10px] col-span-2 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <div>
                    <p className="font-bold text-white text-[10.5px]">Telegram Bot: @VidLocalStudio_Bot</p>
                    <p className="text-[9px] text-slate-500 mt-0.5">Webhook Webapp active & listening</p>
                  </div>
                </div>
                <span className="bg-cyan-500/10 text-cyan-400 font-mono font-bold px-2 py-0.5 rounded text-[9px] uppercase">
                  Webhook OK
                </span>
              </div>
            </div>
          </div>

          {/* Core Urgent Pending Approvals Hero Card */}
          {waitingJobsCount > 0 ? (
            <IOSCard
              id="hero-waiting-approval"
              glowColor="rgba(245, 158, 11, 0.12)"
              className="border-yellow-500/30 border-dashed bg-gradient-to-br from-yellow-500/10 via-transparent to-transparent space-y-3"
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="p-2 rounded-xl bg-yellow-500/15 text-yellow-400 border border-yellow-500/20">
                    <AlertCircle className="w-4 h-4 animate-bounce" />
                  </span>
                  <div>
                    <h3 className="text-xs font-bold text-yellow-400 uppercase tracking-wider">Cần duyệt gấp</h3>
                    <p className="text-[10px] text-slate-400">{waitingJobsCount} video đã dịch xong & chờ bạn kiểm duyệt</p>
                  </div>
                </div>
              </div>

              {/* Show first pending job */}
              {jobs.filter(j => j.status === "waiting_approval").slice(0, 1).map(job => (
                <div key={job.id} className="bg-white/[0.03] border border-white/[0.05] p-3 rounded-2xl flex justify-between items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-xs font-bold text-white truncate">{job.title}</h4>
                    <p className="text-[10px] text-purple-400 font-semibold mt-0.5">
                      {job.current_step === "glossary_review" ? "Duyệt nhân vật" : "Duyệt SEO & Đăng tải"}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedJobId(job.id);
                      setActiveTab("jobs");
                    }}
                    className="flex-shrink-0 bg-yellow-500 text-slate-950 font-black px-3 py-1.5 rounded-xl text-[11px] active:scale-95 transition-all"
                  >
                    Xử lý
                  </button>
                </div>
              ))}
            </IOSCard>
          ) : (
            <div className="bg-emerald-500/5 border border-emerald-500/15 p-4 rounded-3xl flex items-center gap-3 text-emerald-400">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <div className="text-xs">
                <p className="font-bold">Hệ thống sạch bóng!</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Mọi video jobs đã xử lý và lên sóng suôn sẻ.</p>
              </div>
            </div>
          )}

          {/* Quick Action Bento Grid (iOS 18 Grid of 4 columns, elegant circles/pills) */}
          <div className="space-y-2.5">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Quick Studio Actions</h3>
            <div className="grid grid-cols-4 gap-2">
              <button
                onClick={() => setIsAddProjSheetOpen(true)}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-purple-500/15 flex items-center justify-center text-purple-400 border border-purple-500/20">
                  <Plus className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">Tạo Proj</span>
              </button>

              <button
                onClick={() => {
                  setNewPlatform("Facebook");
                  setActiveTab("new");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-blue-500/15 flex items-center justify-center text-blue-400 border border-blue-500/20">
                  <Play className="w-4 h-4 fill-current" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">Fb → YT</span>
              </button>

              <button
                onClick={() => {
                  setNewPlatform("TikTok");
                  setActiveTab("new");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-pink-500/15 flex items-center justify-center text-pink-400 border border-pink-500/20">
                  <Plus className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">TT → YT</span>
              </button>

              <button
                onClick={() => {
                  setSettingsSubTab("files");
                  setActiveTab("settings");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-yellow-500/15 flex items-center justify-center text-yellow-400 border border-yellow-500/20">
                  <Folder className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">Tải Video</span>
              </button>

              <button
                onClick={() => {
                  setSettingsSubTab("queues");
                  setActiveTab("settings");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-[#06B6D4]/15 flex items-center justify-center text-[#06B6D4] border border-[#06B6D4]/20">
                  <Layers className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">Hàng Đợi</span>
              </button>

              <button
                onClick={() => {
                  setSettingsSubTab("bot");
                  setActiveTab("settings");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-emerald-500/15 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
                  <Terminal className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">Bot Center</span>
              </button>

              <button
                onClick={() => {
                  setSettingsSubTab("chat");
                  setActiveTab("settings");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-orange-500/15 flex items-center justify-center text-orange-400 border border-orange-500/20">
                  <MessageSquare className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">AI Chat</span>
              </button>

              <button
                onClick={() => {
                  setSettingsSubTab("logs");
                  setActiveTab("settings");
                }}
                className="bg-white/[0.02] border border-white/[0.04] p-2 rounded-[18px] flex flex-col items-center justify-center text-center gap-1 hover:bg-white/[0.04] active:scale-95 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-red-500/15 flex items-center justify-center text-red-400 border border-red-500/20">
                  <Terminal className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-bold text-slate-300 leading-tight">Hệ Thống Logs</span>
              </button>
            </div>
          </div>

          {/* Recent active jobs list */}
          <div className="space-y-3">
            <div className="flex justify-between items-center px-1">
              <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Jobs Đang Xử Lý</h3>
              <button onClick={() => setActiveTab("jobs")} className="text-xs text-purple-400 font-bold hover:underline">
                Xem Tất Cả
              </button>
            </div>

            {jobs.filter(j => j.status !== "completed" && j.status !== "failed").slice(0, 3).map(job => (
              <JobCard
                key={job.id}
                job={job}
                onClick={() => {
                  setSelectedJobId(job.id);
                  setActiveTab("jobs");
                }}
                onReviewCharacters={() => startReviewGlossary(job)}
                onReviewMetadata={() => startReviewMetadata(job)}
                onRetry={() => handleRetryJob(job.id)}
              />
            ))}

            {jobs.filter(j => j.status !== "completed" && j.status !== "failed").length === 0 && (
              <EmptyState
                title="Không có job đang chạy"
                description="Tạo job tải video tự động từ Facebook/TikTok tại tab New Job bên dưới."
                actionLabel="Tạo Job Ngay"
                onAction={() => setActiveTab("new")}
              />
            )}
          </div>
        </div>
      )}

      {/* 2. JOBS LIST / SEARCH VIEW */}
      {activeTab === "jobs" && !selectedJobId && (
        <div id="view-jobs-list" className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-extrabold text-white tracking-tight">Xử Lý Video (Job-based)</h2>
              <p className="text-xs text-slate-400">Xem tiến trình tải, transcribe và upload</p>
            </div>
            <button 
              onClick={() => loadData(false)}
              className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-slate-300 hover:text-white"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Search bar & filter selection */}
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Tìm tiêu đề, liên kết..."
                value={jobSearch}
                onChange={(e) => setJobSearch(e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-purple-500/50 rounded-2xl py-2.5 pl-10 pr-4 text-xs font-medium text-white placeholder-slate-500 focus:outline-none transition-all"
              />
            </div>

            {/* Filter Pill List */}
            <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
              {[
                { key: "all", label: "All" },
                { key: "facebook", label: "Facebook" },
                { key: "tiktok", label: "TikTok" },
                { key: "waiting", label: "Chờ Duyệt" },
                { key: "completed", label: "Đã Đăng" },
                { key: "failed", label: "Thất Bại" }
              ].map(f => (
                <button
                  key={f.key}
                  onClick={() => setJobFilter(f.key)}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all flex-shrink-0 ${
                    jobFilter === f.key
                      ? "bg-purple-600 text-white"
                      : "bg-white/[0.04] text-slate-400 border border-white/[0.06] hover:bg-white/[0.08]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Job Cards */}
          <div className="space-y-3">
            {filteredJobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                onClick={() => setSelectedJobId(job.id)}
                onReviewCharacters={() => startReviewGlossary(job)}
                onReviewMetadata={() => startReviewMetadata(job)}
                onRetry={() => handleRetryJob(job.id)}
              />
            ))}

            {filteredJobs.length === 0 && (
              <EmptyState
                title="Không tìm thấy job phù hợp"
                description="Thử đổi bộ lọc hoặc thêm job Facebook/TikTok mới để quản lý."
              />
            )}
          </div>
        </div>
      )}

      {/* 3. JOB DETAIL DEEP VIEW */}
      {activeTab === "jobs" && selectedJobId && activeJob && (
        <div id="view-job-detail" className="space-y-4">
          {/* Sub Navigation Bar */}
          <div className="flex justify-between items-center">
            <button
              onClick={() => setSelectedJobId(null)}
              className="text-xs text-slate-400 hover:text-white bg-white/[0.04] border border-white/[0.08] px-3 py-1.5 rounded-xl font-bold flex items-center gap-1 transition-all"
            >
              ← Quay lại list
            </button>
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-slate-500 font-mono font-bold">ID: {activeJob.id}</span>
            </div>
          </div>

          {/* Header section with status */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <SourcePlatformBadge platform={activeJob.platform} />
              <span className="text-[10px] text-slate-500 font-mono">{activeJob.options.upload_privacy}</span>
            </div>
            <h2 className="text-base font-black text-white leading-tight">
              {activeJob.title}
            </h2>
            <div className="flex items-center gap-2 text-slate-400 text-xs">
              <Link className="w-3.5 h-3.5 text-slate-500 truncate" />
              <a href={activeJob.url} target="_blank" rel="noreferrer" className="underline truncate flex-1 text-slate-400 hover:text-cyan-400">
                {activeJob.url}
              </a>
            </div>
          </div>

          {/* Status timeline stepper */}
          <IOSCard className="space-y-3">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/[0.04] pb-2">
              Tiến Trình Pipeline
            </h3>
            <ProgressStepper
              currentStepKey={activeJob.current_step}
              steps={[
                { key: "download", label: "1. Download yt-dlp", status: activeJob.steps.download.status, progress: activeJob.steps.download.progress },
                { key: "transcribe", label: "2. Whisper Speech-To-Text", status: activeJob.steps.transcribe.status, progress: activeJob.steps.transcribe.progress },
                { key: "character_extract", label: "3. Trích Nhân Vật AI", status: activeJob.steps.character_extract.status, progress: activeJob.steps.character_extract.progress },
                { key: "glossary_review", label: "4. Duyệt Xưng Hô (Glossary)", status: activeJob.steps.glossary_review.status, progress: activeJob.steps.glossary_review.progress },
                { key: "seo_metadata", label: "5. Gemini Tạo SEO Metadata", status: activeJob.steps.seo_metadata.status, progress: activeJob.steps.seo_metadata.progress },
                { key: "watermark", label: "6. Gắn Logo Watermark", status: activeJob.steps.watermark.status, progress: activeJob.steps.watermark.progress },
                { key: "upload", label: "7. Upload YouTube API", status: activeJob.steps.upload.status, progress: activeJob.steps.upload.progress }
              ]}
            />
          </IOSCard>

          {/* Tabs for detailed sections */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Chi Tiết Thông Tin</h3>
            
            {/* 1. Overview and Files */}
            <IOSCard className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3 text-[11px] leading-normal">
                <div>
                  <span className="text-slate-500 block">Nguồn:</span>
                  <span className="text-slate-200 font-bold">{activeJob.platform}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Thời gian tạo:</span>
                  <span className="text-slate-200">{new Date(activeJob.created_time).toLocaleString("vi-VN")}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Chế độ Upload:</span>
                  <span className="text-slate-200 font-bold uppercase text-purple-400">{activeJob.options.upload_privacy}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Trích nhân vật:</span>
                  <span className="text-slate-200">{activeJob.options.extract_characters ? "Bật" : "Tắt"}</span>
                </div>
              </div>

              {activeJob.youtube_url && (
                <div className="bg-cyan-950/20 border border-cyan-500/25 p-3 rounded-2xl flex flex-col gap-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">YouTube Video Link</span>
                  <a href={activeJob.youtube_url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-white underline break-all flex items-center gap-1">
                    {activeJob.youtube_url}
                  </a>
                </div>
              )}
            </IOSCard>

            {/* 2. Audio Transcript text area */}
            {activeJob.transcript && (
              <IOSCard className="space-y-2">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">Bản dịch phụ đề (Speech-To-Text)</h4>
                <div className="max-h-40 overflow-y-auto text-xs text-slate-300 font-mono p-3 rounded-2xl bg-black/40 border border-white/[0.04] leading-relaxed whitespace-pre-wrap">
                  {activeJob.transcript}
                </div>
              </IOSCard>
            )}

            {/* 3. Local and pipeline logs */}
            <IOSCard className="space-y-2">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Hệ Thống Logs</h4>
              <div className="max-h-40 overflow-y-auto text-[10px] text-slate-400 font-mono p-3 rounded-2xl bg-black/40 border border-white/[0.04] space-y-1">
                {activeJob.logs.map((log, lidx) => (
                  <div key={lidx} className="flex gap-2 leading-relaxed">
                    <span className="text-slate-600">[{new Date(log.time).toLocaleTimeString()}]</span>
                    <span className={log.level === "error" ? "text-red-400 font-bold" : log.level === "warn" ? "text-yellow-400" : "text-slate-400"}>
                      {log.message}
                    </span>
                  </div>
                ))}
              </div>
            </IOSCard>
          </div>

          {/* Quick inline approval controls */}
          <div className="flex gap-2 pt-2 pb-6">
            {activeJob.status === "waiting_approval" && activeJob.current_step === "glossary_review" && (
              <button
                onClick={() => startReviewGlossary(activeJob)}
                className="flex-1 bg-[#7C3AED] hover:bg-purple-600 text-white font-bold py-3.5 rounded-[22px] text-xs shadow-lg shadow-purple-500/20 active:scale-95 transition-all"
              >
                Tiến Hành Duyệt Glossary
              </button>
            )}

            {activeJob.status === "waiting_approval" && activeJob.current_step === "seo_metadata" && (
              <button
                onClick={() => startReviewMetadata(activeJob)}
                className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-3.5 rounded-[22px] text-xs shadow-lg shadow-cyan-500/20 active:scale-95 transition-all"
              >
                Tiến Hành Duyệt SEO Metadata
              </button>
            )}

            {activeJob.status === "failed" && (
              <button
                onClick={() => handleRetryJob(activeJob.id)}
                className="flex-1 bg-white/[0.06] border border-white/[0.10] text-white font-bold py-3.5 rounded-[22px] text-xs active:scale-95 transition-all"
              >
                Thử Lại Pipeline
              </button>
            )}

            {activeJob.status !== "completed" && activeJob.status !== "failed" && (
              <button
                onClick={() => handleCancelJob(activeJob.id)}
                className="bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 text-red-400 font-bold py-3.5 px-6 rounded-[22px] text-xs active:scale-95 transition-all"
              >
                Dừng Job
              </button>
            )}
          </div>
        </div>
      )}

      {/* 4. NEW JOB / PIPELINE FORM */}
      {activeTab === "new" && (
        <div id="view-new-job" className="space-y-4">
          <div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">Thêm Video Job Mới</h2>
            <p className="text-xs text-slate-400">Khởi động chuỗi xử lý tải video tự động</p>
          </div>

          <IOSCard className="space-y-4">
            {/* Source Segmented Control */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Kênh nguồn (Source Platform)</label>
              <div className="grid grid-cols-3 gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.05]">
                {["Auto", "Facebook", "TikTok"].map((plat: any) => (
                  <button
                    key={plat}
                    type="button"
                    onClick={() => setNewPlatform(plat)}
                    className={`py-1.5 rounded-lg text-xs font-bold transition-all ${
                      newPlatform === plat
                        ? "bg-[#7C3AED] text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {plat}
                  </button>
                ))}
              </div>
            </div>

            {/* URL input */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Đường Dẫn Video (Facebook/TikTok Link)</label>
              <div className="relative">
                <input
                  type="url"
                  required
                  placeholder="Dán link Facebook Watch, Reel hoặc TikTok..."
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] focus:border-purple-500/50 rounded-2xl py-3 px-4 text-xs font-medium text-white placeholder-slate-500 focus:outline-none transition-all"
                />
              </div>
            </div>

            {/* Custom Job Title */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tiêu Đề Tùy Chọn (Optional Title)</label>
              <input
                type="text"
                placeholder="Ví dụ: Iron Man Review Thuyết Minh..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] focus:border-purple-500/50 rounded-2xl py-3 px-4 text-xs font-medium text-white placeholder-slate-500 focus:outline-none transition-all"
              />
            </div>

            {/* Processing Switches */}
            <div className="space-y-3 pt-2 border-t border-white/[0.04]">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Tùy Chọn Pipeline (Pipeline Options)</h4>
              
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-300">Tự động trích xuất nhân vật AI</span>
                <button
                  type="button"
                  onClick={() => setNewOptions({ ...newOptions, extract_characters: !newOptions.extract_characters })}
                  className={`w-10 h-6 rounded-full p-1 transition-colors ${newOptions.extract_characters ? "bg-[#7C3AED]" : "bg-slate-800"}`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-transform ${newOptions.extract_characters ? "translate-x-4" : "translate-x-0"}`} />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-300">Tạo metadata chuẩn SEO bằng Gemini</span>
                <button
                  type="button"
                  onClick={() => setNewOptions({ ...newOptions, generate_seo: !newOptions.generate_seo })}
                  className={`w-10 h-6 rounded-full p-1 transition-colors ${newOptions.generate_seo ? "bg-[#7C3AED]" : "bg-slate-800"}`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-transform ${newOptions.generate_seo ? "translate-x-4" : "translate-x-0"}`} />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-300">Gắn logo chìm (VidLocal Watermark)</span>
                <button
                  type="button"
                  onClick={() => setNewOptions({ ...newOptions, add_watermark: !newOptions.add_watermark })}
                  className={`w-10 h-6 rounded-full p-1 transition-colors ${newOptions.add_watermark ? "bg-[#7C3AED]" : "bg-slate-800"}`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-transform ${newOptions.add_watermark ? "translate-x-4" : "translate-x-0"}`} />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-300">Dịch thuyết minh giọng nói (TTS Dubbing)</span>
                <button
                  type="button"
                  onClick={() => setNewOptions({ ...newOptions, enable_dubbing: !newOptions.enable_dubbing })}
                  className={`w-10 h-6 rounded-full p-1 transition-colors ${newOptions.enable_dubbing ? "bg-[#7C3AED]" : "bg-slate-800"}`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-transform ${newOptions.enable_dubbing ? "translate-x-4" : "translate-x-0"}`} />
                </button>
              </div>
            </div>

            {/* Privacy selection */}
            <div className="space-y-1.5 pt-2 border-t border-white/[0.04]">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Chế độ riêng tư YouTube</label>
              <div className="grid grid-cols-3 gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.05]">
                {["private", "unlisted", "public"].map((priv: any) => (
                  <button
                    key={priv}
                    type="button"
                    onClick={() => setNewOptions({ ...newOptions, upload_privacy: priv })}
                    className={`py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${
                      newOptions.upload_privacy === priv
                        ? "bg-[#06B6D4] text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {priv}
                  </button>
                ))}
              </div>
            </div>
          </IOSCard>

          {/* Submission button */}
          <button
            id="btn-submit-job"
            onClick={handleCreateJob}
            className="w-full bg-gradient-to-r from-purple-600 to-[#7C3AED] hover:from-purple-500 hover:to-purple-600 text-white font-extrabold py-3.5 rounded-[22px] text-xs shadow-lg shadow-purple-500/20 active:scale-95 transition-all duration-300 flex items-center justify-center gap-1.5"
          >
            <Play className="w-4 h-4 fill-current" />
            Khởi Động Pipeline Tự Động
          </button>
        </div>
      )}

      {/* 5. TRADITIONAL PROJECTS LIST */}
      {activeTab === "projects" && !selectedProjectId && (
        <div id="view-projects-list" className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-extrabold text-white tracking-tight">Dự Án Phụ Đề & TTS</h2>
              <p className="text-xs text-slate-400">Quản lý các project dịch thủ công, lồng tiếng cũ</p>
            </div>
            <button
              onClick={() => setIsAddProjSheetOpen(true)}
              className="p-2.5 rounded-xl bg-purple-600 text-white shadow-md active:scale-95 transition-all"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="relative">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Tìm tên dự án dịch..."
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-purple-500/50 rounded-2xl py-2.5 pl-10 pr-4 text-xs font-medium text-white placeholder-slate-500 focus:outline-none transition-all"
            />
          </div>

          <div className="space-y-3">
            {projects
              .filter(p => p.name.toLowerCase().includes(projectSearch.toLowerCase()))
              .map(project => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onClick={() => setSelectedProjectId(project.id)}
                  onTriggerNext={() => handleTriggerProjectStep(project.id, project.current_step)}
                />
              ))}

            {projects.length === 0 && (
              <EmptyState
                title="Chưa có dự án cũ nào"
                description="Khởi tạo một dự án dịch phụ đề/TTS mới để lưu trữ glossary."
                actionLabel="Khởi Tạo Dự Án"
                onAction={() => setIsAddProjSheetOpen(true)}
              />
            )}
          </div>
        </div>
      )}

      {/* 6. PROJECT DETAIL SUBPAGE */}
      {activeTab === "projects" && selectedProjectId && activeProject && (
        <div id="view-project-detail" className="space-y-4">
          <button
            onClick={() => setSelectedProjectId(null)}
            className="text-xs text-slate-400 hover:text-white bg-white/[0.04] border border-white/[0.08] px-3 py-1.5 rounded-xl font-bold transition-all"
          >
            ← Quay lại list dự án
          </button>

          <div className="space-y-1">
            <h2 className="text-base font-black text-white">{activeProject.name}</h2>
            <p className="text-[11px] text-slate-500 font-mono">Dự án ID: {activeProject.id}</p>
          </div>

          <IOSCard className="space-y-3">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/[0.04] pb-2">
              Các Bước Pipeline Dự Án
            </h3>
            
            <div className="space-y-3">
              {[
                { key: "upload", label: "Upload Video", status: activeProject.steps.upload },
                { key: "transcribe", label: "Speech-To-Text", status: activeProject.steps.transcribe },
                { key: "translate", label: "Dịch phụ đề bằng AI", status: activeProject.steps.translate },
                { key: "tts", label: "Lồng tiếng nói (TTS)", status: activeProject.steps.tts },
                { key: "render", label: "Ghép khớp Audio & Video", status: activeProject.steps.render },
                { key: "publish", label: "Publish YouTube", status: activeProject.steps.publish }
              ].map((step, idx) => {
                let statusBadge = "text-slate-500 bg-white/[0.02]";
                if (step.status === "completed") statusBadge = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
                else if (step.status === "running") statusBadge = "text-purple-400 bg-purple-500/10 border-purple-500/25 animate-pulse";
                else if (step.status === "failed") statusBadge = "text-red-400 bg-red-500/10 border-red-500/20";

                return (
                  <div key={step.key} className="flex justify-between items-center text-xs py-1 border-b border-white/[0.02] last:border-none">
                    <span className="text-slate-300 font-medium">{idx + 1}. {step.label}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${statusBadge}`}>
                      {step.status}
                    </span>
                  </div>
                );
              })}
            </div>
          </IOSCard>

          {/* Trigger next pipeline control */}
          {activeProject.current_step !== "done" && (
            <button
              onClick={() => handleTriggerProjectStep(activeProject.id, activeProject.current_step)}
              className="w-full bg-purple-600 hover:bg-purple-500 text-white font-extrabold py-3 rounded-2xl text-xs shadow-lg flex items-center justify-center gap-1.5 transition-all"
            >
              <Play className="w-4 h-4 fill-current" />
              Tiếp Tục Pipeline ({activeProject.current_step})
            </button>
          )}

          {/* CapCut-style Subtitle Editor & Timeline */}
          <div className="space-y-2.5">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
              Bộ biên tập phụ đề (CapCut Subtitle Editor)
            </h3>
            <SubtitleEditor projectId={activeProject.id} projectName={activeProject.name} />
          </div>

          {/* Glossary Entries associated with project */}
          <div className="space-y-2.5">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Từ Điển Riêng Cho Dự Án</h3>
            <div className="space-y-2.5">
              {glossaries.filter(g => g.project_id === activeProject.id).map(entry => (
                <GlossaryItemCard
                  key={entry.id}
                  entry={entry}
                  onDelete={async () => {
                    await deleteGlossaryEntry(entry.id);
                    loadData(true);
                  }}
                />
              ))}

              {glossaries.filter(g => g.project_id === activeProject.id).length === 0 && (
                <p className="text-xs text-slate-500 text-center py-6">Không có nhân vật nào trong dự án này.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 7. SYSTEM SETTINGS VIEW */}
      {activeTab === "settings" && (
        <div id="view-settings" className="space-y-5">
          <div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">Trung Tâm Quản Trị VidLocal</h2>
            <p className="text-xs text-slate-400">Quản lý tích hợp YouTube, R2, AI, bot Telegram & hệ thống</p>
          </div>

          {/* Sub Navigation Bar within Settings */}
          <div className="flex gap-1.5 overflow-x-auto pb-2 border-b border-white/[0.04] -mx-4 px-4 scrollbar-none">
            {[
              { id: "settings", label: "Cấu hình", icon: <Sliders className="w-3.5 h-3.5" /> },
              { id: "bot", label: "Telegram Bot", icon: <Terminal className="w-3.5 h-3.5" /> },
              { id: "queues", label: "Hàng đợi", icon: <Layers className="w-3.5 h-3.5" /> },
              { id: "files", label: "Files", icon: <Folder className="w-3.5 h-3.5" /> },
              { id: "admin", label: "Admin", icon: <Shield className="w-3.5 h-3.5" /> },
              { id: "chat", label: "AI Chat", icon: <MessageSquare className="w-3.5 h-3.5" /> },
              { id: "logs", label: "Logs", icon: <Terminal className="w-3.5 h-3.5" /> },
            ].map(sub => (
              <button
                key={sub.id}
                onClick={() => setSettingsSubTab(sub.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap transition-all border ${
                  settingsSubTab === sub.id
                    ? "bg-purple-600/20 text-purple-300 border-purple-500/30"
                    : "bg-white/[0.02] text-slate-400 border-white/[0.04] hover:text-white"
                }`}
              >
                {sub.icon}
                <span>{sub.label}</span>
              </button>
            ))}
          </div>

          {/* Render Active Sub Tab Content */}
          {settingsSubTab === "settings" && (
            <div className="space-y-5 animate-fade-in">
              {/* Connection row list */}
              <div className="space-y-2.5">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Tích Hợp API & Cloud</h3>
                
                <div className="space-y-2">
                  <SettingsRow
                    label="Đăng Nhập Kênh YouTube"
                    icon={<Link className="w-4 h-4 text-red-500" />}
                    type="button"
                    value={systemSettings?.youtube_connected ? "VidLocal Official" : "Chưa Liên Kết"}
                    onClick={async () => {
                      setIsLoading(true);
                      const res = await toggleYoutubeAuth();
                      if (res.success) {
                        setSystemSettings(res.settings);
                        setToast({ message: "Đã thay đổi kết nối YouTube API!", type: "success" });
                      }
                      setIsLoading(false);
                    }}
                  />

                  <SettingsRow
                    label="Cloudflare R2 Bucket"
                    icon={<Sliders className="w-4 h-4 text-orange-400" />}
                    type="info"
                    value={systemSettings?.r2_bucket || "vidlocal-prod"}
                  />

                  <SettingsRow
                    label="Trạng Thái Cloudflare R2"
                    icon={<Sliders className="w-4 h-4 text-emerald-400" />}
                    type="info"
                    value="Connected"
                  />
                </div>
              </div>

              {/* AI Settings Group */}
              <div className="space-y-2.5">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Cấu Hình Trí Tuệ Nhân Tạo</h3>
                <div className="space-y-2">
                  <SettingsRow
                    label="Dịch Thuyết Minh / SEO"
                    icon={<BookOpen className="w-4 h-4 text-purple-400" />}
                    type="info"
                    value={systemSettings?.ai_provider || "Gemini 2.5 Flash"}
                  />

                  <SettingsRow
                    label="Whisper Speech-To-Text"
                    icon={<Volume2 className="w-4 h-4 text-blue-400" />}
                    type="info"
                    value={systemSettings?.whisper_model || "Whisper Medium v3"}
                  />

                  <SettingsRow
                    label="TTS Voice Reader"
                    icon={<Volume2 className="w-4 h-4 text-yellow-400" />}
                    type="info"
                    value={systemSettings?.tts_voice || "vi-VN-D (Male)"}
                  />
                </div>
              </div>

              {/* Watermark default config group */}
              <div className="space-y-2.5">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Thiết Lập Video Thành Phẩm</h3>
                <div className="space-y-2">
                  <SettingsRow
                    label="Vị Trí Watermark Logo"
                    icon={<Sliders className="w-4 h-4 text-slate-400" />}
                    type="info"
                    value="Top-Right"
                  />

                  <SettingsRow
                    label="Độ Mờ Watermark Overlay"
                    icon={<Sliders className="w-4 h-4 text-slate-400" />}
                    type="info"
                    value="40% Opacity"
                  />

                  <SettingsRow
                    label="Chế Độ Riêng Tư Mặc Định"
                    icon={<Eye className="w-4 h-4 text-slate-400" />}
                    type="info"
                    value="Private"
                  />
                </div>
              </div>

              {/* BotFather Instructions Panel */}
              <IOSCard className="space-y-2 border-indigo-500/20 bg-indigo-500/[0.02]">
                <h4 className="text-xs font-bold text-indigo-400 flex items-center gap-1.5 uppercase tracking-wide">
                  <BookOpen className="w-4 h-4" />
                  Cách Cấu Hình BotFather Telegram
                </h4>
                <div className="text-[10px] text-slate-400 leading-normal space-y-1">
                  <p>Để admin có thể mở Mini App này trực tiếp từ Bot Telegram, hãy cấu hình theo các bước sau:</p>
                  <ol className="list-decimal list-inside pl-1 space-y-0.5 font-sans">
                    <li>Mở chat với <b>@BotFather</b></li>
                    <li>Gửi lệnh: <code className="text-white bg-white/10 px-1 py-0.5 rounded">/setmenubutton</code></li>
                    <li>Chọn bot tương ứng của bạn</li>
                    <li>Nhập URL Mini App: <code className="text-[#06B6D4] font-bold select-all break-all bg-black/40 px-1 py-0.5 rounded">https://ais-dev-ipdqac6gadkqgdlg2fidnh-268830296337.asia-southeast1.run.app</code></li>
                    <li>Đặt tiều đề nút: <code className="text-white bg-white/10 px-1 py-0.5 rounded">VidLocal Studio</code></li>
                  </ol>
                </div>
              </IOSCard>
            </div>
          )}

          {settingsSubTab === "bot" && (
            <div className="space-y-4 animate-fade-in">
              <BotCenter />
            </div>
          )}

          {settingsSubTab === "queues" && (
            <div className="space-y-4 animate-fade-in">
              <QueueMonitor />
            </div>
          )}

          {settingsSubTab === "files" && (
            <div className="space-y-4 animate-fade-in">
              <FileManager />
            </div>
          )}

          {settingsSubTab === "admin" && (
            <div className="space-y-4 animate-fade-in">
              <AdminPanel />
            </div>
          )}

          {settingsSubTab === "chat" && (
            <div className="space-y-4 animate-fade-in">
              <AiChatAssistant />
            </div>
          )}

          {settingsSubTab === "logs" && (
            <div className="space-y-4 animate-fade-in">
              <div className="flex justify-between items-center px-1">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Real-time system log stream</h3>
                <button
                  onClick={async () => {
                    const logs = await getSystemLogs().catch(() => []);
                    setSystemLogs(logs);
                    setToast({ message: "Đã làm mới nhật ký hệ thống!", type: "success" });
                  }}
                  className="text-[10px] text-purple-400 font-bold flex items-center gap-1 active:scale-95 transition-all"
                >
                  <RefreshCw className="w-3 h-3 text-purple-400" />
                  <span>Tải lại logs</span>
                </button>
              </div>

              <div className="bg-black/50 border border-white/[0.06] rounded-[24px] p-3.5 font-mono text-[10px] leading-relaxed max-h-96 overflow-y-auto space-y-1.5 text-slate-300">
                {systemLogs.map((log, idx) => {
                  let levelColor = "text-blue-400";
                  if (log.level === "ERROR") levelColor = "text-red-400 font-bold";
                  else if (log.level === "WARN") levelColor = "text-yellow-500";
                  else if (log.level === "SUCCESS") levelColor = "text-emerald-400";

                  return (
                    <div key={idx} className="border-b border-white/[0.02] pb-1 last:border-none last:pb-0">
                      <span className="text-slate-500">[{log.time}]</span>{" "}
                      <span className={levelColor}>[{log.level}]</span>{" "}
                      <span className="text-purple-400 font-bold">[{log.section}]</span>{" "}
                      <span className="text-slate-200">{log.message}</span>
                    </div>
                  );
                })}

                {systemLogs.length === 0 && (
                  <p className="text-slate-500 text-center py-8 italic">Chưa có nhật ký ghi nhận.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}


      {/* --- ALL INTERACTIVE SLIDE-UP MODAL SHEETS --- */}

      {/* 1. CHARACTER GLOSSARY REVIEW SHEET */}
      <IOSSheet
        isOpen={isGlossarySheetOpen}
        onClose={() => setIsGlossarySheetOpen(false)}
        title="Duyệt nhân vật Việt hóa"
        subtitle="Vui lòng kiểm tra & sửa từ xưng xô Việt hóa phù hợp cho truyện/video."
      >
        <div id="glossary-sheet-content" className="space-y-4">
          <div className="flex justify-between items-center bg-white/[0.02] border border-white/[0.04] p-3 rounded-2xl">
            <span className="text-xs text-slate-400">Tổng số nhân vật AI phát hiện:</span>
            <span className="text-xs font-bold text-purple-400 font-mono">{draftGlossary.length}</span>
          </div>

          {/* Draft Item Cards */}
          <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
            {draftGlossary.map((entry, idx) => (
              <div key={entry.id} className="relative group">
                <GlossaryItemCard
                  entry={entry}
                  onEdit={() => {
                    setActiveDraftEntry({ ...entry });
                    setIsEditGlossaryEntryOpen(true);
                  }}
                  onDelete={() => handleDeleteDraftEntry(entry.id)}
                />
              </div>
            ))}

            {draftGlossary.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-6">Không có nhân vật nào trong bảng.</p>
            )}
          </div>

          {/* Actions panel */}
          <div className="space-y-2 pt-2 border-t border-white/[0.04]">
            <button
              onClick={handleAddDraftEntry}
              className="w-full bg-white/[0.04] border border-white/[0.08] text-slate-200 hover:text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all"
            >
              <Plus className="w-4 h-4" />
              Thêm nhân vật thủ công
            </button>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={handleSkipGlossary}
                className="bg-white/[0.03] border border-white/[0.08] text-slate-300 font-bold py-3 rounded-2xl text-xs active:scale-95 transition-all"
              >
                Bỏ qua (Skip)
              </button>
              <button
                onClick={handleApproveGlossary}
                className="bg-purple-600 hover:bg-purple-500 text-white font-bold py-3 rounded-2xl text-xs shadow-lg shadow-purple-500/10 active:scale-95 transition-all"
              >
                Duyệt Glossary
              </button>
            </div>
          </div>
        </div>
      </IOSSheet>

      {/* 1A. DETAILED DRAFT GLOSSARY ENTRY EDITOR */}
      <IOSSheet
        isOpen={isEditGlossaryEntryOpen}
        onClose={() => setIsEditGlossaryEntryOpen(false)}
        title={activeDraftEntry?.source_name ? `Sửa: ${activeDraftEntry.source_name}` : "Thêm Nhân Vật"}
      >
        {activeDraftEntry && (
          <div id="glossary-entry-editor" className="space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Tên Tiếng Anh / Gốc</label>
                <input
                  type="text"
                  value={activeDraftEntry.source_name || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, source_name: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Tên Việt Hóa</label>
                <input
                  type="text"
                  value={activeDraftEntry.target_name || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, target_name: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Tên gọi khác / Aliases</label>
                <input
                  type="text"
                  value={activeDraftEntry.aliases || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, aliases: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Vai trò</label>
                <input
                  type="text"
                  value={activeDraftEntry.role || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, role: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Xưng hô</label>
                <input
                  type="text"
                  value={activeDraftEntry.pronoun_style || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, pronoun_style: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2 text-white focus:outline-none focus:border-purple-500/50 font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Giới tính</label>
                <input
                  type="text"
                  value={activeDraftEntry.gender || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, gender: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2 text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-400 font-bold text-[10px] uppercase">Gia tộc</label>
                <input
                  type="text"
                  value={activeDraftEntry.family_clan || ""}
                  onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, family_clan: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2 text-white focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-slate-400 font-bold text-[10px] uppercase">Ghi chú ngữ cảnh</label>
              <textarea
                rows={2}
                value={activeDraftEntry.notes || ""}
                onChange={(e) => setActiveDraftEntry({ ...activeDraftEntry, notes: e.target.value })}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 text-white focus:outline-none"
              />
            </div>

            <button
              onClick={handleSaveDraftEntry}
              className="w-full mt-2 bg-purple-600 hover:bg-purple-500 text-white font-bold py-2.5 rounded-xl"
            >
              Lưu Nhân Vật
            </button>
          </div>
        )}
      </IOSSheet>

      {/* 2. SEO METADATA & YOUTUBE APPROVAL SHEET */}
      <IOSSheet
        isOpen={isMetadataSheetOpen}
        onClose={() => setIsMetadataSheetOpen(false)}
        title={thumbnailMode ? "Thiết Kế Thumbnail AI" : "Duyệt SEO Metadata & YouTube"}
        subtitle={thumbnailMode ? "Nhận ý tưởng gợi ý từ Gemini AI, tự làm ảnh rồi upload duyệt thumbnail tự động." : "Kiểm tra tiêu đề giật gân, mô tả chuẩn SEO do Gemini AI tối ưu tự động."}
      >
        {draftMetadata && thumbnailMode ? (
          <div id="thumbnail-ai-content" className="space-y-4 text-xs">
            {/* Header / Back Action */}
            <div className="flex items-center justify-between border-b border-white/[0.04] pb-2">
              <button
                onClick={() => setThumbnailMode(false)}
                className="flex items-center gap-1 text-[#06B6D4] hover:opacity-80 font-bold"
              >
                <X className="w-4 h-4" /> Về Metadata
              </button>
              <span className="font-bold text-slate-300 uppercase tracking-widest text-[9px] font-mono">VidLocal Thumbnail AI</span>
              <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                thumbnailStatus === "approved" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              }`}>
                {thumbnailStatus || "Chờ Thiết Kế"}
              </span>
            </div>

            {/* Quick Modes Explainer */}
            <div className="bg-white/[0.02] border border-white/[0.06] p-3 rounded-2xl text-[10px] text-slate-400 space-y-1.5">
              <p className="font-bold text-slate-300 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                Hỗ trợ 3 chế độ thiết kế thumbnail chuyên nghiệp:
              </p>
              <ul className="list-disc list-inside space-y-0.5 font-mono text-[9px]">
                <li><span className="text-amber-300 font-bold">Auto Prompt Only</span>: Gemini tự động tạo prompts</li>
                <li><span className="text-cyan-300 font-bold">Upload result</span>: Admin tải ảnh Google Flow / Midjourney lên</li>
                <li><span className="text-purple-300 font-bold">Generate via API</span>: Hạ tầng sẵn sàng tích hợp API tự động</li>
              </ul>
            </div>

            {/* Loading / Prompt Content */}
            {isLoadingPrompts ? (
              <div className="space-y-3 py-4">
                <div className="h-4 bg-white/10 rounded-full w-2/3 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-16 bg-white/5 rounded-2xl animate-pulse" />
                  <div className="h-16 bg-white/5 rounded-2xl animate-pulse" />
                  <div className="h-16 bg-white/5 rounded-2xl animate-pulse" />
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="font-bold text-slate-300">4 Prompt gợi ý từ Gemini AI (Sao chép sang Midjourney / DALL-E):</p>
                <div className="space-y-2">
                  {thumbnailPrompts.length > 0 ? (
                    thumbnailPrompts.map((prompt, idx) => (
                      <div key={idx} className="bg-white/[0.02] border border-white/[0.06] p-3 rounded-2xl space-y-1.5">
                        <div className="flex justify-between items-center">
                          <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider font-mono">Ý tưởng #{idx + 1}</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(prompt);
                              setToast({ message: `Đã copy prompt ý tưởng #${idx + 1}!`, type: "success" });
                            }}
                            className="text-[#06B6D4] hover:underline font-bold text-[10px] flex items-center gap-1"
                          >
                            <Plus className="w-3.5 h-3.5 text-cyan-400" /> Sao chép prompt
                          </button>
                        </div>
                        <p className="text-slate-300 italic text-[11px] leading-relaxed select-all font-mono bg-black/20 p-2 rounded-xl border border-white/[0.04] max-h-24 overflow-y-auto">
                          {prompt}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4 bg-white/[0.02] rounded-2xl text-slate-500">
                      Chưa có prompt nào. Nhấp vào "Tạo prompt" bên dưới để gọi Gemini AI.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Preview Image if Approved/Uploaded */}
            {thumbnailImageUrl && (
              <div className="space-y-1.5">
                <p className="font-bold text-slate-300 flex items-center gap-1">
                  <Eye className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                  👁 Preview ảnh Thumbnail đã tải lên:
                </p>
                <div className="relative aspect-video rounded-2xl overflow-hidden border border-emerald-500/30 bg-black shadow-lg">
                  <img
                    src={thumbnailImageUrl}
                    alt="Thumbnail Preview"
                    referrerPolicy="no-referrer"
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute top-2 right-2 bg-emerald-600 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                    APPROVED
                  </div>
                </div>
              </div>
            )}

            {/* Actions Panel */}
            <div className="space-y-2 pt-3 border-t border-white/[0.04]">
              <div className="grid grid-cols-2 gap-2">
                {/* Upload Action */}
                <label className="flex items-center justify-center gap-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-extrabold py-3 px-1.5 rounded-2xl text-xs text-center cursor-pointer active:scale-95 transition-all shadow-md">
                  <Plus className="w-4 h-4" />
                  Upload Image
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleUploadThumbnailFile(e.target.files[0]);
                      }
                    }}
                    className="hidden"
                  />
                </label>

                {/* Regenerate Action */}
                <button
                  onClick={() => handleFetchThumbnailPrompts(true)}
                  className="bg-white/[0.04] border border-white/[0.08] text-amber-400 hover:bg-amber-500/10 font-bold py-3 rounded-2xl text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all"
                >
                  <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />
                  Regenerate Prompts
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {/* Skip Action */}
                <button
                  onClick={handleSkipThumbnailAction}
                  className="bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 font-bold py-3 rounded-2xl text-xs active:scale-95 transition-all"
                >
                  Skip Thumbnail
                </button>

                {/* Back to Metadata editing */}
                <button
                  onClick={() => setThumbnailMode(false)}
                  className="bg-white/[0.05] text-slate-300 font-bold py-3 rounded-2xl text-xs hover:bg-white/10 active:scale-95 transition-all"
                >
                  Back to Metadata
                </button>
              </div>
            </div>
          </div>
        ) : draftMetadata ? (
          <div id="metadata-sheet-content" className="space-y-4 text-xs">
            {/* Risk Warnings */}
            {activeJob?.metadata?.risk_flags && activeJob.metadata.risk_flags.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/20 p-2.5 rounded-2xl space-y-1">
                <p className="text-[10px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                  Cảnh báo bản quyền & nội dung
                </p>
                <div className="flex gap-1 flex-wrap">
                  {activeJob.metadata.risk_flags.map((flag, fidx) => (
                    <RiskFlagBadge key={fidx} flag={flag} />
                  ))}
                </div>
              </div>
            )}

            {/* Editable Title */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <span>Tiêu đề YouTube (Tối đa 90 ký tự)</span>
                <span className={draftMetadata.title.length > 90 ? "text-red-400 font-bold" : "text-slate-500"}>
                  {draftMetadata.title.length}/90
                </span>
              </div>
              <input
                type="text"
                value={draftMetadata.title}
                onChange={(e) => setDraftMetadata({ ...draftMetadata, title: e.target.value })}
                className="w-full bg-white/[0.03] border border-white/[0.08] focus:border-purple-500/50 rounded-xl p-3 text-xs font-bold text-white placeholder-slate-500 focus:outline-none transition-all"
              />
            </div>

            {/* Editable Description */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Mô tả chi tiết video</label>
              <textarea
                rows={4}
                value={draftMetadata.description}
                onChange={(e) => setDraftMetadata({ ...draftMetadata, description: e.target.value })}
                className="w-full bg-white/[0.03] border border-white/[0.08] focus:border-purple-500/50 rounded-xl p-3 text-xs font-medium text-slate-300 placeholder-slate-500 focus:outline-none transition-all leading-relaxed"
              />
            </div>

            {/* Tags & Hashtags inputs */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Từ khóa Tags</label>
                <input
                  type="text"
                  value={draftMetadata.tags}
                  onChange={(e) => setDraftMetadata({ ...draftMetadata, tags: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2 text-white placeholder-slate-500 text-xs font-medium focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Hashtags</label>
                <input
                  type="text"
                  value={draftMetadata.hashtags}
                  onChange={(e) => setDraftMetadata({ ...draftMetadata, hashtags: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-2 text-white placeholder-slate-500 text-xs font-medium focus:outline-none"
                />
              </div>
            </div>

            {/* Segment Privacy Selection */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Chế độ hiển thị YouTube</label>
              <div className="grid grid-cols-3 gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.05]">
                {["private", "unlisted", "public"].map((priv: any) => (
                  <button
                    key={priv}
                    type="button"
                    onClick={() => setDraftMetadata({ ...draftMetadata, privacy: priv })}
                    className={`py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${
                      draftMetadata.privacy === priv
                        ? "bg-[#06B6D4] text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {priv}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions fixed buttons */}
            <div className="space-y-2 pt-2 border-t border-white/[0.04]">
              {/* 🎨 AI THUMBNAIL LAUNCHER */}
              <button
                onClick={() => {
                  setThumbnailMode(true);
                  if (thumbnailPrompts.length === 0) {
                    handleFetchThumbnailPrompts(false);
                  }
                }}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-600 text-white font-extrabold py-3 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all shadow-md shadow-orange-500/10 hover:opacity-90 active:scale-95"
              >
                <Sparkles className="w-4 h-4 text-amber-200" />
                Thiết Kế 🎨 Thumbnail AI {thumbnailStatus === "approved" ? " (Đã Duyệt)" : thumbnailStatus === "skipped" ? " (Đã Bỏ Qua)" : ""}
              </button>

              <button
                onClick={handleRegenerateMetadata}
                className="w-full bg-white/[0.04] border border-white/[0.08] text-cyan-400 hover:bg-cyan-500/10 font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />
                Gemini AI Tối Ưu Lại Thẻ SEO
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setIsMetadataSheetOpen(false)}
                  className="bg-white/[0.03] border border-white/[0.08] text-slate-300 font-bold py-3 rounded-2xl text-xs active:scale-95 transition-all"
                >
                  Hủy bỏ
                </button>
                <button
                  onClick={() => setIsConfirmUploadOpen(true)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-2xl text-xs shadow-lg shadow-emerald-500/10 active:scale-95 transition-all"
                >
                  Xác Nhận Đăng YouTube
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </IOSSheet>

      {/* 2A. EXTRA UPLOAD CONFIRMATION SHEET */}
      <IOSSheet
        isOpen={isConfirmUploadOpen}
        onClose={() => setIsConfirmUploadOpen(false)}
        title="Xác nhận tải video lên YouTube"
        subtitle="Đây là bước cuối cùng của pipeline VidLocal tự động."
      >
        <div id="confirm-upload-content" className="space-y-4 text-xs">
          <div className="bg-emerald-500/5 border border-emerald-500/20 p-4 rounded-3xl space-y-2 text-slate-300">
            <p><b>Video sẽ được đăng tải với các thông số sau:</b></p>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-400">
              <li>Tiêu đề: <span className="text-white">“{draftMetadata?.title}”</span></li>
              <li>Chế độ hiển thị: <span className="text-[#06B6D4] font-bold uppercase">{draftMetadata?.privacy}</span></li>
              <li>Watermark: <span className="text-white">Có chèn (Top-Right)</span></li>
              <li>Xử lý dọn dẹp: <span className="text-white">Tự động sau 7 ngày</span></li>
            </ul>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2">
            <button
              onClick={() => setIsConfirmUploadOpen(false)}
              className="bg-white/[0.03] border border-white/[0.08] text-slate-300 font-bold py-3 rounded-2xl text-xs active:scale-95 transition-all"
            >
              Hủy
            </button>
            <button
              onClick={handleApproveUpload}
              className="bg-[#7C3AED] hover:bg-purple-600 text-white font-bold py-3 rounded-2xl text-xs shadow-lg shadow-purple-500/20 active:scale-95 transition-all"
            >
              Đồng Ý Đăng Tải!
            </button>
          </div>
        </div>
      </IOSSheet>

      {/* 3. ADD NEW PROJECT SHEET */}
      <IOSSheet
        isOpen={isAddProjSheetOpen}
        onClose={() => setIsAddProjSheetOpen(false)}
        title="Tạo dự án dịch / lồng tiếng cũ mới"
        subtitle="Tạo một folder dự án dịch phụ đề và TTS truyền thống."
      >
        <div id="add-project-form" className="space-y-4 text-xs">
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Tên dự án dịch</label>
            <input
              type="text"
              required
              placeholder="Ví dụ: Review Marvel Phân Cảnh Thuyết Minh..."
              value={newProjName}
              onChange={(e) => setNewProjName(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.08] focus:border-purple-500/50 rounded-2xl py-3 px-4 text-xs font-bold text-white placeholder-slate-500 focus:outline-none transition-all"
            />
          </div>

          <button
            onClick={handleCreateProject}
            className="w-full bg-gradient-to-r from-purple-600 to-[#7C3AED] hover:from-purple-500 hover:to-purple-600 text-white font-extrabold py-3 rounded-2xl text-xs shadow-lg shadow-purple-500/20 active:scale-95 transition-all"
          >
            Khởi Tạo Dự Án
          </button>
        </div>
      </IOSSheet>
    </AppShell>
  );
}
