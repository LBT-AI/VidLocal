export interface GlossaryEntry {
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

export interface SEOMetadata {
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

export interface VideoJob {
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
  thumbnail?: {
    prompts?: string[];
    image_url?: string;
    status?: "pending" | "approved" | "skipped";
  };
}

export interface Project {
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

export interface SystemSettings {
  youtube_connected: boolean;
  youtube_account: string;
  r2_status: string;
  r2_bucket: string;
  ai_provider: string;
  whisper_model: string;
  watermark_config: string;
  tts_voice: string;
  default_privacy: string;
  cleanup_retention: string;
}
