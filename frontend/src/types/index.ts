export interface Project {
  id: string;
  title: string;
  status: string;
  source_url?: string;
  original_video_path?: string;
  audio_path?: string;
  zh_srt_path?: string;
  vi_srt_path?: string;
  final_video_path?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface SubtitleCue {
  id: number;
  cue_index: number;
  start_ms: number;
  end_ms: number;
  zh_text?: string;
  vi_text?: string;
  cps?: number;
  status: string;
}

export interface TTSSegment {
  id: number;
  cue_index: number;
  audio_path?: string;
  duration_ms?: number;
  sync_status: string;
}
