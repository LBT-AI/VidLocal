import { VideoJob, Project, GlossaryEntry, SystemSettings } from "../types";

const API_BASE = ""; // Same origin

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
  const jobs = await fetchWithTimeout(`${API_BASE}/api/jobs`).catch(() => []);
  jobs.sort((a: VideoJob, b: VideoJob) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime());
  return jobs;
}

export async function getJob(id: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/jobs/${id}`);
}

export async function createFacebookToYouTubeJob(url: string, options: any, title?: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/facebook-to-youtube`, {
    method: "POST",
    body: JSON.stringify({ url, options, title }),
  });
}

export async function createTikTokToYouTubeJob(url: string, options: any, title?: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/tiktok-to-youtube`, {
    method: "POST",
    body: JSON.stringify({ url, options, title }),
  });
}

export async function approveGlossary(jobId: string, glossary: GlossaryEntry[]): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/approve-glossary`, {
    method: "POST",
    body: JSON.stringify({ glossary }),
  });
}

export async function skipGlossary(jobId: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/skip-glossary`, {
    method: "POST",
  });
}

export async function regenerateMetadata(jobId: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/regenerate-metadata`, {
    method: "POST",
  });
}

export async function approveUpload(jobId: string, metadata: any): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/approve-upload`, {
    method: "POST",
    body: JSON.stringify({ metadata }),
  });
}

export async function cancelJob(jobId: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/cancel`, {
    method: "POST",
  });
}

export async function retryJob(jobId: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/retry`, {
    method: "POST",
  });
}

export async function getProjects(): Promise<Project[]> {
  return fetchWithTimeout(`${API_BASE}/api/projects`);
}

export async function createProject(name: string): Promise<Project> {
  return fetchWithTimeout(`${API_BASE}/api/projects`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function getProject(id: string): Promise<Project> {
  return fetchWithTimeout(`${API_BASE}/api/projects/${id}`);
}

export async function triggerProjectStep(id: string, step: string): Promise<Project> {
  // maps to /api/projects/{id}/upload, /api/projects/{id}/transcribe, etc.
  return fetchWithTimeout(`${API_BASE}/api/projects/${id}/${step}`, {
    method: "POST",
  });
}

export async function getGlossary(projectId?: string): Promise<GlossaryEntry[]> {
  const url = projectId ? `${API_BASE}/api/glossary?project_id=${projectId}` : `${API_BASE}/api/glossary`;
  return fetchWithTimeout(url);
}

export async function createGlossaryEntry(entry: Partial<GlossaryEntry>): Promise<GlossaryEntry> {
  return fetchWithTimeout(`${API_BASE}/api/glossary`, {
    method: "POST",
    body: JSON.stringify(entry),
  });
}

export async function deleteGlossaryEntry(id: string): Promise<{ success: boolean }> {
  return fetchWithTimeout(`${API_BASE}/api/glossary/${id}`, {
    method: "DELETE",
  });
}

export async function getConnectSettings(): Promise<SystemSettings> {
  return fetchWithTimeout(`${API_BASE}/api/connect`);
}

export async function toggleYoutubeAuth(): Promise<{ success: boolean; settings: SystemSettings }> {
  return fetchWithTimeout(`${API_BASE}/api/connect/youtube/auth`);
}

export async function updateSystemSettings(settings: Partial<SystemSettings>): Promise<SystemSettings> {
  return fetchWithTimeout(`${API_BASE}/api/settings/update`, {
    method: "POST",
    body: JSON.stringify(settings),
  });
}

// --- New simulated API calls for user specified features ---
export async function getFiles(): Promise<Record<string, Array<{name: string, size: string, date: string}>>> {
  return fetchWithTimeout(`${API_BASE}/api/files`);
}

export async function uploadFile(folder: string, name: string, size: string): Promise<{ success: boolean, files: any }> {
  return fetchWithTimeout(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: JSON.stringify({ folder, name, size })
  });
}

export async function deleteFile(folder: string, name: string): Promise<{ success: boolean, files: any }> {
  return fetchWithTimeout(`${API_BASE}/api/files/${folder}/${name}`, {
    method: "DELETE"
  });
}

export async function getQueues(): Promise<Record<string, {active: number, queued: number, status: string}>> {
  return fetchWithTimeout(`${API_BASE}/api/queues`);
}

export async function triggerQueueAction(queueName: string, action: string): Promise<{ success: boolean, queues: any }> {
  return fetchWithTimeout(`${API_BASE}/api/queues/${queueName}/${action}`, {
    method: "POST"
  });
}

export async function getBotStatus(): Promise<{ username: string, webhook: string, status: string, polling: string, commands: Array<{command: string, description: string}> }> {
  return fetchWithTimeout(`${API_BASE}/api/bot-status`);
}

export async function triggerBotAction(action: string): Promise<{ success: boolean, bot: any }> {
  return fetchWithTimeout(`${API_BASE}/api/bot-status/action`, {
    method: "POST",
    body: JSON.stringify({ action })
  });
}

export async function getAiServices(): Promise<{ gemini: { status: string, tokenUsage: number, requestsToday: number }, whisper: { status: string, gpuUsage: number, speed: string }, deeplx: { status: string, requests: number, limit: number } }> {
  return fetchWithTimeout(`${API_BASE}/api/ai-services`);
}

export async function getSystemLogs(): Promise<Array<{ time: string, level: string, section: string, message: string }>> {
  return fetchWithTimeout(`${API_BASE}/api/logs`);
}

export async function postAiChat(message: string, jobId?: string): Promise<{ response: string }> {
  return fetchWithTimeout(`${API_BASE}/api/ai-chat`, {
    method: "POST",
    body: JSON.stringify({ message, jobId })
  });
}

export async function generateThumbnailPrompts(jobId: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/thumbnail-prompts`, {
    method: "POST"
  });
}

export async function uploadThumbnailImage(jobId: string, image: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/thumbnail-upload`, {
    method: "POST",
    body: JSON.stringify({ image })
  });
}

export async function skipThumbnail(jobId: string): Promise<VideoJob> {
  return fetchWithTimeout(`${API_BASE}/api/video-jobs/${jobId}/thumbnail-skip`, {
    method: "POST"
  });
}

export function subscribeToJobs(onMessage: (jobs: VideoJob[]) => void, onError?: (err: any) => void) {
  const eventSource = new EventSource(`${API_BASE}/api/jobs/stream`);
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      // Sort desc by created_time like getJobs does
      data.sort((a: VideoJob, b: VideoJob) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime());
      onMessage(data);
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
