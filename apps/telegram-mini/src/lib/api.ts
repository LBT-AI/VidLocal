import { VideoJob, Project, GlossaryEntry, SystemSettings } from "../types";

const API_BASE = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL
  : '';

export async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 8000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
    clearTimeout(id);
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

export async function getJobs(): Promise<VideoJob[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs`).catch(() => ({ data: [] }));
  const jobs: VideoJob[] = (res.data || []);
  jobs.sort((a: VideoJob, b: VideoJob) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime());
  return jobs;
}

export async function getJob(id: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${id}`);
  return res.data;
}

export async function createFacebookToYouTubeJob(url: string, options: any, title?: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs`, {
    method: "POST",
    body: JSON.stringify({ url, platform: "facebook", options, title }),
  });
  return res.data;
}

export async function createTikTokToYouTubeJob(url: string, options: any, title?: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs`, {
    method: "POST",
    body: JSON.stringify({ url, platform: "tiktok", options, title }),
  });
  return res.data;
}

export async function approveGlossary(jobId: string, glossary: GlossaryEntry[]): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/approve-glossary`, {
    method: "POST",
    body: JSON.stringify({ glossary }),
  });
  return res.data;
}

export async function skipGlossary(jobId: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/skip-glossary`, {
    method: "POST",
  });
  return res.data;
}

export async function regenerateMetadata(jobId: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/regenerate-metadata`, {
    method: "POST",
  });
  return res.data;
}

export async function approveUpload(jobId: string, metadata: any): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/approve-upload`, {
    method: "POST",
    body: JSON.stringify({ metadata }),
  });
  return res.data;
}

export async function cancelJob(jobId: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/cancel`, {
    method: "POST",
  });
  return res.data;
}

export async function retryJob(jobId: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/retry`, {
    method: "POST",
  });
  return res.data;
}

export async function getProjects(): Promise<Project[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/projects`);
  return res.data || [];
}

export async function createProject(name: string): Promise<Project> {
  const res = await fetchWithTimeout(`${API_BASE}/api/projects`, {
    method: "POST",
    body: JSON.stringify({ title: name }),
  });
  return res.data;
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetchWithTimeout(`${API_BASE}/api/projects/${id}`);
  return res.data;
}

export async function triggerProjectStep(id: string, step: string): Promise<Project> {
  const res = await fetchWithTimeout(`${API_BASE}/api/projects/${id}/${step}`, {
    method: "POST",
  });
  return res.data;
}

export async function getGlossary(projectId?: string): Promise<GlossaryEntry[]> {
  const url = projectId ? `${API_BASE}/api/glossary?project_id=${projectId}` : `${API_BASE}/api/glossary`;
  const res = await fetchWithTimeout(url);
  return res.data || [];
}

export async function createGlossaryEntry(entry: Partial<GlossaryEntry>): Promise<GlossaryEntry> {
  const res = await fetchWithTimeout(`${API_BASE}/api/glossary`, {
    method: "POST",
    body: JSON.stringify(entry),
  });
  return res.data;
}

export async function deleteGlossaryEntry(id: string): Promise<{ success: boolean }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/glossary/${id}`, {
    method: "DELETE",
  });
  return res.data;
}

export async function getConnectSettings(): Promise<SystemSettings> {
  const res = await fetchWithTimeout(`${API_BASE}/api/connect`);
  return res.data;
}

export async function toggleYoutubeAuth(): Promise<{ success: boolean; settings: SystemSettings }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/connect/youtube/auth`);
  return { success: true, settings: res.data };
}

export async function updateSystemSettings(settings: Partial<SystemSettings>): Promise<SystemSettings> {
  const res = await fetchWithTimeout(`${API_BASE}/api/settings/update`, {
    method: "POST",
    body: JSON.stringify(settings),
  });
  return res.data;
}

export async function getFiles(): Promise<Record<string, Array<{name: string, size: string, date: string}>>> {
  const res = await fetchWithTimeout(`${API_BASE}/api/files`).catch(() => ({ data: {} }));
  return res.data || {};
}

export async function uploadFile(folder: string, name: string, size: string): Promise<{ success: boolean, files: any }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: JSON.stringify({ folder, name, size })
  }).catch(() => ({ data: { success: false, files: [] } }));
  return res.data || { success: false, files: [] };
}

export async function deleteFile(folder: string, name: string): Promise<{ success: boolean, files: any }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/files/${folder}/${name}`, {
    method: "DELETE"
  }).catch(() => ({ data: { success: false, files: [] } }));
  return res.data || { success: false, files: [] };
}

export async function getQueues(): Promise<Record<string, {active: number, queued: number, status: string}>> {
  const res = await fetchWithTimeout(`${API_BASE}/api/queues`).catch(() => ({ data: {} }));
  return res.data || {};
}

export async function triggerQueueAction(queueName: string, action: string): Promise<{ success: boolean, queues: any }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/queues/${queueName}/${action}`, {
    method: "POST"
  }).catch(() => ({ data: { success: false, queues: {} } }));
  return res.data || { success: false, queues: {} };
}

export async function getBotStatus(): Promise<{ username: string, webhook: string, status: string, polling: string, commands: Array<{command: string, description: string}> }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/bot-status`).catch(() => ({ data: { username: "", webhook: "", status: "unknown", polling: "", commands: [] } }));
  return res.data || { username: "", webhook: "", status: "unknown", polling: "", commands: [] };
}

export async function triggerBotAction(action: string): Promise<{ success: boolean, bot: any }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/bot-status/action`, {
    method: "POST",
    body: JSON.stringify({ action })
  }).catch(() => ({ data: { success: false, bot: {} } }));
  return res.data || { success: false, bot: {} };
}

export async function getAiServices(): Promise<{ gemini: { status: string, tokenUsage: number, requestsToday: number }, whisper: { status: string, gpuUsage: number, speed: string }, deeplx: { status: string, requests: number, limit: number } }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/ai-services`).catch(() => ({ data: {} }));
  return res.data || {};
}

export async function getSystemLogs(): Promise<Array<{ time: string, level: string, section: string, message: string }>> {
  const res = await fetchWithTimeout(`${API_BASE}/api/logs`).catch(() => ({ data: [] }));
  return res.data || [];
}

export async function postAiChat(message: string, jobId?: string): Promise<{ response: string }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/ai-chat`, {
    method: "POST",
    body: JSON.stringify({ message, jobId })
  }).catch(() => ({ data: { response: "AI chat not available" } }));
  return res.data || { response: "AI chat not available" };
}

export async function generateThumbnailPrompts(jobId: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/thumbnail-prompts`, {
    method: "POST"
  });
  return res.data;
}

export async function uploadThumbnailImage(jobId: string, image: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/thumbnail-upload`, {
    method: "POST",
    body: JSON.stringify({ image })
  });
  return res.data;
}

export async function skipThumbnail(jobId: string): Promise<VideoJob> {
  const res = await fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/thumbnail-skip`, {
    method: "POST"
  });
  return res.data;
}

export function subscribeToJobs(onMessage: (jobs: VideoJob[]) => void, onError?: (err: any) => void) {
  const eventSource = new EventSource(`${API_BASE}/api/jobs/stream`);
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (Array.isArray(data)) {
        data.sort((a: VideoJob, b: VideoJob) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime());
        onMessage(data);
      } else if (data.data && Array.isArray(data.data)) {
        data.data.sort((a: VideoJob, b: VideoJob) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime());
        onMessage(data.data);
      }
    } catch (e) {
      console.error("Failed to parse SSE jobs data:", e);
    }
  };
  eventSource.onerror = (error) => {
    if (onError) onError(error);
  };
  return () => {
    eventSource.close();
  };
}
