import express from 'express';
import path from 'path';
import fs from 'fs';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(express.json({ limit: '10mb' }));

const tempDirPath = path.join(process.cwd(), 'temp_dir');
if (!fs.existsSync(tempDirPath)) {
  fs.mkdirSync(tempDirPath, { recursive: true });
}
app.use('/temp_dir', express.static(tempDirPath));

// In-memory database
interface Project {
  id: string; title?: string; source_url?: string; source_platform?: string;
  target_platform: string; status: string; progress: number;
  source_file_path?: string; transcript?: string; transcript_language?: string;
  ai_title?: string; ai_description?: string; ai_tags?: string; ai_hashtags?: string;
  ai_category?: string; ai_summary?: string; ai_hook?: string; risk_flags?: string;
  metadata_status: string; glossary_status: string; glossary_draft_id?: string;
  thumbnail_status: string; thumbnail_path?: string; thumbnail_prompts?: string;
  thumbnail_reference_frames?: string; selected_thumbnail_reference?: number;
  youtube_url?: string; admin_chat_id?: string; telegram_message_id?: number;
  error_message?: string; duration_seconds?: number;
  created_at: string; updated_at?: string;
}

interface GlossaryEntry {
  id: string; source_name: string; target_name: string; aliases: string;
  role: string; gender: string; family_clan?: string; pronoun_style: string;
  notes: string; project_id?: string;
}

interface BotLog { timestamp: string; level: string; message: string; }

const projects = new Map<string, Project>();
const glossaryStore = new Map<string, GlossaryEntry>();
const botLogs: BotLog[] = [];
const connections: any[] = [];

let aiClient: GoogleGenAI | null = null;
if (process.env.GEMINI_API_KEY) {
  aiClient = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
}

function generateId(): string { return crypto.randomUUID(); }

function addLog(level: string, message: string) {
  botLogs.push({ timestamp: new Date().toISOString(), level, message });
  if (botLogs.length > 1000) botLogs.splice(0, botLogs.length - 1000);
}

function simulateProgress(id: string) {
  const job = projects.get(id);
  if (!job) return;
  job.status = 'processing';
  const steps = [
    { at: 10, status: 'download' }, { at: 25, status: 'transcribe' },
    { at: 45, status: 'glossary' }, { at: 60, status: 'metadata' },
    { at: 80, status: 'thumbnail' }, { at: 95, status: 'ready' },
  ];
  let stepIdx = 0;
  const interval = setInterval(() => {
    if (!projects.has(id)) { clearInterval(interval); return; }
    const j = projects.get(id)!;
    if (stepIdx < steps.length) {
      j.progress = steps[stepIdx].at;
      addLog('info', `Job ${id.slice(0, 8)}: ${steps[stepIdx].status}`);
      stepIdx++;
    } else {
      j.progress = 100; j.status = 'completed';
      j.ai_title = `Video #${id.slice(0, 4)}`;
      j.ai_description = 'AI-generated description optimized for YouTube SEO.';
      j.ai_tags = JSON.stringify(['video', 'trending', 'viral']);
      j.ai_hashtags = JSON.stringify(['#viral', '#trending']);
      j.ai_category = '22';
      j.ai_summary = 'AI-generated summary';
      j.ai_hook = 'Amazing hook!';
      j.metadata_status = 'generated';
      j.thumbnail_status = 'generated';
      j.thumbnail_prompts = JSON.stringify([
        { style: 'Drama', prompt: 'Dramatic scene with intense lighting and shadows, cinematic composition' },
        { style: 'Review phim', prompt: 'Movie poster style, bold typography, dark background, golden accents' },
        { style: 'Xianxia/Anime', prompt: 'Epic fantasy landscape, floating islands, ethereal glow, ancient temples' },
        { style: 'Viral CTR', prompt: 'High contrast, shocked expression, red circle, arrow pointing, bright colors' },
      ]);
      clearInterval(interval);
    }
  }, 2000);
}

// === API Routes ===

app.get('/api/jobs', (req, res) => {
  const page = parseInt(req.query.page as string) || 1;
  const limit = parseInt(req.query.limit as string) || 20;
  const status = req.query.status as string;
  let items = Array.from(projects.values());
  if (status) items = items.filter(j => j.status === status);
  items.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  const start = (page - 1) * limit;
  res.json({ data: items.slice(start, start + limit), total: items.length, page, limit });
});

app.get('/api/jobs/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  const send = () => {
    const items = Array.from(projects.values()).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    res.write(`data: ${JSON.stringify(items)}\n\n`);
  };
  send();
  const interval = setInterval(send, 3000);
  req.on('close', () => clearInterval(interval));
});

app.get('/api/jobs/:id', (req, res) => {
  const job = projects.get(req.params.id);
  if (!job) return res.status(404).json({ error: 'Job not found' });
  res.json(job);
});

app.post('/api/facebook-to-youtube', (req, res) => {
  const { url } = req.body;
  if (!url) return res.status(400).json({ error: 'URL is required' });
  const id = generateId();
  projects.set(id, {
    id, source_url: url, source_platform: 'facebook', target_platform: 'youtube',
    status: 'pending', progress: 0, metadata_status: 'pending',
    glossary_status: 'pending', thumbnail_status: 'pending',
    created_at: new Date().toISOString(),
  });
  simulateProgress(id);
  res.status(201).json(projects.get(id));
});

app.post('/api/tiktok-to-youtube', (req, res) => {
  const { url } = req.body;
  if (!url) return res.status(400).json({ error: 'URL is required' });
  const id = generateId();
  projects.set(id, {
    id, source_url: url, source_platform: 'tiktok', target_platform: 'youtube',
    status: 'pending', progress: 0, metadata_status: 'pending',
    glossary_status: 'pending', thumbnail_status: 'pending',
    created_at: new Date().toISOString(),
  });
  simulateProgress(id);
  res.status(201).json(projects.get(id));
});

app.post('/api/video-jobs/:id/approve-glossary', (req, res) => {
  const job = projects.get(req.params.id);
  if (!job) return res.status(404).json({ error: 'Job not found' });
  job.glossary_status = 'approved';
  res.json({ success: true });
});

app.post('/api/video-jobs/:id/skip-glossary', (req, res) => {
  const job = projects.get(req.params.id);
  if (!job) return res.status(404).json({ error: 'Job not found' });
  job.glossary_status = 'skipped';
  res.json({ success: true });
});

app.post('/api/video-jobs/:id/approve-upload', (req, res) => {
  const job = projects.get(req.params.id);
  if (!job) return res.status(404).json({ error: 'Job not found' });
  job.status = 'approved';
  job.metadata_status = 'approved';
  job.youtube_url = `https://youtube.com/watch?v=${generateId().slice(0, 11)}`;
  res.json({ success: true, youtube_url: job.youtube_url });
});

app.post('/api/video-jobs/:id/cancel', (req, res) => {
  const job = projects.get(req.params.id);
  if (!job) return res.status(404).json({ error: 'Job not found' });
  job.status = 'cancelled';
  job.metadata_status = 'rejected';
  res.json({ success: true });
});

app.get('/api/glossary', (req, res) => {
  res.json(Array.from(glossaryStore.values()));
});

app.post('/api/glossary', (req, res) => {
  const entry: GlossaryEntry = { id: generateId(), ...req.body };
  glossaryStore.set(entry.id, entry);
  res.status(201).json(entry);
});

app.delete('/api/glossary/:id', (req, res) => {
  res.json({ success: glossaryStore.delete(req.params.id) });
});

app.get('/api/connect', (req, res) => res.json(connections));

app.get('/api/bot-status', (req, res) => {
  res.json({
    running: true, uptime: process.uptime(),
    jobs_active: Array.from(projects.values()).filter(j => j.status === 'processing').length,
    jobs_queued: Array.from(projects.values()).filter(j => j.status === 'pending').length,
    last_logs: botLogs.slice(-50),
  });
});

app.get('/api/logs', (req, res) => res.json(botLogs.slice(-200)));

app.get('/api/ai-services', (req, res) => {
  res.json({ gemini: !!aiClient, models: ['gemini-2.5-flash'], default_model: 'gemini-2.5-flash' });
});

// Serve static files in production
const distPath = path.join(process.cwd(), 'dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    if (!req.path.startsWith('/api/')) {
      res.sendFile(path.join(distPath, 'index.html'));
    }
  });
}

export default app;
