import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
app.use(express.json());

const PORT = 3000;

// Type Definitions for In-Memory Database
interface GlossaryEntry {
  id: string;
  source_name: string;
  target_name: string;
  aliases: string;
  role: string;
  gender: string;
  family_clan?: string;
  pronoun_style: string;
  notes: string;
  project_id?: string;
}

interface SEOMetadata {
  title: string;
  description: string;
  tags: string[];
  hashtags: string[];
  category: string;
  summary: string;
  hook: string;
  risk_flags: string[];
  privacy: "private" | "unlisted" | "public";
  scheduled_time?: string;
}

interface VideoJob {
  id: string;
  platform: "Facebook" | "TikTok";
  url: string;
  title: string;
  status: "pending" | "downloading" | "transcribing" | "waiting_approval" | "approved" | "completed" | "failed";
  progress: number;
  created_time: string;
  youtube_url?: string;
  current_step: "download" | "transcribe" | "character_extract" | "glossary_review" | "seo_metadata" | "watermark" | "upload" | "done";
  steps: {
    download: { status: "pending" | "running" | "completed" | "failed"; progress: number };
    transcribe: { status: "pending" | "running" | "completed" | "failed"; progress: number };
    character_extract: { status: "pending" | "running" | "completed" | "failed"; progress: number };
    glossary_review: { status: "pending" | "running" | "completed" | "failed"; progress: number };
    seo_metadata: { status: "pending" | "running" | "completed" | "failed"; progress: number };
    watermark: { status: "pending" | "running" | "completed" | "failed"; progress: number };
    upload: { status: "pending" | "running" | "completed" | "failed"; progress: number };
  };
  transcript?: string;
  glossary?: GlossaryEntry[];
  metadata?: SEOMetadata;
  files: { name: string; size: string; type: string }[];
  logs: { time: string; level: "info" | "warn" | "error"; message: string }[];
  options: {
    extract_characters: boolean;
    generate_seo: boolean;
    add_watermark: boolean;
    upload_privacy: "private" | "unlisted" | "public";
    enable_dubbing: boolean;
  };
}

interface Project {
  id: string;
  name: string;
  status: "pending" | "transcribing" | "translating" | "tts" | "rendering" | "published" | "failed";
  video_count: number;
  created_time: string;
  current_step: "upload" | "transcribe" | "translate" | "tts" | "render" | "publish" | "done";
  steps: {
    upload: "pending" | "completed" | "failed";
    transcribe: "pending" | "running" | "completed" | "failed";
    translate: "pending" | "running" | "completed" | "failed";
    tts: "pending" | "running" | "completed" | "failed";
    render: "pending" | "running" | "completed" | "failed";
    publish: "pending" | "running" | "completed" | "failed";
  };
}

// Initial Seeds
let globalGlossary: GlossaryEntry[] = [
  {
    id: "g-1",
    source_name: "Tony Stark",
    target_name: "Đông Ni",
    aliases: "Iron Man, Stark",
    role: "Main Character",
    gender: "Male",
    family_clan: "Stark Clan",
    pronoun_style: "Humble/Arrogant Mix",
    notes: "Sarcastic billionaire, keeps Vietnam localized tone of 'Ta' or 'Tôi'.",
    project_id: "p-1"
  },
  {
    id: "g-2",
    source_name: "Bruce Banner",
    target_name: "Bạch Nhân",
    aliases: "Hulk, Bruce",
    role: "Supporting Character",
    gender: "Male",
    pronoun_style: "Polite/Fearful",
    notes: "Localize as 'Anh' or 'Cậu'.",
    project_id: "p-1"
  },
  {
    id: "g-3",
    source_name: "Natasha Romanoff",
    target_name: "Na Sa",
    aliases: "Black Widow, Nat",
    role: "Supporting Character",
    gender: "Female",
    pronoun_style: "Seductive/Confident",
    notes: "Direct localize as 'Cô' or 'Chị'.",
  }
];

let videoJobs: VideoJob[] = [
  {
    id: "job-1",
    platform: "Facebook",
    url: "https://facebook.com/watch/?v=10238471294829",
    title: "Review Iron Man 1: The Beginning of Marvel Cinematic Universe",
    status: "waiting_approval",
    progress: 50,
    created_time: new Date(Date.now() - 3600000 * 2).toISOString(), // 2 hours ago
    current_step: "glossary_review",
    steps: {
      download: { status: "completed", progress: 100 },
      transcribe: { status: "completed", progress: 100 },
      character_extract: { status: "completed", progress: 100 },
      glossary_review: { status: "running", progress: 50 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 },
    },
    transcript: "[00:05] Hello everyone, today we review Iron Man. Tony Stark is captured in Afghanistan. He builds an armor suit... [01:30] He returns and announces he is Iron Man. This starts the Marvel Era...",
    glossary: [
      {
        id: "g-j1-1",
        source_name: "Tony Stark",
        target_name: "Đông Ni",
        aliases: "Iron Man",
        role: "Protagonist",
        gender: "Male",
        family_clan: "Stark Enterprise",
        pronoun_style: "Tớ / Tôi",
        notes: "Rich kid of VidLocal universe."
      },
      {
        id: "g-j1-2",
        source_name: "Obadiah Stane",
        target_name: "Ô Ba",
        aliases: "Iron Monger",
        role: "Antagonist",
        gender: "Male",
        family_clan: "None",
        pronoun_style: "Lão / Ta",
        notes: "Traitor."
      }
    ],
    metadata: {
      title: "Review Iron Man Thuyết Minh Việt Hoá | Đông Ni Đại Chiến Ô Ba",
      description: "Xem lại siêu phẩm Iron Man 1 thuyết minh Việt hoá cực chất. Tony Stark từ tỷ phú vũ khí trở thành siêu anh hùng cứu thế giới.",
      tags: ["iron man", "review phim", "thuyet minh", "marvel viet hoa"],
      hashtags: ["#ironman", "#reviewphim", "#marvel", "#vidlocal"],
      category: "Entertainment",
      summary: "Tóm tắt phim Iron Man 1 thuyết minh mới.",
      hook: "Bắt đầu kỷ nguyên siêu anh hùng đỉnh cao!",
      risk_flags: ["Bạo lực nhẹ", "Bản quyền âm nhạc"],
      privacy: "private"
    },
    files: [
      { name: "source_video.mp4", size: "145 MB", type: "Video" },
      { name: "audio_clean.wav", size: "18 MB", type: "Audio" },
      { name: "transcript_vi.srt", size: "12 KB", type: "Subtitles" }
    ],
    logs: [
      { time: new Date(Date.now() - 7200000).toISOString(), level: "info", message: "Job created." },
      { time: new Date(Date.now() - 7000000).toISOString(), level: "info", message: "Downloading video via yt-dlp..." },
      { time: new Date(Date.now() - 6500000).toISOString(), level: "info", message: "Download completed successfully." },
      { time: new Date(Date.now() - 6400000).toISOString(), level: "info", message: "Whisper Transcription started." },
      { time: new Date(Date.now() - 5000000).toISOString(), level: "info", message: "Whisper Transcription completed." },
      { time: new Date(Date.now() - 4900000).toISOString(), level: "info", message: "AI Character Extraction started." },
      { time: new Date(Date.now() - 4000000).toISOString(), level: "info", message: "AI Character Extraction completed. 2 characters detected." },
      { time: new Date(Date.now() - 3900000).toISOString(), level: "warn", message: "Waiting for Admin to approve glossary." }
    ],
    options: {
      extract_characters: true,
      generate_seo: true,
      add_watermark: true,
      upload_privacy: "private",
      enable_dubbing: true
    }
  },
  {
    id: "job-2",
    platform: "TikTok",
    url: "https://tiktok.com/@vidlocal_channel/video/7392847129",
    title: "Top 5 Mẹo Học Code Cực Nhanh Cho Người Mới Bắt Đầu",
    status: "waiting_approval",
    progress: 75,
    created_time: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    current_step: "seo_metadata",
    steps: {
      download: { status: "completed", progress: 100 },
      transcribe: { status: "completed", progress: 100 },
      character_extract: { status: "completed", progress: 100 },
      glossary_review: { status: "completed", progress: 100 },
      seo_metadata: { status: "running", progress: 50 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 },
    },
    transcript: "[00:01] Hello mọi người, hôm nay mình chia sẻ 5 mẹo học code cực chất... Mẹo 1: Đừng đọc sách chay. Mẹo 2: Thực hành ngay... Mẹo 5: Đừng nản lòng!",
    glossary: [],
    metadata: {
      title: "5 Mẹo Học Lập Trình Siêu Nhanh Năm 2026",
      description: "Bí quyết tự học lập trình hiệu quả cho người mới bắt đầu. Không cần bằng cấp vẫn có thể master coding.",
      tags: ["hoc lap trinh", "tu hoc code", "developer tips", "tiktok coding"],
      hashtags: ["#code", "#developer", "#shorts", "#vidlocal"],
      category: "Education",
      summary: "Hướng dẫn tự học lập trình.",
      hook: "Học code chưa bao giờ dễ thế!",
      risk_flags: [],
      privacy: "unlisted"
    },
    files: [
      { name: "tiktok_source.mp4", size: "42 MB", type: "Video" },
      { name: "audio.wav", size: "4 MB", type: "Audio" }
    ],
    logs: [
      { time: new Date(Date.now() - 3600000).toISOString(), level: "info", message: "TikTok download started." },
      { time: new Date(Date.now() - 3400000).toISOString(), level: "info", message: "Download done." },
      { time: new Date(Date.now() - 3200000).toISOString(), level: "info", message: "Transcription finished." },
      { time: new Date(Date.now() - 3100000).toISOString(), level: "info", message: "Glossary approved or skipped." },
      { time: new Date(Date.now() - 3000000).toISOString(), level: "info", message: "Gemini generating SEO metadata..." },
      { time: new Date(Date.now() - 2900000).toISOString(), level: "warn", message: "Waiting for Admin metadata review & upload approval." }
    ],
    options: {
      extract_characters: false,
      generate_seo: true,
      add_watermark: true,
      upload_privacy: "unlisted",
      enable_dubbing: false
    }
  },
  {
    id: "job-3",
    platform: "Facebook",
    url: "https://facebook.com/reel/9284712984129",
    title: "Kỹ năng sinh tồn nơi hoang dã cực kỳ quan trọng",
    status: "downloading",
    progress: 45,
    created_time: new Date().toISOString(),
    current_step: "download",
    steps: {
      download: { status: "running", progress: 45 },
      transcribe: { status: "pending", progress: 0 },
      character_extract: { status: "pending", progress: 0 },
      glossary_review: { status: "pending", progress: 0 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 },
    },
    files: [],
    logs: [
      { time: new Date().toISOString(), level: "info", message: "Job created and queued." },
      { time: new Date().toISOString(), level: "info", message: "yt-dlp command executed: downloading FB video." }
    ],
    options: {
      extract_characters: true,
      generate_seo: true,
      add_watermark: true,
      upload_privacy: "private",
      enable_dubbing: false
    }
  },
  {
    id: "job-4",
    platform: "TikTok",
    url: "https://tiktok.com/@cooking_vn/video/98374284",
    title: "Cách làm món sườn xào chua ngọt chuẩn vị nhà hàng",
    status: "transcribing",
    progress: 30,
    created_time: new Date(Date.now() - 600000).toISOString(), // 10 mins ago
    current_step: "transcribe",
    steps: {
      download: { status: "completed", progress: 100 },
      transcribe: { status: "running", progress: 30 },
      character_extract: { status: "pending", progress: 0 },
      glossary_review: { status: "pending", progress: 0 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 },
    },
    files: [
      { name: "suon_xao.mp4", size: "31 MB", type: "Video" },
      { name: "extracted_audio.wav", size: "3.2 MB", type: "Audio" }
    ],
    logs: [
      { time: new Date(Date.now() - 600000).toISOString(), level: "info", message: "TikTok downloaded." },
      { time: new Date(Date.now() - 550000).toISOString(), level: "info", message: "Running Whisper base model on CPU/GPU." }
    ],
    options: {
      extract_characters: false,
      generate_seo: true,
      add_watermark: false,
      upload_privacy: "private",
      enable_dubbing: false
    }
  },
  {
    id: "job-5",
    platform: "Facebook",
    url: "https://facebook.com/watch/?v=981273948",
    title: "Review Phim Oppenheimer - Cha Đẻ Bom Nguyên Tử",
    status: "completed",
    progress: 100,
    created_time: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    current_step: "done",
    steps: {
      download: { status: "completed", progress: 100 },
      transcribe: { status: "completed", progress: 100 },
      character_extract: { status: "completed", progress: 100 },
      glossary_review: { status: "completed", progress: 100 },
      seo_metadata: { status: "completed", progress: 100 },
      watermark: { status: "completed", progress: 100 },
      upload: { status: "completed", progress: 100 },
    },
    youtube_url: "https://youtube.com/watch?v=dQw4w9WgXcQ",
    transcript: "Oppenheimer thuyết minh hoàn chỉnh...",
    glossary: [
      {
        id: "g-j5-1",
        source_name: "J. Robert Oppenheimer",
        target_name: "Thần Oai",
        aliases: "Oppie",
        role: "Protagonist",
        gender: "Male",
        pronoun_style: "Tôi",
        notes: "Scientific genius."
      }
    ],
    metadata: {
      title: "Review Oppenheimer Thuyết Minh Việt Hoá Siêu Đỉnh",
      description: "Xem Oppenheimer tóm tắt phim Việt hoá. Khám phá cuộc đời đầy thăng trầm của cha đẻ bom nguyên tử.",
      tags: ["oppenheimer", "tom tat phim", "review phim", "bom nguyen tu"],
      hashtags: ["#oppenheimer", "#reviewphim", "#shorts", "#vidlocal"],
      category: "Entertainment",
      summary: "Tóm tắt phim Oppenheimer.",
      hook: "Kẻ hủy diệt thế giới!",
      risk_flags: [],
      privacy: "private"
    },
    files: [
      { name: "oppenheimer_src.mp4", size: "298 MB", type: "Video" },
      { name: "oppenheimer_rendered.mp4", size: "320 MB", type: "Video" }
    ],
    logs: [
      { time: new Date(Date.now() - 86400000).toISOString(), level: "info", message: "Job created." },
      { time: new Date(Date.now() - 85000000).toISOString(), level: "info", message: "Pipeline finished. Successfully uploaded to YouTube." }
    ],
    options: {
      extract_characters: true,
      generate_seo: true,
      add_watermark: true,
      upload_privacy: "private",
      enable_dubbing: true
    }
  },
  {
    id: "job-6",
    platform: "TikTok",
    url: "https://tiktok.com/@fail_user/video/392847",
    title: "Hài hước động vật ngộ nghĩnh cười ra nước mắt",
    status: "failed",
    progress: 10,
    created_time: new Date(Date.now() - 1200000).toISOString(), // 20 mins ago
    current_step: "download",
    steps: {
      download: { status: "failed", progress: 10 },
      transcribe: { status: "pending", progress: 0 },
      character_extract: { status: "pending", progress: 0 },
      glossary_review: { status: "pending", progress: 0 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 },
    },
    files: [],
    logs: [
      { time: new Date(Date.now() - 1200000).toISOString(), level: "info", message: "Job created." },
      { time: new Date(Date.now() - 1100000).toISOString(), level: "error", message: "yt-dlp failed: Sign in to confirm you are not a bot. Private / restricted video." }
    ],
    options: {
      extract_characters: false,
      generate_seo: true,
      add_watermark: false,
      upload_privacy: "private",
      enable_dubbing: false
    }
  }
];

let projects: Project[] = [
  {
    id: "p-1",
    name: "Marvel Cinematic Việt Hoá",
    status: "translating",
    video_count: 14,
    created_time: new Date(Date.now() - 86400000 * 5).toISOString(), // 5 days ago
    current_step: "translate",
    steps: {
      upload: "completed",
      transcribe: "completed",
      translate: "running",
      tts: "pending",
      render: "pending",
      publish: "pending"
    }
  },
  {
    id: "p-2",
    name: "Học Lập Trình Cơ Bản 2026",
    status: "published",
    video_count: 8,
    created_time: new Date(Date.now() - 86400000 * 10).toISOString(), // 10 days ago
    current_step: "done",
    steps: {
      upload: "completed",
      transcribe: "completed",
      translate: "completed",
      tts: "completed",
      render: "completed",
      publish: "completed"
    }
  }
];

let systemSettings = {
  youtube_connected: true,
  youtube_account: "VidLocal Studio Admin (admin@vidlocal.io)",
  r2_status: "connected",
  r2_bucket: "vidlocal-assets-prod",
  ai_provider: "Gemini 2.5 Flash",
  whisper_model: "Whisper Medium (v3)",
  watermark_config: "Top-Right, 40% Opacity, Custom Image Logo",
  tts_voice: "vi-VN-Wavenet-D (Male)",
  default_privacy: "private",
  cleanup_retention: "7 Days"
};

// SSE Active Clients Tracker
let sseClients: any[] = [];

// Broadcast helper
function broadcastJobsUpdate() {
  const data = JSON.stringify(videoJobs);
  sseClients.forEach(client => {
    try {
      client.write(`data: ${data}\n\n`);
    } catch (e) {
      console.error("Error writing to SSE client", e);
    }
  });
}

// Simulated Background Worker
// This advances jobs in "downloading" or "transcribing" state to simulate a live pipeline.
setInterval(() => {
  const hasActiveJobs = videoJobs.some(job => job.status === "downloading" || job.status === "transcribing");
  if (!hasActiveJobs) return;

  videoJobs = videoJobs.map(job => {
    if (job.status === "downloading") {
      const nextProgress = Math.min(job.progress + 15, 100);
      const isDone = nextProgress === 100;
      return {
        ...job,
        progress: isDone ? 100 : nextProgress,
        status: isDone ? "transcribing" : "downloading",
        current_step: isDone ? "transcribe" : "download",
        steps: {
          ...job.steps,
          download: { status: isDone ? "completed" : "running", progress: nextProgress },
          transcribe: { status: isDone ? "running" : "pending", progress: isDone ? 10 : 0 }
        },
        logs: [
          ...job.logs,
          {
            time: new Date().toISOString(),
            level: "info",
            message: isDone 
              ? "Download completed. Triggering Whisper speech-to-text transcription." 
              : `Downloading via yt-dlp... ${nextProgress}%`
          }
        ]
      };
    } else if (job.status === "transcribing") {
      const nextProgress = Math.min(job.progress + 12, 100);
      const isDone = nextProgress === 100;
      return {
        ...job,
        progress: isDone ? 50 : nextProgress,
        status: isDone ? "waiting_approval" : "transcribing",
        current_step: isDone ? "glossary_review" : "transcribe",
        steps: {
          ...job.steps,
          transcribe: { status: isDone ? "completed" : "running", progress: isDone ? 100 : nextProgress },
          character_extract: { status: isDone ? "completed" : "pending", progress: isDone ? 100 : 0 },
          glossary_review: { status: isDone ? "running" : "pending", progress: isDone ? 50 : 0 }
        },
        transcript: isDone ? "Transcribed audio content: Xin chào quý vị và các bạn, hôm nay chúng ta sẽ tiếp tục..." : job.transcript,
        glossary: isDone ? [
          {
            id: `g-gen-${Date.now()}`,
            source_name: "John Doe",
            target_name: "Dân Thường",
            aliases: "John, Doe",
            role: "Narrator / Secondary",
            gender: "Male",
            pronoun_style: "Tôi",
            notes: "AI Detected"
          }
        ] : job.glossary,
        logs: [
          ...job.logs,
          {
            time: new Date().toISOString(),
            level: "info",
            message: isDone 
              ? "Transcription & AI Character extraction completed. Waiting for admin approval." 
              : `Transcribing audio to text... ${nextProgress}%`
          }
        ]
      };
    }
    return job;
  });

  // Broadcast the update automatically to all listening SSE clients!
  broadcastJobsUpdate();
}, 8000);

// Lazy Initialize Gemini AI
let aiClient: GoogleGenAI | null = null;
function getAI() {
  if (!aiClient) {
    const key = process.env.GEMINI_API_KEY;
    if (!key || key === "MY_GEMINI_API_KEY") {
      console.log("No valid GEMINI_API_KEY found. Utilizing high-fidelity simulated AI.");
      return null;
    }
    aiClient = new GoogleGenAI({ apiKey: key });
  }
  return aiClient;
}

// 1. Video Jobs Endpoints
app.get("/api/jobs", (req, res) => {
  res.json(videoJobs);
});

app.get("/api/jobs/stream", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  
  // Send initial data immediately
  res.write(`data: ${JSON.stringify(videoJobs)}\n\n`);
  
  sseClients.push(res);
  
  req.on("close", () => {
    sseClients = sseClients.filter(client => client !== res);
  });
});

app.get("/api/facebook-to-youtube", (req, res) => {
  const fbJobs = videoJobs.filter(j => j.platform === "Facebook");
  res.json(fbJobs);
});

app.get("/api/tiktok-to-youtube", (req, res) => {
  const ttJobs = videoJobs.filter(j => j.platform === "TikTok");
  res.json(ttJobs);
});

app.get("/api/facebook-to-youtube/:id", (req, res) => {
  const job = videoJobs.find(j => j.id === req.params.id);
  if (job) {
    res.json(job);
  } else {
    res.status(404).json({ error: "Job not found" });
  }
});

app.get("/api/tiktok-to-youtube/:id", (req, res) => {
  const job = videoJobs.find(j => j.id === req.params.id);
  if (job) {
    res.json(job);
  } else {
    res.status(404).json({ error: "Job not found" });
  }
});

app.get("/api/jobs/:id", (req, res) => {
  const job = videoJobs.find(j => j.id === req.params.id);
  if (job) {
    res.json(job);
  } else {
    res.status(404).json({ error: "Job not found" });
  }
});

app.post("/api/facebook-to-youtube", (req, res) => {
  const { url, options, title } = req.body;
  if (!url) {
    return res.status(400).json({ error: "URL is required" });
  }

  const newJob: VideoJob = {
    id: `job-${Date.now()}`,
    platform: "Facebook",
    url: url,
    title: title || `Facebook Video Job - ${new Date().toLocaleTimeString()}`,
    status: "downloading",
    progress: 10,
    created_time: new Date().toISOString(),
    current_step: "download",
    steps: {
      download: { status: "running", progress: 10 },
      transcribe: { status: "pending", progress: 0 },
      character_extract: { status: "pending", progress: 0 },
      glossary_review: { status: "pending", progress: 0 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 }
    },
    files: [],
    logs: [
      { time: new Date().toISOString(), level: "info", message: "Job created from Telegram Mini App." },
      { time: new Date().toISOString(), level: "info", message: "Starting yt-dlp downloader task." }
    ],
    options: {
      extract_characters: options?.extract_characters ?? true,
      generate_seo: options?.generate_seo ?? true,
      add_watermark: options?.add_watermark ?? true,
      upload_privacy: options?.upload_privacy ?? "private",
      enable_dubbing: options?.enable_dubbing ?? false
    }
  };

  videoJobs.unshift(newJob);
  broadcastJobsUpdate();
  res.status(201).json(newJob);
});

app.post("/api/tiktok-to-youtube", (req, res) => {
  const { url, options, title } = req.body;
  if (!url) {
    return res.status(400).json({ error: "URL is required" });
  }

  const newJob: VideoJob = {
    id: `job-${Date.now()}`,
    platform: "TikTok",
    url: url,
    title: title || `TikTok Video Job - ${new Date().toLocaleTimeString()}`,
    status: "downloading",
    progress: 10,
    created_time: new Date().toISOString(),
    current_step: "download",
    steps: {
      download: { status: "running", progress: 10 },
      transcribe: { status: "pending", progress: 0 },
      character_extract: { status: "pending", progress: 0 },
      glossary_review: { status: "pending", progress: 0 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 }
    },
    files: [],
    logs: [
      { time: new Date().toISOString(), level: "info", message: "Job created from Telegram Mini App." },
      { time: new Date().toISOString(), level: "info", message: "Starting yt-dlp downloader task." }
    ],
    options: {
      extract_characters: options?.extract_characters ?? true,
      generate_seo: options?.generate_seo ?? true,
      add_watermark: options?.add_watermark ?? true,
      upload_privacy: options?.upload_privacy ?? "private",
      enable_dubbing: options?.enable_dubbing ?? false
    }
  };

  videoJobs.unshift(newJob);
  broadcastJobsUpdate();
  res.status(201).json(newJob);
});

// Job action: Approve Glossary
app.post("/api/video-jobs/:id/approve-glossary", (req, res) => {
  const { glossary } = req.body;
  const jobIndex = videoJobs.findIndex(j => j.id === req.params.id);
  if (jobIndex === -1) {
    return res.status(404).json({ error: "Job not found" });
  }

  const job = videoJobs[jobIndex];
  // Advance to SEO metadata generation
  const updatedJob: VideoJob = {
    ...job,
    glossary: glossary || job.glossary,
    current_step: "seo_metadata",
    progress: 75,
    steps: {
      ...job.steps,
      glossary_review: { status: "completed", progress: 100 },
      seo_metadata: { status: "running", progress: 50 }
    },
    logs: [
      ...job.logs,
      { time: new Date().toISOString(), level: "info", message: "Admin approved AI glossary." },
      { time: new Date().toISOString(), level: "info", message: "Starting Gemini AI SEO Metadata generation." }
    ]
  };

  videoJobs[jobIndex] = updatedJob;
  broadcastJobsUpdate();
  res.json(updatedJob);
});

// Job action: Skip Glossary
app.post("/api/video-jobs/:id/skip-glossary", (req, res) => {
  const jobIndex = videoJobs.findIndex(j => j.id === req.params.id);
  if (jobIndex === -1) {
    return res.status(404).json({ error: "Job not found" });
  }

  const job = videoJobs[jobIndex];
  const updatedJob: VideoJob = {
    ...job,
    current_step: "seo_metadata",
    progress: 75,
    steps: {
      ...job.steps,
      glossary_review: { status: "completed", progress: 100 },
      seo_metadata: { status: "running", progress: 50 }
    },
    logs: [
      ...job.logs,
      { time: new Date().toISOString(), level: "info", message: "Admin skipped glossary review." },
      { time: new Date().toISOString(), level: "info", message: "Proceeding immediately to SEO Metadata generation." }
    ]
  };

  videoJobs[jobIndex] = updatedJob;
  broadcastJobsUpdate();
  res.json(updatedJob);
});

// Job action: Regenerate SEO Metadata using real Gemini SDK
app.post("/api/video-jobs/:id/regenerate-metadata", async (req, res) => {
  const jobIndex = videoJobs.findIndex(j => j.id === req.params.id);
  if (jobIndex === -1) {
    return res.status(404).json({ error: "Job not found" });
  }

  const job = videoJobs[jobIndex];
  let generatedMetadata: SEOMetadata = {
    title: `[REGEN] Review ${job.title} | VidLocal Special Edit`,
    description: `Xem video hấp dẫn ${job.title} phiên bản tối ưu hóa chuẩn SEO của VidLocal Studio. Đăng ký kênh để không bỏ lỡ!`,
    tags: ["review phim", "vidlocal video", "trending", "youtube short"],
    hashtags: ["#review", "#trending", "#vidlocal"],
    category: "Entertainment",
    summary: "Nội dung phim thuyết minh Việt hóa.",
    hook: "Kịch tính đến giây cuối cùng!",
    risk_flags: [],
    privacy: job.metadata?.privacy || "private"
  };

  try {
    const ai = getAI();
    if (ai) {
      const prompt = `Bạn là một chuyên gia SEO YouTube cho hệ thống VidLocal. 
Hãy viết lại siêu dữ liệu (SEO Metadata) chuẩn tối ưu hóa YouTube cho video có tiêu đề gốc: "${job.title}".
Dựa vào bản dịch text: "${job.transcript || 'Không có bản dịch'}" và thông tin nhân vật: "${JSON.stringify(job.glossary || [])}".

Trả về DUY NHẤT một mã JSON có cấu trúc chính xác như sau:
{
  "title": "Tiêu đề tiếng Việt cực kỳ giật gân, cuốn hút, tối đa 90 ký tự",
  "description": "Mô tả chi tiết, sinh động, chèn từ khóa tự nhiên, kèm lời kêu gọi subscribe",
  "tags": ["tag1", "tag2", "tag3"],
  "hashtags": ["#ht1", "#ht2"],
  "category": "Entertainment hoặc Film & Animation",
  "summary": "Tóm tắt ngắn gọn cốt truyện",
  "hook": "Câu kêu gọi/mở đầu lôi cuốn nhất",
  "risk_flags": ["Cảnh báo bản quyền âm nhạc hoặc bạo lực nếu có"]
}`;

      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: prompt,
        config: {
          responseMimeType: "application/json"
        }
      });

      const responseText = response.text;
      if (responseText) {
        const parsed = JSON.parse(responseText.trim());
        generatedMetadata = {
          ...generatedMetadata,
          ...parsed,
          privacy: job.metadata?.privacy || "private"
        };
      }
    }
  } catch (error) {
    console.error("Error generating metadata with Gemini API:", error);
    generatedMetadata.title = `[Auto-Fix] Review ${job.title} - Bản Thuyết Minh Hay Nhất`;
  }

  const updatedJob: VideoJob = {
    ...job,
    metadata: generatedMetadata,
    logs: [
      ...job.logs,
      { time: new Date().toISOString(), level: "info", message: "Regenerated SEO Metadata via Gemini AI successfully." }
    ]
  };

  videoJobs[jobIndex] = updatedJob;
  broadcastJobsUpdate();
  res.json(updatedJob);
});

// Job action: Approve Upload / Metadata
app.post("/api/video-jobs/:id/approve-upload", (req, res) => {
  const { metadata } = req.body;
  const jobIndex = videoJobs.findIndex(j => j.id === req.params.id);
  if (jobIndex === -1) {
    return res.status(404).json({ error: "Job not found" });
  }

  const job = videoJobs[jobIndex];
  // Change status to approved, start watermark then upload
  const updatedJob: VideoJob = {
    ...job,
    status: "approved",
    progress: 85,
    metadata: metadata || job.metadata,
    current_step: "watermark",
    steps: {
      ...job.steps,
      seo_metadata: { status: "completed", progress: 100 },
      watermark: { status: "running", progress: 50 },
    },
    logs: [
      ...job.logs,
      { time: new Date().toISOString(), level: "info", message: "Admin approved metadata and authorized YouTube upload." },
      { time: new Date().toISOString(), level: "info", message: "Applying VidLocal watermark overlay..." }
    ]
  };

  videoJobs[jobIndex] = updatedJob;
  broadcastJobsUpdate();

  // Simulate watermark application & youtube uploading after 4 seconds
  setTimeout(() => {
    const freshJobIndex = videoJobs.findIndex(j => j.id === job.id);
    if (freshJobIndex !== -1) {
      const currJob = videoJobs[freshJobIndex];
      videoJobs[freshJobIndex] = {
        ...currJob,
        current_step: "upload",
        steps: {
          ...currJob.steps,
          watermark: { status: "completed", progress: 100 },
          upload: { status: "running", progress: 50 }
        },
        logs: [
          ...currJob.logs,
          { time: new Date().toISOString(), level: "info", message: "Watermark applied successfully. Uploading video stream to YouTube API..." }
        ]
      };
      broadcastJobsUpdate();
    }
  }, 4000);

  // Simulate completion after 8 seconds
  setTimeout(() => {
    const freshJobIndex = videoJobs.findIndex(j => j.id === job.id);
    if (freshJobIndex !== -1) {
      const currJob = videoJobs[freshJobIndex];
      videoJobs[freshJobIndex] = {
        ...currJob,
        status: "completed",
        progress: 100,
        current_step: "done",
        youtube_url: `https://youtube.com/watch?v=vid_${Math.random().toString(36).substr(2, 9)}`,
        steps: {
          ...currJob.steps,
          upload: { status: "completed", progress: 100 }
        },
        logs: [
          ...currJob.logs,
          { time: new Date().toISOString(), level: "info", message: "Uploaded successfully. Private video link published on channel." },
          { time: new Date().toISOString(), level: "info", message: "Cleaning up local yt-dlp workspace and cached segments." }
        ]
      };
      broadcastJobsUpdate();
    }
  }, 9000);

  res.json(updatedJob);
});

// Job Action: Cancel
app.post("/api/video-jobs/:id/cancel", (req, res) => {
  const jobIndex = videoJobs.findIndex(j => j.id === req.params.id);
  if (jobIndex === -1) {
    return res.status(404).json({ error: "Job not found" });
  }

  const job = videoJobs[jobIndex];
  const updatedJob: VideoJob = {
    ...job,
    status: "failed",
    logs: [
      ...job.logs,
      { time: new Date().toISOString(), level: "error", message: "Job cancelled by Admin." }
    ]
  };

  videoJobs[jobIndex] = updatedJob;
  broadcastJobsUpdate();
  res.json(updatedJob);
});

// Job Action: Retry
app.post("/api/video-jobs/:id/retry", (req, res) => {
  const jobIndex = videoJobs.findIndex(j => j.id === req.params.id);
  if (jobIndex === -1) {
    return res.status(404).json({ error: "Job not found" });
  }

  const job = videoJobs[jobIndex];
  const updatedJob: VideoJob = {
    ...job,
    status: "downloading",
    progress: 15,
    current_step: "download",
    steps: {
      download: { status: "running", progress: 15 },
      transcribe: { status: "pending", progress: 0 },
      character_extract: { status: "pending", progress: 0 },
      glossary_review: { status: "pending", progress: 0 },
      seo_metadata: { status: "pending", progress: 0 },
      watermark: { status: "pending", progress: 0 },
      upload: { status: "pending", progress: 0 }
    },
    logs: [
      ...job.logs,
      { time: new Date().toISOString(), level: "info", message: "Admin triggered retry. Re-queueing job..." }
    ]
  };

  videoJobs[jobIndex] = updatedJob;
  broadcastJobsUpdate();
  res.json(updatedJob);
});


// 2. Project Endpoints
app.get("/api/projects", (req, res) => {
  res.json(projects);
});

app.post("/api/projects", (req, res) => {
  const { name } = req.body;
  if (!name) {
    return res.status(400).json({ error: "Project name is required" });
  }

  const newProject: Project = {
    id: `p-${Date.now()}`,
    name,
    status: "pending",
    video_count: 0,
    created_time: new Date().toISOString(),
    current_step: "upload",
    steps: {
      upload: "pending",
      transcribe: "pending",
      translate: "pending",
      tts: "pending",
      render: "pending",
      publish: "pending"
    }
  };

  projects.unshift(newProject);
  res.status(201).json(newProject);
});

app.get("/api/projects/:id", (req, res) => {
  const project = projects.find(p => p.id === req.params.id);
  if (project) {
    res.json(project);
  } else {
    res.status(404).json({ error: "Project not found" });
  }
});

// Project pipeline steps
app.post("/api/projects/:id/upload", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.upload = "completed";
  projects[projIndex].status = "transcribing";
  projects[projIndex].current_step = "transcribe";
  projects[projIndex].steps.transcribe = "running";
  res.json(projects[projIndex]);
});

app.post("/api/projects/:id/import-url", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.upload = "completed";
  projects[projIndex].status = "transcribing";
  projects[projIndex].current_step = "transcribe";
  projects[projIndex].steps.transcribe = "running";
  res.json(projects[projIndex]);
});

app.post("/api/projects/:id/transcribe", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.transcribe = "completed";
  projects[projIndex].status = "translating";
  projects[projIndex].current_step = "translate";
  projects[projIndex].steps.translate = "running";
  res.json(projects[projIndex]);
});

app.post("/api/projects/:id/translate", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.translate = "completed";
  projects[projIndex].status = "tts";
  projects[projIndex].current_step = "tts";
  projects[projIndex].steps.tts = "running";
  res.json(projects[projIndex]);
});

app.post("/api/projects/:id/tts", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.tts = "completed";
  projects[projIndex].status = "rendering";
  projects[projIndex].current_step = "render";
  projects[projIndex].steps.render = "running";
  res.json(projects[projIndex]);
});

app.post("/api/projects/:id/render", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.render = "completed";
  projects[projIndex].status = "published";
  projects[projIndex].current_step = "publish";
  projects[projIndex].steps.publish = "running";
  res.json(projects[projIndex]);
});

app.post("/api/projects/:id/publish", (req, res) => {
  const projIndex = projects.findIndex(p => p.id === req.params.id);
  if (projIndex === -1) return res.status(404).json({ error: "Project not found" });

  projects[projIndex].steps.publish = "completed";
  projects[projIndex].status = "published";
  projects[projIndex].current_step = "done";
  projects[projIndex].video_count += 1;
  res.json(projects[projIndex]);
});


// 3. Global Glossary Endpoints
app.get("/api/glossary", (req, res) => {
  const projectId = req.query.project_id as string;
  if (projectId) {
    return res.json(globalGlossary.filter(g => g.project_id === projectId));
  }
  res.json(globalGlossary);
});

app.post("/api/glossary", (req, res) => {
  const { source_name, target_name, aliases, role, gender, family_clan, pronoun_style, notes, project_id } = req.body;
  if (!source_name || !target_name) {
    return res.status(400).json({ error: "Source name and target name are required" });
  }

  const newEntry: GlossaryEntry = {
    id: `g-${Date.now()}`,
    source_name,
    target_name,
    aliases: aliases || "",
    role: role || "",
    gender: gender || "",
    family_clan,
    pronoun_style: pronoun_style || "",
    notes: notes || "",
    project_id
  };

  globalGlossary.push(newEntry);
  res.status(201).json(newEntry);
});

app.delete("/api/glossary/:id", (req, res) => {
  const index = globalGlossary.findIndex(g => g.id === req.params.id);
  if (index !== -1) {
    globalGlossary.splice(index, 1);
    res.json({ success: true });
  } else {
    res.status(404).json({ error: "Glossary entry not found" });
  }
});


// 4. Integrations / Connections Status Endpoints
app.get("/api/connect", (req, res) => {
  res.json(systemSettings);
});

app.get("/api/connect/youtube/auth", (req, res) => {
  // Simulate auth toggle
  systemSettings.youtube_connected = !systemSettings.youtube_connected;
  if (systemSettings.youtube_connected) {
    systemSettings.youtube_account = "VidLocal Channel Official (verified@vidlocal.io)";
  } else {
    systemSettings.youtube_account = "";
  }
  res.json({ success: true, settings: systemSettings });
});

// Update system settings configuration
app.post("/api/settings/update", (req, res) => {
  systemSettings = {
    ...systemSettings,
    ...req.body
  };
  res.json(systemSettings);
});


// Setup Vite or Static Build Serving
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
